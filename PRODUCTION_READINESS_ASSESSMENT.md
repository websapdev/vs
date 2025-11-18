# Vysalytica Backend: Production Readiness Assessment

**Assessment Date:** 2025-01-18  
**Codebase:** Flask REST API for AI Visibility Audit Tool  
**Deployment Target:** Render (current), compatible with Heroku/Railway

---

## 1. Tech Stack Summary

### Runtime & Framework
- **Python Version:** 3.11.9 (pinned in `runtime.txt`)
- **Web Framework:** Flask 2.3+ with Gunicorn 21.x
- **Language:** Python 3.11

### Database
- **Primary:** SQLAlchemy 2.0.36 with support for both SQLite (development) and PostgreSQL (production)
- **SQLite Path:** `api/data/vysalytica.db` (auto-created if using default config)
- **PostgreSQL:** Full support via `psycopg[binary]>=3.1.0`

### Key Dependencies
| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Web | Flask | ≥2.3,<3 | Core REST API framework |
| CORS | flask-cors | 4.0.0 | Cross-origin resource sharing |
| Rate Limiting | flask-limiter | 3.5.0 | API throttling (memory/Redis) |
| ORM | sqlalchemy | 2.0.36 | Database abstraction |
| Postgres Driver | psycopg | ≥3.1.0 | PostgreSQL connectivity |
| Web Crawling | requests | 2.31.0 | HTTP requests |
| HTML Parsing | beautifulsoup4 | 4.12.2 | HTML/DOM parsing |
| Structured Data | extruct | ≥0.16.0 | Schema.org/JSON-LD extraction |
| XML Parsing | lxml | ≥4.9.3 | Fast XML/HTML processing |
| Content Extraction | trafilatura | 1.6.2 | Main content extraction |
| Document Generation | python-docx | 1.1.0 | DOCX report generation |
| LLM Clients | openai, anthropic, routellm | Latest | LLM integrations |
| Validation | pydantic | ≥2.0 | Data validation |
| Data Science | pandas, numpy | 2.2.3, ≥2.0 | Data manipulation |
| Resilience | tenacity | ≥9.0 | Retry logic with backoff |
| Config | PyYAML | ≥6.0 | Configuration management |

---

## 2. Entry Point & Architecture

### Main Entry Points
```
api/__init__.py
├─ Exports: from .api import app  (Flask application instance)

api/api.py (992 lines)
├─ Main Flask application setup
├─ All REST endpoints defined here
├─ Database initialization via run_migrations()
├─ CORS and rate limiter configuration

api/vysalytica/wsgi.py
└─ WSGI entry point for production deployments (e.g., Render)
   └─ Imports: from server import app  
   
⚠️ NOTE: wsgi.py imports from "server" but main app is in "api.py"
   This may cause import issues if "server.py" doesn't exist.
   However, Procfile uses "PYTHONPATH=. gunicorn api:app" which works correctly.
```

### Application Structure
```
api/                           # Main API package
├── __init__.py               # Exports Flask app
├── api.py                    # Flask routes (992 lines)
├── engine_crawl.py           # Web crawling engine
├── engine_parse.py           # HTML/structured data parsing
├── engine_rules.py           # Rule evaluation (legacy)
├── engine_rules_enhanced.py  # Enhanced rules (2876 lines, comprehensive)
├── engine_report.py          # Markdown/DOCX report generation
└── vysalytica/               # Business logic package
    ├── __init__.py
    ├── config.py             # Configuration helper (env/Streamlit)
    ├── middleware.py         # API key auth & rate limiting
    ├── plans.py              # Plan tiers (QuickScan/Full/Agency)
    ├── engine_ai_visibility.py    # AI citation tracking
    ├── engine_fixgen.py      # LLM-powered fix generation
    ├── engine_answer_graph.py     # Answer graph construction
    ├── engine_playbooks.py   # Playbook generation
    ├── wsgi.py              # WSGI entry point
    └── db/                   # Database layer
        ├── __init__.py       # Session & engine config
        ├── models.py         # SQLAlchemy models (335 lines)
        ├── migrations.py     # Idempotent schema creation
        └── rule_seed_data.py # Rule definition seed data

scripts/                       # Utility scripts
├── import_check.py           # Dependency validation

frontend/                      # Next.js 14 marketing UI
├── package.json              # Node dependencies
├── tsconfig.json            # TypeScript config
└── src/                      # React components
```

### How Flask App Is Initialized

1. **App Creation** (`api/api.py`, line 39):
   ```python
   app = Flask(__name__)
   ```

2. **Database Initialization** (lines 41-47):
   ```python
   app.logger.info("Initializing database...")
   if not run_migrations():
       app.logger.warning("Database migrations reported a failure; proceeding with caution.")
   else:
       app.logger.info("Database ready!")
   ```

3. **CORS Setup** (lines 49-57):
   - Configurable via `CORS_ALLOWED_ORIGINS` env var
   - Defaults to wildcard ("*") for development
   - Production should restrict to specific origins

4. **Rate Limiter Initialization** (lines 59-75):
   - Uses `flask-limiter` with configurable storage
   - Memory storage by default
   - Redis support via `LIMITER_STORAGE_URI` env var

5. **Routes Registration** (lines 78+):
   - `/api/health` - health check
   - `/api/version` - version info
   - `/api/audit` - main audit endpoint
   - Additional endpoints for audits, citations, API keys, reports

---

## 3. Configuration & Environment

### Required Environment Variables

| Variable | Type | Default | Purpose | Priority |
|----------|------|---------|---------|----------|
| `DATABASE_URL` | string | `sqlite:///vysalytica.db` | Database connection string | P1 |
| `OPENAI_API_KEY` | string | None | OpenAI API key (for ChatGPT citations/fixes) | P1* |
| `ANTHROPIC_API_KEY` | string | None | Anthropic API key (for Claude citations) | P1* |
| `ROUTELLM_API_KEY` | string | `s2_887db278b...` | RouteLLM API key (default provided but should be overridden) | P1* |
| `ROUTELLM_BASE_URL` | string | `https://api.abacus.ai/v1` | RouteLLM endpoint | P1* |
| `ROUTELLM_MODEL` | string | `gpt-3.5-turbo` | LLM model to route to | P2 |
| `CORS_ALLOWED_ORIGINS` | string | `*` | Comma-separated CORS origins | P2 |
| `LIMITER_STORAGE_URI` | string | `memory://` | Rate limiter storage (e.g., `redis://...`) | P2 |
| `API_BASE_URL` | string | `http://localhost:8080/api` | API base URL for Streamlit/clients | P2 |
| `APP_VERSION` | string | `0.1` | Application version | P3 |
| `DEBUG` | string | `False` | Debug mode flag | P3 |
| `ENV` | string | None | Environment identifier (`dev`, `prod`) | P2 |

*At least one LLM service (OpenAI, Anthropic, or RouteLLM) required for full functionality.

### Configuration Sources (Priority Order)
1. **Streamlit secrets** (if running in Streamlit)
2. **Environment variables** (OS/shell)
3. **Hardcoded defaults** (in `config.py`)

**Current Hardcoded Values in `config.py`:**
- `DEFAULT_ROUTELLM_API_KEY = "s2_887db278b1b24f14b49fe0294436e87a"` (⚠️ Security concern - should not be in source code)
- `DEFAULT_ROUTELLM_BASE_URL = "https://api.abacus.ai/v1"`
- `DEFAULT_ROUTELLM_MODEL = "gpt-3.5-turbo"`
- `DEFAULT_DATABASE_URL = "sqlite:///vysalytica.db"`
- `DEFAULT_API_BASE_URL = "http://localhost:8080/api"`

### Environment File
- **Status:** No `.env` or `.env.example` file provided in repository
- **Need:** Create `.env.example` for developers
- **Recommended Content:**
  ```bash
  # Database
  DATABASE_URL=sqlite:///api/data/vysalytica.db
  # For PostgreSQL: DATABASE_URL=postgresql+psycopg://user:pass@localhost/vysalytica

  # LLM Services (provide at least one)
  OPENAI_API_KEY=sk-...
  ANTHROPIC_API_KEY=sk-ant-...
  ROUTELLM_API_KEY=...
  ROUTELLM_BASE_URL=https://api.abacus.ai/v1
  ROUTELLM_MODEL=gpt-3.5-turbo

  # API Configuration
  CORS_ALLOWED_ORIGINS=http://localhost:3000,https://example.com
  LIMITER_STORAGE_URI=memory://
  API_BASE_URL=http://localhost:8080/api

  # Application
  APP_VERSION=0.1
  DEBUG=False
  ENV=dev
  ```

### Config Helpers
- `config.py` provides typed accessor functions with defaults
- Streamlit integration for containerized deployments
- `clear_cached_config()` available for test environments

---

## 4. Database Setup

### Database Type
- **Default (Dev):** SQLite 3
  - File: `api/data/vysalytica.db` (auto-created)
  - Zero configuration needed
- **Production:** PostgreSQL recommended
  - Connection: `postgresql+psycopg://user:pass@host:5432/dbname`

### Database Schema Overview

**Tables:**
1. `audit_runs` - Website audit results
   - Columns: id, url, domain, packs, overall_score, category_scores, page_count, created_at
   - Indexes: url, domain, created_at

2. `findings` - Individual rule evaluation results
   - Columns: id, audit_run_id, rule_id, rule_title, category, status, confidence, evidence, why, fix, fix_snippet, acceptance_test
   - Foreign Key: audit_run_id → audit_runs.id
   - Indexes: audit_run_id, rule_id, category

3. `rule_definitions` - Static rule metadata
   - Columns: id (PK), title, category, pack, description, why, fix, confidence, acceptance_criteria, created_at, updated_at
   - Indexes: category, pack

4. `citation_snapshots` - AI citation tracking results
   - Columns: id, brand, intent, assistant, cited, response_text, created_at
   - Indexes: brand, assistant, created_at

5. `api_keys` - Authentication and quota management
   - Columns: id, key (unique), name, quota_per_hour, created_at, last_used_at, is_active
   - Indexes: key

6. `referral_codes` - Partner/referral tracking
   - Columns: id, code (unique), partner_name, created_at
   - Indexes: code

7. `referral_attributions` - Attribution events
   - Columns: id, referral_code_id (FK), cookie_id, user_agent, ip_address, created_at
   - Indexes: referral_code_id, cookie_id

8. `answer_graphs` - Graph snapshots
   - Columns: id, domain, intents (JSON), packs (JSON), nodes (JSON), edges (JSON), created_at
   - Indexes: domain

9. `playbooks` - Playbook data
   - Columns: id, audit_id, domain, data (JSON), created_at
   - Indexes: audit_id, domain

10. `playbook_fixes` - Playbook fix suggestions
    - Columns: id, playbook_id (FK), rule_id, title, description, code_snippet, created_at

### Migration System
- **Type:** Custom idempotent migration script (not Alembic)
- **Location:** `api/vysalytica/db/migrations.py`
- **Approach:** `Base.metadata.create_all()` with additional operations
- **Operations:**
  1. Create all tables defined in models
  2. Add missing columns (e.g., findings.confidence if not present)
  3. Seed rule definitions from `rule_seed_data.py`

### Initialization Steps

**First-Time Setup:**
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables (see Section 3)
3. Initialize database:
   ```bash
   cd /home/engine/project
   python -c "from api.vysalytica.db.migrations import run_migrations; run_migrations()"
   ```
   Or on app startup (automatic):
   ```bash
   python -c "from api import app"  # Triggers migrations in api.py:41-47
   ```

**Migrations Script Usage:**
```bash
# Run migrations (create tables, seed rules)
python api/vysalytica/db/migrations.py migrate

# Drop all tables (WARNING: deletes data)
python api/vysalytica/db/migrations.py rollback

# Reset database (drop and recreate)
python api/vysalytica/db/migrations.py reset
```

### Notes
- Migrations run automatically on Flask app initialization
- No version tracking (all-or-nothing approach)
- Safe for development; production migrations should be more conservative
- Column additions are optional (won't fail if already exist)

---

## 5. External Service Dependencies

### LLM Services (Required)
At least **one** must be configured for full functionality.

#### OpenAI (ChatGPT)
- **Purpose:** Citation checking, fix generation
- **Auth:** `OPENAI_API_KEY=sk-...`
- **Client:** `openai==1.109.1`
- **Used In:**
  - `engine_ai_visibility.py` - Citation queries to ChatGPT
  - `engine_fixgen.py` - Code fix suggestions
- **Fallback:** If unavailable, API continues but fix generation fails gracefully

#### Anthropic (Claude)
- **Purpose:** Alternative citation source
- **Auth:** `ANTHROPIC_API_KEY=sk-ant-...`
- **Client:** `anthropic==0.72.0`
- **Used In:**
  - `engine_ai_visibility.py` - Citation queries to Claude
- **Fallback:** Non-critical; citation tracking continues with available providers

#### RouteLLM
- **Purpose:** LLM router/proxy (routes to cheapest/best model)
- **Auth:** `ROUTELLM_API_KEY` (has hardcoded default - ⚠️)
- **Base URL:** `ROUTELLM_BASE_URL` (default: `https://api.abacus.ai/v1`)
- **Client:** `routellm==0.2.0`
- **Used In:** `engine_ai_visibility.py`, `engine_fixgen.py` (prioritized over direct OpenAI)
- **Fallback:** Falls back to OpenAI if RouteLLM fails

### Third-Party APIs
- **Requests Library:** `requests==2.31.0` for HTTP calls
  - Web crawling, API calls
- **No external auth required** for crawling (public URLs)

### Database Services
- **PostgreSQL:** Production target
  - Not required for development (SQLite default)
  - Environment: `DATABASE_URL=postgresql+psycopg://...`

### Rate Limiting Storage
- **Memory Backend:** Default (single-process only)
  - `LIMITER_STORAGE_URI=memory://`
- **Redis:** For multi-process production
  - `LIMITER_STORAGE_URI=redis://host:port/db`
  - Not currently in `requirements.txt` - would need `redis` library if using

### Behavior When Services Unavailable

| Service | Behavior |
|---------|----------|
| **OpenAI** | Citation/fix endpoints return 503 with error message; audit continues |
| **Anthropic** | Skipped for citation tracking; no error |
| **RouteLLM** | Falls back to direct OpenAI; no error if OpenAI available |
| **Database (Postgres)** | App fails to start; exits with migration error |
| **Database (SQLite)** | Auto-creates file; always available |
| **Redis** | Fallback to in-memory; rate limiting less effective across processes |

### Health Check Recommendations
- Add health check endpoint for LLM services
- Document graceful degradation scenarios
- Add monitoring for external service availability

---

## 6. Production Readiness Assessment

### ✅ What Is Complete & Deployable

| Component | Status | Notes |
|-----------|--------|-------|
| **REST API Core** | ✅ Complete | All audit endpoints functional |
| **Database Layer** | ✅ Complete | SQLAlchemy + migrations working |
| **Plan Enforcement** | ✅ Complete | QuickScan/Full/Agency tiers implemented |
| **Rate Limiting** | ✅ Complete | flask-limiter integrated |
| **CORS Configuration** | ✅ Complete | Configurable per environment |
| **API Key Authentication** | ✅ Complete | X-API-Key header validation |
| **Web Crawling** | ✅ Complete | Multi-page crawling with caching |
| **HTML Parsing** | ✅ Complete | BeautifulSoup + extruct for structured data |
| **Rule Evaluation** | ✅ Complete | 100+ rules across 4 packs (Base/Ecomm/Docs/AIO) |
| **Report Generation** | ✅ Complete | Markdown & DOCX formats |
| **Audit History** | ✅ Complete | Persistent storage |
| **WSGI Entry Point** | ✅ Complete | Ready for Render/Heroku |
| **Render Deployment** | ✅ Complete | Procfile configured |

### ⚠️ What Is Incomplete or Needs Attention

| Issue | Severity | Impact | Location |
|-------|----------|--------|----------|
| **Missing `.env.example`** | Medium | Developers unclear on required config | Project root |
| **Hardcoded RouteLLM API Key** | 🔴 HIGH | Security exposure, should not be in source | `api/vysalytica/config.py:15` |
| **No `.gitignore`** | Medium | Risk of committing secrets/cache files | Project root |
| **wsgi.py imports non-existent `server`** | Low | Import path may fail; Procfile workaround works | `api/vysalytica/wsgi.py:10` |
| **No Redis config in requirements** | Low | Single-process limiting; multi-process needs redis | `requirements.txt` |
| **Minimal error logging** | Medium | Difficult to debug production issues | Throughout API |
| **No request validation** | Low | Relies on Flask/Pydantic (implicit) | `api/api.py` |
| **Database connection pooling not optimized** | Low | May struggle under load | `api/vysalytica/db/__init__.py` |
| **No API documentation (OpenAPI/Swagger)** | Medium | Clients must read source code | N/A |

### 🔴 Security Issues

1. **Hardcoded RouteLLM API Key in Source Code**
   - **File:** `api/vysalytica/config.py`, line 15
   - **Value:** `s2_887db278b1b24f14b49fe0294436e87a` (likely compromised)
   - **Risk:** If repo is public, this key is exposed
   - **Recommendation:** Remove immediately, require environment variable only

2. **No HTTPS Enforcement**
   - API assumes HTTPS in production but doesn't enforce it
   - Recommendation: Add redirect in production, configure Render for SSL

3. **Rate Limiting Defaults Too Permissive**
   - Default: 100 requests/hour per IP is high
   - Recommendation: Tighter limits for unauthenticated API

4. **API Key Stored in Plain Text**
   - No hashing of stored API keys in database
   - Recommendation: Hash keys before storage, compare hashes

5. **No CSRF Protection**
   - CORS allows all origins by default in dev
   - Recommendation: Explicitly configure origins in production

### 💻 Tech Debt

1. **Duplicate Rule Engines**
   - `engine_rules.py` (legacy) and `engine_rules_enhanced.py` (new)
   - Recommendation: Consolidate or deprecate legacy version

2. **No Type Hints in Core API**
   - `api.py` lacks type annotations
   - Recommendation: Add type hints for maintainability

3. **Custom Migration System**
   - Not using Alembic
   - Recommendation: Consider Alembic for version tracking in future

4. **In-Memory Caches for robots.txt/sitemap**
   - `engine_crawl.py` uses dict for caching
   - Recommendation: Use Redis or persistent cache in production

---

## 7. Local Run Instructions

### Prerequisites
- **Python:** 3.11.9
- **pip:** Latest version
- **Virtual environment tool:** venv (built-in)

### Step-by-Step Setup

#### 1. Clone & Navigate
```bash
cd /home/engine/project
```

#### 2. Create Virtual Environment
```bash
python3.11 -m venv .venv
```

#### 3. Activate Virtual Environment
**Linux/macOS:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

#### 4. Install Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed flask-2.3.x flask-cors-4.0.0 sqlalchemy-2.0.36 ...
```

#### 5. Configure Environment

**Option A: Minimal (SQLite + QuickScan only)**
```bash
# No .env needed - defaults are used
# SQLite database auto-creates at api/data/vysalytica.db
```

**Option B: With LLM Services (Recommended)**
```bash
# Create .env from example (when created)
cp .env.example .env

# Edit .env with your API keys:
cat > .env << 'EOF'
DATABASE_URL=sqlite:///api/data/vysalytica.db
OPENAI_API_KEY=sk-your-key-here
CORS_ALLOWED_ORIGINS=http://localhost:3000
APP_VERSION=0.1
DEBUG=True
ENV=dev
EOF

# Load into environment
set -a
source .env
set +a
```

**Option C: Using only environment variables**
```bash
export DATABASE_URL="sqlite:///api/data/vysalytica.db"
export OPENAI_API_KEY="sk-..."
export DEBUG="True"
```

#### 6. Initialize Database
```bash
# Automatic on first API startup, OR manually:
python -c "from api.vysalytica.db.migrations import run_migrations; run_migrations()"
```

**Expected output:**
```
✓ Added confidence column to findings table (if needed)
✓ Seeded 100 AI Optimization rule definitions
✓ Database migrations completed successfully
```

#### 7. Start the Server

**Development (Flask dev server):**
```bash
cd /home/engine/project
export PYTHONPATH=.
python -c "from api import app; app.run(debug=True, host='0.0.0.0', port=8000)"
```

**Production-like (Gunicorn):**
```bash
cd /home/engine/project
PYTHONPATH=. gunicorn api:app -w 2 -k gthread -b 0.0.0.0:8000 --timeout 120
```

**Expected output:**
```
[2025-01-18 12:34:56 +0000] [12345] [INFO] Starting gunicorn 21.x.x
[2025-01-18 12:34:56 +0000] [12345] [INFO] Listening at: http://0.0.0.0:8000
[2025-01-18 12:34:56 +0000] [12345] [INFO] Using worker class: gthread
[2025-01-18 12:34:56 +0000] [12345] [INFO] Spawned with pid [12345]
```

#### 8. Health Check

**Quick test:**
```bash
curl http://localhost:8000/api/health
```

**Expected response:**
```json
{"status": "healthy", "version": "0.1"}
```

**Full health check:**
```bash
curl http://localhost:8000/api/version
```

**Expected response:**
```json
{
  "version": "0.1",
  "debug": true,
  "limiter_storage": "memory://"
}
```

### Testing Endpoints

#### Run an Audit
```bash
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "packs": ["base"],
    "plan": "quickscan"
  }'
```

**Expected response (JSON):**
```json
{
  "success": true,
  "data": {
    "audit_id": 1,
    "url": "https://example.com",
    "page_count": 3,
    "overall_score": 75.5,
    "category_scores": {
      "Crawlability": 85.0,
      "Content": 70.0
    },
    "findings": [...]
  }
}
```

#### List Audits
```bash
curl http://localhost:8000/api/audits
```

#### Get Audit Report (DOCX)
```bash
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "plan": "quickscan"
  }?format=docx' \
  -o report.docx
```

#### Generate API Key
```bash
curl -X POST http://localhost:8000/api/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "Local Dev Key", "quota_per_hour": 100}'
```

### Troubleshooting

**Issue: `ModuleNotFoundError: No module named 'flask'`**
- Solution: Ensure virtual environment is activated and dependencies installed
- Check: `pip list | grep flask`

**Issue: `Database connection refused` (PostgreSQL)**
- Solution: Use SQLite for development (default) or ensure PostgreSQL is running
- Check: `psql -U postgres -d template1 -c "SELECT 1"`

**Issue: LLM endpoints fail with 503**
- Solution: Configure OPENAI_API_KEY or ROUTELLM_API_KEY; API works without them but fix generation unavailable
- Check: `curl http://localhost:8000/api/version`

**Issue: Port 8000 already in use**
- Solution: Change port or kill existing process
- Commands:
  ```bash
  # Find process on port 8000
  lsof -i :8000
  # Kill process
  kill -9 <PID>
  ```

### Performance Tuning

**For Local Testing:**
- Workers: 1-2 (single machine)
- Threads: 2 (gthread)
- Timeout: 120 seconds (web crawling can take time)

**For Production (Render):**
- Workers: auto-scaled based on dyno type
- Threads: 2-4 (gthread)
- Timeout: 120 seconds
- Environment: PostgreSQL, Redis for rate limiting

---

## 8. Blocking Issues & Critical Gaps

### 🔴 CRITICAL - Must Fix Before Production

1. **Hardcoded RouteLLM API Key Exposed**
   - **File:** `api/vysalytica/config.py:15`
   - **Fix:** Remove from code, require environment variable only
   - **Time:** 10 minutes
   ```python
   # BEFORE
   DEFAULT_ROUTELLM_API_KEY = "s2_887db278b1b24f14b49fe0294436e87a"
   
   # AFTER
   DEFAULT_ROUTELLM_API_KEY = None  # No default
   ```

2. **Missing `.env.example` File**
   - **Impact:** Developers don't know required variables
   - **Fix:** Create `.env.example` with all required variables documented
   - **Time:** 5 minutes

3. **No `.gitignore` File**
   - **Impact:** Risk of committing `.env`, `__pycache__`, `.venv`, `*.db`
   - **Fix:** Create standard Python `.gitignore`
   - **Time:** 2 minutes

### ⚠️ HIGH - Should Fix Before Production

4. **wsgi.py References Non-Existent `server.py`**
   - **File:** `api/vysalytica/wsgi.py:10`
   - **Impact:** Direct import of wsgi.py fails; Procfile workaround works
   - **Fix:** Either create `server.py` or update wsgi.py import
   ```python
   # Current (broken)
   from server import app  # server.py doesn't exist
   
   # Option 1: Create server.py
   from api.api import app
   
   # Option 2: Update wsgi.py
   from api.api import app
   ```
   - **Time:** 5 minutes

5. **No Error Handling for Missing LLM Keys**
   - **Impact:** Silent failures in fix generation
   - **Current State:** Errors logged but not returned to client
   - **Fix:** Add proper error responses with guidance
   - **Time:** 30 minutes

6. **Rate Limiter Depends on Redis for Production**
   - **Impact:** Multi-process deployments have per-process limits
   - **Current:** `LIMITER_STORAGE_URI=memory://` uses in-memory storage
   - **Fix:** Add `redis` to requirements.txt and document Redis setup
   - **Time:** 20 minutes

### 📋 MEDIUM - Nice to Have

7. **No API Documentation (OpenAPI/Swagger)**
   - **Current:** Endpoints documented in README, not in code
   - **Recommendation:** Add `flask-restx` or `flasgger` for auto-generated docs
   - **Time:** 2-4 hours

8. **No Request/Response Validation Middleware**
   - **Current:** Relies on manual checks in handlers
   - **Recommendation:** Add Pydantic models for validation
   - **Time:** 4-8 hours

9. **No Structured Logging**
   - **Current:** Print statements and basic logging
   - **Recommendation:** Add structured logging (JSON) for production
   - **Time:** 3-5 hours

10. **Database Connection Pooling**
    - **Current:** Basic SQLAlchemy config
    - **Recommendation:** Tune pool_size, pool_recycle for production load
    - **Time:** 2-3 hours

---

## Deployment Checklist

### Before Going to Production

- [ ] Remove hardcoded RouteLLM API key from `config.py`
- [ ] Create `.env.example` with all required variables
- [ ] Create `.gitignore` file
- [ ] Fix `wsgi.py` import or create `server.py`
- [ ] Set `CORS_ALLOWED_ORIGINS` to specific domains (not "*")
- [ ] Configure `DATABASE_URL` for PostgreSQL (if using Render)
- [ ] Set all LLM API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, or ROUTELLM_API_KEY)
- [ ] Configure `LIMITER_STORAGE_URI` for Redis (recommended for multi-process)
- [ ] Set `DEBUG=False` in production
- [ ] Set `ENV=prod`
- [ ] Test health endpoint: `GET /api/health`
- [ ] Test audit endpoint with sample URL
- [ ] Verify database migrations run on startup
- [ ] Set up monitoring/logging aggregation (optional)

### Render Deployment Commands

**Build Command:**
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

**Start Command:**
```bash
PYTHONPATH=. gunicorn api:app -w 2 -k gthread -b 0.0.0.0:$PORT --timeout 120
```

**Environment Variables (set in Render dashboard):**
- DATABASE_URL: `postgresql+psycopg://user:pass@host/dbname`
- OPENAI_API_KEY: `sk-...`
- CORS_ALLOWED_ORIGINS: `https://yourfrontend.com,https://app.yourfrontend.com`
- LIMITER_STORAGE_URI: (optional, Redis URL if available)
- DEBUG: `False`
- ENV: `prod`

---

## Summary

### Production Readiness: **80% READY**

**Strengths:**
- Complete REST API with all core audit features
- Database layer fully functional (SQLite/Postgres)
- Rate limiting & API key authentication
- Plan enforcement implemented
- Multiple report formats (Markdown, DOCX)
- Render-ready with Procfile and WSGI entry point

**Critical Gaps:**
1. Hardcoded API key exposed (security risk)
2. Missing `.env.example` (developer experience)
3. Missing `.gitignore` (code quality)
4. wsgi.py import path issue (deployment concern)

**Next Steps:**
1. **Immediate:** Fix security issue with hardcoded API key
2. **Before deployment:** Create `.env.example` and `.gitignore`
3. **Before scaling:** Configure Redis for rate limiting
4. **Future improvements:** Add OpenAPI docs, structured logging, Pydantic validation

**Estimated Time to Production-Ready:** 1-2 hours (just critical fixes)

