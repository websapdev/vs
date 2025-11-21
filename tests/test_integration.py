import api.api as api_module
from api.vysalytica.db import SessionLocal
from api.vysalytica.db.models import AuditRun, Finding


def test_audit_creates_records(monkeypatch, client):
    monkeypatch.setattr(
        api_module.engine_crawl, "discover_pages", lambda url: ["https://example.com"]
    )
    monkeypatch.setattr(api_module.engine_crawl, "fetch", lambda url: (url, ""))
    monkeypatch.setattr(
        api_module.engine_parse, "parse_site", lambda urls: [{"url": urls[0], "error": False}]
    )
    monkeypatch.setattr(
        api_module.engine_rules,
        "evaluate",
        lambda pages, meta, packs: (
            [
                {
                    "id": "RULE-1",
                    "title": "Rule Title",
                    "category": "base",
                    "status": "fail",
                    "confidence": 0.5,
                    "evidence": [],
                    "why": "",
                    "fix": "",
                }
            ],
            {"overall": 50.0, "by_category": {"base": 50.0}},
        ),
    )
    monkeypatch.setattr(api_module.engine_fixgen, "generate_fixes_bulk", lambda findings: findings)
    monkeypatch.setattr(api_module.plans, "check_feature_access", lambda plan, feature: True)

    resp = client.post("/api/audit", json={"url": "https://example.com"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["audit_id"] is not None

    session = SessionLocal()
    try:
        assert session.query(AuditRun).count() == 1
        assert session.query(Finding).count() == 1
    finally:
        session.close()
