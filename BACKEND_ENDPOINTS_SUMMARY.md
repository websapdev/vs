# Backend Endpoints Summary

**Quick Reference for All 32 API Endpoints**

---

## Health & Discovery (5 endpoints)

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| GET | `/healthz` | ✅ | DB probe + liveness check |
| GET | `/version` | ✅ | Git SHA, build info |
| GET | `/openapi.json` | ✅ | OpenAPI spec (lightweight) |
| GET | `/api/health` | ✅ | Legacy health check |
| GET | `/api/version` | ✅ | Legacy version info |

---

## Audit Execution (3 endpoints)

| Method | Path | Status | Auth | Rate Limit | Purpose |
|--------|------|--------|------|-----------|---------|
| POST | `/api/audit` | ⚠️ | API Key (paid) | Dynamic | Run website audit |
| GET | `/api/audit/history` | ⚠️ | Optional | None | List past audits |
| GET | `/api/audit/<id>` | ❌ | None | None | Get audit detail |

**Request: POST /api/audit**
```json
{
  "url": "https://example.com",
  "packs": ["base"],
  "plan": "quickscan",
  "brand_id": 1  // optional, for authenticated users
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "audit_id": 123,
    "url": "https://example.com",
    "domain": "example.com",
    "page_count": 3,
    "scores": { "overall": 85.0 },
    "findings": [...]
  }
}
```

---

## Citations Tracking (2 endpoints)

| Method | Path | Status | Auth | Purpose |
|--------|------|--------|------|---------|
| POST | `/api/citations/track` | ⚠️ | API Key | Track brand mentions in LLMs |
| GET | `/api/citations/stats` | ⚠️ | API Key | Get citation statistics |

**Request: POST /api/citations/track**
```json
{
  "brand": "Asana",
  "intent": "best project management tools",
  "assistants": ["chatgpt", "claude"]
}
```

---

## API Key Management (2 endpoints)

| Method | Path | Status | Auth | Purpose |
|--------|------|--------|------|---------|
| POST | `/api/keys/create` | ⚠️ | None | Generate API key |
| GET | `/api/keys/list` | ⚠️ | None | List API keys (masked) |

**Request: POST /api/keys/create**
```json
{
  "name": "My API Key",
  "quota_per_hour": 10
}
```

---

## Plans & Features (2 endpoints)

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| GET | `/api/plans` | ✅ | List all plans (quickscan, full, agency) |
| GET | `/api/plans/compare` | ✅ | Plan comparison matrix |

**Plans:**
- **quickscan**: Free, 3 pages, base rules only
- **full**: $49, 5 pages, all rule packs, fix generation
- **agency**: $199, 12 pages, API access, citations tracking

---

## Report Generation (4 endpoints)

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| POST | `/api/report/markdown` | ✅ | Generate Markdown report |
| POST | `/api/report/docx` | ✅ | Generate DOCX report |
| POST | `/api/report/playbook_md` | ⚠️ | Playbook Markdown |
| POST | `/api/report/playbook_docx` | ⚠️ | Playbook DOCX |

**Request: POST /api/report/docx**
```json
{
  "url": "https://example.com",
  "packs": ["base"],
  "scores": { "overall": 85.0 },
  "findings": [...]
}
```

**Response:** Binary DOCX file

---

## Answer Graphs (2 endpoints)

| Method | Path | Status | Auth | Rate Limit | Purpose |
|--------|------|--------|------|-----------|---------|
| POST | `/api/answer_graph/build` | ❌ | None | 5/min | Build domain/intent graph |
| GET | `/api/answer_graph/` | ❌ | None | None | Retrieve graphs |

**Request: POST /api/answer_graph/build**
```json
{
  "domain": "example.com",
  "intents": ["best tools", "how to"],
  "packs": ["base"]
}
```

---

## Playbooks (1 endpoint)

| Method | Path | Status | Auth | Rate Limit | Purpose |
|--------|------|--------|------|-----------|---------|
| POST | `/api/playbooks/generate` | ❌ | None | None | Generate visibility playbook |

**Request: POST /api/playbooks/generate**
```json
{
  "domain": "example.com",
  "intent": "best project management",
  "target_assistant": "chatgpt"
}
```

---

## Authentication (3 endpoints)

| Method | Path | Status | Auth | Rate Limit | Purpose |
|--------|------|--------|------|-----------|---------|
| POST | `/api/v1/auth/signup` | ⚠️ | None | None | User registration |
| POST | `/api/v1/auth/login` | ⚠️ | None | 5/min* | User login |
| GET | `/api/v1/auth/me` | ⚠️ | Bearer | None | Get current user |

*Rate limit to be added

**Request: POST /api/v1/auth/signup**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe"
}
```

**Request: POST /api/v1/auth/login**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": { "id": 1, "email": "user@example.com" },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

---

## Brand Management (4 endpoints)

| Method | Path | Status | Auth | Purpose |
|--------|------|--------|------|---------|
| GET | `/api/v1/brands` | ⚠️ | Bearer | List user brands |
| POST | `/api/v1/brands` | ⚠️ | Bearer | Create brand |
| GET | `/api/v1/brands/<id>` | ⚠️ | Bearer | Get brand detail |
| GET | `/api/v1/brands/<id>/audits` | ⚠️ | Bearer | Get brand audits |

**Request: POST /api/v1/brands**
```json
{
  "name": "Acme Corp",
  "primary_url": "https://acme.com",
  "catalog_url": "https://acme.com/products",
  "competitors": ["https://competitor1.com"]
}
```

---

## Payments (2 endpoints)

| Method | Path | Status | Auth | Purpose |
|--------|------|--------|------|---------|
| POST | `/api/v1/payments/create-checkout-session` | ⚠️ | Bearer | Create Stripe checkout |
| POST | `/api/v1/payments/webhook` | ❌ | Stripe Sig | Handle Stripe events |

**Request: POST /api/v1/payments/create-checkout-session**
```json
{
  "amount": 5000,
  "currency": "usd",
  "success_url": "https://example.com/success",
  "cancel_url": "https://example.com/cancel"
}
```

---

## CORS (2 endpoints)

| Method | Path | Status | Purpose |
|--------|------|--------|---------|
| OPTIONS | `/` | ✅ | Preflight request |
| OPTIONS | `/<path>` | ✅ | Preflight request |

---

## Missing Endpoints (Should Be Added)

| Method | Path | Feature | Effort |
|--------|------|---------|--------|
| POST | `/api/v1/auth/logout` | Session invalidation | 1h |
| POST | `/api/v1/auth/refresh` | Token refresh | 1h |
| POST | `/api/v1/auth/forgot-password` | Password reset | 2h |
| PUT | `/api/v1/brands/<id>` | Update brand | 1h |
| DELETE | `/api/v1/brands/<id>` | Delete brand | 1h |
| DELETE | `/api/audit/<id>` | Delete audit | 1h |
| GET | `/api/v1/payments/invoices` | List invoices | 1h |
| PUT | `/api/v1/payments/update-method` | Update payment method | 1h |
| POST | `/api/audit/<id>/schedule` | Schedule audit | 3h |
| GET | `/api/rules` | Get rule definitions | 1h |

---

## Error Response Format

All endpoints return errors in this format:

```json
{
  "success": false,
  "error": "Description of what went wrong"
}
```

HTTP Status Codes:
- 200: Success
- 400: Bad request (validation error)
- 401: Unauthorized (missing/invalid auth)
- 403: Forbidden (no permission)
- 404: Not found
- 429: Rate limited
- 500: Server error

---

## Rate Limiting Summary

| Endpoint | Limit | Type |
|----------|-------|------|
| `/api/audit` | Dynamic | QuickScan: 3/min; Paid: API key quota |
| `/api/answer_graph/build` | 5/minute | Fixed |
| `/api/playbooks/generate` | 10/minute | Fixed (default) |
| `/api/v1/auth/login` | 5/minute | **To be added** |
| All others | 60/minute | Default |

---

## Authentication Methods

1. **API Key** - Header: `X-API-Key`
   - For audit operations with paid plans
   - For citations, playbooks, answer graphs

2. **Bearer Token** - Header: `Authorization: Bearer <token>`
   - For user endpoints (auth, brands, payments)
   - Token obtained from `/api/v1/auth/login`
   - Valid for 24 hours

3. **No Auth** - Public endpoints
   - QuickScan audits
   - Health checks
   - Plan information

---

## Database Models

| Table | Records | Purpose |
|-------|---------|---------|
| users | 1-1000s | User accounts |
| brands | 1-10000s | User brands/projects |
| audit_runs | 1-100000s | Audit executions |
| findings | 1-1000000s | Rule evaluation results |
| citation_snapshots | 1-100000s | Brand citations in LLMs |
| api_keys | 1-1000s | API authentication |
| payments | 1-10000s | Stripe transactions |
| answer_graphs | 1-10000s | Domain/intent graphs |
| playbooks | 1-10000s | Visibility playbooks |
| rule_definitions | ~100 | Static rule metadata |

---

## Environment Variables by Feature

### Required for Production
- `SECRET_KEY` - Flask session secret
- `JWT_SECRET_KEY` - JWT signing key
- `DATABASE_URL` - PostgreSQL connection
- `STRIPE_SECRET_KEY` - Stripe API key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing

### Required for LLM Features
- `OPENAI_API_KEY` - For fix generation
- `ANTHROPIC_API_KEY` - For citations

### Optional (Performance)
- `LIMITER_STORAGE_URI` - Redis for rate limiting (default: memory)
- `QUICKSCAN_CACHE_ENABLED` - Cache audit results (default: true)
- `QUICKSCAN_CACHE_TTL_SECONDS` - Cache duration (default: 900)

### Optional (Security)
- `WIDGET_ALLOWED_ORIGINS` - Restrict QuickScan origins
- `CORS_ORIGINS` - Frontend URLs

---

## Deployment Readiness by Feature Tier

### Tier 1: Production Ready ✅
- Health & discovery (5 endpoints)
- Plans & comparison (2 endpoints)
- Report generation (4 endpoints)
- Audit core (with caveats on caching)

### Tier 2: Production Ready with Fixes ⚠️
- Audit history (add pagination)
- Citations (add error handling)
- API keys (add authentication)

### Tier 3: Pre-Production ❌
- Auth (add email verification, password strength)
- Brands (add authorization checks, CRUD)
- Payments (complete webhook, add subscriptions)
- Answer graphs (add validation)
- Playbooks (add error handling)

---

**Generated:** 2025-01-10  
**Status:** Deployment Assessment Complete
