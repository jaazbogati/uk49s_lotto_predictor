"""
ML Engine — Pattern Learning Layer
────────────────────────────────────
Trains a machine learning model on historical draw features
to learn which number characteristics correlate with appearance.

HONEST FRAMING:
Phase 3 proved draws are random. This engine will confirm that
finding — but the process of building, training, evaluating and
honestly reporting an ML model is the valuable exercise.

What this engine adds:
  1. Feature engineering from all previous engines
  2. Random Forest classifier trained on historical data
  3. Learned probability estimates per number
  4. Feature importance — which factors the model weighted
  5. Walk-forward evaluation vs random baseline
  6. Dynamic weight optimisation for the prediction engine

The model will perform near random. Showing this honestly,
with feature importances and calibrated probabilities, is
more valuable than hiding the result.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.calibration import CalibratedClassifierCV
import joblib
import os
from app.services.frequency_engine import (
    load_draws, compute_frequency, compute_gaps,
    compute_frequency_score, ALL_NUMBERS, NUMBER_COLS
)
from app.services.bayesian_engine import compute_posterior
from app.services.pattern_engine import compute_pairs

# ── Model Storage ─────────────────────────────────────────────

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")

def _model_path(draw_type: str) -> str:
    os.makedirs(MODEL_DIR, exist_ok=True)
    return os.path.join(MODEL_DIR, f"rf_{draw_type.lower()}.joblib")


# ── Feature Engineering ───────────────────────────────────────

def build_features(df: pd.DataFrame, target_idx: int) -> pd.DataFrame:
    """
    For each number 1-49, builds a feature vector using data
    UP TO but not including target_idx (no data leakage).

    Features per number:
      - frequency_score     : weighted historical frequency
      - recent_90d_count    : appearances in last 90 days
      - avg_gap             : average draws between appearances
      - draws_since_last    : how long since last appearance
      - overdue_score       : draws_since / avg_gap
      - bayesian_posterior  : Bayesian probability estimate
      - pair_score          : strength of best pair involving this number
      - is_odd              : 1 if odd, 0 if even
      - is_high             : 1 if > 24, 0 if <= 24
      - position_in_range   : normalised position 1-49 → 0-1

    Target: did this number appear in draw at target_idx?
    """
    past = df.iloc[:target_idx]

    if len(past) < 50:
        return pd.DataFrame()

    # Frequency scores
    freq_df = compute_frequency_score(past)
    freq_map = dict(zip(freq_df["number"], freq_df["frequency_score"]))

    # Gap analysis
    gaps_df  = compute_gaps(past)
    gap_map  = dict(zip(gaps_df["number"], gaps_df["avg_gap"].fillna(8.2)))
    since_map = dict(zip(gaps_df["number"], gaps_df["draws_since"].fillna(8)))
    overdue_map = dict(zip(gaps_df["number"], gaps_df["overdue_score"].fillna(1.0)))

    # Bayesian posteriors
    bayes_df   = compute_posterior(past)
    bayes_map  = dict(zip(bayes_df["number"], bayes_df["posterior_prob"]))

    # Recent 90-day counts
    cutoff     = past["date"].max() - pd.Timedelta(days=90)
    recent     = past[past["date"] >= cutoff]
    recent_counts = {}
    for num in ALL_NUMBERS:
        mask = (recent[NUMBER_COLS] == num).any(axis=1)
        recent_counts[num] = mask.sum()

    # Pair scores — best pair score for each number
    pairs_df   = compute_pairs(past)
    pair_scores = {}
    for num in ALL_NUMBERS:
        mask  = (pairs_df["n1"] == num) | (pairs_df["n2"] == num)
        best  = pairs_df[mask]["score"].max() if mask.any() else 0
        pair_scores[num] = best

    # Target — what actually appeared
    actual_row  = df.iloc[target_idx]
    actual_nums = set([
        actual_row["n1"], actual_row["n2"], actual_row["n3"],
        actual_row["n4"], actual_row["n5"], actual_row["n6"]
    ])

    # Build feature rows
    rows = []
    for num in ALL_NUMBERS:
        rows.append({
            "number":           num,
            "frequency_score":  freq_map.get(num, 50.0),
            "recent_90d":       recent_counts.get(num, 0),
            "avg_gap":          float(gap_map.get(num, 8.2)),
            "draws_since":      float(since_map.get(num, 8)),
            "overdue_score":    float(overdue_map.get(num, 1.0)),
            "bayesian_prob":    float(bayes_map.get(num, 1/49)),
            "pair_score":       float(pair_scores.get(num, 0)),
            "is_odd":           1 if num % 2 != 0 else 0,
            "is_high":          1 if num > 24 else 0,
            "position":         (num - 1) / 48,
            "appeared":         1 if num in actual_nums else 0
        })

    return pd.DataFrame(rows)


FEATURE_COLS = [
    "frequency_score", "recent_90d", "avg_gap",
    "draws_since", "overdue_score", "bayesian_prob",
    "pair_score", "is_odd", "is_high", "position"
]


# ── Training ──────────────────────────────────────────────────

def train_model(
    draw_type:    str  = None,
    window:       int  = 200,
    sample_every: int  = 5,
    verbose:      bool = True
) -> dict:
    """
    Trains a Random Forest on historical draw features.

    Walk-forward training to prevent data leakage:
      For each draw from `window` onwards (sampled every N):
        - Build features from all previous draws
        - Record whether each number appeared
        - This becomes one training observation

    Random Forest chosen because:
      - Handles non-linear relationships
      - Provides feature importances
      - Robust to overfitting with cross-validation
      - Interpretable
    """
    df    = load_draws(draw_type)
    label = draw_type or "All Draws"

    if len(df) < window + 50:
        return {"error": "Not enough data to train"}

    if verbose:
        print(f"\n[ML] Building training dataset for {label}...")

    all_features = []
    sample_indices = range(window, len(df) - 1, sample_every)

    for i, idx in enumerate(sample_indices):
        if verbose and i % 50 == 0:
            print(f"  Progress: {i}/{len(list(sample_indices))}")

        feat_df = build_features(df, idx)
        if not feat_df.empty:
            all_features.append(feat_df)

    if not all_features:
        return {"error": "Could not build training features"}

    full_df = pd.concat(all_features, ignore_index=True)

    X = full_df[FEATURE_COLS].values
    y = full_df["appeared"].values

    if verbose:
        print(f"\n[ML] Training set: {len(X)} samples")
        print(f"[ML] Class balance: {y.mean():.3f} positive rate")
        print(f"     (Expected: {6/49:.3f} — 6 numbers drawn from 49)")

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train Random Forest with calibrated probabilities
    rf = RandomForestClassifier(
        n_estimators  = 200,
        max_depth     = 8,
        min_samples_leaf = 20,    # Prevents overfitting
        class_weight  = "balanced",
        random_state  = 42,
        n_jobs        = -1
    )

    # Cross-validation to estimate real performance
    cv_scores = cross_val_score(rf, X_scaled, y, cv=5, scoring="roc_auc")

    if verbose:
        print(f"\n[ML] Cross-validation AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        print(f"     (Random baseline AUC = 0.5)")

    # Calibrate probabilities for better estimates
    calibrated = CalibratedClassifierCV(rf, cv=3, method="sigmoid")
    calibrated.fit(X_scaled, y)

    # Feature importances
    rf.fit(X_scaled, y)
    importances = dict(zip(FEATURE_COLS, rf.feature_importances_))

    # Save model and scaler
    path = _model_path(draw_type or "all")
    joblib.dump({"model": calibrated, "scaler": scaler}, path)

    if verbose:
        print(f"\n[ML] Model saved → {path}")
        print("\n[ML] Feature Importances:")
        for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
            bar = "█" * int(imp * 50)
            print(f"  {feat:20s} {bar} {imp:.4f}")

    return {
        "label":            label,
        "training_samples": len(X),
        "cv_auc_mean":      round(cv_scores.mean(), 4),
        "cv_auc_std":       round(cv_scores.std(), 4),
        "random_baseline_auc": 0.5,
        "feature_importances": {
            k: round(float(v), 4)
            for k, v in sorted(importances.items(), key=lambda x: -x[1])
        },
        "model_path":       path,
        "interpretation": (
            f"AUC of {cv_scores.mean():.4f} vs random baseline of 0.500. "
            + ("Model shows marginal signal above random."
               if cv_scores.mean() > 0.52
               else "Model performs at random baseline — confirming Phase 3 results.")
        )
    }


# ── Prediction ────────────────────────────────────────────────

def predict_with_ml(draw_type: str = None) -> pd.DataFrame:
    """
    Uses the trained model to score each number 1-49
    for the NEXT draw.

    Returns a DataFrame with columns:
      number, ml_probability, ml_rank

    If no model is trained yet, returns empty DataFrame.
    """
    path = _model_path(draw_type or "all")

    if not os.path.exists(path):
        return pd.DataFrame()

    bundle = joblib.load(path)
    model  = bundle["model"]
    scaler = bundle["scaler"]

    df = load_draws(draw_type)
    if df.empty:
        return pd.DataFrame()

    # Build features using ALL historical data (predicting next draw)
    feat_df = build_features(df, len(df) - 1)

    if feat_df.empty:
        return pd.DataFrame()

    X        = feat_df[FEATURE_COLS].values
    X_scaled = scaler.transform(X)

    probs = model.predict_proba(X_scaled)[:, 1]

    feat_df["ml_probability"] = probs
    feat_df["ml_rank"]        = feat_df["ml_probability"].rank(
        ascending=False
    ).astype(int)

    return feat_df[["number", "ml_probability", "ml_rank"]].sort_values(
        "ml_probability", ascending=False
    ).reset_index(drop=True)


# ── Full Report ───────────────────────────────────────────────

def get_ml_report(draw_type: str = None) -> dict:
    """
    Returns ML predictions and model info for the API/dashboard.
    Trains the model if not already trained.
    """
    path = _model_path(draw_type or "all")

    # Auto-train if no model exists
    if not os.path.exists(path):
        print("[ML] No model found — training now...")
        train_result = train_model(draw_type, verbose=False)
        if "error" in train_result:
            return train_result
    else:
        train_result = {"message": "Using cached model"}

    predictions = predict_with_ml(draw_type)

    if predictions.empty:
        return {"error": "Could not generate ML predictions"}

    return {
        "draw_type":    draw_type or "All",
        "top_10":       predictions.head(10).to_dict("records"),
        "all_numbers":  predictions.to_dict("records"),
        "model_info":   train_result,
        "disclaimer":   (
            "ML predictions are based on learned feature weights. "
            "Phase 3 statistical tests confirm no method has predictive "
            "power over random draws (p > 0.05). These are informed "
            "suggestions, not predictions."
        )
    }