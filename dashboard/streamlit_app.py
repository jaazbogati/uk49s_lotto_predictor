"""
Phase 8 — Streamlit Internal Analytics Dashboard
──────────────────────────────────────────────────
Internal tool for exploring the data visually.
Not the public-facing UI — that's the React frontend.

Run with:
  streamlit run dashboard/streamlit_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# ── Path setup ─────────────────────────────────────────────────
# Streamlit runs from its own working directory.
# We add the project root to sys.path so imports work correctly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.frequency_engine import (
    load_draws, compute_frequency, compute_gaps,
    compute_frequency_score, compute_rolling
)
from app.services.stats_engine import (
    test_randomness, test_draw_independence
)
from app.services.predictor import generate_predictions, score_numbers

# ── Page Config ────────────────────────────────────────────────

st.set_page_config(
    page_title = "UK49s Analytics",
    page_icon  = "🎰",
    layout     = "wide"
)

# ── Sidebar ────────────────────────────────────────────────────

st.sidebar.title("🎰 UK49s Analytics")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Overview", "📈 Frequency Analysis", "🔬 Statistical Tests", "🎯 Predictions",
      "📉 Backtest Results"]
)

draw_type = st.sidebar.selectbox(
    "Draw Type",
    ["Lunchtime", "Teatime"]
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ Statistical tests confirm all draws are random. "
    "No analysis method improves your odds. "
    "For entertainment and education only."
)

# ── Data Loading ───────────────────────────────────────────────
# Cache the data load so navigating between pages is instant

@st.cache_data(ttl=300)   # Refresh every 5 minutes
def get_draws(dt):
    return load_draws(dt)

@st.cache_data(ttl=300)
def get_frequency(dt):
    df = get_draws(dt)
    return compute_frequency(df)

@st.cache_data(ttl=300)
def get_gaps(dt):
    df = get_draws(dt)
    return compute_gaps(df)

@st.cache_data(ttl=300)
def get_scores(dt):
    df = get_draws(dt)
    return compute_frequency_score(df)

@st.cache_data(ttl=300)
def get_rolling(dt):
    df = get_draws(dt)
    return compute_rolling(df, days=90)

# ── Page 1: Overview ───────────────────────────────────────────

if page == "📊 Overview":
    st.title("📊 UK49s — Data Overview")
    st.markdown(f"**Draw type:** {draw_type}")

    df = get_draws(draw_type)

    # ── Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Draws",   f"{len(df):,}")
    col2.metric("Date From",     str(df["date"].min().date()))
    col3.metric("Date To",       str(df["date"].max().date()))
    col4.metric("Years Covered", f"{(df['date'].max() - df['date'].min()).days // 365}")

    st.markdown("---")

    # ── Recent draws table
    st.subheader("📋 Most Recent Draws")
    recent = df.sort_values("date", ascending=False).head(20)
    recent["numbers"] = recent[["n1","n2","n3","n4","n5","n6"]].apply(
        lambda r: " · ".join(str(n) for n in sorted(r)), axis=1
    )
    st.dataframe(
        recent[["date", "draw_type", "numbers", "booster"]],
        use_container_width=True,
        hide_index=True
    )

    # ── Draws per month chart
    st.markdown("---")
    st.subheader("📅 Draws Per Month")
    df["month"] = df["date"].dt.to_period("M").astype(str)
    monthly = df.groupby("month").size().reset_index(name="count")

    fig = px.bar(
        monthly, x="month", y="count",
        color_discrete_sequence=["#4F86C6"],
        labels={"month": "Month", "count": "Draws"}
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Page 2: Frequency Analysis ─────────────────────────────────

elif page == "📈 Frequency Analysis":
    st.title("📈 Frequency Analysis")
    st.markdown(f"**Draw type:** {draw_type}")
    st.markdown(
        "How often each number appeared historically. "
        "Deviations from expected are normal in any finite random dataset."
    )

    freq   = get_frequency(draw_type)
    scores = get_scores(draw_type)
    gaps   = get_gaps(draw_type)

    # ── Frequency bar chart
    st.subheader("🔢 Appearance Count — All Numbers")

    # Colour bars by hot/cold status
    freq_sorted = freq.sort_values("number")
    colors = freq_sorted["status"].map({
        "🔥 Hot":     "#E05C5C",
        "🧊 Cold":    "#5C9BE0",
        "➖ Neutral": "#A0A0A0"
    })

    fig = go.Figure(go.Bar(
        x     = freq_sorted["number"],
        y     = freq_sorted["count"],
        marker_color = colors.tolist(),
        text  = freq_sorted["count"],
        textposition = "outside"
    ))
    fig.add_hline(
        y=freq_sorted["expected"].iloc[0],
        line_dash="dash",
        line_color="orange",
        annotation_text="Expected (random)"
    )
    fig.update_layout(
        xaxis_title  = "Number",
        yaxis_title  = "Appearances",
        plot_bgcolor = "rgba(0,0,0,0)",
        paper_bgcolor= "rgba(0,0,0,0)",
        showlegend   = False
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Heatmap — numbers 1–49 in a 7×7 grid
    st.subheader("🌡️ Frequency Heatmap")
    st.caption("Darker = appeared more often. Every number should be similar in a fair draw.")

    freq_dict  = dict(zip(freq["number"], freq["count"]))
    grid_data  = []
    grid_text  = []

    for row in range(7):
        data_row = []
        text_row = []
        for col in range(7):
            num = row * 7 + col + 1
            if num <= 49:
                data_row.append(freq_dict.get(num, 0))
                text_row.append(str(num))
            else:
                data_row.append(None)
                text_row.append("")
        grid_data.append(data_row)
        grid_text.append(text_row)

    fig2 = go.Figure(go.Heatmap(
        z           = grid_data,
        text        = grid_text,
        texttemplate= "%{text}",
        colorscale  = "RdYlGn",
        showscale   = True
    ))
    fig2.update_layout(
        height       = 400,
        plot_bgcolor = "rgba(0,0,0,0)",
        paper_bgcolor= "rgba(0,0,0,0)",
        xaxis        = dict(showticklabels=False),
        yaxis        = dict(showticklabels=False, autorange="reversed")
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Two column layout: hot/cold + overdue
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔥 Top 10 Hot Numbers")
        hot = scores.head(10)[["number", "frequency_score", "status"]]
        st.dataframe(hot, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("⏰ Most Overdue Numbers")
        overdue = gaps.dropna(subset=["overdue_score"]).head(10)[
            ["number", "avg_gap", "draws_since", "overdue_score"]
        ]
        st.dataframe(overdue, use_container_width=True, hide_index=True)

    # ── Rolling 90-day frequency
    st.markdown("---")
    st.subheader("📉 Rolling 90-Day Frequency")
    st.caption("Which numbers have been most active in the last 90 days?")

    rolling = get_rolling(draw_type).sort_values(
        "last_90d_count", ascending=False
    )
    fig3 = px.bar(
        rolling.head(20),
        x="number", y="last_90d_count",
        color="last_90d_count",
        color_continuous_scale="Blues",
        labels={"number": "Number", "last_90d_count": "Appearances (90 days)"}
    )
    fig3.update_layout(
        plot_bgcolor = "rgba(0,0,0,0)",
        paper_bgcolor= "rgba(0,0,0,0)"
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Page 3: Statistical Tests ──────────────────────────────────

elif page == "🔬 Statistical Tests":
    st.title("🔬 Statistical Tests")
    st.markdown(
        "These tests answer the fundamental question: "
        "**can any analysis of past draws improve future predictions?**"
    )

    st.info(
        "P-value interpretation: "
        "**> 0.05** = cannot reject randomness. "
        "**< 0.05** = statistically significant deviation."
    )

    # ── Chi-square test
    st.markdown("---")
    st.subheader("Test 1 — Chi-Square Goodness of Fit")
    st.markdown(
        "Tests whether number frequencies match what a truly random "
        "draw would produce."
    )

    with st.spinner("Running chi-square test..."):
        r = test_randomness(draw_type)

    col1, col2, col3 = st.columns(3)
    col1.metric("Chi² Statistic", r["chi2"])
    col2.metric("P-Value",        r["p_value"])
    col3.metric("Result", "✅ Random" if r["is_random"] else "⚠️ Non-random")
    if r ["is_random"]:
        st.success(
            r["conclusion"]
        )
    else:
        st.warning(
            r["conclusion"]
        )
    # ── Independence test
    st.markdown("---")
    st.subheader("Test 2 — Lunchtime vs Teatime Independence")
    st.markdown(
        "Tests whether knowing the Lunchtime result tells you "
        "anything about the Teatime result."
    )

    with st.spinner("Running independence test..."):
        ind = test_draw_independence()

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Shared Numbers",   ind["avg_shared_numbers"])
    col2.metric("Expected if Random",   ind["expected_if_random"])
    col3.metric("P-Value",              ind["p_value"])
    if ind["are_independent"]:
        st.success(
            ind["conclusion"]
        )
    else:
        st.warning(
            ind["conclusion"]
        )

    # ── Phase 3 summary
    st.markdown("---")
    st.subheader("📋 Full Phase 3 Summary")

    results = {
        "Test": [
            "Chi-Square (Lunchtime)",
            "Chi-Square (Teatime)",
            "Hot Number Predictive Power",
            "Overdue Score Predictive Power",
            "Draw Independence"
        ],
        "P-Value": [0.6689, 0.1975, 0.772, 0.541, 0.308],
        "Verdict": [
            "✅ Random",
            "✅ Random",
            "❌ No predictive power",
            "❌ No predictive power",
            "✅ Independent"
        ]
    }
    st.dataframe(
        pd.DataFrame(results),
        use_container_width=True,
        hide_index=True
    )

    st.error(
        "**Conclusion:** All five statistical tests confirm that UK49s draws "
        "are consistent with true randomness. Hot numbers, cold numbers, and "
        "overdue numbers have no predictive power over future draws. "
        "The lottery has no memory."
    )

# ── Page 4: Predictions ────────────────────────────────────────

elif page == "🎯 Predictions":
    st.title("🎯 Prediction Engine")
    st.markdown(f"**Draw type:** {draw_type}")

    st.warning(
        "⚠️ These suggestions are generated by combining frequency analysis, "
        "Bayesian probability, Monte Carlo simulation, and a Genetic Algorithm. "
        "Statistical tests (Phase 3) confirm they perform **no better than "
        "random selection**. Use for entertainment only."
    )

    n_tickets = st.slider("Number of ticket suggestions", 3, 10, 5)

    # ── Session state keys ────────────────────────────────────
    # These persist across reruns so predictions survive checkbox clicks
    if "prediction_result" not in st.session_state:
        st.session_state.prediction_result = None
    if "prediction_draw_type" not in st.session_state:
        st.session_state.prediction_draw_type = None
    if "logged" not in st.session_state:
        st.session_state.logged = False

    if st.button("🚀 Generate Predictions", type="primary"):
        with st.spinner(
            "Running full pipeline: Monte Carlo → Genetic Algorithm → Scoring... (~60s)"
        ):
            result = generate_predictions(
                draw_type = draw_type,
                n_tickets = n_tickets,
                verbose   = False
            )
        # Store in session state — survives checkbox reruns
        st.session_state.prediction_result    = result
        st.session_state.prediction_draw_type = draw_type
        st.session_state.logged               = False

    # ── Display stored result (persists across reruns) ────────
    result = st.session_state.prediction_result

    if result is not None:

        # ── Top numbers
        st.markdown("---")
        st.subheader("📊 Top Numbers by Combined Score")

        num_df = pd.DataFrame(result["top_numbers"])
        fig = px.bar(
            num_df.head(20), x="number", y="combined_score",
            color="status",
            color_discrete_map={
                "🔥 Hot":     "#E05C5C",
                "🧊 Cold":    "#5C9BE0",
                "➖ Neutral": "#A0A0A0"
            },
            labels={"number": "Number", "combined_score": "Score"}
        )
        fig.update_layout(
            plot_bgcolor = "rgba(0,0,0,0)",
            paper_bgcolor= "rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Suggested tickets
        st.markdown("---")
        st.subheader(f"🎟️ Suggested Tickets")

        for i, ticket in enumerate(result["suggestions"], 1):
            with st.expander(
                f"Ticket {i}: {ticket['ticket']}  —  Score: {ticket['overall_score']}"
            ):
                col1, col2, col3 = st.columns(3)
                col1.metric("Overall Score", ticket["overall_score"])
                col2.metric("Odd / Even",    ticket["odd_even"])
                col3.metric("High / Low",    ticket["high_low"])

        # ── GA best ticket
        st.markdown("---")
        st.subheader("🧬 Genetic Algorithm Best Ticket")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("GA Fitness Score", result["ga_fitness"])
            st.write("**Numbers:**")
            st.write(" · ".join(str(n) for n in result["ga_ticket"]))

        with col2:
            breakdown = result["ga_breakdown"]
            fig2 = go.Figure(go.Bar(
                x           = list(breakdown.values()),
                y           = list(breakdown.keys()),
                orientation = "h",
                marker_color = "#4F86C6"
            ))
            fig2.update_layout(
                xaxis_range  = [0, 1],
                height       = 250,
                plot_bgcolor = "rgba(0,0,0,0)",
                paper_bgcolor= "rgba(0,0,0,0)",
                margin       = dict(l=0, r=0, t=0, b=0)
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ── Reality check
        st.markdown("---")
        st.error(
            f"**Statistical Reality Check** — "
            f"Hot number test p={result['phase3_reminder']['hot_number_p']} | "
            f"Overdue test p={result['phase3_reminder']['overdue_p']} | "
            f"{result['phase3_reminder']['conclusion']}"
        )

        # ── Logging — stays visible because result is in session_state
        st.markdown("---")
        st.subheader("📝 Log These Predictions")

        if st.session_state.logged:
            st.success(
                f"✅ Already logged for "
                f"{st.session_state.prediction_draw_type} — "
                f"visible in Backtest Results → Live Track Record"
            )
        else:
            from datetime import date, timedelta

            col1, col2 = st.columns([2, 1])
            with col1:
                log_date = st.date_input(
                    "Log for draw date",
                    value = date.today() + timedelta(days=1),
                    min_value = date.today()
                )
            with col2:
                st.write("")  # Spacer
                st.write("")
                if st.button("💾 Save to prediction log"):
                    from app.services.outcome_tracker import log_predictions

                    # ── Temporary debug ───────────────────────────────────
                    print(f"[DEBUG] draw_type: {st.session_state.prediction_draw_type}")
                    print(f"[DEBUG] suggestions count: {len(result['suggestions'])}")
                    print(f"[DEBUG] first ticket: {result['suggestions'][0]['ticket']}")
                    print(f"[DEBUG] first score: {result['suggestions'][0].get('overall_score')}")
                    # ── End debug ─────────────────────────────────────────

                    logged = log_predictions(
                        draw_type   = st.session_state.prediction_draw_type,
                        draw_date   = log_date,
                        suggestions = result["suggestions"],
                        ga_fitness  = result["ga_fitness"]
                    )
                    st.session_state.logged = True
                    st.success(
                        f"✅ Logged {logged} tickets for "
                        f"{st.session_state.prediction_draw_type} "
                        f"on {log_date}"
                    )
                    st.rerun()

# ── Page 5: Backtest Results ─────────────────────────────────
elif page == "📉 Backtest Results":
    st.title("📉 Backtest Results")
    st.markdown(
        "Walk-forward backtesting — the model predicts each draw using "
        "only past data, then we measure how many numbers actually appeared. "
        "Compared against pure random selection side by side."
    )

    st.info(
        "This is the most honest section of the project. "
        "The model is tested against history it has never seen, "
        "then compared directly against random guessing. "
        "Phase 3 statistical tests predicted this outcome."
    )

    # ── Session state — persists results across refreshes ─────
    if "bt_result" not in st.session_state:
        st.session_state.bt_result = None

    # ── Controls row ──────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        window       = st.number_input("History window", 100, 500, 200, 50)
    with col3:
        sample_every = st.number_input("Sample every N draws", 1, 20, 10, 1)

    # ── Button row ────────────────────────────────────────────
    btn_col1, btn_col2 = st.columns([1, 5])
    with btn_col1:
        run_bt = st.button("▶ Run Backtest (~2 min)", type="primary")
    with btn_col2:
        if st.session_state.bt_result is not None:
            if st.button("🗑️ Clear Results"):
                st.session_state.bt_result = None
                st.rerun()

    # ── Run and store ─────────────────────────────────────────
    if run_bt:
        with st.spinner("Running walk-forward backtest..."):
            from app.services.backtester import backtest
            bt = backtest(
                draw_type    = draw_type,
                window       = int(window),
                sample_every = int(sample_every),
                verbose      = False
            )
        st.session_state.bt_result = bt

    # ── Display stored results ────────────────────────────────
    bt = st.session_state.bt_result

    if bt is not None:
        if "error" in bt:
            st.error(bt["error"])
        else:
            st.markdown("---")
            st.subheader("🔍 Transparency — Raw Performance")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Draws Tested",    bt["draws_tested"])
            c2.metric("Model Avg Hits",  bt["model_avg_hits"])
            c3.metric("Random Avg Hits", bt["random_avg_hits"])
            delta_color = "normal" if bt["delta_avg"] >= 0 else "inverse"
            c4.metric("Delta",           bt["delta_avg"], delta_color=delta_color)

            st.caption(
                "⚠️ Delta varies between runs due to random sampling variance. "
                "Run the backtest multiple times — it will oscillate around zero, "
                "confirming no method consistently outperforms random."
            )

            interp = bt["interpretation"]
            if "no advantage" in interp["verdict"]:
                st.error(f"**Verdict:** {interp['transparency']}")
            elif "marginal advantage" in interp["verdict"]:
                st.warning(f"**Verdict:** {interp['transparency']}")
            else:
                st.error(f"**Verdict:** {interp['transparency']}")

            st.markdown("---")
            st.subheader("📊 Draw-by-Draw Comparison")

            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Model Beat Random",    f"{bt['beat_random_pct']}%")
            cc2.metric("Tied Random",          f"{bt['tied_random_pct']}%")
            cc3.metric("Model Lost to Random", f"{bt['lost_random_pct']}%")

            st.subheader("🎯 Hit Distribution — Model vs Random")
            dist_data = [
                {
                    "Hits":   str(k),
                    "Model":  bt["model_hit_dist"].get(str(k), 0),
                    "Random": bt["random_hit_dist"].get(str(k), 0)
                }
                for k in range(5)
            ]
            dist_df = pd.DataFrame(dist_data)
            fig = px.bar(
                dist_df, x="Hits", y=["Model", "Random"],
                barmode="group",
                color_discrete_map={"Model": "#4F86C6", "Random": "#94a3b8"},
                labels={"value": "Draw count", "variable": "Method"}
            )
            fig.update_layout(
                plot_bgcolor = "rgba(0,0,0,0)",
                paper_bgcolor= "rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📈 Model vs Random — Per Draw Over Time")
            per_draw = pd.DataFrame(bt["per_draw_results"])
            per_draw["rolling_model"]  = per_draw["model_hits"].rolling(20).mean()
            per_draw["rolling_random"] = per_draw["random_hits"].rolling(20).mean()

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x    = per_draw["date"],
                y    = per_draw["rolling_model"],
                name = "Model (20-draw avg)",
                line = dict(color="#4F86C6", width=2)
            ))
            fig2.add_trace(go.Scatter(
                x    = per_draw["date"],
                y    = per_draw["rolling_random"],
                name = "Random (20-draw avg)",
                line = dict(color="#94a3b8", width=2)
            ))
            fig2.update_layout(
                plot_bgcolor = "rgba(0,0,0,0)",
                paper_bgcolor= "rgba(0,0,0,0)",
                xaxis_title  = "Date",
                yaxis_title  = "Avg hits (20-draw rolling)"
            )
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("---")
            st.subheader("💡 Context & Interpretation")
            st.success(f"**Why this matters:** {interp['context']}")
            st.info(f"**Portfolio note:** {interp['portfolio_note']}")


    # ── Live track record ─────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Live Prediction Track Record")
    st.caption(
        "Predictions logged from the Predictions page are scored here "
        "after each draw. This record grows over time."
    )

    from app.services.outcome_tracker import get_track_record, score_pending_predictions

    if st.button("🔄 Score Pending Predictions"):
        with st.spinner("Scoring..."):
            result = score_pending_predictions()
        st.success(f"Scored {result['scored']} predictions. Missed: {result['missed']}")

    record = get_track_record(draw_type)

    if record["total_scored"] == 0:
        st.info(record.get("message", "No scored predictions yet."))
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Scored",    record["total_scored"])
        col2.metric("Avg Hits",        record["avg_hits"])
        col3.metric("Random Baseline", record["random_baseline"])

        st.dataframe(
            pd.DataFrame(record["recent_predictions"]),
            use_container_width=True,
            hide_index=True
        )

    # ── All logged predictions (pending + scored) ─────────────────
    st.markdown("---")
    st.subheader("📂 All Logged Predictions")
    st.caption("Every prediction saved from the Predictions page — pending and scored.")

    from app.core.database import SessionLocal
    from app.models.prediction_log import PredictionLog

    def get_all_logged(dt=None):
        db   = SessionLocal()
        try:
            query = db.query(PredictionLog)
            if dt:
                query = query.filter(PredictionLog.draw_type == dt)
            rows = query.order_by(PredictionLog.draw_date.desc()).all()
        finally:
            db.close()
        return rows

    all_logged = get_all_logged(draw_type)

    if not all_logged:
        st.info("No predictions logged yet. Go to Predictions page, generate tickets, then save them.")
    else:
        log_data = []
        for r in all_logged:
            log_data.append({
                "Date":        str(r.draw_date),
                "Draw":        r.draw_type,
                "Ticket":      str(r.ticket),
                "Score":       r.overall_score,
                "Status":      r.status.value,
                "Hits":        r.hits if r.hits is not None else "—",
                "Actual":      str(r.actual_numbers) if r.actual_numbers else "—",
                "Booster Hit": "✅" if r.booster_hit else "—"
            })

        log_df = pd.DataFrame(log_data)

        # Colour code by status
        status_counts = log_df["Status"].value_counts()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Logged",  len(log_df))
        c2.metric("Pending",       status_counts.get("pending", 0))
        c3.metric("Scored",        status_counts.get("scored",  0))

        # Filter controls
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "pending", "scored", "missed"]
        )

        filtered = log_df if status_filter == "All" else log_df[log_df["Status"] == status_filter]

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True
        )

        # Download as CSV
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label     = "⬇️ Download as CSV",
            data      = csv,
            file_name = f"predictions_{draw_type.lower()}.csv",
            mime      = "text/csv"
        )
