import pandas as pd, pytest
from analysis import run_plan, PlanError

@pytest.fixture
def df():
    return pd.read_csv("sample_data.csv")

def test_group_sum(df):
    res, fig = run_plan(df, {"operation": "sum", "group_column": "region", "value_column": "revenue"})
    assert len(res) == 4 and fig is not None
    assert abs(res["revenue"].sum() - df["revenue"].sum()) < 1e-6

def test_overall_mean(df):
    res, _ = run_plan(df, {"operation": "mean", "value_column": "units"})
    assert abs(res["value"][0] - df["units"].mean()) < 1e-9

def test_trend(df):
    res, fig = run_plan(df, {"operation": "trend", "date_column": "date", "value_column": "revenue"})
    assert len(res) == 12 and fig is not None

def test_anomalies(df):
    res, _ = run_plan(df, {"operation": "anomalies", "value_column": "revenue"})
    assert len(res) >= 2

def test_summary(df):
    res, _ = run_plan(df, {"operation": "summary"})
    assert not res.empty

def test_bad_column(df):
    with pytest.raises(PlanError):
        run_plan(df, {"operation": "sum", "group_column": "nope", "value_column": "revenue"})

def test_bad_op(df):
    with pytest.raises(PlanError):
        run_plan(df, {"operation": "os.system"})
