"""Trusted analysis functions. The LLM never runs code; it only picks from these."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

OPERATIONS = ["sum", "mean", "count", "trend", "anomalies", "summary"]


class PlanError(ValueError):
    """Raised when a plan refers to something invalid."""


def _check_col(df: pd.DataFrame, col, kind: str | None = None) -> str:
    if col is None or col not in df.columns:
        raise PlanError(f"Column '{col}' not found. Available: {list(df.columns)}")
    if kind == "numeric" and not pd.api.types.is_numeric_dtype(df[col]):
        raise PlanError(f"Column '{col}' must be numeric.")
    return col


def group_agg(df, group_col, value_col, how="sum", top_n=20):
    _check_col(df, group_col)
    _check_col(df, value_col, "numeric")
    res = (
        df.groupby(group_col, dropna=False)[value_col]
        .agg(how)
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )
    fig = px.bar(res, x=group_col, y=value_col, title=f"{how.title()} of {value_col} by {group_col}")
    return res, fig


def overall_agg(df, value_col, how="sum"):
    _check_col(df, value_col, "numeric")
    val = getattr(df[value_col], how)()
    return pd.DataFrame({"metric": [f"{how} of {value_col}"], "value": [val]}), None


def count_rows(df, group_col=None):
    if group_col:
        _check_col(df, group_col)
        res = df[group_col].value_counts(dropna=False).reset_index()
        res.columns = [group_col, "count"]
        return res, px.bar(res.head(20), x=group_col, y="count", title=f"Rows per {group_col}")
    return pd.DataFrame({"metric": ["row count"], "value": [len(df)]}), None


def trend_over_time(df, date_col, value_col, freq="M"):
    _check_col(df, date_col)
    _check_col(df, value_col, "numeric")
    d = df[[date_col, value_col]].copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        raise PlanError(f"Column '{date_col}' could not be parsed as dates.")
    alias = {"D": "D", "W": "W", "M": "ME", "Q": "QE", "Y": "YE"}.get(freq, "ME")
    try:
        res = d.set_index(date_col)[value_col].resample(alias).sum().reset_index()
    except ValueError:  # older pandas
        res = d.set_index(date_col)[value_col].resample(freq).sum().reset_index()
    fig = px.line(res, x=date_col, y=value_col, markers=True, title=f"{value_col} over time")
    if len(res) >= 3:
        x = range(len(res))
        slope, intercept = pd.Series(res[value_col].values).pipe(
            lambda s: _linfit(list(x), s.values)
        )
        fig.add_trace(go.Scatter(x=res[date_col], y=[intercept + slope * i for i in x],
                                 mode="lines", name="trend", line=dict(dash="dot")))
    return res, fig


def _linfit(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    denom = sum((xi - mx) ** 2 for xi in x) or 1
    slope = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / denom
    return slope, my - slope * mx


def detect_anomalies(df, value_col, z_thresh=3.0):
    _check_col(df, value_col, "numeric")
    s = df[value_col]
    std = s.std()
    if not std or pd.isna(std):
        return df.iloc[0:0], px.histogram(df, x=value_col, title=f"Distribution of {value_col}")
    z = (s - s.mean()) / std
    out = df[z.abs() > z_thresh].assign(z_score=z[z.abs() > z_thresh].round(2))
    fig = px.box(df, y=value_col, points="outliers", title=f"Outliers in {value_col}")
    return out, fig


def summary_stats(df, value_col=None):
    if value_col:
        _check_col(df, value_col, "numeric")
        res = df[[value_col]].describe().T.reset_index().rename(columns={"index": "column"})
        return res, px.histogram(df, x=value_col, title=f"Distribution of {value_col}")
    res = df.describe(include="all").T.reset_index().rename(columns={"index": "column"})
    return res, None


def run_plan(df: pd.DataFrame, plan: dict):
    """Execute a validated JSON plan. Returns (result_df, figure_or_None)."""
    op = plan.get("operation")
    if op not in OPERATIONS:
        raise PlanError(f"Unsupported operation '{op}'. Choose from {OPERATIONS}.")
    g, v, d = plan.get("group_column"), plan.get("value_column"), plan.get("date_column")

    if op in ("sum", "mean"):
        return group_agg(df, g, v, op) if g else overall_agg(df, v, op)
    if op == "count":
        return count_rows(df, g)
    if op == "trend":
        return trend_over_time(df, d or g, v, plan.get("frequency", "M"))
    if op == "anomalies":
        return detect_anomalies(df, v)
    return summary_stats(df, v)
