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

draw_type = st.sidebar.selectbox("Draw Type", ["Lunchtime", "Teatime"])

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ Statistical tests confirm all draws are random. "
    "No analysis method improves your odds. "
    "For entertainment and education only."
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Data Updates")

if st.sidebar.button("🕷️ Scrape Latest Results"):
    with st.spinner("Fetching latest draws from LotteryExtreme..."):
        from app.services.scraper import run_scraper
        run_scraper()
        st.cache_data.clear()
    st.sidebar.success("✅ Latest results fetched")
    st.rerun()

st.sidebar.caption("Data updates daily. Run scraper to fetch latest draws.")

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 ML Model")

if st.sidebar.button("🧠 Train ML Model"):
    with st.spinner("Training Random Forest on historical data (~2 min)..."):
        from app.services.ml_engine import train_model
        result = train_model(draw_type, verbose=False)
    if "error" in result:
        st.sidebar.error(result["error"])
    else:
        st.sidebar.success(
            f"✅ Trained — AUC: {result['cv_auc_mean']} "
            f"(random baseline: 0.500)"
        )
        st.sidebar.caption(result["interpretation"])

# ── Data Loading ───────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_draws(dt):
    return load_draws(dt)

@st.cache_data(ttl=300)
def get_frequency(dt):
    return compute_frequency(get_draws(dt))

@st.cache_data(ttl=300)
def get_gaps(dt):
    return compute_gaps(get_draws(dt))

@st.cache_data(ttl=300)
def get_scores(dt):
    return compute_frequency_score(get_draws(dt))

@st.cache_data(ttl=300)
def get_rolling(dt):
    return compute_rolling(get_draws(dt), days=90)


# ── Helper: render pair hit details for one draw ───────────────
def render_pair_hit_block(draw_date, draw_type_label, actual_numbers,
                           pair_hits, predicted_pairs):
    """
    Renders the scored pair grid for one draw date — matching the
    React UI ScoredPairAccordion format:
      - Actual draw numbers at the top
      - All predicted pairs as colour-coded badges
        🟢 green  = both numbers hit
        🟡 amber  = one number hit (near miss)
        ⚫ grey   = neither hit
    """
    actual_set  = set(actual_numbers or [])
    ph          = pair_hits or {}
    hit_count   = ph.get("hit_count", 0)
    near_count  = ph.get("near_miss_count", 0)
    hit_rate    = ph.get("hit_rate", 0)
    baseline    = ph.get("random_baseline", 0.2551)
    total_pairs = ph.get("predicted_pairs", 20)

    # ── Actual draw numbers ────────────────────────────────────
    if actual_numbers:
        st.markdown("**Actual Draw Numbers**")
        num_html = " ".join(
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,0.1);'
            f'border:2px solid rgba(255,255,255,0.25);color:white;'
            f'font-weight:bold;font-size:14px;margin:2px;">{n}</span>'
            for n in sorted(actual_numbers)
        )
        st.markdown(num_html, unsafe_allow_html=True)
        st.markdown("")

    # ── Stats row ─────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Pairs Hit",       f"{hit_count}/{total_pairs}")
    c2.metric("Hit Rate",        f"{hit_rate}%")
    c3.metric("Random Baseline", f"{baseline * 100:.1f}%")

    # ── Legend ────────────────────────────────────────────────
    st.markdown(
        '<span style="font-size:12px;color:#94a3b8;">'
        '🟢 Both hit &nbsp;&nbsp; 🟡 One hit (near miss) &nbsp;&nbsp; ⚫ Neither hit'
        '</span>',
        unsafe_allow_html=True
    )
    st.markdown("")

    # ── Colour-coded pair badges ───────────────────────────────
    if predicted_pairs:
        badges_html = ""
        for p in predicted_pairs:
            n1 = p.get("n1")
            n2 = p.get("n2")
            label = p.get("pair", f"{n1}-{n2}")

            if n1 is None or n2 is None:
                continue

            n1_hit = n1 in actual_set
            n2_hit = n2 in actual_set

            if n1_hit and n2_hit:
                bg, color, border = "#14532d", "#86efac", "#22c55e"   # green
            elif n1_hit or n2_hit:
                bg, color, border = "#451a03", "#fcd34d", "#f59e0b"   # amber
            else:
                bg, color, border = "#1e293b", "#94a3b8", "#475569"   # slate

            badges_html += (
                f'<span style="display:inline-flex;align-items:center;gap:4px;'
                f'background:{bg};color:{color};border:1px solid {border};'
                f'border-radius:999px;padding:4px 10px;margin:3px;'
                f'font-size:13px;font-weight:bold;">'
                f'{label}'
                f'<span style="font-size:10px;opacity:0.6;font-weight:normal;">'
                f'×{p.get("count","")}</span>'
                f'</span>'
            )
        st.markdown(badges_html, unsafe_allow_html=True)
    else:
        # Fallback — no full pairs list, just show which hit
        hit_pairs  = ph.get("hit_pairs", [])
        near_miss  = ph.get("near_misses", [])
        if hit_pairs:
            hit_html = " ".join(
                f'<span style="background:#14532d;color:#86efac;border:1px solid #22c55e;'
                f'border-radius:999px;padding:4px 10px;margin:3px;'
                f'font-size:13px;font-weight:bold;">{pair}</span>'
                for pair in hit_pairs
            )
            st.markdown(f"**✅ Hit pairs:**", unsafe_allow_html=False)
            st.markdown(hit_html, unsafe_allow_html=True)
        if near_miss:
            near_html = " ".join(
                f'<span style="background:#451a03;color:#fcd34d;border:1px solid #f59e0b;'
                f'border-radius:999px;padding:4px 10px;margin:3px;'
                f'font-size:13px;font-weight:bold;">{pair}</span>'
                for pair in near_miss[:10]
            )
            st.markdown("**🟡 Near misses:**", unsafe_allow_html=False)
            st.markdown(near_html, unsafe_allow_html=True)


# ── Page 1: Overview ───────────────────────────────────────────
if page == "📊 Overview":
    st.title("📊 UK49s — Data Overview")
    st.markdown(f"**Draw type:** {draw_type}")

    df = get_draws(draw_type)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Draws",   f"{len(df):,}")
    col2.metric("Date From",     str(df["date"].min().date()))
    col3.metric("Date To",       str(df["date"].max().date()))
    col4.metric("Years Covered", f"{(df['date'].max() - df['date'].min()).days // 365}")

    st.markdown("---")
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

    st.subheader("🔢 Appearance Count — All Numbers")
    freq_sorted = freq.sort_values("number")
    colors = freq_sorted["status"].map({
        "🔥 Hot":     "#E05C5C",
        "🧊 Cold":    "#5C9BE0",
        "➖ Neutral": "#A0A0A0"
    })
    fig = go.Figure(go.Bar(
        x=freq_sorted["number"], y=freq_sorted["count"],
        marker_color=colors.tolist(),
        text=freq_sorted["count"], textposition="outside"
    ))
    fig.add_hline(
        y=freq_sorted["expected"].iloc[0],
        line_dash="dash", line_color="orange",
        annotation_text="Expected (random)"
    )
    fig.update_layout(
        xaxis_title="Number", yaxis_title="Appearances",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🌡️ Frequency Heatmap")
    st.caption("Darker = appeared more often. Every number should be similar in a fair draw.")
    freq_dict = dict(zip(freq["number"], freq["count"]))
    grid_data, grid_text = [], []
    for row in range(7):
        data_row, text_row = [], []
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
        z=grid_data, text=grid_text, texttemplate="%{text}",
        colorscale="RdYlGn", showscale=True
    ))
    fig2.update_layout(
        height=400,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False, autorange="reversed")
    )
    st.plotly_chart(fig2, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔥 Top 10 Hot Numbers")
        st.dataframe(
            scores.head(10)[["number", "frequency_score", "status"]],
            use_container_width=True, hide_index=True
        )
    with col2:
        st.subheader("⏰ Most Overdue Numbers")
        st.dataframe(
            gaps.dropna(subset=["overdue_score"]).head(10)[
                ["number", "avg_gap", "draws_since", "overdue_score"]
            ],
            use_container_width=True, hide_index=True
        )

    st.markdown("---")
    st.subheader("📉 Rolling 90-Day Frequency")
    st.caption("Which numbers have been most active in the last 90 days?")
    rolling = get_rolling(draw_type).sort_values("last_90d_count", ascending=False)
    fig3 = px.bar(
        rolling.head(20), x="number", y="last_90d_count",
        color="last_90d_count", color_continuous_scale="Blues",
        labels={"number": "Number", "last_90d_count": "Appearances (90 days)"}
    )
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
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

    st.markdown("---")
    st.subheader("Test 1 — Chi-Square Goodness of Fit")
    st.markdown(
        "Tests whether number frequencies match what a truly random draw would produce."
    )
    with st.spinner("Running chi-square test..."):
        r = test_randomness(draw_type)
    col1, col2, col3 = st.columns(3)
    col1.metric("Chi² Statistic", r["chi2"])
    col2.metric("P-Value",        r["p_value"])
    col3.metric("Result", "✅ Random" if r["is_random"] else "⚠️ Non-random")
    if r["is_random"]:
        st.success(r["conclusion"])
    else:
        st.warning(r["conclusion"])

    st.markdown("---")
    st.subheader("Test 2 — Lunchtime vs Teatime Independence")
    st.markdown(
        "Tests whether knowing the Lunchtime result tells you "
        "anything about the Teatime result."
    )
    with st.spinner("Running independence test..."):
        ind = test_draw_independence()
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Shared Numbers", ind["avg_shared_numbers"])
    col2.metric("Expected if Random", ind["expected_if_random"])
    col3.metric("P-Value",            ind["p_value"])
    if ind["are_independent"]:
        st.success(ind["conclusion"])
    else:
        st.warning(ind["conclusion"])

    st.markdown("---")
    st.subheader("📋 Full Phase 3 Summary")
    results = {
        "Test": [
            "Chi-Square (Lunchtime)", "Chi-Square (Teatime)",
            "Hot Number Predictive Power", "Overdue Score Predictive Power",
            "Draw Independence"
        ],
        "P-Value": [0.6689, 0.1975, 0.772, 0.541, 0.308],
        "Verdict": [
            "✅ Random", "✅ Random",
            "❌ No predictive power", "❌ No predictive power",
            "✅ Independent"
        ]
    }
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
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

    if "prediction_result"    not in st.session_state:
        st.session_state.prediction_result    = None
    if "prediction_draw_type" not in st.session_state:
        st.session_state.prediction_draw_type = None
    if "logged"               not in st.session_state:
        st.session_state.logged               = False

    if st.button("🚀 Generate Predictions", type="primary"):
        with st.spinner(
            "Running full pipeline: Monte Carlo → Genetic Algorithm → Scoring... (~60s)"
        ):
            result = generate_predictions(
                draw_type = draw_type,
                n_tickets = n_tickets,
                verbose   = False
            )
        st.session_state.prediction_result    = result
        st.session_state.prediction_draw_type = draw_type
        st.session_state.logged               = False

    result = st.session_state.prediction_result

    if result is not None:
        st.markdown("---")
        st.subheader("📊 Top Numbers by Combined Score")
        num_df = pd.DataFrame(result["top_numbers"])
        fig = px.bar(
            num_df.head(20), x="number", y="combined_score",
            color="status",
            color_discrete_map={
                "🔥 Hot": "#E05C5C", "🧊 Cold": "#5C9BE0", "➖ Neutral": "#A0A0A0"
            },
            labels={"number": "Number", "combined_score": "Score"}
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True)

        if result.get("ml_available"):
            st.markdown("---")
            st.subheader("🤖 ML Probability Estimates")
            st.caption(
                "Random Forest trained on frequency, gap, Bayesian, "
                "and pair features. AUC near 0.5 confirms random baseline."
            )
            ml_data = [
                {"Number": r["number"],
                 "ML Probability": r.get("ml_probability", 0),
                 "Combined Score": r["combined_score"]}
                for r in result["top_numbers"]
            ]
            ml_df = pd.DataFrame(ml_data).sort_values("ML Probability", ascending=False)
            fig_ml = px.bar(
                ml_df, x="Number", y="ML Probability",
                color="ML Probability", color_continuous_scale="Blues",
                labels={"Number": "Number", "ML Probability": "Probability"}
            )
            fig_ml.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_ml, use_container_width=True)
        else:
            st.info("🤖 Train the ML model from the sidebar to see ML probability estimates.")

        st.markdown("---")
        st.subheader("🎟️ Suggested Tickets")
        for i, ticket in enumerate(result["suggestions"], 1):
            with st.expander(
                f"Ticket {i}: {ticket['ticket']}  —  Score: {ticket['overall_score']}"
            ):
                col1, col2, col3 = st.columns(3)
                col1.metric("Overall Score", ticket["overall_score"])
                col2.metric("Odd / Even",    ticket["odd_even"])
                col3.metric("High / Low",    ticket["high_low"])

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
                x=list(breakdown.values()), y=list(breakdown.keys()),
                orientation="h", marker_color="#4F86C6"
            ))
            fig2.update_layout(
                xaxis_range=[0, 1], height=250,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=0, b=0)
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.subheader("🔗 Top 20 Predicted Pairs")
        st.caption(
            "Number pairs that appear together most frequently in historical draws. "
            "Weighted by recency. No predictive power confirmed by Phase 3."
        )
        if "top_pairs" in result:
            pairs_df = pd.DataFrame(result["top_pairs"])
            col1, col2 = st.columns([3, 1])
            with col1:
                pairs_html = ""
                for _, row in pairs_df.iterrows():
                    pairs_html += (
                        f'<span style="background:#1e3a5f;color:#93c5fd;'
                        f'padding:4px 10px;border-radius:20px;margin:3px;'
                        f'display:inline-block;font-size:13px;font-weight:bold;">'
                        f'{row["pair"]}</span>'
                    )
                st.markdown(pairs_html, unsafe_allow_html=True)
            with col2:
                st.dataframe(
                    pairs_df[["pair", "count", "score"]].head(10),
                    use_container_width=True, hide_index=True
                )

        st.markdown("---")
        st.error(
            f"**Statistical Reality Check** — "
            f"Hot number test p={result['phase3_reminder']['hot_number_p']} | "
            f"Overdue test p={result['phase3_reminder']['overdue_p']} | "
            f"{result['phase3_reminder']['conclusion']}"
        )

        st.markdown("---")
        st.subheader("📝 Log These Predictions")
        if st.session_state.logged:
            st.success(
                f"✅ Already logged for {st.session_state.prediction_draw_type} — "
                f"visible in Backtest Results → Live Track Record"
            )
        else:
            from datetime import date, timedelta
            col1, col2 = st.columns([2, 1])
            with col1:
                log_date = st.date_input(
                    "Log for draw date",
                    value=date.today() + timedelta(days=1),
                    min_value=date.today()
                )
            with col2:
                st.write("")
                st.write("")
                if st.button("💾 Save to prediction log"):
                    from app.services.outcome_tracker import log_predictions
                    logged = log_predictions(
                        draw_type       = st.session_state.prediction_draw_type,
                        draw_date       = log_date,
                        suggestions     = result["suggestions"],
                        ga_fitness      = result["ga_fitness"],
                        predicted_pairs = result.get("top_pairs", [])
                    )
                    st.session_state.logged = True
                    st.success(
                        f"✅ Logged {logged} tickets for "
                        f"{st.session_state.prediction_draw_type} on {log_date}"
                    )
                    st.rerun()


# ── Page 5: Backtest Results ───────────────────────────────────
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

    if "bt_result" not in st.session_state:
        st.session_state.bt_result = None

    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        window       = st.number_input("History window", 100, 500, 200, 50)
    with col3:
        sample_every = st.number_input("Sample every N draws", 1, 20, 10, 1)

    btn_col1, btn_col2 = st.columns([1, 5])
    with btn_col1:
        run_bt = st.button("▶ Run Backtest (~2 min)", type="primary")
    with btn_col2:
        if st.session_state.bt_result is not None:
            if st.button("🗑️ Clear Results"):
                st.session_state.bt_result = None
                st.rerun()

    if run_bt:
        with st.spinner("Running walk-forward backtest..."):
            from app.services.backtester import backtest
            bt = backtest(
                draw_type=draw_type, window=int(window),
                sample_every=int(sample_every), verbose=False
            )
        st.session_state.bt_result = bt

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
            c4.metric("Delta", bt["delta_avg"], delta_color=delta_color)
            st.caption(
                "⚠️ Delta varies between runs due to random sampling variance. "
                "Run the backtest multiple times — it will oscillate around zero."
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
                {"Hits": str(k),
                 "Model":  bt["model_hit_dist"].get(str(k), 0),
                 "Random": bt["random_hit_dist"].get(str(k), 0)}
                for k in range(5)
            ]
            fig = px.bar(
                pd.DataFrame(dist_data), x="Hits", y=["Model", "Random"],
                barmode="group",
                color_discrete_map={"Model": "#4F86C6", "Random": "#94a3b8"},
                labels={"value": "Draw count", "variable": "Method"}
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📈 Model vs Random — Per Draw Over Time")
            per_draw = pd.DataFrame(bt["per_draw_results"])
            per_draw["rolling_model"]  = per_draw["model_hits"].rolling(20).mean()
            per_draw["rolling_random"] = per_draw["random_hits"].rolling(20).mean()
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=per_draw["date"], y=per_draw["rolling_model"],
                name="Model (20-draw avg)", line=dict(color="#4F86C6", width=2)
            ))
            fig2.add_trace(go.Scatter(
                x=per_draw["date"], y=per_draw["rolling_random"],
                name="Random (20-draw avg)", line=dict(color="#94a3b8", width=2)
            ))
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Date", yaxis_title="Avg hits (20-draw rolling)"
            )
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("---")
            st.subheader("💡 Context & Interpretation")
            st.success(f"**Why this matters:** {interp['context']}")
            st.info(f"**Portfolio note:** {interp['portfolio_note']}")

    # ── Live track record ──────────────────────────────────────
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
            use_container_width=True, hide_index=True
        )

    # ── All logged predictions ─────────────────────────────────
    st.markdown("---")
    st.subheader("📂 All Logged Predictions")
    st.caption("Every prediction saved from the Predictions page — pending and scored.")

    from app.core.database import SessionLocal
    from app.models.prediction_log import PredictionLog

    def get_all_logged(dt=None):
        db = SessionLocal()
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
        st.info("No predictions logged yet.")
    else:
        log_data = []
        for r in all_logged:
            pair_hit_info = "—"
            if r.pair_hits:
                pair_hit_info = (
                    f"{r.pair_hits.get('hit_count', 0)}/"
                    f"{r.pair_hits.get('predicted_pairs', 20)} pairs hit"
                )
            log_data.append({
                "Date":        str(r.draw_date),
                "Draw":        r.draw_type,
                "Ticket":      str(r.ticket),
                "Score":       r.overall_score,
                "Status":      r.status.value,
                "Hits":        r.hits if r.hits is not None else "—",
                "Pair Hits":   pair_hit_info,
                "Actual":      str(r.actual_numbers) if r.actual_numbers else "—",
                "Booster Hit": "✅" if r.booster_hit else "—"
            })

        log_df = pd.DataFrame(log_data)
        status_counts = log_df["Status"].value_counts()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Logged", len(log_df))
        c2.metric("Pending",      status_counts.get("pending", 0))
        c3.metric("Scored",       status_counts.get("scored",  0))

        status_filter = st.selectbox(
            "Filter by status", ["All", "pending", "scored", "missed"]
        )
        filtered = (
            log_df if status_filter == "All"
            else log_df[log_df["Status"] == status_filter]
        )
        st.dataframe(filtered, use_container_width=True, hide_index=True)

        # ── Pair Hit Details — new format ──────────────────────
        if status_filter in ["All", "scored"]:
            st.markdown("---")
            st.subheader("🔗 Pair Hit Details")
            st.caption(
                "One accordion per draw date — actual numbers at top, "
                "all predicted pairs colour-coded: "
                "🟢 both hit · 🟡 one hit · ⚫ neither hit"
            )

            # Group by draw_date — one accordion per draw, not per ticket
            from itertools import groupby
            scored_rows = [
                r for r in all_logged
                if r.status.value == "scored" and r.pair_hits
            ]
            scored_rows.sort(key=lambda r: str(r.draw_date), reverse=True)

            if not scored_rows:
                st.info("No scored predictions with pair data yet.")
            else:
                # Group: one expander per draw_date
                seen_dates = set()
                for r in scored_rows:
                    date_key = str(r.draw_date)
                    if date_key in seen_dates:
                        continue          # skip duplicate tickets for same draw
                    seen_dates.add(date_key)

                    ph         = r.pair_hits
                    hit_count  = ph.get("hit_count", 0)
                    total_p    = ph.get("predicted_pairs", 20)
                    ticket_hits = r.hits or 0

                    with st.expander(
                        f"{r.draw_date}  {r.draw_type}  —  "
                        f"Ticket hits: {ticket_hits}/6  |  "
                        f"Pair hits: {hit_count}/{total_p}",
                        expanded=False
                    ):
                        render_pair_hit_block(
                            draw_date        = str(r.draw_date),
                            draw_type_label  = r.draw_type,
                            actual_numbers   = r.actual_numbers,
                            pair_hits        = r.pair_hits,
                            predicted_pairs  = r.predicted_pairs   # full list with n1/n2
                        )

        # Download CSV
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label     = "⬇️ Download as CSV",
            data      = csv,
            file_name = f"predictions_{draw_type.lower()}.csv",
            mime      = "text/csv"
        )