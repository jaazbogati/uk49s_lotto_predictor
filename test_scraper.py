from app.services.scraper import fetch_page, parse_html
from datetime import datetime

print("Testing scraper connection...")

raw = fetch_page(datetime.now().year, "May")

if raw:
    results = parse_html(raw)
    print(f"✅ Scraper connected — found {len(results)} draws on latest page")
    if results:
        print(f"   First draw: {results[0]['date']} {results[0]['draw_type']}")
        print(f"   Numbers:    {[results[0][f'n{i}'] for i in range(1,7)]}")
else:
    print("❌ Scraper failed to connect")