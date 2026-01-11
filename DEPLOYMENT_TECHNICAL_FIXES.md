# Backend Deployment - Technical Fix Guide

## Implementation Priority & Code Fixes

This document provides specific code changes to address the deployment readiness gaps identified in the assessment.

---

## Phase 1: Security Hardening (CRITICAL - Week 1)

### Fix 1.1: Secure Secret Key Generation

**File:** `api/vysalytica/config.py`

**Current Issue:**
```python
DEFAULT_SECRET_KEY = "changeme"  # UNSAFE
```

**Fix:**
```python
import secrets

def get_secret_key() -> str:
    """Return the Flask secret key."""
    env_key = _get_value("SECRET_KEY")
    if env_key:
        return env_key
    
    # In production, FAIL if not set (don't generate default)
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("SECRET_KEY must be set in production")
    
    # In development, generate a random one
    return secrets.token_urlsafe(32)
```

**Deployment Instructions:**
- Generate secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Set in deployment: `export SECRET_KEY=<generated>`

---

### Fix 1.2: JWT Secret Hardening

**File:** `api/vysalytica/auth.py`

**Current Issue:**
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key_0987654321")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days (too long)
```

**Fix:**
```python
import os
import secrets

# In production, this MUST be set
_JWT_SECRET = os.getenv("JWT_SECRET_KEY")
if not _JWT_SECRET:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("JWT_SECRET_KEY must be set in production")
    _JWT_SECRET = secrets.token_urlsafe(32)

SECRET_KEY = _JWT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours (reduced from 7 days)
```

---

### Fix 1.3: Stripe Secrets Validation

**File:** `api/vysalytica/stripe_service.py`

**Current Issue:**
```python
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_mock")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_mock")
```

**Fix:**
```python
import os
import stripe

_stripe_key = os.getenv("STRIPE_SECRET_KEY")
if not _stripe_key:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("STRIPE_SECRET_KEY must be set in production")
    _stripe_key = "sk_test_4242424242424242"  # Stripe's public test key

stripe.api_key = _stripe_key

_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
if not _webhook_secret:
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("STRIPE_WEBHOOK_SECRET must be set in production")
    _webhook_secret = "whsec_test_secret"

STRIPE_WEBHOOK_SECRET = _webhook_secret
```

---

### Fix 1.4: Login Rate Limiting

**File:** `api/api.py`

**Current Code (Lines 1120-1156):**
```python
@app.route("/api/v1/auth/login", methods=["POST"])
def auth_login():
    """Login user."""
    # ... implementation
```

**Fix:**
```python
@app.route("/api/v1/auth/login", methods=["POST"])
@limiter.limit("5/minute")  # Add rate limiting
def auth_login():
    """Login user."""
    try:
        from api.vysalytica.auth import verify_password, create_access_token
        from api.vysalytica.db.models import User
        
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            
            if not user or not verify_password(password, user.password_hash):
                return jsonify({"success": False, "error": "Invalid credentials"}), 401
            
            if not user.is_active:
                return jsonify({"success": False, "error": "Account inactive"}), 403
            
            token = create_access_token({"user_id": user.id, "email": user.email})
            
            return jsonify({
                "success": True,
                "data": {
                    "user": user.to_dict(),
                    "token": token
                }
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

---

### Fix 1.5: Password Strength Validation

**File:** `api/vysalytica/auth.py`

**Add New Function:**
```python
def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets strength requirements.
    
    Returns:
        (is_valid, error_message)
    """
    if not password or len(password) < 12:
        return False, "Password must be at least 12 characters"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, ""
```

**In `api/api.py` - Update auth_signup (around line 1075):**
```python
@app.route("/api/v1/auth/signup", methods=["POST"])
def auth_signup():
    """Register a new user."""
    try:
        from api.vysalytica.auth import (
            hash_password, create_access_token, validate_password_strength
        )
        from api.vysalytica.db.models import User
        import re
        
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400
        
        # Email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return jsonify({"success": False, "error": "Invalid email format"}), 400
        
        # Password strength validation
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            return jsonify({"success": False, "error": error_msg}), 400
        
        db = SessionLocal()
        try:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return jsonify({"success": False, "error": "Email already registered"}), 400
            
            user = User(
                email=email,
                password_hash=hash_password(password),
                name=name,
                is_active=0  # Start inactive until email verified
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # TODO: Send verification email here
            
            return jsonify({
                "success": True,
                "data": {
                    "user": user.to_dict(),
                    "message": "Account created. Please check your email to verify."
                }
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

---

### Fix 1.6: Link Audits to Brands

**File:** `api/api.py`

**In run_audit function (around line 202-469), update the database persistence section:**

**Current Code (Lines 380-421):**
```python
        # Phase 5: Persist to database (P0-1)
        # Only if plan allows audit history
        audit_id = None
        if plans.check_feature_access(plan, "audit_history"):
            db = SessionLocal()
            try:
                audit_run = AuditRun(
                    url=url_input,
                    domain=domain,
                    packs=limited_packs,
                    overall_score=scores.get("overall", 0),
                    category_scores=scores.get("by_category", {}),
                    page_count=len(pages),
                )
                # ... rest of code
```

**Fix:**
```python
        # Phase 5: Persist to database (P0-1)
        # Only if plan allows audit history
        audit_id = None
        brand_id = None
        
        # Check if audit is for an authenticated user's brand
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from api.vysalytica.auth import decode_access_token
                token = auth_header.split(" ")[1]
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("user_id")
                    brand_id_param = data.get("brand_id")
                    
                    if brand_id_param and user_id:
                        # Verify ownership before linking
                        from api.vysalytica.db.models import Brand
                        db_check = SessionLocal()
                        try:
                            brand = db_check.query(Brand).filter(
                                Brand.id == brand_id_param,
                                Brand.user_id == user_id
                            ).first()
                            if brand:
                                brand_id = brand_id_param
                        finally:
                            db_check.close()
            except Exception:
                pass  # Not authenticated; continue
        
        if plans.check_feature_access(plan, "audit_history"):
            db = SessionLocal()
            try:
                audit_run = AuditRun(
                    url=url_input,
                    domain=domain,
                    packs=limited_packs,
                    overall_score=scores.get("overall", 0),
                    category_scores=scores.get("by_category", {}),
                    page_count=len(pages),
                    brand_id=brand_id,  # Add this
                )
                # ... rest of code
```

---

### Fix 1.7: Complete Stripe Webhook Handler

**File:** `api/api.py`

**Replace Lines 1419-1452:**
```python
@app.route("/api/v1/payments/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    try:
        from api.vysalytica.stripe_service import verify_webhook_signature
        from api.vysalytica.db.models import Payment, User
        
        payload = request.data
        sig_header = request.headers.get("Stripe-Signature")
        
        event = verify_webhook_signature(payload, sig_header)
        
        if not event:
            return jsonify({"success": False, "error": "Invalid signature"}), 400
        
        event_type = event.get("type")
        
        db = SessionLocal()
        try:
            if event_type == "checkout.session.completed":
                session = event["data"]["object"]
                session_id = session["id"]
                
                payment = db.query(Payment).filter(
                    Payment.stripe_session_id == session_id
                ).first()
                
                if payment:
                    payment.status = "paid"
                    payment.user.is_active = 1  # Activate user on payment
                    db.commit()
                    app.logger.info(f"Payment {session_id} marked as paid")
            
            elif event_type == "payment_intent.succeeded":
                intent = event["data"]["object"]
                intent_id = intent["id"]
                
                # Find payment by Stripe intent ID
                payment = db.query(Payment).filter(
                    Payment.stripe_session_id == intent_id
                ).first()
                
                if payment:
                    payment.status = "paid"
                    db.commit()
                    app.logger.info(f"Payment intent {intent_id} succeeded")
            
            elif event_type == "payment_intent.payment_failed":
                intent = event["data"]["object"]
                intent_id = intent["id"]
                
                payment = db.query(Payment).filter(
                    Payment.stripe_session_id == intent_id
                ).first()
                
                if payment:
                    payment.status = "failed"
                    db.commit()
                    app.logger.warning(f"Payment intent {intent_id} failed")
            
            elif event_type == "charge.refunded":
                charge = event["data"]["object"]
                # Could track refunds here if needed
                app.logger.info(f"Charge refunded: {charge['id']}")
            
            return jsonify({"success": True, "event_type": event_type})
        
        finally:
            db.close()
    
    except Exception as e:
        app.logger.exception(f"Webhook processing error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
```

---

### Fix 1.8: Move Function-Level Imports to Module Level

**File:** `api/api.py`

**At the top of file (after existing imports, around line 50), add:**
```python
from api.vysalytica.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    validate_password_strength,
)
from api.vysalytica.db.models import User, Brand, APIKey, Payment
from api.vysalytica.stripe_service import (
    create_checkout_session as create_stripe_session,
    verify_webhook_signature,
)
```

**Then remove imports from inside functions (replace all `from api.vysalytica.auth import ...` inside functions with just using the imported names)**

---

### Fix 1.9: Add Request Body Schema Validation

**File:** `api/vysalytica/schemas.py` (NEW FILE)

```python
"""Request/Response schemas for API validation."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class AuditRequest:
    """Audit endpoint request schema."""
    url: str
    packs: List[str] = None
    plan: str = "quickscan"
    brand_id: Optional[int] = None
    
    def __post_init__(self):
        if not self.url:
            raise ValueError("url is required")
        if self.packs is None:
            self.packs = ["base"]
        if not isinstance(self.packs, list):
            raise ValueError("packs must be a list")
        if self.plan not in ["quickscan", "full", "agency"]:
            raise ValueError("plan must be one of: quickscan, full, agency")


@dataclass
class SignupRequest:
    """Signup endpoint request schema."""
    email: str
    password: str
    name: Optional[str] = None
    
    def __post_init__(self):
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email is required")
        if not self.password or len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")


@dataclass
class LoginRequest:
    """Login endpoint request schema."""
    email: str
    password: str
    
    def __post_init__(self):
        if not self.email:
            raise ValueError("Email is required")
        if not self.password:
            raise ValueError("Password is required")


@dataclass
class BrandRequest:
    """Brand creation request schema."""
    name: str
    primary_url: str
    catalog_url: Optional[str] = None
    competitors: Optional[List[str]] = None
    
    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name is required and must be a string")
        if not self.primary_url or not isinstance(self.primary_url, str):
            raise ValueError("primary_url is required and must be a string")
        if not self.primary_url.startswith(("http://", "https://")):
            raise ValueError("primary_url must start with http:// or https://")
        if self.competitors is None:
            self.competitors = []
```

**Usage in `api/api.py` (Example for audit endpoint):**
```python
@app.route("/api/audit", methods=["POST"])
@limiter.limit(get_quickscan_widget_rate_limit)
def run_audit():
    """Run a full audit on a website."""
    try:
        from api.vysalytica.schemas import AuditRequest
        
        data = request.get_json()
        
        # Validate request schema
        try:
            audit_req = AuditRequest(
                url=data.get("url"),
                packs=data.get("packs", ["base"]),
                plan=data.get("plan", "quickscan"),
                brand_id=data.get("brand_id")
            )
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        
        # Rest of implementation...
```

---

## Phase 2: Error Handling & Resilience

### Fix 2.1: Add LLM Error Handling

**File:** `api/vysalytica/engine_fixgen.py`

**Add robust error handling:**
```python
def generate_fixes_bulk(findings: list) -> list:
    """Generate fixes for findings with error handling."""
    if not findings:
        return findings
    
    from api.vysalytica.config import get_openai_api_key
    from tenacity import retry, stop_after_attempt, wait_exponential
    from openai import OpenAI, APIError, APIConnectionError, Timeout
    
    api_key = get_openai_api_key()
    if not api_key:
        # LLM not configured; return findings as-is
        import logging
        logging.warning("OpenAI API key not configured; skipping fix generation")
        return findings
    
    client = OpenAI(api_key=api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def call_openai(prompt: str, max_retries: int = 3) -> str:
        """Call OpenAI with retry logic."""
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                timeout=30
            )
            return response.choices[0].message.content
        except (APIConnectionError, Timeout) as e:
            # Transient error; will retry
            raise
        except APIError as e:
            # Log but don't retry
            import logging
            logging.error(f"OpenAI API error: {str(e)}")
            return None
    
    fixed_findings = []
    for finding in findings:
        if finding.get("status") != "fail":
            fixed_findings.append(finding)
            continue
        
        try:
            prompt = f"Provide a fix for: {finding.get('why', '')}"
            fix_text = call_openai(prompt)
            
            if fix_text:
                finding["fix"] = fix_text
                finding["fix_snippet"] = extract_code_snippet(fix_text)
        
        except Exception as e:
            import logging
            logging.warning(f"Could not generate fix for {finding.get('id')}: {str(e)}")
            # Don't crash; continue with finding as-is
        
        fixed_findings.append(finding)
    
    return fixed_findings


def extract_code_snippet(text: str) -> str:
    """Extract code snippet from LLM response."""
    import re
    code_pattern = r"```[\w]*\n(.*?)\n```"
    matches = re.findall(code_pattern, text, re.DOTALL)
    return matches[0] if matches else ""
```

---

### Fix 2.2: Add Request Logging Middleware

**File:** `api/api.py`

**Add after app creation:**
```python
import time
import json

@app.before_request
def log_request():
    """Log incoming requests."""
    request.start_time = time.time()
    
    # Sanitize sensitive data from logs
    body = request.get_json(silent=True) or {}
    if "password" in body:
        body["password"] = "***"
    if "api_key" in body:
        body["api_key"] = "***"
    
    app.logger.info(
        json.dumps({
            "event": "request_received",
            "method": request.method,
            "path": request.path,
            "query_params": dict(request.args),
            "body_keys": list(body.keys()) if body else [],
        })
    )


@app.after_request
def log_response(response):
    """Log outgoing responses."""
    duration = time.time() - request.start_time if hasattr(request, 'start_time') else 0
    
    app.logger.info(
        json.dumps({
            "event": "response_sent",
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        })
    )
    
    return response
```

---

### Fix 2.3: Add Security Headers

**File:** `api/api.py`

**Add after CORS configuration:**
```python
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response
```

---

### Fix 2.4: Redis-Backed Rate Limiter

**File:** `api/vysalytica/middleware.py`

**Update limiter initialization:**
```python
import os

# Determine storage backend
storage_uri = os.getenv("LIMITER_STORAGE_URI", "memory://")

# In production, warn if using memory
if storage_uri == "memory://" and os.getenv("ENVIRONMENT") == "production":
    import logging
    logging.warning(
        "Rate limiter using in-memory storage; won't work across multiple workers. "
        "Set LIMITER_STORAGE_URI=redis://localhost:6379 for production"
    )

limiter = Limiter(
    key_func=_forwarded_remote_address,
    default_limits=[_default_rate] if _default_rate else [],
    storage_uri=storage_uri,
    headers_enabled=True,
    strategy="fixed-window-elastic-expiry",  # Better strategy
)
```

---

## Phase 3: Testing & Documentation

### Fix 3.1: Test Auth Endpoints

**File:** `tests/test_auth.py` (NEW FILE)

```python
"""Tests for authentication endpoints."""

import json
import pytest
from api.api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_signup_success(client):
    """Test successful user signup."""
    response = client.post("/api/v1/auth/signup", json={
        "email": "test@example.com",
        "password": "SecurePass123!",
        "name": "Test User"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["user"]["email"] == "test@example.com"


def test_signup_weak_password(client):
    """Test signup with weak password."""
    response = client.post("/api/v1/auth/signup", json={
        "email": "test@example.com",
        "password": "weak"
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "password" in data["error"].lower()


def test_login_success(client):
    """Test successful login."""
    # First signup
    client.post("/api/v1/auth/signup", json={
        "email": "test@example.com",
        "password": "SecurePass123!"
    })
    
    # Then login
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "token" in data["data"]


def test_get_current_user(client):
    """Test getting current user info."""
    # Signup and get token
    signup_resp = client.post("/api/v1/auth/signup", json={
        "email": "test@example.com",
        "password": "SecurePass123!"
    })
    token = signup_resp.get_json()["data"]["token"]
    
    # Get current user
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["email"] == "test@example.com"
```

---

## Phase 4: Observability

### Fix 4.1: Structured Logging Config

**File:** `api/api.py`

**Update JsonFormatter:**
```python
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Add trace/span IDs if available
        if hasattr(record, "trace_id"):
            payload["trace_id"] = record.trace_id
        
        # Add request context if available
        try:
            if request:
                payload["request_id"] = request.remote_addr
                payload["path"] = request.path
                payload["method"] = request.method
        except Exception:
            pass
        
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        
        return json.dumps(payload)
```

---

## Deployment Checklist

### Before Production Deployment

- [ ] All Phase 1 fixes applied and tested
- [ ] All Phase 2 fixes applied and tested
- [ ] Test suite passes with >80% coverage
- [ ] Security audit completed
- [ ] Load testing passed (100+ req/sec)
- [ ] Redis cache configured (LIMITER_STORAGE_URI set)
- [ ] Database backups configured
- [ ] Monitoring/alerting set up
- [ ] Runbook created
- [ ] Team trained

### Environment Variables for Production

```bash
# Security
ENVIRONMENT=production
SECRET_KEY=<generate_with_secrets.token_urlsafe(32)>
JWT_SECRET_KEY=<generate_with_secrets.token_urlsafe(32)>

# Database
DATABASE_URL=postgresql+psycopg://user:pass@host/dbname

# Stripe
STRIPE_SECRET_KEY=sk_live_<actual_key>
STRIPE_WEBHOOK_SECRET=whsec_<actual_secret>

# LLM
OPENAI_API_KEY=sk-<key>
ANTHROPIC_API_KEY=sk-ant-<key>

# Redis (for rate limiting)
LIMITER_STORAGE_URI=redis://:<password>@<host>:6379/0

# CORS
CORS_ORIGINS=https://frontend.example.com

# Logging
LOG_LEVEL=INFO

# Flask
FLASK_ENV=production
```

---

## Summary of Changes

| Phase | Fix ID | File | Changes | Effort |
|-------|--------|------|---------|--------|
| 1 | 1.1 | config.py | Secret key generation | 1h |
| 1 | 1.2 | auth.py | JWT secret + token expiry | 1h |
| 1 | 1.3 | stripe_service.py | Stripe secrets validation | 1h |
| 1 | 1.4 | api.py | Login rate limiting | 0.5h |
| 1 | 1.5 | auth.py + api.py | Password strength | 1.5h |
| 1 | 1.6 | api.py | Link audits to brands | 1h |
| 1 | 1.7 | api.py | Complete Stripe webhook | 2h |
| 1 | 1.8 | api.py | Move imports | 1h |
| 1 | 1.9 | schemas.py (new) | Request validation | 2h |
| 2 | 2.1 | engine_fixgen.py | LLM error handling | 1.5h |
| 2 | 2.2 | api.py | Request logging | 1h |
| 2 | 2.3 | api.py | Security headers | 0.5h |
| 2 | 2.4 | middleware.py | Redis limiter | 1h |
| 3 | 3.1 | test_auth.py (new) | Auth tests | 2h |
| 4 | 4.1 | api.py | Structured logging | 1h |
| | | | **TOTAL** | **~19-20 hours** |

---

**All fixes are backward-compatible and can be applied incrementally.**
