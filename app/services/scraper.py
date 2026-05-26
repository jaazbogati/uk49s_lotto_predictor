import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
import os
from datetime import datetime
from fake_useragent import UserAgent
from sqlalchemy.dialects.postgresql import insert
from app.core.database import SessionLocal, init_db
from app.models.draw_model import Draw

# ── Config ────────────────────────────────────────────────────

BASE_URL   = "https://www.lotteryextreme.com/49s/results"
START_YEAR = 2020
END_YEAR   = datetime.now().year

CSV_BACKUP = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "uk49s_results.csv"
)

MONTHS = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]

MONTH_NUM = {m: i + 1 for i, m in enumerate(MONTHS)}

ua      = UserAgent()
session = requests.Session()

# ── Regex ─────────────────────────────────────────────────────
#
# Debug revealed the <td class="xgame"> cell contains ALL draws
# for the month as plain text in this exact format:
#   "Thursday 1 October 2020  Lunchtime 1 11 31 41 46 49 5
#    Thursday 1 October 2020  Teatime 5 9 15 19 42 46 36 ..."
#
# Both draw types appear as text here (unlike the visible page
# where Lunchtime is an image). Everything we need is in the text.

_DAYS_PAT   = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
_MONTHS_ALT = (
    r"January|February|March|April|May|June|July|August"
    r"|September|October|November|December"
)
_TYPES_ALT  = r"Brunchtime|Lunchtime|Drivetime|Teatime"

# Full draw pattern — matches one complete draw in the cell text
_DRAW_FULL_RE = re.compile(
    rf"{_DAYS_PAT}\s+"                              # Day name (consumed, not captured)
    rf"(?P<day>\d{{1,2}})\s+"                       # Day number
    rf"(?P<month>{_MONTHS_ALT})\s+"                 # Month name
    rf"(?P<year>\d{{4}})\s+"                        # Year
    rf"(?P<draw_type>{_TYPES_ALT})?\s*"             # Draw type (optional — safety net)
    rf"(?P<nums>(?:\d{{1,2}}\s+){{6}}\d{{1,2}})"   # 7 space-separated numbers
)

MONTH_NUM = {m: i + 1 for i, m in enumerate([
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
])}

# ── Request Helpers ───────────────────────────────────────────

def get_headers():
    return {
        "User-Agent":                ua.random,
        "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language":           "en-US,en;q=0.5",
        "Accept-Encoding":           "gzip, deflate",
        "Content-Type":              "application/x-www-form-urlencoded",
        "Origin":                    "https://www.lotteryextreme.com",
        "Referer":                   BASE_URL,
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def fetch_page(year, month_name, retries=3):
    """
    POST to LotteryExtreme with the correct field names discovered
    via diagnose_form():
      tryb   = 'rokmsc'  → year+month filter mode
      _year  = '2024'    → underscore prefix, numeric string
      _month = '3'       → numeric month, NOT the name
    """
    month_num = str(MONTHS.index(month_name) + 1)

    form_data = {
        "tryb":   "rokmsc",
        "_year":  str(year),
        "_month": month_num,
    }

    for attempt in range(retries):
        try:
            delay = random.uniform(2, 4)
            print(f"    [WAIT] {delay:.1f}s...")
            time.sleep(delay)

            resp = session.post(
                BASE_URL,
                data=form_data,
                headers=get_headers(),
                timeout=15
            )
            resp.raise_for_status()
            return resp.text

        except requests.RequestException as e:
            print(f"    [ERROR] Attempt {attempt + 1}/{retries}: {e}")
            time.sleep(random.uniform(3, 6))

    print(f"    [FAILED] Could not fetch {month_name} {year}")
    return None

# ── Validation ────────────────────────────────────────────────

def is_valid_draw(numbers):
    if len(numbers) != 6:
        return False
    if len(set(numbers)) != 6:
        return False
    if not all(1 <= n <= 49 for n in numbers):
        return False
    return True

# ── Parser ────────────────────────────────────────────────────

def parse_html(raw_text, expected_year=None, expected_month=None):
    """
    What the debug revealed:

    The <td class="xgame"> cell contains the ENTIRE month's draws
    as a single block of plain text. Numbers are inline, not in a
    separate row. The structure we assumed (sibling <tr> with balls)
    doesn't exist — everything is already here.

    Strategy:
    - Find the first <td class="xgame"> (it holds all month data)
    - Run _DRAW_FULL_RE.finditer() on its text
    - Each match is one complete draw: date + type + 7 numbers
    """
    soup    = BeautifulSoup(raw_text, "html.parser")
    results = []
    seen    = set()

    # find() returns the first match — the outer container with all data
    xgame_cell = soup.find("td", class_="xgame")

    if not xgame_cell:
        print("    [WARN] No xgame cell found on page")
        return results

    cell_text = xgame_cell.get_text(" ", strip=True)
    matches   = list(_DRAW_FULL_RE.finditer(cell_text))
    print(f"    [INFO] Found {len(matches)} draw pattern matches")

    for match in matches:
        day_str    = match.group("day")
        month_name = match.group("month")
        year_str   = match.group("year")
        draw_type  = match.group("draw_type") or "Lunchtime"
        nums_str   = match.group("nums")

        # ── Build date ────────────────────────────────────────
        try:
            date_obj = datetime(
                int(year_str),
                MONTH_NUM[month_name],
                int(day_str)
            ).date()
        except (ValueError, KeyError):
            continue

        # ── Filter to requested period ────────────────────────
        if expected_year  and date_obj.year  != expected_year:
            continue
        if expected_month and date_obj.month != MONTH_NUM[expected_month]:
            continue

        # ── Deduplicate ───────────────────────────────────────
        key = (date_obj, draw_type)
        if key in seen:
            continue
        seen.add(key)

        # ── Split numbers and booster ─────────────────────────
        all_nums = [int(n) for n in nums_str.split()]
        booster  = None

        if len(all_nums) == 7:
            booster  = all_nums[6]
            numbers  = all_nums[:6]
        else:
            numbers  = all_nums

        # ── Validate ──────────────────────────────────────────
        if not is_valid_draw(numbers):
            print(f"    [SKIP] {date_obj} {draw_type} → {numbers}")
            continue

        results.append({
            "date":      date_obj,
            "draw_type": draw_type,
            "source":    "LotteryExtreme",
            "n1": numbers[0], "n2": numbers[1], "n3": numbers[2],
            "n4": numbers[3], "n5": numbers[4], "n6": numbers[5],
            "booster":   booster
        })

    return results

# ── Database ──────────────────────────────────────────────────

def save_to_db(results):
    if not results:
        return 0

    db       = SessionLocal()
    inserted = 0

    try:
        for row in results:
            stmt = (
                insert(Draw)
                .values(**row)
                .on_conflict_do_nothing(index_elements=["date", "draw_type"])
            )
            result   = db.execute(stmt)
            inserted += result.rowcount

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"    [DB ERROR] {e}")

    finally:
        db.close()

    return inserted

# ── CSV Backup ────────────────────────────────────────────────

def save_csv_backup(results):
    if not results:
        return

    os.makedirs(os.path.dirname(CSV_BACKUP), exist_ok=True)
    df = pd.DataFrame(results)

    if os.path.exists(CSV_BACKUP):
        existing = pd.read_csv(CSV_BACKUP)
        existing["date"] = pd.to_datetime(existing["date"]).dt.date  # ← fixes the type
        df = pd.concat([existing, df]).drop_duplicates(subset=["date", "draw_type"])

    df.sort_values("date", ascending=False, inplace=True)
    df.to_csv(CSV_BACKUP, index=False)
    print(f"    [CSV] Backup saved → {CSV_BACKUP}")

# ── Main ──────────────────────────────────────────────────────

def run_scraper():
    total_processed = 0
    total_inserted  = 0

    for year in range(START_YEAR, END_YEAR + 1):
        for month in MONTHS:

            now = datetime.now()
            if year == now.year and MONTHS.index(month) >= now.month:
                break

            print(f"\n  [{year} - {month}]")
            raw_text = fetch_page(year, month)

            if not raw_text:
                continue

            results = parse_html(
                raw_text,
                expected_year=year,
                expected_month=month
            )
            total_processed += len(results)

            if results:
                inserted       = save_to_db(results)
                total_inserted += inserted
                save_csv_backup(results)
                print(f"    ✓ {len(results)} parsed | {inserted} new inserted")
            else:
                print(f"    [WARN] 0 valid draws for {month} {year}")

    print(f"\n{'='*60}")
    print(f"✅ Done — {total_processed} processed | {total_inserted} inserted")
    print(f"{'='*60}")
    
     # ── Auto-score pending predictions after every scrape ─────
    # Any predictions whose draw date is now in the DB will be scored
    try:
        from app.services.outcome_tracker import score_pending_predictions
        print("\n[SCORING] Checking for pending predictions to score...")
        result = score_pending_predictions()
        if result["scored"] > 0:
            print(f"[SCORING] ✅ Scored {result['scored']} predictions")
        elif result["pending_found"] > 0:
            print(f"[SCORING] ⚠️ Found {result['pending_found']} pending but couldn't score — draw data may not be available yet")
        else:
            print(f"[SCORING] No pending predictions found")
    except Exception as e:
        print(f"[SCORING ERROR] {e}")
# ── Entry Point ───────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🎰 UK49s Scraper\n")
    init_db()
    run_scraper()