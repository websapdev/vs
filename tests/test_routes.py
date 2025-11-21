import api.api as api_module


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["db"] == "up"


def test_version_contains_git_sha(client):
    resp = client.get("/version")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "git_sha" in body
    assert "python" in body


def test_openapi_lists_routes(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "/healthz" in body["paths"]


def test_get_routes_smoke(client):
    app = api_module.app
    rules = [
        rule
        for rule in app.url_map.iter_rules()
        if "GET" in rule.methods and "<" not in rule.rule and not rule.rule.startswith("/static")
    ]
    for rule in rules:
        resp = client.get(rule.rule)
        assert resp.status_code < 500
        # allow non-json like docx endpoints, but prefer JSON
        if resp.data:
            assert resp.is_json or resp.mimetype in {
                "application/json",
                "text/html",
                "text/markdown",
            }
