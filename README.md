# Vysalytica API

Production-ready REST API for AI Visibility Audit Tool, optimized for Render deployment.

## Overview

The Vysalytica API provides endpoints for:
- Website AI visibility auditing
- Citation tracking and analysis
- API key management
- Plan enforcement and rate limiting
- Report generation (Markdown/DOCX)

## Local Development

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Environment Configuration
```bash
# Copy environment template and configure
cp .env.example .env
# Edit .env with your local configuration values

# Load environment variables for testing
export $(grep -v '^#' .env.example | xargs)
python -c "import os; print('env ok')"
```

### Run Locally
```bash
gunicorn api:app -w 2 -k gthread -b 0.0.0.0:8000 --timeout 120
```

The API will be available at `http://localhost:8000`

## Health Check

```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{"status": "healthy", "version": "0.1"}
```

## Render Deployment

### Build Command
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

### Start Command
```bash
gunicorn api:app -w 2 -k gthread -b 0.0.0.0:$PORT --timeout 120
```

### Environment Variables on Render
Configure these in your Render service environment:
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key for AI features
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude integration
- `CORS_ALLOWED_ORIGINS` - Comma-separated list of allowed frontend origins
- `ROUTE_LLM_API_KEY` - RouteLLM API key if using routing service
- `LIMITER_STORAGE_URI` - Rate limiter storage (default: `memory://`)
- `ENV=prod` - Set to production mode

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/version` - Version and configuration info
- `POST /api/audit` - Run website audit
- `GET /api/audits` - List audit history
- `GET /api/audits/{id}` - Get specific audit
- `GET /api/citations` - Citation tracking
- `POST /api/keys` - Generate API key
- `GET /api/keys` - List API keys
- `DELETE /api/keys/{id}` - Revoke API key

## Architecture

- **Entry Point**: `api/__init__.py` exports Flask `app`
- **Core API**: `api/api.py` contains all route handlers
- **Business Logic**: `api/vysalytica/` package with engine modules
- **Database**: SQLAlchemy with PostgreSQL
- **Rate Limiting**: Flask-Limiter (memory or Redis)
- **CORS**: Configurable per environment

## Repository Structure

```
├── api/                    # Main API package
│   ├── __init__.py        # Exports Flask app
│   ├── api.py             # Flask routes and handlers
│   ├── engine_*.py        # Core audit engines
│   └── vysalytica/        # Business logic package
├── requirements.txt       # Production dependencies only
├── runtime.txt           # Python 3.11.9
├── Procfile              # Gunicorn startup command
├── .env.example          # Environment template
├── .gitignore           # Python/production gitignore
├── README.md            # This file
└── archive/             # Archived non-production files
```