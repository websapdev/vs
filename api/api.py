"""
Flask API for AI Visibility Audit Tool
Provides REST endpoints for the web front-end
"""

from __future__ import annotations

import io
import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from sqlalchemy import text
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from api import engine_crawl, engine_parse, engine_report
from api import engine_rules_enhanced as engine_rules
from api.vysalytica import engine_ai_visibility, engine_fixgen, plans
from api.vysalytica.config import (
    get_cors_origins,
    get_log_level,
    get_secret_key,
)
from api.vysalytica.db import SessionLocal
from api.vysalytica.db.migrations import run_migrations
from api.vysalytica.db.models import AnswerGraph as AnswerGraphModel
from api.vysalytica.db.models import (
    AuditRun,
    CitationSnapshot,
    Finding,
)
from api.vysalytica.db.models import Playbook as PlaybookModel
from api.vysalytica.db.models import PlaybookFix as PlaybookFixModel
from api.vysalytica.engine_answer_graph import build_answer_graph
from api.vysalytica.engine_playbooks import generate_playbook
from api.vysalytica.middleware import (
    generate_api_key,
    get_quickscan_widget_rate_limit,
    limiter,
    list_api_keys,
)

app = Flask(__name__)
BUILT_AT = datetime.utcnow().isoformat() + "Z"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - trivial
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level_name: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level_name)


def _parse_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(testing: bool = False) -> Flask:
    configure_logging(get_log_level())
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    app.config["SECRET_KEY"] = get_secret_key()
    app.config["JSON_SORT_KEYS"] = False
    app.config["TESTING"] = testing

    app.logger.info("Initializing database...")
    if not run_migrations():
        app.logger.warning("Database migrations reported a failure; proceeding with caution.")
    else:
        app.logger.info("Database ready!")

    # CORS configuration
    origins = _parse_origins(get_cors_origins())
    cors_kwargs: dict[str, Any] = {
        "supports_credentials": True,
        "resources": {r"/*": {"origins": origins or "*"}},
        "expose_headers": ["Content-Disposition"],
    }
    CORS(app, **cors_kwargs)

    limiter.init_app(app)

    register_error_handlers(app)
    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        code = exc.code or 500
        return jsonify({"error": {"code": str(code), "message": exc.description}}), code

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):  # pragma: no cover - defensive
        app.logger.exception("Unhandled exception")
        return (
            jsonify({"error": {"code": "500", "message": str(exc)}}),
            500,
        )


def _get_git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return os.getenv("GIT_SHA", "unknown")


def _build_version_payload() -> dict[str, Any]:
    return {
        "git_sha": _get_git_sha(),
        "built_at": BUILT_AT,
        "python": platform.python_version(),
        "app": "vysalytica-api",
    }


def _build_openapi_spec() -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        methods = [
            method
            for method in sorted(rule.methods)
            if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}
        ]
        paths[rule.rule] = {"methods": methods}
    return {
        "openapi": "3.0.0",
        "info": {"title": "Vysalytica API", "version": _build_version_payload()["git_sha"]},
        "paths": paths,
    }


@app.route("/healthz", methods=["GET"])
def healthz():
    status: dict[str, Any] = {"ok": True, "db": "up"}
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        status["ok"] = False
        status["db"] = "down"
        status["error"] = str(exc)
        return jsonify(status), 500
    return jsonify(status)


@app.route("/version", methods=["GET"])
def version_root():
    return jsonify(_build_version_payload())


@app.route("/openapi.json", methods=["GET"])
def openapi_json():
    return jsonify(_build_openapi_spec())


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "version": _build_version_payload()["git_sha"]})


@app.route("/api/version", methods=["GET"])
def version_info():
    payload = _build_version_payload()
    payload["limiter_storage"] = os.getenv("LIMITER_STORAGE_URI", "memory://")
    return jsonify(payload)


@app.route("/api/audit", methods=["POST"])
@limiter.limit(get_quickscan_widget_rate_limit)
def run_audit():
    """
    Run a full audit on a website.

    Request body:
    {
        "url": "https://example.com",
        "packs": ["base", "ecomm", "docs"],
        "plan": "quickscan"  // optional, default: "quickscan"
    }

    Query parameters:
    - format: "json" (default) or "docx" - Return format for the audit results

    Returns (format=json):
    {
        "success": true,
        "data": {
            "audit_id": 123,
            "url": "https://example.com",
            "page_count": 12,
            "scores": {...},
            "findings": [...]
        }
    }

    Returns (format=docx):
    Binary .docx file with Content-Disposition: attachment header
    """
    try:
        data = request.get_json()
        response_format = request.args.get("format", "json").lower()

        # Validate input
        if not data or "url" not in data:
            return jsonify({"success": False, "error": "URL is required"}), 400

        url_input = data["url"]
        packs = data.get("packs", ["base"])
        plan = data.get("plan", "quickscan")

        # Enforce API key for non-free plans (P0-4 auth alignment)
        if plan != "quickscan":
            auth_key = request.headers.get("X-API-Key")
            if not auth_key:
                return (
                    jsonify({"success": False, "error": "X-API-Key required for paid plans"}),
                    401,
                )

            # Validate API key
            from api.vysalytica.db.models import APIKey

            db = SessionLocal()
            try:
                key_record = (
                    db.query(APIKey).filter(APIKey.key == auth_key, APIKey.is_active == 1).first()
                )

                if not key_record:
                    return (
                        jsonify({"success": False, "error": "Invalid or inactive API key"}),
                        401,
                    )

                # Update last used timestamp
                key_record.last_used_at = datetime.utcnow()
                db.commit()
            except Exception as e:
                db.rollback()
                app.logger.error(f"API key validation error: {str(e)}")
                return jsonify({"success": False, "error": "Authentication error"}), 500
            finally:
                db.close()

        # Validate URL
        if not url_input.startswith("http://") and not url_input.startswith("https://"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "URL must start with http:// or https://",
                    }
                ),
                400,
            )

        # Anti-abuse: allow simple origin whitelist for widget calls
        origin = request.headers.get("Origin") or ""
        allowed_origins = os.getenv("WIDGET_ALLOWED_ORIGINS", "").strip()
        if allowed_origins:
            allowed = [o.strip() for o in allowed_origins.split(",") if o.strip()]
            if "*" not in allowed and origin and origin not in allowed and plan == "quickscan":
                return (
                    jsonify({"success": False, "error": "Origin not allowed for QuickScan"}),
                    403,
                )

        # Phase 1: Crawl
        urls = engine_crawl.discover_pages(url_input)
        if not urls:
            return jsonify({"success": False, "error": "Failed to discover pages"}), 500

        # Phase 1.5: Enforce plan limits (P0-5)
        enforcement = plans.enforce_plan(plan, urls, packs)
        limited_urls = enforcement["pages"]
        limited_packs = enforcement["packs"]

        # QuickScan cache: domain-level cache for 15 minutes to reduce load
        cache_enabled = os.getenv("QUICKSCAN_CACHE_ENABLED", "true").lower() == "true"
        cache_ttl_seconds = int(os.getenv("QUICKSCAN_CACHE_TTL_SECONDS", "900"))

        cache_key = None
        cached_payload = None
        if cache_enabled and plan == "quickscan":
            try:
                if not hasattr(run_audit, "_cache_store"):
                    run_audit._cache_store = {}
                if not hasattr(run_audit, "_cache_times"):
                    run_audit._cache_times = {}

                parsed_url = urlparse(url_input)
                domain = parsed_url.netloc
                cache_key = (domain, tuple(sorted(limited_packs)))
                last_ts = run_audit._cache_times.get(cache_key)
                if last_ts and (datetime.utcnow().timestamp() - last_ts) < cache_ttl_seconds:
                    cached_payload = run_audit._cache_store.get(cache_key)
            except Exception:
                cached_payload = None

        if cached_payload:
            return jsonify(cached_payload)

        # Phase 2: Parse
        pages = engine_parse.parse_site(limited_urls)
        if all(page.get("error", False) for page in pages):
            return jsonify({"success": False, "error": "Failed to parse pages"}), 500

        # Phase 3: Extract site metadata
        parsed_url = urlparse(url_input)
        domain = parsed_url.netloc
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # Fetch robots.txt (cached via engine_crawl)
        robots_txt = None
        try:
            _, robots_content = engine_crawl.fetch(f"{base_url}/robots.txt")
            robots_txt = robots_content if robots_content else None
        except Exception:
            pass

        # Check for sitemap (cached via engine_crawl)
        sitemap_url = None
        try:
            _, sitemap_content = engine_crawl.fetch(f"{base_url}/sitemap.xml")
            if sitemap_content:
                sitemap_url = f"{base_url}/sitemap.xml"
        except Exception:
            pass

        site_meta = {
            "domain": domain,
            "base_url": base_url,
            "robots_txt": robots_txt,
            "sitemap_url": sitemap_url,
            "homepage": pages[0] if pages else {},
        }

        # Phase 4: Evaluate
        findings, scores = engine_rules.evaluate(pages, site_meta, limited_packs)

        # Phase 4.5: Generate fixes for failed rules (P0-3)
        # Only if plan allows fix generation
        if plans.check_feature_access(plan, "fix_generation"):
            findings = engine_fixgen.generate_fixes_bulk(findings)

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
                db.add(audit_run)
                db.flush()  # Get the ID without committing yet

                # Create finding records
                for finding in findings:
                    finding_record = Finding(
                        audit_run_id=audit_run.id,
                        rule_id=finding.get("id", ""),
                        rule_title=finding.get("title", ""),
                        category=finding.get("category", ""),
                        status=finding.get("status", "fail"),
                        confidence=finding.get("confidence"),
                        evidence=finding.get("evidence", []),
                        why=finding.get("why", ""),
                        fix=finding.get("fix", ""),
                        fix_snippet=finding.get("fix_snippet", ""),
                        acceptance_test=finding.get("acceptance_test", ""),
                    )
                    db.add(finding_record)

                db.commit()
                audit_id = audit_run.id
            except Exception as e:
                db.rollback()
                app.logger.error(f"Database error: {str(e)}")
                audit_id = None  # Continue even if persistence fails
            finally:
                db.close()

        # Return results
        payload = {
            "success": True,
            "data": {
                "audit_id": audit_id,
                "url": url_input,
                "domain": domain,
                "page_count": len(pages),
                "packs": limited_packs,
                "plan": plan,
                "plan_limits_applied": enforcement["limited"],
                "scores": scores,
                "findings": findings,
                "timestamp": datetime.now().isoformat(),
            },
        }

        # Save to cache if eligible
        if cache_enabled and plan == "quickscan" and cache_key is not None:
            try:
                run_audit._cache_store[cache_key] = payload
                run_audit._cache_times[cache_key] = datetime.utcnow().timestamp()
            except Exception:
                pass

        # Return based on requested format
        if response_format == "docx":
            # Generate DOCX report
            docx_bytes = engine_report.generate_docx(url_input, limited_packs, scores, findings)

            # Create file-like object
            buffer = io.BytesIO(docx_bytes)
            buffer.seek(0)

            filename = (
                f"{urlparse(url_input).netloc}_audit_{datetime.now().strftime('%Y%m%d')}.docx"
            )

            return send_file(
                buffer,
                as_attachment=True,
                download_name=filename,
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        else:
            # Default: return JSON
            return jsonify(payload)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/audit/history", methods=["GET"])
def get_audit_history():
    """
    Get audit history for a domain.

    Query parameters:
    - domain: Filter by domain (optional)
    - limit: Number of results (default: 10, max: 100)

    Returns:
    {
        "success": true,
        "data": [
            {
                "id": 1,
                "url": "https://example.com",
                "domain": "example.com",
                "overall_score": 85.5,
                "created_at": "2025-10-17T12:00:00"
            },
            ...
        ]
    }
    """
    try:
        domain_filter = request.args.get("domain")
        limit = min(int(request.args.get("limit", 10)), 100)

        db = SessionLocal()
        try:
            query = db.query(AuditRun)

            if domain_filter:
                query = query.filter(AuditRun.domain == domain_filter)

            audit_runs = query.order_by(AuditRun.created_at.desc()).limit(limit).all()

            results = [
                {
                    "id": run.id,
                    "url": run.url,
                    "domain": run.domain,
                    "packs": run.packs,
                    "overall_score": run.overall_score,
                    "category_scores": run.category_scores,
                    "page_count": run.page_count,
                    "created_at": (run.created_at.isoformat() if run.created_at else None),
                }
                for run in audit_runs
            ]

            return jsonify({"success": True, "data": results, "count": len(results)})
        finally:
            db.close()

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/audit/<int:audit_id>", methods=["GET"])
def get_audit_detail(audit_id):
    """
    Get detailed audit results by ID.

    Returns:
    {
        "success": true,
        "data": {
            "id": 1,
            "url": "https://example.com",
            "findings": [...]
        }
    }
    """
    try:
        db = SessionLocal()
        try:
            audit_run = db.query(AuditRun).filter(AuditRun.id == audit_id).first()

            if not audit_run:
                return jsonify({"success": False, "error": "Audit not found"}), 404

            return jsonify({"success": True, "data": audit_run.to_dict()})
        finally:
            db.close()

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/citations/track", methods=["POST"])
def track_citations():
    """
    Track AI citations for a brand across ChatGPT and Claude.

    Request body:
    {
        "brand": "Asana",
        "intent": "best project management tools",
        "assistants": ["chatgpt", "claude"]  // optional
    }

    Returns:
    {
        "success": true,
        "data": {
            "results": [
                {
                    "assistant": "ChatGPT",
                    "cited": true,
                    "response": "..."
                },
                ...
            ],
            "summary": {
                "total": 2,
                "cited": 1,
                "rate": 50.0
            }
        }
    }
    """
    try:
        data = request.get_json()

        # Validate input
        if not data or "brand" not in data or "intent" not in data:
            return (
                jsonify({"success": False, "error": "Brand and intent are required"}),
                400,
            )

        brand = data["brand"]
        intent = data["intent"]
        assistants = data.get("assistants", ["chatgpt", "claude"])

        # Track citations
        results = engine_ai_visibility.track_citations(intent, brand, assistants)

        # Persist to database
        db = SessionLocal()
        try:
            for result in results:
                if "error" not in result:  # Only persist successful queries
                    citation = CitationSnapshot(
                        brand=brand,
                        intent=intent,
                        assistant=result["assistant"],
                        cited=1 if result["cited"] else 0,
                        response_text=result.get("response", ""),
                    )
                    db.add(citation)
            db.commit()
        except Exception as e:
            db.rollback()
            app.logger.error(f"Citation persistence error: {str(e)}")
        finally:
            db.close()

        # Calculate summary
        total = len(results)
        cited_count = sum(1 for r in results if r.get("cited", False))
        rate = (cited_count / total * 100) if total > 0 else 0.0

        return jsonify(
            {
                "success": True,
                "data": {
                    "results": results,
                    "summary": {
                        "total": total,
                        "cited": cited_count,
                        "rate": round(rate, 1),
                    },
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/citations/stats", methods=["GET"])
def get_citation_stats():
    """
    Get citation statistics for a brand.

    Query parameters:
    - brand: Brand name (required)

    Returns:
    {
        "success": true,
        "data": {
            "brand": "Asana",
            "total_queries": 10,
            "overall_rate": 40.0,
            "chatgpt_rate": 50.0,
            "claude_rate": 30.0
        }
    }
    """
    try:
        brand = request.args.get("brand")

        if not brand:
            return (
                jsonify({"success": False, "error": "Brand parameter is required"}),
                400,
            )

        db = SessionLocal()
        try:
            stats = engine_ai_visibility.get_citation_rate(brand, db)
            return jsonify({"success": True, "data": stats})
        finally:
            db.close()

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/keys/create", methods=["POST"])
def create_api_key():
    """
    Create a new API key.

    Request body:
    {
        "name": "My App Key",  // optional
        "quota_per_hour": 10   // optional, default: 10
    }

    Returns:
    {
        "success": true,
        "data": {
            "key": "abc123...",
            "name": "My App Key",
            "quota_per_hour": 10,
            "created_at": "2025-10-17T12:00:00"
        }
    }
    """
    try:
        data = request.get_json() or {}
        name = data.get("name")
        quota = data.get("quota_per_hour", 10)

        # Validate quota
        if not isinstance(quota, int) or quota < 1 or quota > 1000:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "quota_per_hour must be between 1 and 1000",
                    }
                ),
                400,
            )

        # Generate key
        key_data = generate_api_key(name=name, quota_per_hour=quota)

        return jsonify({"success": True, "data": key_data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/keys/list", methods=["GET"])
def list_keys():
    """
    List all API keys (masked for security).

    Returns:
    {
        "success": true,
        "data": [
            {
                "id": 1,
                "key": "abc123...xyz",
                "name": "My Key",
                "is_active": true
            },
            ...
        ]
    }
    """
    try:
        keys = list_api_keys()
        return jsonify({"success": True, "data": keys, "count": len(keys)})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plans", methods=["GET"])
def get_plans():
    """
    Get all available audit plans.

    Returns:
    {
        "success": true,
        "data": [
            {
                "id": "quickscan",
                "name": "QuickScan",
                "price": 0,
                "max_pages": 3,
                ...
            },
            ...
        ]
    }
    """
    try:
        all_plans = plans.get_all_plans()
        return jsonify({"success": True, "data": all_plans})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plans/compare", methods=["GET"])
def compare_plans():
    """
    Get plan comparison matrix.

    Returns:
    {
        "success": true,
        "data": [
            {
                "name": "Pages Scanned",
                "quickscan": "Up to 3",
                "full": "Up to 12",
                "agency": "Up to 12"
            },
            ...
        ]
    }
    """
    try:
        comparison = plans.compare_plans()
        return jsonify({"success": True, "data": comparison})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report/markdown", methods=["POST"])
def generate_markdown_report():
    """
    Generate Markdown report from audit results.

    Request body: audit results data
    Returns: Markdown file
    """
    try:
        data = request.get_json()

        url = data.get("url")
        packs = data.get("packs", ["base"])
        scores = data.get("scores")
        findings = data.get("findings")

        markdown_content = engine_report.generate_markdown(url, packs, scores, findings)

        # Create file-like object
        buffer = io.BytesIO(markdown_content.encode("utf-8"))
        buffer.seek(0)

        filename = f"{urlparse(url).netloc}_audit_{datetime.now().strftime('%Y%m%d')}.md"

        return send_file(
            buffer, as_attachment=True, download_name=filename, mimetype="text/markdown"
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report/docx", methods=["POST"])
def generate_docx_report():
    """
    Generate DOCX report from audit results.

    Request body: audit results data
    Returns: DOCX file
    """
    try:
        data = request.get_json()

        url = data.get("url")
        packs = data.get("packs", ["base"])
        scores = data.get("scores")
        findings = data.get("findings")

        docx_bytes = engine_report.generate_docx(url, packs, scores, findings)

        # Create file-like object
        buffer = io.BytesIO(docx_bytes)
        buffer.seek(0)

        filename = f"{urlparse(url).netloc}_audit_{datetime.now().strftime('%Y%m%d')}.docx"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================
# New: Answer Graph & Playbooks APIs (dev server)
# =========================


@app.route("/api/answer_graph/build", methods=["POST"])
@limiter.limit("5/minute")
def api_answer_graph_build():
    try:
        data = request.get_json() or {}
        domain = data.get("domain")
        intents = data.get("intents", [])
        packs = data.get("packs", ["base"])
        if not domain or not isinstance(intents, list):
            return (
                jsonify({"success": False, "error": "domain and intents[] required"}),
                400,
            )

        max_intents = int(os.getenv("PLAYBOOK_MAX_INTENTS", "5"))
        intents = intents[:max_intents]

        payload = build_answer_graph(domain, intents, packs)

        db = SessionLocal()
        try:
            rec = AnswerGraphModel(
                domain=payload.get("domain"),
                intents=payload.get("intents"),
                packs=payload.get("packs"),
                nodes=payload.get("nodes"),
                edges=payload.get("edges"),
                gaps=payload.get("gaps"),
                priority_score=payload.get("priority_score", 0.0),
            )
            db.add(rec)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return jsonify({"success": True, "data": payload})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/answer_graph/", methods=["GET"])
def api_answer_graph_get():
    try:
        domain = request.args.get("domain")
        if not domain:
            return jsonify({"success": False, "error": "domain required"}), 400
        limit = min(int(request.args.get("limit", 1)), 5)

        db = SessionLocal()
        try:
            q = (
                db.query(AnswerGraphModel)
                .filter(AnswerGraphModel.domain == domain)
                .order_by(AnswerGraphModel.created_at.desc())
                .limit(limit)
                .all()
            )
            data = [r.to_dict() for r in q]
            return jsonify({"success": True, "data": data, "count": len(data)})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/playbooks/generate", methods=["POST"])
@limiter.limit("5/minute")
def api_playbooks_generate():
    try:
        data = request.get_json() or {}
        domain = data.get("domain")
        intent = data.get("intent")
        target_assistant = data.get("target_assistant", "chatgpt")
        if not domain or not intent:
            return (
                jsonify({"success": False, "error": "domain and intent required"}),
                400,
            )

        gaps = data.get("gaps")
        if not isinstance(gaps, list):
            try:
                ag = build_answer_graph(domain, [intent], ["base"])
                gaps = ag.get("gaps", [])
            except Exception:
                gaps = []

        playbook = generate_playbook(domain, intent, target_assistant, gaps)

        db = SessionLocal()
        try:
            p = PlaybookModel(
                domain=domain,
                intent=intent,
                target_assistant=target_assistant,
                playbook_json=playbook,
            )
            db.add(p)
            db.flush()
            for fx in playbook.get("fixes", []):
                f = PlaybookFixModel(
                    playbook_id=p.id,
                    fix_id=fx.get("id", ""),
                    title=fx.get("title", ""),
                    language=fx.get("language"),
                    snippet=fx.get("snippet"),
                    why=fx.get("why"),
                )
                db.add(f)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return jsonify({"success": True, "data": playbook})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report/playbook_md", methods=["POST"])
def api_report_playbook_md():
    try:
        from engine_report import generate_playbook_markdown

        data = request.get_json() or {}
        playbook = data.get("playbook")
        if not isinstance(playbook, dict):
            return jsonify({"success": False, "error": "playbook dict required"}), 400
        md = generate_playbook_markdown(playbook)
        import io as _io

        buffer = _io.BytesIO(md.encode("utf-8"))
        buffer.seek(0)
        domain = playbook.get("domain", "playbook")
        filename = f"{domain}_playbook_{datetime.now().strftime('%Y%m%d')}.md"
        return send_file(
            buffer, as_attachment=True, download_name=filename, mimetype="text/markdown"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report/playbook_docx", methods=["POST"])
def api_report_playbook_docx():
    try:
        from engine_report import generate_playbook_docx

        data = request.get_json() or {}
        playbook = data.get("playbook")
        if not isinstance(playbook, dict):
            return jsonify({"success": False, "error": "playbook dict required"}), 400
        bytes_docx = generate_playbook_docx(playbook)
        import io as _io

        buffer = _io.BytesIO(bytes_docx)
        buffer.seek(0)
        domain = playbook.get("domain", "playbook")
        filename = f"{domain}_playbook_{datetime.now().strftime('%Y%m%d')}.docx"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



# =========================
# Authentication Endpoints
# =========================

@app.route("/api/v1/auth/signup", methods=["POST"])
def auth_signup():
    """Register a new user."""
    try:
        from api.vysalytica.auth import hash_password, create_access_token
        from api.vysalytica.db.models import User
        
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password required"}), 400
        
        db = SessionLocal()
        try:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return jsonify({"success": False, "error": "Email already registered"}), 400
            
            user = User(
                email=email,
                password_hash=hash_password(password),
                name=name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
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


@app.route("/api/v1/auth/login", methods=["POST"])
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


@app.route("/api/v1/auth/me", methods=["GET"])
def auth_me():
    """Get current user info from token."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import User
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            
            return jsonify({"success": True, "data": user.to_dict()})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================
# Brand Management Endpoints
# =========================

@app.route("/api/v1/brands", methods=["GET"])
def get_brands():
    """Get all brands for the authenticated user."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import User, Brand
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        
        db = SessionLocal()
        try:
            brands = db.query(Brand).filter(Brand.user_id == user_id).all()
            return jsonify({
                "success": True,
                "data": [b.to_dict() for b in brands]
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/brands", methods=["POST"])
def create_brand():
    """Create a new brand."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import Brand
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        data = request.get_json()
        
        name = data.get("name")
        primary_url = data.get("primary_url")
        
        if not name or not primary_url:
            return jsonify({"success": False, "error": "Name and primary_url required"}), 400
        
        db = SessionLocal()
        try:
            brand = Brand(
                user_id=user_id,
                name=name,
                primary_url=primary_url,
                catalog_url=data.get("catalog_url"),
                competitors=data.get("competitors", [])
            )
            db.add(brand)
            db.commit()
            db.refresh(brand)
            
            return jsonify({"success": True, "data": brand.to_dict()})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/brands/<int:brand_id>", methods=["GET"])
def get_brand(brand_id):
    """Get a specific brand."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import Brand
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        
        db = SessionLocal()
        try:
            brand = db.query(Brand).filter(
                Brand.id == brand_id,
                Brand.user_id == user_id
            ).first()
            
            if not brand:
                return jsonify({"success": False, "error": "Brand not found"}), 404
            
            return jsonify({"success": True, "data": brand.to_dict()})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/brands/<int:brand_id>/audits", methods=["GET"])
def get_brand_audits(brand_id):
    """Get all audits for a brand."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.db.models import Brand
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        
        db = SessionLocal()
        try:
            brand = db.query(Brand).filter(
                Brand.id == brand_id,
                Brand.user_id == user_id
            ).first()
            
            if not brand:
                return jsonify({"success": False, "error": "Brand not found"}), 404
            
            audits = db.query(AuditRun).filter(AuditRun.brand_id == brand_id).order_by(
                AuditRun.created_at.desc()
            ).all()
            
            return jsonify({
                "success": True,
                "data": [a.to_dict() for a in audits]
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================
# Payment Endpoints
# =========================

@app.route("/api/v1/payments/create-checkout-session", methods=["POST"])
def create_checkout_session():
    """Create a Stripe checkout session."""
    try:
        from api.vysalytica.auth import decode_access_token
        from api.vysalytica.stripe_service import create_checkout_session as create_stripe_session
        from api.vysalytica.db.models import Payment
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        
        user_id = payload.get("user_id")
        data = request.get_json()
        
        amount = data.get("amount", 10000)  # Default $100
        currency = data.get("currency", "usd")
        success_url = data.get("success_url", "http://localhost:3000/checkout/success")
        cancel_url = data.get("cancel_url", "http://localhost:3000/checkout/cancel")
        
        session_data = create_stripe_session(
            user_id=user_id,
            amount=amount,
            currency=currency,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if not session_data:
            return jsonify({"success": False, "error": "Failed to create checkout session"}), 500
        
        db = SessionLocal()
        try:
            payment = Payment(
                user_id=user_id,
                stripe_session_id=session_data["session_id"],
                amount=amount,
                currency=currency,
                status="pending"
            )
            db.add(payment)
            db.commit()
        finally:
            db.close()
        
        return jsonify({
            "success": True,
            "data": {
                "url": session_data["url"],
                "session_id": session_data["session_id"]
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/payments/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    try:
        from api.vysalytica.stripe_service import verify_webhook_signature
        from api.vysalytica.db.models import Payment
        
        payload = request.data
        sig_header = request.headers.get("Stripe-Signature")
        
        event = verify_webhook_signature(payload, sig_header)
        
        if not event:
            return jsonify({"success": False, "error": "Invalid signature"}), 400
        
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session["id"]
            
            db = SessionLocal()
            try:
                payment = db.query(Payment).filter(
                    Payment.stripe_session_id == session_id
                ).first()
                
                if payment:
                    payment.status = "paid"
                    db.commit()
            finally:
                db.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/", methods=["OPTIONS"])
@app.route("/<path:any_path>", methods=["OPTIONS"])
def options_handler(any_path: str | None = None):
    return jsonify({"ok": True})


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
