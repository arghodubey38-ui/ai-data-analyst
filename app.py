import os

import pandas as pd
import streamlit as st

from analysis import PlanError, run_plan
from planner import DEFAULT_MODEL, get_plan, list_models, summarize

st.set_page_config(page_title="AI Data Analyst", page_icon="📊", layout="wide")
st.title("📊 AI Data Analyst")
st.caption("Upload a CSV, ask in plain English, get insights. Powered by Groq (LLM plans) + Pandas (calculations).")

def _secret_key() -> str:
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.environ.get("GROQ_API_KEY", "")


with st.sidebar:
    st.header("Settings")
    api_key = _secret_key() or st.text_input(
        "Groq API key", type="password", help="Free key at console.groq.com/keys"
    )
    model = DEFAULT_MODEL
    if api_key:
        try:
            models = list_models(api_key)
            if models:
                model = st.selectbox("Groq model", models)
        except Exception as e:
            st.warning(f"Could not load models: {e}")
            model = st.text_input("Groq model", value="llama-3.1-8b-instant")
    show_plan = st.checkbox("Show JSON plan", value=True)
    use_sample = st.button("Load sample data")

if use_sample:
    st.session_state["df"] = pd.read_csv("sample_data.csv")

uploaded = st.file_uploader("Upload a CSV", type="csv")
if uploaded:
    st.session_state["df"] = pd.read_csv(uploaded)

df = st.session_state.get("df")
if df is None:
    st.info("Upload a CSV or click **Load sample data** in the sidebar.")
    st.stop()

with st.expander(f"Data preview ({len(df):,} rows × {df.shape[1]} columns)", expanded=False):
    st.dataframe(df.head(50), use_container_width=True)

question = st.text_input("Ask a question about your data",
                         placeholder="e.g. Total revenue by region? / Show monthly revenue trend / Any outliers in revenue?")

if st.button("Analyze", type="primary") and question:
    try:
        with st.spinner("Planning..."):
            plan = get_plan(df, question, api_key, model=model)
    except Exception as e:
        st.error(f"Could not get a plan from Groq ({e}). Check your API key and model name.")
        st.stop()

    if show_plan:
        st.subheader("Plan")
        st.json(plan)

    try:
        result, fig = run_plan(df, plan)
    except PlanError as e:
        st.warning(f"The plan couldn't be executed: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.stop()

    st.subheader("Result")
    if result.empty:
        st.write("No rows matched (e.g. no anomalies found).")
    else:
        st.dataframe(result, use_container_width=True)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    try:
        with st.spinner("Summarizing..."):
            st.subheader("Summary")
            st.write(summarize(question, plan, result, api_key, model=model))
    except Exception as e:
        st.caption(f"Summary unavailable: {e}")
