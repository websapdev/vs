"""
Engine: AI Answer Graph

Builds a lightweight entity and page graph for a domain and set of intents,
using existing crawl/parse engines. Optimized for free-tier environments.

Outputs:
- nodes: list of nodes with type (page|entity), id, label, meta
- edges: list of edges (source, target, type)
- gaps: list of gap dicts with id, title, severity, evidence
- priority_score: float 0-100 summarizing urgency/impact
- stats: counts and schema coverage

Caching:
- In-process TTL cache keyed by (domain, intents, packs) with ANSWER_GRAPH_CACHE_TTL seconds

"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

# Reuse project engines
from api import engine_crawl, engine_parse

_CACHE: Dict[Tuple[str, Tuple[str, ...], Tuple[str, ...]], Tuple[float, Dict[str, Any]]] = {}


def _ttl_seconds() -> int:
    try:
        return int(os.getenv("ANSWER_GRAPH_CACHE_TTL", "900"))
    except Exception:
        return 900


def _norm_domain(domain_or_url: str) -> str:
    parsed = urlparse(
        domain_or_url if domain_or_url.startswith("http") else f"https://{domain_or_url}"
    )
    return parsed.netloc.lower()


def _extract_entities_from_page(page: Dict[str, Any]) -> List[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    url = page.get("url")
    title = page.get("title")
    h1s = page.get("h_tags", {}).get("h1", []) or []

    # Title/H1 entities
    if title:
        entities.append(
            {
                "type": "entity",
                "id": f"ent:{url}#title",
                "label": title[:120],
                "source": url,
                "kind": "Title",
            }
        )
    for idx, h in enumerate(h1s[:3]):
        entities.append(
            {
                "type": "entity",
                "id": f"ent:{url}#h1-{idx}",
                "label": h[:120],
                "source": url,
                "kind": "H1",
            }
        )

    # JSON-LD entities
    for jd in page.get("jsonld", []) or []:
        if isinstance(jd, dict):
            typ = jd.get("@type")
            name = jd.get("name") or jd.get("headline") or jd.get("title")
            if isinstance(typ, list):
                typ = ",".join(t for t in typ if isinstance(t, str))
            if typ or name:
                label = f"{name or typ}"
                entities.append(
                    {
                        "type": "entity",
                        "id": f"ent:{url}#jsonld:{name or typ}",
                        "label": str(label)[:160],
                        "source": url,
                        "kind": f"JSON-LD:{typ or 'Unknown'}",
                    }
                )
    return entities


def _detect_gaps(
    pages: List[Dict[str, Any]], domain: str, intents: List[str]
) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []

    # Homepage signals
    homepage = pages[0] if pages else {}
    jsonld_home = homepage.get("jsonld", []) if homepage else []
    has_org = any(
        isinstance(j, dict)
        and (
            j.get("@type") == "Organization"
            or (isinstance(j.get("@type"), list) and "Organization" in j.get("@type"))
        )
        for j in (jsonld_home or [])
    )
    if not has_org:
        gaps.append(
            {
                "id": "gap:org-jsonld",
                "title": "Missing Organization JSON-LD on homepage",
                "severity": "high",
                "evidence": {
                    "page": homepage.get("url"),
                    "hint": "Add Organization with sameAs, url, logo",
                },
            }
        )

    # FAQ/TLDR presence across pages
    def _has_tldr_or_faq(page: Dict[str, Any]) -> bool:
        title = (page.get("title") or "").lower()
        h2s = [h.lower() for h in page.get("h_tags", {}).get("h2", []) or []]
        body_join = "\n".join(page.get("h_tags", {}).get("h3", []) or []).lower()
        return ("tl;dr" in title) or any("faq" in h or "tl;dr" in h for h in (h2s + [body_join]))

    if not any(_has_tldr_or_faq(p) for p in pages[:5]):
        gaps.append(
            {
                "id": "gap:tldr-faq",
                "title": "No TL;DR or FAQ blocks detected",
                "severity": "medium",
                "evidence": {"pages_checked": [p.get("url") for p in pages[:5]]},
            }
        )

    # Intent coverage (very simple keyword match over titles/H1)
    for intent in intents[:10]:
        tokens = [t.strip().lower() for t in intent.split()] if intent else []
        covered = False
        for p in pages:
            text_blob = " ".join(
                [(p.get("title") or ""), " ".join(p.get("h_tags", {}).get("h1", []) or [])]
            ).lower()
            if all(tok in text_blob for tok in tokens[:2]):  # cheap heuristic
                covered = True
                break
        if not covered:
            gaps.append(
                {
                    "id": f"gap:intent:{intent}",
                    "title": f"Weak coverage for intent: {intent}",
                    "severity": "medium",
                    "evidence": {"hint": "Create hub or FAQ addressing phrasing variations"},
                }
            )

    # Schema coverage on key types
    required_types = {"FAQPage", "HowTo", "Product", "Article"}
    found_types = set()
    for p in pages:
        for jd in p.get("jsonld", []) or []:
            if isinstance(jd, dict):
                t = jd.get("@type")
                if isinstance(t, str):
                    found_types.add(t)
                elif isinstance(t, list):
                    for s in t:
                        if isinstance(s, str):
                            found_types.add(s)
    for req in sorted(required_types - found_types):
        gaps.append(
            {
                "id": f"gap:schema:{req}",
                "title": f"Missing {req} schema on relevant pages",
                "severity": "low",
            }
        )

    return gaps


def _priority_score(gaps: List[Dict[str, Any]]) -> float:
    weights = {"high": 25, "medium": 12, "low": 6}
    score = 0
    for g in gaps:
        score += weights.get(str(g.get("severity", "low")).lower(), 6)
    return max(0.0, min(100.0, float(score)))


def build_answer_graph(domain: str, intents: List[str], packs: List[str]) -> Dict[str, Any]:
    """
    Build the answer graph and gap analysis for a domain.
    Falls back gracefully on partial failures.
    """
    domain_norm = _norm_domain(domain)
    intents_tuple = tuple(intents or [])
    packs_tuple = tuple(packs or ["base"])  # unused for now, reserved for rule scoping

    # TTL cache lookup
    cache_key = (domain_norm, intents_tuple, packs_tuple)
    now = time.time()
    if cache_key in _CACHE:
        ts, payload = _CACHE[cache_key]
        if now - ts < _ttl_seconds():
            return payload

    # Crawl + parse
    try:
        urls = engine_crawl.discover_pages(f"https://{domain_norm}")
    except Exception:
        urls = [f"https://{domain_norm}"]

    pages = []
    try:
        pages = engine_parse.parse_site(urls)
    except Exception:
        # Partial failure handling: still return minimal graph
        pages = [
            {
                "url": u,
                "title": None,
                "h_tags": {"h1": [], "h2": [], "h3": []},
                "jsonld": [],
                "error": True,
            }
            for u in urls
        ]

    # Build nodes/edges
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    page_nodes = []
    for p in pages:
        page_node = {
            "type": "page",
            "id": f"page:{p['url']}",
            "label": p.get("title") or p["url"],
            "url": p["url"],
            "meta": {"has_error": bool(p.get("error"))},
        }
        page_nodes.append(page_node)
        nodes.append(page_node)
        # Add entity nodes and edges
        ents = _extract_entities_from_page(p)
        for e in ents:
            nodes.append(e)
            edges.append({"source": page_node["id"], "target": e["id"], "type": "page-entity"})

    # Simple internal linking opportunities: pages missing mention of top intent tokens
    if intents:
        top_tokens = [t.lower() for t in (" ".join(intents)).split() if len(t) > 3][:6]
        for p in pages:
            blob = (p.get("title") or "") + " " + " ".join(p.get("h_tags", {}).get("h1", []) or [])
            if not any(tok in blob.lower() for tok in top_tokens):
                edges.append(
                    {
                        "source": f"page:{p['url']}",
                        "target": f"intent:{intents[0]}",
                        "type": "suggest-link",
                        "reason": "Add internal link with target intent anchor",
                    }
                )
        # Add intent node (virtual)
        nodes.append(
            {"type": "entity", "id": f"intent:{intents[0]}", "label": intents[0], "kind": "Intent"}
        )

    # Gaps and scores
    gaps = _detect_gaps(pages, domain_norm, intents)
    score = _priority_score(gaps)

    payload = {
        "domain": domain_norm,
        "intents": list(intents or []),
        "packs": list(packs or ["base"]),
        "nodes": nodes,
        "edges": edges,
        "gaps": gaps,
        "priority_score": score,
        "stats": {
            "pages": len(pages),
            "entities": len([n for n in nodes if n.get("type") == "entity"]),
            "schema_entities": sum(
                1 for n in nodes if str(n.get("kind", "")).startswith("JSON-LD")
            ),
        },
    }

    _CACHE[cache_key] = (now, payload)
    return payload
