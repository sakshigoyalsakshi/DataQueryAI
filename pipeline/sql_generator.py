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


SYSTEM_PROMPT = """You are an expert SQL assistant for SQLite databases. Given a table schema and a natural language question, generate a valid SQL query.

RULES:
- Only generate SELECT statements. Never use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, or TRUNCATE.
- Use exact column names from the schema — do not invent columns.
- Add LIMIT 1000 if the query could return many rows and no LIMIT is specified.
- If the question cannot be answered from the available data, return an error object.
- Wrap table names in square brackets: [table_name].

RESPONSE FORMAT (JSON only, no markdown, no explanation outside JSON):
{
  "sql": "SELECT ...",
  "explanation": "One sentence describing what this query does",
  "viz_type": "bar" | "line" | "pie" | "scatter" | "table" | "text",
  "viz_config": {
    "x": "column_name",
    "y": "column_name",
    "title": "Chart title"
  }
}

OR on error:
{
  "error": "Reason why the question cannot be answered"
}

VIZ TYPE GUIDE:
- "bar": comparisons across categories (revenue by region, top products)
- "line": trends over time (monthly revenue, daily orders)
- "pie": proportions/percentages (% of orders by region)
- "scatter": correlation between two numeric columns
- "table": filtered/sorted lists of rows, multi-column results without aggregation
- "text": single number answers (total count, average, max)

FEW-SHOT EXAMPLES:

Q: "What is the total revenue by category?"
Schema has: category (text), revenue (float)
A: {"sql": "SELECT category, SUM(revenue) AS total_revenue FROM [table] GROUP BY category ORDER BY total_revenue DESC", "explanation": "Sums revenue grouped by product category.", "viz_type": "bar", "viz_config": {"x": "category", "y": "total_revenue", "title": "Total Revenue by Category"}}

Q: "Show all orders over $500 from Q4"
Schema has: revenue (float), date (text)
A: {"sql": "SELECT * FROM [table] WHERE revenue > 500 AND strftime('%m', date) IN ('10','11','12') LIMIT 1000", "explanation": "Filters orders where revenue exceeds $500 in Q4 months.", "viz_type": "table", "viz_config": {}}

Q: "How did monthly revenue change over time?"
Schema has: date (text), revenue (float)
A: {"sql": "SELECT strftime('%Y-%m', date) AS month, SUM(revenue) AS monthly_revenue FROM [table] GROUP BY month ORDER BY month", "explanation": "Aggregates total revenue per month.", "viz_type": "line", "viz_config": {"x": "month", "y": "monthly_revenue", "title": "Monthly Revenue Over Time"}}

Q: "What percentage of orders came from each region?"
Schema has: region (text)
A: {"sql": "SELECT region, COUNT(*) AS order_count FROM [table] GROUP BY region ORDER BY order_count DESC", "explanation": "Counts orders per region for proportion analysis.", "viz_type": "pie", "viz_config": {"x": "region", "y": "order_count", "title": "Orders by Region"}}

Q: "Total number of orders"
A: {"sql": "SELECT COUNT(*) AS total_orders FROM [table]", "explanation": "Counts all rows in the table.", "viz_type": "text", "viz_config": {"title": "Total Orders"}}
"""


def generate_sql(
    question: str, table_name: str, schema_str: str,
    chat_history: "list[dict] | None" = None,
) -> dict:
    """
    Call Groq LLM to generate SQL for the given question and schema.
    chat_history: list of {question, sql, explanation} for prior turns.
    Returns a dict with keys: sql, explanation, viz_type, viz_config
    OR a dict with key: error
    """
    user_message = f"""Schema:
{schema_str}

Question: {question}

Remember: use [{table_name}] as the table name in your SQL."""

    # Build message list — inject last 3 turns as conversation history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if chat_history:
        for turn in chat_history[-3:]:
            prior_user = (
                f"Schema:\n{schema_str}\n\nQuestion: {turn['question']}\n\nRemember: use [{table_name}]."
            )
            prior_assistant = json.dumps({
                "sql": turn["sql"],
                "explanation": turn["explanation"],
                "viz_type": turn.get("viz_type", "table"),
                "viz_config": turn.get("viz_config", {}),
            })
            messages.append({"role": "user", "content": prior_user})
            messages.append({"role": "assistant", "content": prior_assistant})
    messages.append({"role": "user", "content": user_message})

    client = _get_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.0,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        return result

    except json.JSONDecodeError:
        return {"error": "The AI returned an unexpected response format. Please try rephrasing your question."}
    except Exception as e:
        error_str = str(e)
        if "rate_limit" in error_str.lower():
            return {"error": "Rate limit reached. Please wait a moment and try again."}
        return {"error": f"AI service error: {error_str}"}
