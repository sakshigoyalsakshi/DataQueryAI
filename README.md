# DataQuery AI

An intelligent data query and visualization system that lets you ask natural language questions about CSV data and get answers as tables, charts, and insights — powered by Groq's Llama 3.3 70B.

## Live Demo

- **URL:** `<your-railway-url>`
- **Test credentials:** `demo@example.com` / `demo1234`
- **Pre-loaded dataset:** `ecommerce_sales.csv` (650 rows of e-commerce order data)

> Free-tier deployment may have a 30–60 second cold-start delay. Just refresh if the page is unresponsive.

---

## Sample Queries to Try

The pre-loaded `ecommerce_sales.csv` has columns: `order_id`, `date`, `product_name`, `category`, `region`, `quantity`, `unit_price`, `discount_pct`, `revenue`, `customer_id`.

| # | Query | Expected Result |
|---|-------|----------------|
| 1 | What is the total revenue by category? | Bar chart |
| 2 | Show all orders over $500 from Q4 | Table (filtered rows) |
| 3 | What are the top 10 products by total quantity sold? | Bar chart |
| 4 | Average order value by region | Bar chart |
| 5 | How did monthly revenue change over time? | Line chart |
| 6 | What percentage of orders came from each region? | Pie chart |
| 7 | Show products with a discount greater than 20% | Table |
| 8 | What is the total number of orders? | Single number |
| 9 | What is the average unit price per category? | Bar chart |
| 10 | Which months had the highest revenue in 2024? | Line or bar chart |

---

## Architecture

```
streamlit_app.py        ← Entry point, session management, page routing
│
├── auth/
│   ├── auth.py         ← Register, login, bcrypt hashing, JWT creation/decode
│   └── models.py       ← User dataclass
│
├── data/
│   ├── db.py           ← SQLite init, connection factory (read-only mode)
│   ├── csv_manager.py  ← CSV upload → sanitize → store as SQLite table
│   └── schema_inspector.py  ← Build schema strings for LLM prompts
│
├── pipeline/           ← NL-to-SQL pipeline
│   ├── sql_generator.py   ← Groq LLM call, prompt engineering, JSON parse
│   ├── sql_validator.py   ← Block destructive keywords, enforce SELECT-only
│   ├── query_executor.py  ← Run SQL on SQLite in read-only mode
│   └── viz_recommender.py ← Map LLM viz_type → Plotly figure
│
├── ui/
│   ├── login_page.py   ← Login / Register forms
│   ├── upload_page.py  ← File upload, preview, delete
│   └── query_page.py   ← NL input → SQL display → chart/table results
│
└── sample_data/
    └── ecommerce_sales.csv  ← 650-row pre-loaded dataset
```

### NL-to-SQL Pipeline

1. **Schema introspection** — extract column names, inferred types, and 3 sample values per column from the SQLite table
2. **Prompt construction** — inject schema into a system prompt with rules (SELECT-only, exact column names, LIMIT 1000) and 5 few-shot examples covering bar, line, pie, table, and text responses
3. **LLM call** — send to Groq `llama-3.3-70b-versatile` at temperature 0.0; model returns JSON: `{sql, explanation, viz_type, viz_config}`
4. **Validation** — regex block-list rejects DROP/DELETE/UPDATE/INSERT/TRUNCATE/ALTER/CREATE; confirm query starts with SELECT; verify table references are user-owned
5. **Execution** — run on SQLite opened in read-only URI mode (`file:app.db?mode=ro`)
6. **Rendering** — map `viz_type` to Plotly Express chart (bar/line/pie/scatter) or `st.dataframe` / `st.metric`

### Database Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,      -- uuid4
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP
);

CREATE TABLE files (
    id TEXT PRIMARY KEY,      -- uuid4
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    table_name TEXT NOT NULL, -- "u{uid8}_{fid8}" — opaque, not guessable
    row_count INTEGER,
    columns_info TEXT,        -- JSON: [{name, type, samples}]
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Each uploaded CSV becomes a dynamic table named by table_name
```

### Authentication

- Email/password with bcrypt hashing
- JWT tokens (HS256, 24-hour expiry) stored in `st.session_state`
- Per-user data isolation: every CSV table is named with a user-scoped opaque ID; the SQL validator checks that generated queries only reference the current user's tables

---

## Local Setup

### Prerequisites

- Python 3.11+
- [Groq API key](https://console.groq.com) (free tier)

### Steps

```bash
git clone <repo-url>
cd JobAssigment

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and set GROQ_API_KEY and SECRET_KEY

# Generate sample data (run once)
python generate_sample_data.py

# Start the app
streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). The app auto-creates the DB, demo user, and loads sample data on first run.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | From [console.groq.com](https://console.groq.com) |
| `SECRET_KEY` | Yes | Random string for JWT signing |
| `DB_PATH` | No | SQLite file path (default: `app.db`) |

---

## Deployment (Railway)

1. Push repo to GitHub
2. Create new Railway project → **Deploy from GitHub repo**
3. Add environment variables: `GROQ_API_KEY`, `SECRET_KEY`
4. Railway auto-detects the `Dockerfile` and deploys
5. The app seeds the demo user and sample data on startup

Alternatively, deploy on **Render** as a Web Service using the same Dockerfile. Set the start command to:
```
streamlit run streamlit_app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true
```

---

## Architecture Decisions

**Why Streamlit over React + FastAPI?**  
Given the 8–12 hour scope, a single-service Python stack lets me focus time on the NL-to-SQL pipeline quality rather than API wiring. Streamlit's built-in Plotly integration and session state cover all UI needs without a separate frontend build step.

**Why SQLite?**  
Zero-config, file-based, and perfectly sufficient for CSVs up to 100K rows. Dynamic tables per user avoid schema migrations. For 1M+ rows, the natural upgrade is PostgreSQL with per-user schemas.

**Why Groq (Llama 3.3 70B)?**  
Free tier, fast inference (~1–2s), and Llama 3.3 70B performs on par with GPT-4o-mini for structured JSON SQL generation. Temperature 0.0 keeps output deterministic.

**SQL safety approach**  
Two-layer guard: (1) regex block-list on destructive keywords, (2) read-only SQLite connection URI. This prevents both intentional injection and LLM hallucination of mutations. Not production-grade injection prevention — as noted in the spec, this is about guardrails.

**Trade-offs made**  
- No streaming (single-shot LLM call is simpler and fast enough)
- No conversational context / follow-up questions (would require history management)
- SQLite not suitable for concurrent write load (acceptable for demo scale)

**With more time I would add:**  
- Streaming token output from Groq
- Conversational query context (pass last 3 Q&A pairs to LLM)
- Data profiling on upload (summary stats, null counts, value distributions)
- Multi-file JOIN queries
- Unit tests for the SQL validator and generator
- PostgreSQL for production deployments

---

## AI Tool Usage

This project was built with **Claude Code** (AI coding assistant). Key areas of AI assistance:
- Boilerplate for bcrypt/JWT auth flow
- Prompt engineering for the NL-to-SQL system prompt and few-shot examples
- Plotly chart configuration patterns

Overridden AI suggestions:
- AI initially suggested storing CSVs as flat files with separate metadata; switched to loading directly into SQLite tables for simpler querying
- AI suggested a more complex token refresh flow; simplified to single 24-hour JWT given demo scope

---

## Known Limitations

- Cold-start delay on free-tier hosting (30–60 seconds)
- Groq rate limits on free tier (~30 req/min) — if hit, wait a moment and retry
- Complex multi-table JOINs across uploaded files are not yet supported
- SQLite file is ephemeral on Railway/Render free tiers (resets on redeploy) — use Railway volumes or switch to PostgreSQL for persistence
