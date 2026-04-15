# PropIQ — AI-Powered Real Estate Due Diligence

PropIQ enables structured due diligence on any residential or commercial real estate project in India. It aggregates RERA filings, MCA corporate data, complaint history, registered transaction data, and news sentiment into a single risk-scored profile for every project.

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url> propiq && cd propiq

# 2. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, POSTGRES_PASSWORD, and optionally ANTHROPIC_API_KEY

# 3. Start Postgres + Redis
docker compose up -d postgres redis

# 4. Install backend dependencies
cd backend && pip install -r requirements.txt

# 5. Run database migrations
alembic upgrade head

# 6. Seed test data (25 projects, 5 developers, risk scores)
python -m app.seed_data

# 7. Start backend
uvicorn app.main:app --reload
# → http://localhost:8000  (Swagger UI at /docs)

# 8. Start frontend (new terminal)
cd ../frontend && npm install && npm run dev
# → http://localhost:5173
```

### All-in-one with Docker Compose

```bash
cp .env.example .env  # fill in SECRET_KEY at minimum
docker compose up -d
# Postgres + Redis + Backend + Frontend all start together
# Seed data: docker compose exec backend python -m app.seed_data
```

Services after startup:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Adminer (DB GUI) | http://localhost:8080 |

---

## Architecture

```
propiq/
├── backend/                    FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Redis
│   ├── app/
│   │   ├── api/                Route handlers (auth, projects, developers, search, diligence, chat)
│   │   ├── core/               Security (JWT/bcrypt), middleware, exceptions, dependencies
│   │   ├── models/             SQLAlchemy ORM (Project, Developer, RiskScore, User, ...)
│   │   ├── schemas/            Pydantic request/response schemas
│   │   ├── services/           Business logic (RiskEngine, AppreciationModel, AIChat, ...)
│   │   ├── scrapers/           Data ingestion (RERA, MCA, news, pipeline)
│   │   └── seed_data.py        Test data seeder (25 projects, 5 developers)
│   ├── tests/                  pytest + httpx integration tests
│   └── alembic/                Database migrations
│
├── frontend/                   React 18 · TypeScript · Vite · Tailwind · TanStack Query · Zustand
│   └── src/
│       ├── pages/              HomePage, SearchPage, ProjectDetailPage, ComparePage, ...
│       ├── components/         UI primitives, project cards, risk gauges, charts
│       ├── hooks/              useProjectDetail, useSearchProjects, useCuratedDeals, ...
│       ├── services/           Axios API client with JWT injection
│       ├── store/              Zustand (auth, UI state)
│       └── types/              TypeScript interfaces matching backend schemas
│
├── docker-compose.yml          Local dev stack (postgres, redis, adminer, backend, frontend)
├── docker-compose.prod.yml     Production overrides
├── Makefile                    Common dev commands
└── .env.example                All environment variables with documentation
```

---

## API Documentation

- **Swagger UI**: http://localhost:8000/docs (development only)
- **ReDoc**: http://localhost:8000/redoc (development only)

### Core endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login → JWT |
| GET | `/api/v1/auth/me` | Current user profile |
| PUT | `/api/v1/auth/me` | Update profile |
| POST | `/api/v1/auth/watchlist/{id}` | Add to watchlist |
| DELETE | `/api/v1/auth/watchlist/{id}` | Remove from watchlist |
| GET | `/api/v1/projects/` | Search/filter projects |
| GET | `/api/v1/projects/{id}` | Full project detail |
| GET | `/api/v1/projects/{id}/risk-score` | Current risk score |
| POST | `/api/v1/projects/{id}/refresh` | Re-scrape + re-score |
| GET | `/api/v1/developers/{id}` | Developer profile |
| GET | `/api/v1/search/` | Full-text search |
| GET | `/api/v1/search/suggestions` | Autocomplete |
| GET | `/api/v1/diligence/curated` | Curated low/medium risk deals |
| GET | `/api/v1/diligence/compare` | Side-by-side comparison |
| POST | `/api/v1/diligence/report/{id}` | Generate PDF report (Pro) |
| POST | `/api/v1/chat/ask` | AI question answering |

---

## Risk Score Methodology

PropIQ computes a composite **0–100 score** (higher = safer) across 6 dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Legal & Compliance | 25% | RERA registration status, OC/CC, land encumbrance, active complaints |
| Developer Track Record | 25% | On-time delivery %, NCLT proceedings, MCA filing compliance, financial stress |
| Project Execution | 20% | Construction progress %, possession date slippage, units sold velocity |
| Location Quality | 15% | City tier, micromarket desirability, price vs registered transactions |
| Financial Indicators | 10% | Developer solvency, sold ratio, pricing data completeness |
| Macro Environment | 5% | Repo rate, GDP growth, CPI inflation, RE demand index |

**Risk bands:**
- 🟢 **Low** (80–100) — Safe to proceed with standard diligence
- 🟡 **Medium** (60–79) — Investigate flagged items before committing
- 🟠 **High** (40–59) — Significant risk; legal/financial verification required
- 🔴 **Critical** (0–39) — Multiple red flags; do not proceed without counsel

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | 24+ |
| Docker Compose | v2 |
| Python | 3.11+ |
| Node.js | 20+ |

---

## Environment Variables

Copy `.env.example` → `.env`. Required variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `POSTGRES_PASSWORD` | Postgres password (Docker Compose) |
| `REDIS_URL` | Redis connection string |

Optional but recommended:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API — enables AI chat and report summaries |
| `OPENAI_API_KEY` | GPT-4o fallback for AI chat |
| `NEWSAPI_KEY` | News sentiment data |

---

## Running Tests

```bash
cd backend

# Install test deps (already in requirements.txt)
pip install pytest pytest-asyncio httpx aiosqlite

# Run all tests
pytest tests/ -v

# Run a specific test module
pytest tests/test_risk_engine.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

Test database uses **SQLite in-memory** for speed — no Postgres required for tests.

---

## Seed Data

The seed script creates realistic test data:

- **5 developers**: Lodha Group (excellent), Prestige Estates (good), BuildRight Properties (troubled + NCLT), GreenArch Developers (new), Skyline Real Estate (critical/fraud signals)
- **25 projects** across Mumbai, Bengaluru, Pune — mix of residential/commercial and all 4 risk bands
- **Risk scores** generated by the RiskEngine (not hardcoded)
- **50+ transactions** across micromarkets (Powai, BKC, Whitefield, Koramangala, Hinjewadi, etc.)
- **30+ complaints** with varied statuses
- **20 news items** with positive/negative/critical sentiment
- **2 test users**: `free@propiq.test` / `pro@propiq.test` (password: `Test1234!`)

```bash
python -m app.seed_data
```

---

## Key Design Decisions

- **Async-first backend**: SQLAlchemy 2.0 async + asyncpg for non-blocking DB I/O under concurrent load
- **Score-never-deleted**: RiskScore rows are append-only; only `is_current=True` flag changes, preserving full history
- **Dual AI provider**: Anthropic Claude primary, OpenAI GPT-4o fallback — degrades gracefully if both keys are absent
- **Subscription gating at the HTTP layer**: `require_pro_subscription` dependency on `/diligence/report` routes; 403 → frontend shows upgrade modal
- **SQLite in tests**: avoids Postgres/Redis dependency in CI; aiosqlite driver + in-memory DB per test function for isolation
- **Redis rate limiting**: sliding-window counters per user+endpoint prevent API abuse and enforce tier quotas without a separate queue worker

---

## Data Sources

| Source | Data Collected |
|--------|---------------|
| MahaRERA, K-RERA, TSRERA | Project registrations, complaints, timelines |
| MCA21 | CIN, financial filings, director details, charges |
| IGR Maharashtra / Kaveri Karnataka | Registered sale deed transactions (price history) |
| NewsAPI / GNews | Developer and project news with sentiment analysis |
| eCourts | NCLT/DRT proceedings |

---

## License

Proprietary — © 2026 PropIQ Technologies Pvt. Ltd.
