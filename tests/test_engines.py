import api.engine_crawl as engine_crawl
import api.engine_parse as engine_parse
import api.engine_report as engine_report
import api.engine_rules_enhanced as engine_rules


def test_discover_pages_prefers_sitemap(monkeypatch):
    sitemap = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.com/about</loc></url>
        <url><loc>https://example.com/contact</loc></url>
    </urlset>
    """

    def fake_get(url, *args, **kwargs):
        class Resp:
            def __init__(self, text, status_code=200):
                self.text = text
                self.status_code = status_code

        if url.endswith("sitemap.xml"):
            return Resp(sitemap)
        return Resp("<html><body><a href='/blog'>Blog</a></body></html>")

    monkeypatch.setattr(engine_crawl.requests, "get", fake_get)
    pages = engine_crawl.discover_pages("https://example.com", max_pages=3)
    assert pages[0] == "https://example.com"
    assert "https://example.com/about" in pages


def test_parse_page_extracts_metadata():
    html = """
    <html>
      <head>
        <title>Example Title</title>
        <meta name="description" content="Example description" />
        <link rel="canonical" href="https://example.com/" />
      </head>
      <body>
        <h1>Welcome</h1>
        <a href="https://example.com/about">About</a>
      </body>
    </html>
    """
    parsed = engine_parse.parse_page("https://example.com", html)
    assert parsed["title"] == "Example Title"
    assert parsed["meta_desc"] == "Example description"
    assert parsed["canonical"].startswith("https://example.com")
    assert "Welcome" in parsed["h_tags"]["h1"][0]


def test_engine_rules_evaluate_basic():
    html = "<html><head><title>Welcome</title></head><body><h1>Headline</h1></body></html>"
    page = engine_parse.parse_page("https://example.com", html)
    findings, scores = engine_rules.evaluate(
        [page],
        {
            "domain": "example.com",
            "base_url": "https://example.com",
            "homepage": page,
            "robots_txt": None,
            "sitemap_url": None,
        },
        ["base"],
    )
    assert isinstance(findings, list)
    assert "overall" in scores
    assert "by_category" in scores


def test_generate_docx_returns_bytes():
    findings = [
        {
            "id": "RULE-1",
            "title": "Rule One",
            "category": "base",
            "status": "pass",
            "confidence": 1.0,
            "evidence": [],
            "why": "",
            "fix": "",
        }
    ]
    scores = {"overall": 100.0, "by_category": {"base": 100.0}}
    content = engine_report.generate_docx("https://example.com", ["base"], scores, findings)
    assert isinstance(content, (bytes, bytearray))
    assert len(content) > 0
