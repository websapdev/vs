"""
API Key Middleware (P0-4)
Provides authentication and rate limiting for public API
"""

import os
import secrets
from datetime import datetime
from functools import wraps

from flask import current_app, jsonify, request
from flask_limiter import Limiter

from api.vysalytica.config import get_rate_limit
from api.vysalytica.db import SessionLocal
from api.vysalytica.db.models import APIKey

# Initialize rate limiter (storage configurable via env)
_storage_uri = os.getenv("LIMITER_STORAGE_URI", "memory://")
_default_rate = get_rate_limit()


def _forwarded_remote_address() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


limiter = Limiter(
    key_func=_forwarded_remote_address,
    default_limits=[_default_rate] if _default_rate else [],
    storage_uri=_storage_uri,
    headers_enabled=True,
)


def require_api_key(f):
    """
    Decorator to require valid API key for endpoint access.

    Checks for X-API-Key header and validates against database.
    Updates last_used_at timestamp on successful auth.

    Usage:
        @app.route('/api/protected')
        @require_api_key
        def protected_endpoint():
            return jsonify({'data': 'secret'})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return (
                jsonify({"success": False, "error": "X-API-Key header required"}),
                401,
            )

        # Validate API key
        db = SessionLocal()
        try:
            key_record = (
                db.query(APIKey).filter(APIKey.key == api_key, APIKey.is_active == 1).first()
            )

            if not key_record:
                return (
                    jsonify({"success": False, "error": "Invalid or inactive API key"}),
                    401,
                )

            # Update last used timestamp
            key_record.last_used_at = datetime.utcnow()
            db.commit()

            # Store key info in request context for rate limiting
            request.api_key_id = key_record.id
            request.api_key_quota = key_record.quota_per_hour

        except Exception as e:
            db.rollback()
            current_app.logger.error(f"API key validation error: {str(e)}")
            return jsonify({"success": False, "error": "Authentication error"}), 500
        finally:
            db.close()

        return f(*args, **kwargs)

    return decorated_function


def get_api_key_rate_limit():
    """
    Dynamic rate limit function based on API key quota.
    Falls back to IP-based limiting if no API key present.
    """
    if hasattr(request, "api_key_quota"):
        return f"{request.api_key_quota} per hour"
    else:
        return "10 per hour"  # Default for non-authenticated requests


def get_quickscan_widget_rate_limit() -> str:
    """
    Dynamic rate limit for the public QuickScan widget calls.

    - If a valid API key is present, use the per-key quota (same as get_api_key_rate_limit)
    - Otherwise, apply a tighter limit suitable for unauthenticated widget traffic

    Returns a limit string understood by flask-limiter, e.g. "3/minute;20/hour".
    """
    # If request has a validated API key context, honor that quota
    # (require_api_key decorator sets request.api_key_quota; otherwise fall back)
    if request.headers.get("X-API-Key"):
        if hasattr(request, "api_key_quota"):
            return f"{request.api_key_quota} per hour"
        return "100 per hour"

    # For unauthenticated calls: apply tight limits ONLY for QuickScan plan to avoid
    # interfering with paid-plan auth checks in tests/production.
    try:
        is_audit_path = request.path.endswith("/api/audit")
        if is_audit_path:
            # Inspect body plan safely
            data = request.get_json(silent=True) or {}
            plan = str(data.get("plan", "quickscan")).lower()
            if plan == "quickscan":
                return "3/minute;20/hour"
            # Non-QuickScan without API key: allow generous limit so 401 can surface
            return "100 per hour"
    except Exception:
        # If anything goes wrong, use a safe default that won't cause false 429s
        return "100 per hour"

    # Fallback default for other endpoints
    return "10 per hour"


def generate_api_key(name: str = None, quota_per_hour: int = 10) -> dict:
    """
    Generate a new API key.

    Args:
        name: Optional name/description for the key
        quota_per_hour: Rate limit for this key (default: 10)

    Returns:
        {
            "key": str,
            "name": str,
            "quota_per_hour": int,
            "created_at": str
        }
    """
    db = SessionLocal()
    try:
        # Generate secure random key
        key = secrets.token_urlsafe(32)

        # Create API key record
        api_key = APIKey(key=key, name=name, quota_per_hour=quota_per_hour, is_active=1)

        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        return {
            "id": api_key.id,
            "key": api_key.key,
            "name": api_key.name,
            "quota_per_hour": api_key.quota_per_hour,
            "created_at": (api_key.created_at.isoformat() if api_key.created_at else None),
        }

    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to generate API key: {str(e)}") from e
    finally:
        db.close()


def revoke_api_key(key: str) -> bool:
    """
    Revoke (deactivate) an API key.

    Args:
        key: The API key to revoke

    Returns:
        True if successful, False if key not found
    """
    db = SessionLocal()
    try:
        key_record = db.query(APIKey).filter(APIKey.key == key).first()

        if not key_record:
            return False

        key_record.is_active = 0
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to revoke API key: {str(e)}") from e
    finally:
        db.close()


def list_api_keys() -> list:
    """
    List all API keys (excluding the actual key value for security).

    Returns:
        List of API key info dicts
    """
    db = SessionLocal()
    try:
        keys = db.query(APIKey).all()

        return [
            {
                "id": k.id,
                "key": k.key[:8] + "..." + k.key[-4:],  # Masked key
                "name": k.name,
                "quota_per_hour": k.quota_per_hour,
                "is_active": bool(k.is_active),
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]

    finally:
        db.close()


# Optional: Per-key rate limiter (more sophisticated implementation)
class APIKeyRateLimiter:
    """
    Rate limiter that tracks usage per API key.
    Can be used for more sophisticated quota management.
    """

    def __init__(self):
        self.usage_cache = {}  # In-memory cache, should use Redis in production

    def check_limit(self, api_key_id: int, quota: int) -> tuple:
        """
        Check if API key has exceeded quota.

        Returns:
            (allowed: bool, remaining: int, reset_time: datetime)
        """
        # Simple implementation - would need Redis for production
        # This is a placeholder for future enhancement
        return (True, quota, datetime.utcnow())

    def record_usage(self, api_key_id: int):
        """
        Record API usage for tracking.
        """
        # Placeholder for future enhancement
        pass
