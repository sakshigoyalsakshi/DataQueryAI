# DataQuery AI

An intelligent data query and visualization system that lets you ask natural language questions about CSV data and get answers as tables, charts, and insights — powered by Groq's Llama 3.3 70B.

## Live Demo

- **URL:** https://dataqueryai-production.up.railway.app/
- **Test credentials:** `demo@example.com` / `demo1234`
- **Pre-loaded CSV:** `ecommerce_sales.csv` (650 rows of e-commerce order data)
- **Pre-loaded PDF:** `business_report.pdf` (Global E-commerce Industry Report 2023, 8 pages)

> Free-tier deployment may have a 30–60 second cold-start delay. Just refresh if the page is unresponsive.

---

## Bonus Features Implemented

Two bonus features from the assignment have been implemented:

### 1. Document Q&A / RAG (PDF Upload)
Upload PDF documents and ask natural language questions — answers include page-level citations showing exactly where the information came from. Built with:
- **pypdf** for text extraction
- **ChromaDB** for vector storage and semantic search (persisted to Railway volume)
- **Groq Llama 3.3 70B** for answer generation with strict source-only instructions

### 2. Conversational Follow-up Context
The Query Data page maintains a full conversation thread per dataset. The last 3 Q&A turns are passed to the LLM as context, enabling natural follow-up questions such as:
- *"What is total revenue by category?"* → bar chart
- *"Now show only Electronics and Clothing"* → filtered bar chart
- *"Sort that by revenue descending"* → reordered result

---

## Sample Queries — CSV (Query Data page)

The pre-loaded `ecommerce_sales.csv` has columns: `order_id`, `date`, `product_name`, `category`, `region`, `quantity`, `unit_price`, `discount_pct`, `revenue`, `customer_id`.

| # | Query | Expected Result |
|---|-------|----------------|
| 1 | What is the total revenue by category? | Bar chart |
| 2 | Show all orders over $500 from Q4 | Table |
| 3 | What are the top 10 products by total quantity sold? | Bar chart |
| 4 | Average order value by region | Bar chart |
| 5 | How did monthly revenue change over time? | Line chart |
| 6 | What percentage of orders came from each region? | Pie chart |
| 7 | Show products with a discount greater than 20% | Table |
| 8 | What is the total number of orders? | Single number |
| 9 | What is the average unit price per category? | Bar chart |
| 10 | Which months had the highest revenue in 2024? | Bar chart |

**Follow-up example:** After query 1, try *"Now filter to show only the top 3 categories"* or *"Show the same but as a pie chart"*.

---

## Sample Queries — Document Q&A (RAG page)

The pre-loaded `business_report.pdf` is a Global E-commerce Industry Report 2023 covering market size, regional breakdown, product categories, consumer trends, and 2024 projections.

| # | Question | Expected Answer |
|---|----------|----------------|
| 1 | What was the global e-commerce market size in 2023? | $5.8 trillion (p.1) |
| 2 | Which region had the highest e-commerce sales? | Asia-Pacific at $2.9T (p.2) |
| 3 | What percentage of transactions were mobile? | 60% (p.1) |
| 4 | What is the projected market size for 2024? | $6.4 trillion (p.8) |
| 5 | Which product category generated the most revenue? | Electronics at $1.04T (p.3) |
| 6 | What was the global cart abandonment rate? | 69.8% (p.1) |
| 7 | How did Amazon perform in 2023? | $514B GMV, 37.6% market share (p.7) |
| 8 | What is the average last-mile delivery cost? | $10.10 per package (p.6) |

---

## Architecture

```
streamlit_app.py        <- Entry point, session management, page routing
|
+-- auth/
|   +-- auth.py         <- Register, login, bcrypt hashing, JWT creation/decode
|   +-- models.py       <- User dataclass
|
+-- data/
|   +-- db.py           <- SQLite init, connection factory (read-only mode)
|   +-- csv_manager.py  <- CSV upload -> sanitize -> store as SQLite table
|   +-- schema_inspector.py  <- Build schema strings for LLM prompts
|
+-- pipeline/           <- NL-to-SQL pipeline
|   +-- sql_generator.py   <- Groq LLM call, prompt engineering, conversation history
|   +-- sql_validator.py   <- Block destructive keywords, enforce SELECT-only
|   +-- query_executor.py  <- Run SQL on SQLite in read-only mode
|   +-- viz_recommender.py <- Map LLM viz_type -> Plotly figure
|
+-- rag/                <- Document Q&A pipeline
|   +-- pdf_parser.py   <- pypdf text extraction, chunking (1200 char / 150 overlap)
|   +-- vector_store.py <- ChromaDB wrapper (per-user collections, persistent)
|   +-- rag_pipeline.py <- Retrieve top-6 chunks, generate answer with citations
|
+-- ui/
|   +-- login_page.py   <- Login / Register forms with cookie-based persistence
|   +-- upload_page.py  <- CSV file upload, preview, delete
|   +-- query_page.py   <- Chat-style NL query with conversation history
|   +-- rag_page.py     <- PDF upload, indexing, and Q&A chat interface
|
+-- sample_data/
    +-- ecommerce_sales.csv     <- 650-row pre-loaded e-commerce dataset
    +-- business_report.pdf     <- 8-page e-commerce industry report for RAG demo
```

### NL-to-SQL Pipeline

1. **Schema introspection** — extract column names, inferred types, and 3 sample values per column from the SQLite table
2. **Prompt construction** — inject schema into a system prompt with rules (SELECT-only, exact column names, LIMIT 1000) and 5 few-shot examples covering bar, line, pie, table, and text responses
3. **Conversation history** — last 3 Q&A turns injected as prior messages so the LLM understands follow-up references
4. **LLM call** — send to Groq `llama-3.3-70b-versatile` at temperature 0.0; model returns JSON: `{sql, explanation, viz_type, viz_config}`
5. **Validation** — regex block-list rejects DROP/DELETE/UPDATE/INSERT/TRUNCATE/ALTER/CREATE; confirm query starts with SELECT; verify table references are user-owned
6. **Execution** — run on SQLite opened in read-only URI mode (`file:app.db?mode=ro`)
7. **Rendering** — map `viz_type` to Plotly Express chart (bar/line/pie/scatter) or `st.dataframe` / `st.metric`

### RAG Pipeline

1. **PDF parsing** — pypdf extracts text page by page; split into 1200-character chunks with 150-character overlap to preserve context across boundaries
2. **Indexing** — chunks embedded and stored in a per-user ChromaDB collection (cosine similarity space)
3. **Retrieval** — question embedded at query time; top-6 most similar chunks retrieved
4. **Generation** — Groq LLM generates an answer strictly from retrieved excerpts; cites `[filename, page X]` for every claim
5. **Persistence** — ChromaDB stored alongside SQLite on the Railway volume at `/data/chroma_db`

### Database Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP
);

CREATE TABLE files (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    table_name TEXT NOT NULL,   -- "u{uid8}_{fid8}" opaque, not guessable
    row_count INTEGER,
    columns_info TEXT,          -- JSON: [{name, type, samples}]
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE pdfs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    page_count INTEGER,
    chunk_count INTEGER,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Each uploaded CSV becomes a dynamic SQLite table named by table_name
```

### Authentication

- Email/password with bcrypt hashing
- JWT tokens (HS256, 24-hour expiry) persisted in browser cookie via `streamlit-cookies-controller` — survives page refreshes
- Per-user data isolation: CSV tables use opaque user-scoped IDs; SQL validator verifies table ownership; ChromaDB uses separate collections per user

---

## Local Setup

### Prerequisites

- Python 3.9+
- [Groq API key](https://console.groq.com) (free tier)

### Steps

```bash
git clone <repo-url>
cd JobAssigment

python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env: set GROQ_API_KEY, SECRET_KEY, and DB_PATH=app.db

# Generate sample data (run once)
python generate_sample_data.py
python generate_test_data.py

# Start the app
streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). The app auto-creates the DB, demo user, and pre-loads both sample files on first run.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | From [console.groq.com](https://console.groq.com) |
| `SECRET_KEY` | Yes | Random string for JWT signing (`python3 -c "import secrets; print(secrets.token_hex(32))"`) |
| `DB_PATH` | No | SQLite file path — use `app.db` locally, `/data/app.db` on Railway with a volume |

---

## Deployment (Railway)

1. Push repo to GitHub
2. Create new Railway project → **Deploy from GitHub repo**
3. Add environment variables: `GROQ_API_KEY`, `SECRET_KEY`, `DB_PATH=/data/app.db`
4. Go to service → **Volumes** → add volume mounted at `/data` for persistent storage
5. Railway auto-detects the `Dockerfile` and deploys
6. The app seeds the demo user and pre-loads sample data on startup

---

## Architecture Decisions

**Why Streamlit over React + FastAPI?**
Given the 8-12 hour scope, a single-service Python stack lets me focus time on the NL-to-SQL pipeline quality rather than API wiring. Streamlit's built-in Plotly integration and session state cover all UI needs without a separate frontend build step.

**Why SQLite + ChromaDB?**
Both are file-based and zero-config. SQLite handles structured CSV data; ChromaDB handles vector embeddings for RAG. Both persist to the same Railway volume at `/data/`. For 1M+ rows, the natural upgrade is PostgreSQL with per-user schemas.

**Why Groq (Llama 3.3 70B)?**
Free tier, fast inference (~1-2s), and Llama 3.3 70B performs on par with GPT-4o-mini for structured JSON SQL generation. Temperature 0.0 keeps SQL output deterministic.

**SQL safety approach**
Two-layer guard: (1) regex block-list on destructive keywords, (2) read-only SQLite connection URI. This prevents both intentional injection and LLM hallucination of mutations.

**RAG chunking strategy**
1200-character chunks with 150-character overlap. Larger chunks (vs the common 500-char default) preserve paragraph-level context, which is critical for business documents where a single fact may span multiple sentences.

**Trade-offs made**
- No streaming (single-shot LLM call is fast enough at ~1-2s)
- No multi-file SQL JOINs across uploaded CSVs
- SQLite not suitable for high concurrent write load (acceptable for demo scale)
- No intent detection to automatically route between CSV and PDF queries

**With more time I would add:**
- Streaming token output from Groq
- Data profiling on CSV upload (summary stats, null counts, value distributions)
- Multi-file JOIN queries across uploaded CSVs
- Intent detection to route questions to CSV or PDF automatically
- Unit tests for the SQL validator, generator, and RAG pipeline
- PostgreSQL for production-scale deployments

---

## AI Tool Usage

This project was built with **Claude Code** (AI coding assistant). Key areas of AI assistance:
- Boilerplate for bcrypt/JWT auth flow and cookie persistence
- Prompt engineering for the NL-to-SQL system prompt and few-shot examples
- ChromaDB integration and RAG pipeline structure
- Plotly chart configuration patterns

Overridden AI suggestions:
- AI initially suggested storing CSVs as flat files with separate metadata; switched to loading directly into SQLite tables for simpler querying
- AI suggested a more complex token refresh flow; simplified to single 24-hour JWT given demo scope
- AI defaulted to 500-char RAG chunks; increased to 1200 chars after observing retrieval misses on multi-sentence facts

---

## Known Limitations

- Cold-start delay on free-tier hosting (30-60 seconds)
- Groq rate limits on free tier (~30 req/min) — if hit, wait a moment and retry
- Complex multi-table JOINs across uploaded CSV files are not supported
- RAG does not work on image-based or scanned PDFs (text extraction requires selectable text)
- User sessions expire after 24 hours (JWT expiry)
