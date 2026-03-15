"""
starter_model.py
----------------
First-pass logistic-regression models predicting go/no-go responding as
a function of stimulus similarity and reinforcement history.

These are *descriptive* approximations -- not mechanistic diffusion models.
See the docstrings and inline comments for guidance on extending to a
proper evidence-accumulation / diffusion model.

Extension roadmap
-----------------
1. Replace logistic regression with a drift-diffusion model (DDM) where
   the drift rate is parameterized by similarity-weighted reinforcement
   history.  Packages: HDDM, PyDDM, or a custom Stan / PyMC model.
2. Allow drift rate to vary across stimulus positions so that the model
   produces a full generalization gradient from its fitted parameters.
3. Add hierarchical (mixed-effects) structure so that participant-level
   parameters are drawn from a group distribution.
4. Fit the model to both choice (go/no-go) and RT data simultaneously.
5. Use Bayesian model comparison (WAIC, LOO) to compare generalization
   kernels (Gaussian vs. exponential vs. Shepard's law).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler


def _prepare_features(
    df: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Select features and target, drop rows with NaNs.

    Returns
    -------
    X : np.ndarray
        Feature matrix.
    y : np.ndarray
        Binary target (1 = response, 0 = no response).
    df_clean : pd.DataFrame
        Rows that survived NaN removal (aligned with X, y).
    """
    target_col = "response_occurred"
    cols = feature_cols + [target_col]
    df_clean = df[cols].dropna().copy()
    X = df_clean[feature_cols].values.astype(float)
    y = df_clean[target_col].astype(int).values
    return X, y, df_clean


def fit_simple_model(
    df: pd.DataFrame,
    output_dir: Union[str, Path] = "../outputs",
) -> LogisticRegression:
    """Fit a simple logistic regression predicting P(response).

    Model specification::

        P(response) ~ similarity_gaussian
                      + cumulative_similarity_weighted_reinforcement
                      + absolute_distance_from_target
                      + block_number

    Parameters
    ----------
    df : pd.DataFrame
        Modeling dataset (output of ``build_modeling_dataset``).
    output_dir : str or Path
        Where to save summary plots.

    Returns
    -------
    LogisticRegression
        Fitted sklearn model.
    """
    feature_cols = [
        "similarity_gaussian",
        "cumulative_similarity_weighted_reinforcement",
        "absolute_distance_from_target",
        "block_number",
    ]

    X, y, df_clean = _prepare_features(df, feature_cols)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=1000, solver="lbfgs")
    model.fit(X_scaled, y)

    # ---- Print summary ----
    print("=" * 60)
    print("SIMPLE LOGISTIC REGRESSION MODEL")
    print("=" * 60)
    print(f"Features: {feature_cols}")
    print(f"N trials used: {len(y)}")
    print(f"Base rate (response): {y.mean():.3f}")
    print()
    print("Coefficients (standardized):")
    for name, coef in zip(feature_cols, model.coef_[0]):
        print(f"  {name:>50s}  {coef:+.4f}")
    print(f"  {'intercept':>50s}  {model.intercept_[0]:+.4f}")
    print()

    y_pred_prob = model.predict_proba(X_scaled)[:, 1]
    y_pred = model.predict(X_scaled)

    try:
        auc = roc_auc_score(y, y_pred_prob)
        print(f"ROC AUC: {auc:.4f}")
    except ValueError:
        print("ROC AUC: could not compute (single class?)")

    print()
    print(classification_report(y, y_pred, target_names=["no-go", "go"]))

    # ---- Predicted vs observed gradient ----
    df_clean["predicted_prob"] = y_pred_prob
    stim = pd.to_numeric(df_clean.get("stimulus_x_normalized", df.loc[df_clean.index, "stimulus_x_normalized"]), errors="coerce")
    if stim.isna().all():
        stim = pd.to_numeric(df.loc[df_clean.index, "stimulus_x_normalized"], errors="coerce")
    df_clean["stimulus_x"] = stim.values if len(stim) == len(df_clean) else np.nan

    obs = df_clean.groupby("stimulus_x")["response_occurred"].mean()
    pred = df_clean.groupby("stimulus_x")["predicted_prob"].mean()

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(obs.index, obs.values, "o-", label="Observed", color="#2c7bb6")
    ax.plot(pred.index, pred.values, "s--", label="Predicted", color="#d7191c")
    ax.set_xlabel("Stimulus position (normalized)")
    ax.set_ylabel("P(response)")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Simple model: predicted vs observed gradient")
    ax.legend(frameon=False)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / "simple_model_gradient.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    return model


def fit_history_weighted_model(
    df: pd.DataFrame,
    output_dir: Union[str, Path] = "../outputs",
) -> LogisticRegression:
    """Fit a richer logistic regression using reinforcement-history features.

    Model specification::

        P(response) ~ similarity_gaussian
                      + similarity_exponential
                      + cumulative_similarity_weighted_reinforcement
                      + cumulative_reinforcers_at_target
                      + absolute_distance_from_target
                      + block_number
                      + rolling_response_rate
                      + rolling_reinforcement_rate
                      + lagged_response_1
                      + lagged_reinforcement_1
                      + trials_since_last_reinforcement

    This model captures more of the trial-by-trial dynamics but is still
    a logistic regression -- not a mechanistic model.

    Parameters
    ----------
    df : pd.DataFrame
        Modeling dataset.
    output_dir : str or Path
        Where to save summary plots.

    Returns
    -------
    LogisticRegression
        Fitted sklearn model.
    """
    feature_cols = [
        "similarity_gaussian",
        "similarity_exponential",
        "cumulative_similarity_weighted_reinforcement",
        "cumulative_reinforcers_at_target",
        "absolute_distance_from_target",
        "block_number",
        "rolling_response_rate",
        "rolling_reinforcement_rate",
        "lagged_response_1",
        "lagged_reinforcement_1",
        "trials_since_last_reinforcement",
    ]

    X, y, df_clean = _prepare_features(df, feature_cols)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=2000, solver="lbfgs")
    model.fit(X_scaled, y)

    # ---- Print summary ----
    print("=" * 60)
    print("HISTORY-WEIGHTED LOGISTIC REGRESSION MODEL")
    print("=" * 60)
    print(f"Features: {feature_cols}")
    print(f"N trials used: {len(y)}")
    print(f"Base rate (response): {y.mean():.3f}")
    print()
    print("Coefficients (standardized):")
    for name, coef in zip(feature_cols, model.coef_[0]):
        print(f"  {name:>50s}  {coef:+.4f}")
    print(f"  {'intercept':>50s}  {model.intercept_[0]:+.4f}")
    print()

    y_pred_prob = model.predict_proba(X_scaled)[:, 1]
    y_pred = model.predict(X_scaled)

    try:
        auc = roc_auc_score(y, y_pred_prob)
        print(f"ROC AUC: {auc:.4f}")
    except ValueError:
        print("ROC AUC: could not compute (single class?)")

    print()
    print(classification_report(y, y_pred, target_names=["no-go", "go"]))

    # ---- Predicted vs observed gradient ----
    df_clean["predicted_prob"] = y_pred_prob
    stim = pd.to_numeric(df_clean.get("stimulus_x_normalized", df.loc[df_clean.index, "stimulus_x_normalized"]), errors="coerce")
    if stim.isna().all():
        stim = pd.to_numeric(df.loc[df_clean.index, "stimulus_x_normalized"], errors="coerce")
    df_clean["stimulus_x"] = stim.values if len(stim) == len(df_clean) else np.nan

    obs = df_clean.groupby("stimulus_x")["response_occurred"].mean()
    pred = df_clean.groupby("stimulus_x")["predicted_prob"].mean()

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(obs.index, obs.values, "o-", label="Observed", color="#2c7bb6")
    ax.plot(pred.index, pred.values, "s--", label="Predicted", color="#d7191c")
    ax.set_xlabel("Stimulus position (normalized)")
    ax.set_ylabel("P(response)")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("History-weighted model: predicted vs observed")
    ax.legend(frameon=False)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / "history_model_gradient.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    return model


# ---- Extending to a diffusion model ----
#
# To move from logistic regression to a drift-diffusion model (DDM):
#
# 1. Install a DDM package:
#      pip install pyddm   # or hddm, ssms
#
# 2. Define drift rate as a function of stimulus similarity and
#    reinforcement history:
#
#      drift(x, t) = v_base
#                    + v_sim * similarity(x, S+)
#                    + v_reinf * cumulative_sim_weighted_reinf(t)
#
# 3. The DDM produces both choice probabilities AND RT distributions,
#    so you can fit both simultaneously.
#
# 4. Use hierarchical Bayesian estimation (e.g., via PyMC or Stan)
#    to share strength across participants.
#
# 5. Compare Gaussian vs exponential similarity kernels using WAIC/LOO.
#
# A minimal PyDDM example:
#
#   import pyddm
#
#   class SimilarityDrift(pyddm.Drift):
#       name = "Similarity-weighted drift"
#       required_parameters = ["v_base", "v_sim", "v_reinf"]
#       required_conditions = ["similarity", "cum_reinf"]
#
#       def get_drift(self, conditions, **kwargs):
#           return (self.v_base
#                   + self.v_sim * conditions["similarity"]
#                   + self.v_reinf * conditions["cum_reinf"])
#
#   model = pyddm.Model(
#       drift=SimilarityDrift(v_base=0, v_sim=1, v_reinf=0.5),
#       noise=pyddm.NoiseConstant(noise=1),
#       bound=pyddm.BoundConstant(B=1),
#       overlay=pyddm.OverlayNonDecision(nondectime=0.3),
#   )
#   pyddm.fit_adjust_model(sample=my_sample, model=model)


def main(
    modeling_csv: Optional[str] = None,
    output_dir: str = "../outputs",
) -> None:
    """Run both starter models end to end.

    Parameters
    ----------
    modeling_csv : str, optional
        Path to the modeling dataset CSV.  If None, looks for
        ``../outputs/modeling_dataset.csv``.
    output_dir : str
        Where to write outputs.
    """
    if modeling_csv is None:
        modeling_csv = str(Path(output_dir) / "modeling_dataset.csv")

    path = Path(modeling_csv)
    if not path.exists():
        print(f"Modeling dataset not found at {path}.")
        print("Run the pipeline first:  python -m analysis.run_pipeline <data.csv>")
        sys.exit(1)

    df = pd.read_csv(path)
    # Coerce booleans
    for col in ["response_occurred", "reinforcement_delivered"]:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)

    print()
    fit_simple_model(df, output_dir=output_dir)
    print()
    fit_history_weighted_model(df, output_dir=output_dir)
    print()
    print(f"Plots saved to {output_dir}/")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else "../outputs"
    main(modeling_csv=csv_path, output_dir=out)
