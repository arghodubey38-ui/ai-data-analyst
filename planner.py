"""Asks a Groq-hosted LLM to turn a plain-English question into a JSON plan."""
from __future__ import annotations

import json
import re

import pandas as pd

from analysis import OPERATIONS

PLAN_KEYS = ["operation", "group_column", "value_column", "date_column", "frequency"]
DEFAULT_MODEL = "llama-3.3-70b-versatile"
PREFERRED = [DEFAULT_MODEL, "llama-3.1-8b-instant", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]
_NOT_CHAT = ("whisper", "tts", "guard", "playai", "distil-whisper", "embed")


def schema_text(df: pd.DataFrame) -> str:
    return "\n".join(f"- {c} ({df[c].dtype})" for c in df.columns)


def build_prompt(df: pd.DataFrame, question: str) -> str:
    return f"""You are a data analysis planner. Do NOT write code.
Reply with ONE JSON object only, no prose.

Dataset columns:
{schema_text(df)}

Sample rows:
{df.head(3).to_csv(index=False)}

JSON keys:
- "operation": one of {OPERATIONS}
- "group_column": column to group by, or null
- "value_column": numeric column to aggregate, or null
- "date_column": date column (for "trend"), or null
- "frequency": "D", "W", "M", "Q" or "Y" (for "trend"), default "M"

Use only column names listed above.

Question: {question}
JSON:"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("The model did not return JSON.")
    return json.loads(match.group(0))


def _client(api_key: str):
    from groq import Groq

    if not api_key:
        raise ValueError("Missing Groq API key.")
    return Groq(api_key=api_key)


def get_plan(df: pd.DataFrame, question: str, api_key: str, model: str = DEFAULT_MODEL) -> dict:
    resp = _client(api_key).chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": build_prompt(df, question)}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    plan = _extract_json(resp.choices[0].message.content)
    return {k: plan.get(k) for k in PLAN_KEYS}


def summarize(question: str, plan: dict, result: pd.DataFrame, api_key: str,
              model: str = DEFAULT_MODEL) -> str:
    """Plain-English summary. Only the computed result table is sent to the LLM."""
    prompt = (
        f"Question: {question}\nPlan: {json.dumps(plan)}\n"
        f"Computed result (trust these numbers, do not recalculate):\n"
        f"{result.head(15).to_csv(index=False)}\n\n"
        "Write a 2-3 sentence plain-English answer. Mention specific numbers."
    )
    resp = _client(api_key).chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}], temperature=0.2
    )
    return resp.choices[0].message.content.strip()


def list_models(api_key: str) -> list[str]:
    """Chat models this API key can actually use, best default first."""
    ids = [m.id for m in _client(api_key).models.list().data]
    ids = sorted(i for i in ids if not any(x in i.lower() for x in _NOT_CHAT))
    first = [m for m in PREFERRED if m in ids]
    return first + [i for i in ids if i not in first]
