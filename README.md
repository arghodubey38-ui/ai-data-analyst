# AI Data Analyst

Upload a CSV, ask questions in plain English, get tables, interactive charts and a summary. Uses Groq's free API for the LLM.

## Stack
- **Pandas** – all calculations
- **Plotly** – interactive charts
- **Streamlit** – interface
- **Groq** – fast hosted open-source LLM (free tier)

## How it works
1. **LLM plans, doesn't code.** The model returns a JSON plan (`operation`, `group_column`, `value_column`, `date_column`, `frequency`). No arbitrary Python is executed.
2. **Pandas does the math.** `analysis.py` holds a small set of trusted functions: group sum/mean, count, trend over time, anomaly detection (z-score), summary stats. Column names and types are validated before running.
3. **Streamlit ships it.** Upload → ask → table + chart → plain-English summary (the LLM only sees the computed result).

## Setup
1. Get a free API key at https://console.groq.com/keys
2. Install and run:
```bash
pip install -r requirements.txt
python -m streamlit run app.py
```
3. Paste the key into the sidebar, or save it once in `.streamlit/secrets.toml` (copy `secrets.toml.example`):
```toml
GROQ_API_KEY = "gsk_..."
```
Click **Load sample data** to try it with `sample_data.csv`.

## Deploy free on Streamlit Community Cloud
1. Push this folder to a GitHub repo (do NOT commit `secrets.toml`; `.gitignore` already blocks it).
2. Go to https://share.streamlit.io, sign in with GitHub, click **Create app**.
3. Pick the repo, branch `main`, main file `app.py`.
4. Open **Advanced settings → Secrets** and paste: `GROQ_API_KEY = "gsk_..."`
5. Click **Deploy**. You get a public link.

## Example questions
- Total revenue by region
- Average units sold per product
- Show the monthly revenue trend
- Are there any outliers in revenue?
- Give me summary stats for revenue

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI |
| `planner.py` | Prompts Groq for a JSON plan and writes the summary |
| `analysis.py` | Trusted Pandas/Plotly functions + `run_plan` |
| `test_analysis.py` | Tests for the engine (`pytest`) |
| `sample_data.csv` | Demo dataset |

## Extending
Add a function in `analysis.py`, register it in `OPERATIONS` and `run_plan`, and describe it in the prompt in `planner.py`.
