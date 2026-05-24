import json
import os
import re

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


SYSTEM_PROMPT = """You are a query router. Given a list of available data sources and a user question, decide which source(s) to query.

RULES:
- "csv"  → quantitative questions: totals, averages, counts, filters, trends, rankings, comparisons across rows
- "pdf"  → qualitative questions: explanations, policies, reports, text content, definitions, summaries
- "both" → only when the question genuinely needs information from BOTH structured data AND documents
- When in doubt between csv and pdf, prefer "csv" for anything numerical or analytical
- When source is "csv" or "both", pick the single most relevant CSV file based on its column names

When source is "both" you MUST split into two independent sub-questions:
- csv_question: ask ONLY about the dataset columns (e.g. "What is our total revenue from Electronics?"). Must be answerable by SQL alone. NO mention of global/industry/external figures.
- pdf_question: ask ONLY about what the document contains (e.g. "What was Electronics' share of global e-commerce revenue according to the report?"). NO mention of our dataset.

Return JSON only, no markdown:
{"source": "csv" | "pdf" | "both", "reasoning": "one concise sentence", "csv_filename": "filename.csv or null", "csv_question": "SQL-only sub-question or null", "pdf_question": "document-only sub-question or null"}"""


def detect_intent(
    question: str,
    csv_files: list[dict],
    pdf_files: list[dict],
) -> dict:
    """
    Classify the question as targeting 'csv', 'pdf', or 'both'.
    csv_files: list of {filename, columns_info}
    pdf_files: list of {filename}
    Returns {"source": ..., "reasoning": ...}. Falls back to "both" on error.
    """
    csv_descriptions = []
    for f in csv_files:
        cols = ", ".join(c["name"] for c in f["columns_info"])
        csv_descriptions.append(f"  - {f['filename']} (columns: {cols})")

    pdf_descriptions = [f"  - {p['filename']}" for p in pdf_files]

    context = "Available data sources:\n"
    if csv_descriptions:
        context += "CSV tables:\n" + "\n".join(csv_descriptions) + "\n"
    if pdf_descriptions:
        context += "PDF documents:\n" + "\n".join(pdf_descriptions) + "\n"

    user_message = f"{context}\nQuestion: {question}"

    try:
        response = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=250,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)
        if result.get("source") not in ("csv", "pdf", "both"):
            return {"source": "both", "reasoning": "Could not determine source.", "csv_filename": None}
        return result
    except Exception:
        return {"source": "both", "reasoning": "Could not determine source, querying all.", "csv_filename": None}
