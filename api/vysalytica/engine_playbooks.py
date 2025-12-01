"""
Engine: Visibility Playbooks

Generates prescriptive, structured playbooks per intent, including:
- Gaps addressed
- Copyable schema JSON-LD
- TL;DR / FAQ blocks
- Acceptance tests (pytest-style) with simple assertions

Free-tier friendly:
- If ROUTELLM_* or OpenAI/Anthropic not configured, produce rule-based minimal playbook.
- If LLM is available via RouteLLM, enrich with wording but keep structure identical.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from api.vysalytica.config import (
    create_openai_client_safe,
    debug_openai_client_info,
    get_openai_api_key,
    get_routellm_api_key,
    get_routellm_base_url,
    get_routellm_model,
)

# Optional LLM via RouteLLM/OpenAI
ROUTELLM_API_KEY = get_routellm_api_key()
ROUTELLM_BASE_URL = get_routellm_base_url()
ROUTELLM_MODEL = get_routellm_model()
OPENAI_API_KEY = get_openai_api_key()

openai_client = None
if ROUTELLM_API_KEY:
    try:
        # Debug client parameters to help diagnose version conflicts
        debug_openai_client_info()

        openai_client = create_openai_client_safe(
            api_key=ROUTELLM_API_KEY, base_url=ROUTELLM_BASE_URL
        )
        print(
            f"[OK] RouteLLM configured for playbook enrichment (base_url: {ROUTELLM_BASE_URL}, model: {ROUTELLM_MODEL})"
        )
    except TypeError as exc:
        if "proxies" in str(exc):
            print(f"[FAIL] RouteLLM still receiving 'proxies' argument: {exc}")
            print(f"[FAIL] This suggests an external library is passing 'proxies'")
        else:
            print(f"[FAIL] RouteLLM initialization failed: {exc}")
        openai_client = None
    except Exception as exc:
        openai_client = None
        print(f"⚠️ RouteLLM initialization failed for playbook generation: {exc}")
elif OPENAI_API_KEY:
    try:
        openai_client = create_openai_client_safe(api_key=OPENAI_API_KEY)
        print("[OK] OpenAI configured for playbook enrichment")
    except TypeError as exc:
        if "proxies" in str(exc):
            print(f"[FAIL] OpenAI still receiving 'proxies' argument: {exc}")
        else:
            print(f"[FAIL] OpenAI initialization failed: {exc}")
        openai_client = None
    except Exception as exc:
        openai_client = None
        print(f"⚠️ OpenAI initialization failed for playbook generation: {exc}")
else:
    print("ℹ️ LLM API key not configured; playbooks will use rule-based defaults.")


def _minimal_jsonld(domain: str) -> Dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": domain.split(".")[0].title(),
        "url": f"https://{domain}",
        "sameAs": [],
        "logo": f"https://{domain}/logo.png",
    }


def _tldr_block(intent: str) -> str:
    return "\n".join(
        [
            "<!-- TL;DR: Place near top of page -->",
            '<section id="tldr">',
            f"  <h2>TL;DR — {intent}</h2>",
            "  <ul>",
            "    <li>One-sentence answer with brand context.</li>",
            "    <li>Key evidence or metric.</li>",
            "    <li>Link to detailed section below.</li>",
            "  </ul>",
            "</section>",
        ]
    )


def _faq_block(intent: str, domain: str) -> str:
    faqs = [
        (
            f"What is {domain.split('.')[0].title()}?",
            "A concise definition with differentiators.",
        ),
        (f"How does it compare for {intent}?", "Short comparison and when to use."),
        ("Where can I find docs?", f"See https://{domain}/docs for details."),
    ]
    html = ['<section id="faq">', "  <h2>FAQ</h2>"]
    for q, a in faqs:
        html.extend([f"  <h3>{q}</h3>", f"  <p>{a}</p>"])
    html.append("</section>")
    return "\n".join(html)


def _acceptance_tests(domain: str, intent: str, target_assistant: str) -> str:
    return "\n".join(
        [
            "import re",
            "def test_tldr_present(html):",
            "    assert '<section id=\"tldr\"' in html",
            "def test_faq_present(html):",
            "    assert '<section id=\"faq\"' in html",
            "def test_jsonld_has_org(jsonld):",
            "    assert any(obj.get('@type') in ('Organization', ['Organization']) for obj in jsonld)",
            "def test_brand_mention_first_paragraph(html):",
            f"    assert '{domain.split('.')[0].title()}' in html[:2000]",
        ]
    )


def generate_playbook(
    domain: str, intent: str, target_assistant: str, gaps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Returns a structured playbook dict with portable sections.
    """
    domain_norm = domain.lower()

    # Base content
    jsonld_obj = _minimal_jsonld(domain_norm)
    tldr_html = _tldr_block(intent)
    faq_html = _faq_block(intent, domain_norm)

    # If LLM available, ask to refine TL;DR copy (optional, best-effort)
    refined_tldr = None
    if openai_client is not None:
        try:
            prompt = (
                "You are refining a TL;DR for an answer engine. Keep 2 bullets. Neutral, cite brand neutrally.\n"
                f"Intent: {intent}\nBrand domain: {domain_norm}\n"
            )
            resp = openai_client.chat.completions.create(
                model=ROUTELLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.2,
            )
            refined_tldr = resp.choices[0].message.content.strip()
        except Exception:
            refined_tldr = None

    schema_json = json.dumps(jsonld_obj, indent=2)

    playbook: Dict[str, Any] = {
        "domain": domain_norm,
        "intent": intent,
        "target_assistant": target_assistant,
        "fixes": [
            {
                "id": "fix:org-jsonld",
                "title": "Add Organization JSON-LD to homepage",
                "snippet": schema_json,
                "language": "json",
                "why": "Ground brand entity for assistants and link sameAs profiles.",
            },
            {
                "id": "fix:tldr",
                "title": "Add TL;DR section near top",
                "snippet": refined_tldr or tldr_html,
                "language": "html",
                "why": "Assistants reuse concise summaries for snippets and citations.",
            },
            {
                "id": "fix:faq",
                "title": "Add FAQ section aligned to intent",
                "snippet": faq_html,
                "language": "html",
                "why": "Questions map to conversational paraphrases and improve recall.",
            },
        ],
        "jsonld": jsonld_obj,
        "tldr_html": refined_tldr or tldr_html,
        "faq_html": faq_html,
        "acceptance_tests_py": _acceptance_tests(domain_norm, intent, target_assistant),
        "gaps_addressed": [g.get("id") for g in gaps],
        "projected_impact": 12.0 + 6.0 * len([g for g in gaps if g.get("severity") == "high"]),
    }

    return playbook
