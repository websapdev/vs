"""
Enhanced Rules Engine for AI Visibility MVP
Based on 2025 AI visibility optimization research
Includes comprehensive GEO (Generative Engine Optimization) best practices
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse


# Enhanced rule pack definitions with new 2025 rules
RULE_PACKS = {
    "base": [
        "CRW-ROB-001",
        "CRW-SMP-001",
        "CRW-CAN-001",
        "SCH-ORG-001",
        "SCH-FAQ-001",
        "SCH-BRD-001",
        "SCH-ART-001",
        "ANS-HDR-001",
        "ANS-TLD-001",
        "ANS-LEN-001",
        "CTX-REV-001",
        "CTX-AUT-001",
    ],
    "ecomm": ["ECM-PRO-001", "ECM-OFR-001", "ECM-REV-001", "ECM-AGG-001"],
    "docs": ["DOC-OAS-001", "DOC-EXM-001", "DOC-TUT-001"],
    "aio": [
        "AIO-ENT-001",
        "AIO-ENT-002",
        "AIO-ENTITY-006",
        "AIO-ENT-011",
        "AIO-ENT-012",
        "AIO-ENT-013",
        "AIO-ENT-014",
        "AIO-ENT-015",
        "AIO-ENT-016",
        "AIO-ENT-017",
        "AIO-SCHEMA-003",
        "AIO-SCHEMA-004",
        "AIO-CONTENT-005",
        "AIO-UX-007",
        "AIO-SOCIAL-008",
        "AIO-FRESH-009",
        "AIO-MULTI-010",
        "AIO-SEM-018",
        "AIO-SEM-019",
        "AIO-SEM-020",
        "AIO-SEM-021",
        "AIO-SEM-022",
        "AIO-SEM-023",
        "AIO-SEM-024",
        "AIO-SEM-025",
    ],
}


AUTHORITY_SAMEAS_DOMAINS = {"wikipedia.org", "wikidata.org", "linkedin.com"}
LINKEDIN_CRUNCHBASE_DOMAINS = {"linkedin.com", "crunchbase.com"}
SOCIAL_PROFILE_DOMAINS = {
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
}
GENERIC_ANCHOR_TEXT = {
    "click here",
    "learn more",
    "read more",
    "here",
    "details",
}


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _iter_jsonld(pages: List[Dict]) -> List[Tuple[Dict, Dict, List[str]]]:
    for page in pages:
        for item in page.get("jsonld", []):
            item_type = item.get("@type")
            types = (
                item_type
                if isinstance(item_type, list)
                else [item_type] if item_type else []
            )
            yield page, item, types


def _get_sameas_urls(item: Dict[str, Any]) -> List[str]:
    sameas = item.get("sameAs")
    if isinstance(sameas, list):
        return [link for link in sameas if isinstance(link, str)]
    if isinstance(sameas, str):
        return [sameas]
    return []


def _parse_date_string(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        iso_value = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(iso_value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        pass
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%d %B %Y",
        "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            continue
    return None


def _gather_candidate_dates(page: Dict[str, Any]) -> List[datetime]:
    dates: List[datetime] = []
    meta = page.get("meta", {})
    article_meta = meta.get("article", {}) if isinstance(meta, dict) else {}
    for key in ["modified_time", "published_time", "updated_time"]:
        dt = _parse_date_string(article_meta.get(key))
        if dt:
            dates.append(dt)
    if isinstance(meta, dict):
        dt = _parse_date_string(meta.get("http_equiv_last_modified"))
        if dt:
            dates.append(dt)
    for _, item, _ in _iter_jsonld([page]):
        for key in ["dateModified", "datePublished", "uploadDate"]:
            dt = _parse_date_string(item.get(key))
            if dt:
                dates.append(dt)
    return dates


def _is_descriptive_anchor(text: str) -> bool:
    if not text:
        return False
    normalized = re.sub(r"\s+", " ", text.strip()).lower()
    if normalized in GENERIC_ANCHOR_TEXT:
        return False
    return len(normalized.split()) >= 2 and len(normalized) >= 8


def _page_has_social_link(page: Dict[str, Any]) -> bool:
    # Check JSON-LD sameAs first
    for _, item, _ in _iter_jsonld([page]):
        sameas_urls = _get_sameas_urls(item)
        for url in sameas_urls:
            domain = urlparse(url).netloc.lower()
            if any(
                domain.endswith(social_domain)
                for social_domain in SOCIAL_PROFILE_DOMAINS
            ):
                return True
    # Fallback to anchor links
    for link in page.get("links", []):
        href = link.get("href")
        if not href:
            continue
        domain = urlparse(href).netloc.lower()
        if any(
            domain.endswith(social_domain) for social_domain in SOCIAL_PROFILE_DOMAINS
        ):
            return True
    return False


def _collect_sameas_domains(pages: List[Dict]) -> List[str]:
    domains: List[str] = []
    for _, item, _ in _iter_jsonld(pages):
        for url in _get_sameas_urls(item):
            domain = urlparse(url).netloc.lower()
            if domain:
                domains.append(domain)
    return domains


def _indexable_pages(pages: List[Dict]) -> List[Dict]:
    indexable = []
    for page in pages:
        robots_meta = ""
        meta = page.get("meta")
        if isinstance(meta, dict):
            robots_meta = (meta.get("robots") or "").lower()
        if "noindex" in robots_meta:
            continue
        indexable.append(page)
    return indexable


def check_robots_gptbot(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if robots.txt allows GPTBot and other AI crawlers."""
    robots_txt = site_meta.get("robots_txt")

    if not robots_txt:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": f"{site_meta['base_url']}/robots.txt",
                    "snippet": "robots.txt not accessible",
                }
            ],
        }

    # Check for AI crawler bots
    ai_bots = [
        "gptbot",
        "googlebot-other",
        "claude-web",
        "perplexitybot",
        "anthropic-ai",
    ]
    lines = robots_txt.lower().split("\n")
    current_agent = None
    blocked_bots = []

    for line in lines:
        line = line.strip()
        if line.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            current_agent = agent
        elif line.startswith("disallow:") and current_agent:
            disallow_path = line.split(":", 1)[1].strip()
            if disallow_path == "/" and any(bot in current_agent for bot in ai_bots):
                blocked_bots.append(current_agent)

    if blocked_bots:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": f"{site_meta['base_url']}/robots.txt",
                    "snippet": f'AI bots blocked: {", ".join(blocked_bots)}',
                }
            ],
        }

    return {"status": "pass", "evidence": []}


def check_sitemap(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if sitemap.xml exists."""
    if site_meta.get("sitemap_url"):
        return {"status": "pass", "evidence": []}

    robots_txt = site_meta.get("robots_txt", "")
    if robots_txt and "sitemap:" in robots_txt.lower():
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": site_meta["base_url"],
                    "snippet": "Sitemap referenced in robots.txt but not found at /sitemap.xml",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [{"url": site_meta["base_url"], "snippet": "No sitemap.xml found"}],
    }


def check_canonicals(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if canonical tags are present on at least 70% of pages."""
    total = len(pages)
    if total == 0:
        return {
            "status": "fail",
            "evidence": [
                {"url": site_meta["base_url"], "snippet": "No pages to check"}
            ],
        }

    with_canonical = sum(1 for page in pages if page.get("canonical"))
    pct = (with_canonical / total) * 100

    if pct >= 70:
        return {"status": "pass", "evidence": []}

    urls_without = [page["url"] for page in pages if not page.get("canonical")]
    return {
        "status": "fail",
        "evidence": [
            {"url": url, "snippet": "Missing canonical tag"} for url in urls_without[:3]
        ],
    }


def check_org_schema(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if Organization schema with sameAs is present on homepage."""
    homepage = site_meta.get("homepage", {})
    jsonld_list = homepage.get("jsonld", [])

    for jsonld in jsonld_list:
        jsonld_type = jsonld.get("@type", "")
        types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

        if "Organization" in types:
            same_as = jsonld.get("sameAs")
            if same_as:
                return {"status": "pass", "evidence": []}
            else:
                return {
                    "status": "partial",
                    "evidence": [
                        {
                            "url": homepage.get("url", site_meta["base_url"]),
                            "snippet": "Organization schema found but missing sameAs property",
                        }
                    ],
                }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": homepage.get("url", site_meta["base_url"]),
                "snippet": "No Organization schema on homepage",
            }
        ],
    }


def check_faq_schema(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if FAQPage or QAPage schema exists (HIGH IMPACT for AI)."""
    for page in pages:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if "FAQPage" in types or "QAPage" in types:
                return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "No FAQPage or QAPage schema found (critical for AI citations)",
            }
        ],
    }


def check_breadcrumb(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if BreadcrumbList schema exists."""
    for page in pages:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if "BreadcrumbList" in types:
                return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {"url": site_meta["base_url"], "snippet": "No BreadcrumbList schema found"}
        ],
    }


def check_article_schema(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks for Article/BlogPosting schema (important for content visibility)."""
    found_articles = []

    for page in pages:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if any(
                t in types
                for t in ["Article", "BlogPosting", "NewsArticle", "TechArticle"]
            ):
                # Check for author and datePublished
                has_author = "author" in jsonld
                has_date = "datePublished" in jsonld

                if has_author and has_date:
                    found_articles.append(page["url"])

    if len(found_articles) > 0:
        return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "No Article schema with author/datePublished found (reduces AI trust)",
            }
        ],
    }


def check_headings(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if pages have proper H2/H3 structure."""
    total = len(pages)
    if total == 0:
        return {
            "status": "fail",
            "evidence": [
                {"url": site_meta["base_url"], "snippet": "No pages to check"}
            ],
        }

    with_headings = sum(
        1
        for page in pages
        if page.get("h_tags", {}).get("h2") and page.get("h_tags", {}).get("h3")
    )
    pct = (with_headings / total) * 100

    if pct >= 50:
        return {"status": "pass", "evidence": []}

    urls_without = [
        page["url"]
        for page in pages
        if not (page.get("h_tags", {}).get("h2") and page.get("h_tags", {}).get("h3"))
    ]

    return {
        "status": "fail",
        "evidence": [
            {"url": url, "snippet": "Missing H2/H3 structure"}
            for url in urls_without[:3]
        ],
    }


def check_tldr_sections(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks for TL;DR summaries (HIGH IMPACT for AI citations)."""
    pages_with_tldr = 0

    for page in pages:
        # Check in headings
        h_tags = page.get("h_tags", {})
        all_headings = (
            h_tags.get("h1", []) + h_tags.get("h2", []) + h_tags.get("h3", [])
        )

        has_tldr = any(
            "tl;dr" in h.lower()
            or "tldr" in h.lower()
            or "quick takeaway" in h.lower()
            or "key takeaway" in h.lower()
            for h in all_headings
        )

        if has_tldr:
            pages_with_tldr += 1

    if pages_with_tldr > 0:
        pct = (pages_with_tldr / len(pages)) * 100
        if pct >= 25:  # At least 25% of pages should have TL;DR
            return {"status": "pass", "evidence": []}
        else:
            return {
                "status": "partial",
                "evidence": [
                    {
                        "url": site_meta["base_url"],
                        "snippet": f"Only {pct:.0f}% of pages have TL;DR sections (target: 25%+)",
                    }
                ],
            }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "No TL;DR/Quick Takeaway sections found (critical for AI summaries)",
            }
        ],
    }


def check_content_length(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks if pages have substantial content (AI prefers comprehensive answers)."""
    # Count H2+H3 headings as proxy for content length
    substantial_pages = 0

    for page in pages:
        h_tags = page.get("h_tags", {})
        total_headings = len(h_tags.get("h2", [])) + len(h_tags.get("h3", []))

        # Pages with 5+ headings likely have substantial content
        if total_headings >= 5:
            substantial_pages += 1

    if len(pages) == 0:
        return {
            "status": "fail",
            "evidence": [
                {"url": site_meta["base_url"], "snippet": "No pages to check"}
            ],
        }

    pct = (substantial_pages / len(pages)) * 100

    if pct >= 60:
        return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": f"Only {pct:.0f}% have substantial content (target: 60%+)",
            }
        ],
    }


def check_review_schema(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks for Review/AggregateRating schema (13-31% impact on AI visibility)."""
    for page in pages:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if "Review" in types or "AggregateRating" in jsonld:
                return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "No Review/AggregateRating schema (reduces trust signals)",
            }
        ],
    }


def check_author_authority(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks for author information (E-E-A-T signals)."""
    pages_with_authors = 0

    for page in pages:
        for jsonld in page.get("jsonld", []):
            if "author" in jsonld:
                author = jsonld["author"]
                # Check if author has additional details
                if isinstance(author, dict):
                    has_details = (
                        "url" in author or "sameAs" in author or "jobTitle" in author
                    )
                    if has_details:
                        pages_with_authors += 1
                        break
                elif author:  # Simple string author
                    pages_with_authors += 1
                    break

    if len(pages) == 0:
        return {
            "status": "fail",
            "evidence": [
                {"url": site_meta["base_url"], "snippet": "No pages to check"}
            ],
        }

    pct = (pages_with_authors / len(pages)) * 100

    if pct >= 40:
        return {"status": "pass", "evidence": []}
    elif pct >= 20:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": site_meta["base_url"],
                    "snippet": f"{pct:.0f}% of pages have author information (target: 40%+)",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "Insufficient author information (critical for E-E-A-T)",
            }
        ],
    }


def check_product_schema(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if Product schema exists on product pages."""
    product_pages = [
        p
        for p in pages
        if "/product" in p["url"].lower() or "/shop" in p["url"].lower()
    ]
    pages_to_check = product_pages if product_pages else pages

    for page in pages_to_check:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if "Product" in types:
                return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {"url": site_meta["base_url"], "snippet": "No Product schema found"}
        ],
    }


def check_offer_fields(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if Product schema includes complete Offer data."""
    product_pages = [
        p
        for p in pages
        if "/product" in p["url"].lower() or "/shop" in p["url"].lower()
    ]
    pages_to_check = product_pages if product_pages else pages

    for page in pages_to_check:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if "Product" in types:
                offers = jsonld.get("offers", jsonld.get("offer"))
                if offers:
                    offer_list = [offers] if isinstance(offers, dict) else offers
                    for offer in offer_list:
                        if (
                            offer.get("price")
                            and offer.get("priceCurrency")
                            and offer.get("availability")
                        ):
                            return {"status": "pass", "evidence": []}

                    return {
                        "status": "partial",
                        "evidence": [
                            {
                                "url": page["url"],
                                "snippet": "Product schema incomplete: missing price/currency/availability",
                            }
                        ],
                    }

    return {
        "status": "fail",
        "evidence": [
            {"url": site_meta["base_url"], "snippet": "No Product schema found"}
        ],
    }


def check_product_reviews(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks if products have review schema (31% impact on AI recommendations)."""
    product_pages = [
        p
        for p in pages
        if "/product" in p["url"].lower() or "/shop" in p["url"].lower()
    ]
    if not product_pages:
        return {"status": "pass", "evidence": []}  # Not applicable

    products_with_reviews = 0

    for page in product_pages:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if "Product" in types:
                has_reviews = "review" in jsonld or "aggregateRating" in jsonld
                if has_reviews:
                    products_with_reviews += 1
                    break

    pct = (products_with_reviews / len(product_pages)) * 100 if product_pages else 0

    if pct >= 50:
        return {"status": "pass", "evidence": []}
    elif pct >= 25:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": site_meta["base_url"],
                    "snippet": f"{pct:.0f}% of products have reviews (target: 50%+)",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "Products lack review schema (31% impact on AI recommendations)",
            }
        ],
    }


def check_aggregate_rating(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks for AggregateRating on products/services."""
    pages_with_ratings = 0

    for page in pages:
        for jsonld in page.get("jsonld", []):
            if "aggregateRating" in jsonld:
                rating = jsonld["aggregateRating"]
                # Check for complete rating data
                if (
                    isinstance(rating, dict)
                    and rating.get("ratingValue")
                    and rating.get("reviewCount")
                ):
                    pages_with_ratings += 1
                    break

    if pages_with_ratings > 0:
        return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "No AggregateRating schema with complete data",
            }
        ],
    }


def check_openapi(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if OpenAPI spec is discoverable."""
    docs_pages = [
        p for p in pages if "/docs" in p["url"].lower() or "/api" in p["url"].lower()
    ]

    if docs_pages:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": docs_pages[0]["url"],
                    "snippet": "Docs pages found but OpenAPI spec discoverability unclear",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [{"url": site_meta["base_url"], "snippet": "No docs pages found"}],
    }


def check_code_examples(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks for code examples in documentation (usage data signal)."""
    docs_pages = [
        p for p in pages if "/docs" in p["url"].lower() or "/api" in p["url"].lower()
    ]

    if not docs_pages:
        return {"status": "pass", "evidence": []}  # Not applicable

    # Check for code-related headings as proxy
    pages_with_examples = 0
    for page in docs_pages:
        h_tags = page.get("h_tags", {})
        all_headings = h_tags.get("h2", []) + h_tags.get("h3", [])

        has_examples = any(
            "example" in h.lower()
            or "code" in h.lower()
            or "sample" in h.lower()
            or "tutorial" in h.lower()
            for h in all_headings
        )

        if has_examples:
            pages_with_examples += 1

    pct = (pages_with_examples / len(docs_pages)) * 100 if docs_pages else 0

    if pct >= 50:
        return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": f"Only {pct:.0f}% of docs have code examples (target: 50%+)",
            }
        ],
    }


def check_tutorial_content(pages: List[Dict], site_meta: Dict) -> Dict:
    """NEW: Checks for tutorial/how-to content (high AI citation rate)."""
    docs_pages = [
        p
        for p in pages
        if "/docs" in p["url"].lower()
        or "/tutorial" in p["url"].lower()
        or "/guide" in p["url"].lower()
    ]

    if not docs_pages:
        return {"status": "pass", "evidence": []}  # Not applicable

    # Check for HowTo schema
    pages_with_howto = 0
    for page in docs_pages:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if "HowTo" in types or "Tutorial" in types:
                pages_with_howto += 1
                break

    if pages_with_howto > 0:
        return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "No HowTo schema on tutorial pages (reduces AI citations)",
            }
        ],
    }


def check_org_sameas_authority(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    org_present = False
    sameas_found = False
    authority_hits = []

    for page, item, types in _iter_jsonld(pages):
        if any(t in ("Organization", "Corporation", "LocalBusiness") for t in types):
            org_present = True
            sameas_urls = _get_sameas_urls(item)
            if sameas_urls:
                sameas_found = True
                for profile_url in sameas_urls:
                    domain = urlparse(profile_url).netloc.lower()
                    if any(
                        domain.endswith(authority)
                        for authority in AUTHORITY_SAMEAS_DOMAINS
                    ):
                        authority_hits.append(
                            {
                                "url": page.get("url", base_url),
                                "profile": profile_url,
                            }
                        )

    if authority_hits:
        return {
            "status": "pass",
            "evidence": [
                {"url": hit["url"], "snippet": f'sameAs references {hit["profile"]}'}
                for hit in authority_hits[:3]
            ],
        }

    if org_present and sameas_found:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "Organization sameAs present but missing Wikipedia/Wikidata/LinkedIn profiles",
                }
            ],
        }

    if org_present:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "Organization schema missing authoritative sameAs profiles (Wikipedia/Wikidata/LinkedIn)",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No Organization schema detected for authority profile check",
            }
        ],
    }


def check_author_profile_links(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    authors_seen = 0
    complete_authors = []
    incomplete_authors = []

    for page, item, _ in _iter_jsonld(pages):
        author = item.get("author")
        if not author:
            continue
        for entry in _as_list(author):
            if isinstance(entry, dict):
                name = entry.get("name")
                profile = entry.get("url") or entry.get("@id")
                if name:
                    authors_seen += 1
                    if profile:
                        complete_authors.append(
                            {
                                "url": page.get("url", base_url),
                                "name": name,
                                "profile": profile,
                            }
                        )
                    else:
                        incomplete_authors.append(
                            {
                                "url": page.get("url", base_url),
                                "name": name,
                            }
                        )
            elif isinstance(entry, str) and entry.strip():
                authors_seen += 1
                incomplete_authors.append(
                    {
                        "url": page.get("url", base_url),
                        "name": entry.strip(),
                    }
                )

    if complete_authors:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": author["url"],
                    "snippet": f'Author {author["name"]} links to profile {author["profile"]}',
                }
                for author in complete_authors[:3]
            ],
        }

    if authors_seen > 0:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": author["url"],
                    "snippet": f'Author {author["name"]} missing url/@id to expert profile',
                }
                for author in incomplete_authors[:3]
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No author schema with profile links detected",
            }
        ],
    }


def check_internal_entity_links(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    descriptive_links = []

    for page in pages:
        for link in page.get("internal_links", []):
            if _is_descriptive_anchor(link.get("text")):
                descriptive_links.append(
                    {
                        "url": page.get("url", base_url),
                        "text": link.get("text", ""),
                        "target": link.get("href"),
                    }
                )

    if len(descriptive_links) >= 3:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": link["url"],
                    "snippet": f'Internal anchor "{link["text"]}" → {link["target"]}',
                }
                for link in descriptive_links[:3]
            ],
        }

    if descriptive_links:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": descriptive_links[0]["url"],
                    "snippet": f"Only {len(descriptive_links)} descriptive internal anchors found (need 3+)",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No descriptive internal links to entity hub pages detected",
            }
        ],
    }


def check_entity_id_consistency(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    name_to_id: Dict[str, str] = {}
    conflicts = []
    missing_ids = []

    for page, item, _ in _iter_jsonld(pages):
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        normalized = name.strip().lower()
        entity_id = item.get("@id")
        if entity_id:
            existing = name_to_id.get(normalized)
            if existing and existing != entity_id:
                conflicts.append(
                    {
                        "url": page.get("url", base_url),
                        "name": name,
                        "ids": (existing, entity_id),
                    }
                )
            else:
                name_to_id[normalized] = entity_id
        else:
            missing_ids.append(
                {
                    "url": page.get("url", base_url),
                    "name": name,
                }
            )

    if conflicts:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": conflict["url"],
                    "snippet": f'Entity "{conflict["name"]}" uses multiple @id values {conflict["ids"][0]} vs {conflict["ids"][1]}',
                }
                for conflict in conflicts[:3]
            ],
        }

    if name_to_id and not missing_ids:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "Recurring entities reuse consistent @id values across schema",
                }
            ],
        }

    if name_to_id:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": item["url"],
                    "snippet": f'Entity "{item["name"]}" missing @id while others reuse consistent identifiers',
                }
                for item in missing_ids[:3]
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No identifiable entities with @id values found to verify consistency",
            }
        ],
    }


def check_schema_node_ids(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    total = 0
    complete = 0
    missing_details = []

    for page, item, _ in _iter_jsonld(pages):
        total += 1
        has_id = bool(item.get("@id"))
        has_url = bool(item.get("url"))
        if has_id and has_url:
            complete += 1
        else:
            missing = []
            if not has_id:
                missing.append("@id")
            if not has_url:
                missing.append("url")
            missing_details.append(
                {
                    "url": page.get("url", base_url),
                    "snippet": f"{item.get('name', 'Schema node')} missing {', '.join(missing)}",
                }
            )

    if total == 0:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "No structured data found to verify @id/url coverage",
                }
            ],
        }

    coverage = complete / total

    if coverage >= 0.8:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": f"{int(coverage * 100)}% of schema nodes include both @id and url",
                }
            ],
        }

    if coverage > 0:
        return {
            "status": "partial",
            "evidence": missing_details[:3]
            or [
                {
                    "url": base_url,
                    "snippet": f"Only {int(coverage * 100)}% of schema nodes include @id and url",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": missing_details[:3]
        or [
            {
                "url": base_url,
                "snippet": "Schema nodes missing both @id and url identifiers",
            }
        ],
    }


def check_person_expertise(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    person_found = False
    expertise_hits = []
    missing_expertise = []

    for page, item, types in _iter_jsonld(pages):
        if "Person" not in types:
            continue
        person_found = True
        knows_about = _as_list(item.get("knowsAbout"))
        works_for = item.get("worksFor")
        if knows_about or works_for:
            expertise_hits.append(
                {
                    "url": page.get("url", base_url),
                    "name": item.get("name"),
                    "topics": knows_about,
                    "works_for": works_for,
                }
            )
        else:
            missing_expertise.append(
                {
                    "url": page.get("url", base_url),
                    "name": item.get("name"),
                }
            )

    if expertise_hits:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": hit["url"],
                    "snippet": (
                        f'Person {hit["name"] or "entity"} lists expertise ({", ".join(hit["topics"][:2])})'
                        if hit["topics"]
                        else f'Person {hit["name"] or "entity"} worksFor {hit["works_for"]}'
                    ),
                }
                for hit in expertise_hits[:3]
            ],
        }

    if person_found:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": person["url"],
                    "snippet": f'Person {person["name"] or "entity"} missing knowsAbout or worksFor details',
                }
                for person in missing_expertise[:3]
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No Person schema detected with expertise or employer information",
            }
        ],
    }


def check_org_contact_profiles(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    org_found = False
    contact_points = []
    profile_hits = []

    for page, item, types in _iter_jsonld(pages):
        if any(t in ("Organization", "Corporation", "LocalBusiness") for t in types):
            org_found = True
            contact_point = item.get("contactPoint")
            if contact_point:
                contact_points.append(page.get("url", base_url))
            for profile_url in _get_sameas_urls(item):
                domain = urlparse(profile_url).netloc.lower()
                if any(
                    domain.endswith(required)
                    for required in LINKEDIN_CRUNCHBASE_DOMAINS
                ):
                    profile_hits.append(
                        {
                            "url": page.get("url", base_url),
                            "profile": profile_url,
                        }
                    )

    if contact_points or profile_hits:
        evidence = []
        if profile_hits:
            evidence.extend(
                [
                    {
                        "url": hit["url"],
                        "snippet": f'sameAs includes verified profile {hit["profile"]}',
                    }
                    for hit in profile_hits[:3]
                ]
            )
        if contact_points and not evidence:
            evidence.append(
                {
                    "url": contact_points[0],
                    "snippet": "Organization schema exposes ContactPoint details",
                }
            )
        return {"status": "pass", "evidence": evidence}

    if org_found:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "Organization schema lacks ContactPoint data or LinkedIn/Crunchbase profiles",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No Organization schema detected for contact/social profile validation",
            }
        ],
    }


def check_sameas_wikidata(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    sameas_found = False
    wikidata_hits = []

    for page, item, _ in _iter_jsonld(pages):
        sameas_urls = _get_sameas_urls(item)
        if sameas_urls:
            sameas_found = True
        for profile_url in sameas_urls:
            domain = urlparse(profile_url).netloc.lower()
            if domain.endswith("wikidata.org") or domain.endswith("wikipedia.org"):
                wikidata_hits.append(
                    {
                        "url": page.get("url", base_url),
                        "profile": profile_url,
                    }
                )

    if wikidata_hits:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": hit["url"],
                    "snippet": f'sameAs references {hit["profile"]}',
                }
                for hit in wikidata_hits[:3]
            ],
        }

    if sameas_found:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "sameAs present but missing Wikidata/Wikipedia references",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No sameAs links to Wikidata or Wikipedia detected",
            }
        ],
    }


def check_org_founder(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    founder_links = []
    founder_present = False

    for page, item, types in _iter_jsonld(pages):
        if any(t in ("Organization", "Corporation", "LocalBusiness") for t in types):
            founders = _as_list(item.get("founder"))
            if founders:
                founder_present = True
            for founder in founders:
                if isinstance(founder, dict):
                    if (
                        founder.get("@type") == "Person"
                        or founder.get("@id")
                        or founder.get("name")
                    ):
                        founder_links.append(
                            {
                                "url": page.get("url", base_url),
                                "name": founder.get("name")
                                or founder.get("@id")
                                or "Person",
                            }
                        )

    if founder_links:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": link["url"],
                    "snippet": f'Organization founder linked: {link["name"]}',
                }
                for link in founder_links[:3]
            ],
        }

    if founder_present:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "Founder property present but missing structured Person references",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No founder property linking Person → Organization detected",
            }
        ],
    }


def check_product_brand_linking(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    products_found = False
    brand_links = []
    missing_brands = []

    for page, item, types in _iter_jsonld(pages):
        if not any(t in ("Product", "Service") for t in types):
            continue
        products_found = True
        brand = item.get("brand")
        if isinstance(brand, dict):
            brand_ref = brand.get("@id") or brand.get("url") or brand.get("name")
            if brand_ref:
                brand_links.append(
                    {
                        "url": page.get("url", base_url),
                        "brand": brand_ref,
                    }
                )
            else:
                missing_brands.append(page.get("url", base_url))
        elif isinstance(brand, str) and brand.strip():
            brand_links.append(
                {
                    "url": page.get("url", base_url),
                    "brand": brand.strip(),
                }
            )
        else:
            missing_brands.append(page.get("url", base_url))

    if brand_links:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": link["url"],
                    "snippet": f'Product/Service brand set to {link["brand"]}',
                }
                for link in brand_links[:3]
            ],
        }

    if products_found:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": missing_brands[0] if missing_brands else base_url,
                    "snippet": "Product/Service schema missing brand property referencing organization",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No Product or Service schema found for brand linkage check",
            }
        ],
    }


def check_specific_schema_types(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    specific_types = set()
    has_jsonld = False

    for _, item, types in _iter_jsonld(pages):
        if types:
            has_jsonld = True
        for schema_type in types:
            if schema_type and schema_type != "WebPage":
                specific_types.add(schema_type)

    if specific_types:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": f'Specific schema types detected: {", ".join(sorted(specific_types))}',
                }
            ],
        }

    if has_jsonld:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "Structured data present but only generic WebPage types detected",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No structured data found using specific Schema.org types",
            }
        ],
    }


def check_schema_field_coverage(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    essentials = {
        "Organization": ["@id", "url", "name", "sameAs"],
        "Person": ["@id", "name", "url"],
        "Product": ["@id", "name", "brand", "description"],
        "Service": ["@id", "name", "provider"],
        "Article": ["headline", "datePublished", "author", "description"],
        "BlogPosting": ["headline", "datePublished", "author", "description"],
    }
    coverage_scores = []

    for page, item, types in _iter_jsonld(pages):
        for schema_type, fields in essentials.items():
            if schema_type in types:
                filled = sum(1 for field in fields if item.get(field))
                coverage = filled / len(fields)
                missing = [field for field in fields if not item.get(field)]
                coverage_scores.append(
                    {
                        "url": page.get("url", base_url),
                        "type": schema_type,
                        "coverage": coverage,
                        "missing": missing,
                    }
                )

    if not coverage_scores:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "No key schema entities (Organization/Person/Product/Article) detected for coverage analysis",
                }
            ],
        }

    best_score = max(coverage_scores, key=lambda entry: entry["coverage"])

    if best_score["coverage"] >= 0.8:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": best_score["url"],
                    "snippet": f"{best_score['type']} schema covers {int(best_score['coverage'] * 100)}% of essential fields",
                }
            ],
        }

    if best_score["coverage"] >= 0.5:
        missing_fields = ", ".join(best_score["missing"]) or "several fields"
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": best_score["url"],
                    "snippet": f"{best_score['type']} schema missing fields: {missing_fields}",
                }
            ],
        }

    missing_fields = ", ".join(best_score["missing"]) or "key fields"
    return {
        "status": "fail",
        "evidence": [
            {
                "url": best_score["url"],
                "snippet": f"{best_score['type']} schema only covers {int(best_score['coverage'] * 100)}% of essentials (missing {missing_fields})",
            }
        ],
    }


def check_faqpage_detail(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    faq_found = False
    complete_entries = []
    incomplete_entries = []

    for page, item, types in _iter_jsonld(pages):
        if "FAQPage" not in types:
            continue
        faq_found = True
        questions = _as_list(item.get("mainEntity"))
        for question in questions:
            if not isinstance(question, dict):
                continue
            answer = question.get("acceptedAnswer")
            answer_text = None
            for ans in _as_list(answer):
                if isinstance(ans, dict) and ans.get("text"):
                    answer_text = ans.get("text")
                    break
            if question.get("name") and answer_text:
                complete_entries.append(
                    {
                        "url": page.get("url", base_url),
                        "question": question.get("name"),
                    }
                )
            else:
                incomplete_entries.append(
                    {
                        "url": page.get("url", base_url),
                        "question": question.get("name"),
                    }
                )

    if complete_entries:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": entry["url"],
                    "snippet": f'FAQ question "{entry["question"]}" includes acceptedAnswer',
                }
                for entry in complete_entries[:3]
            ],
        }

    if faq_found:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": (
                        incomplete_entries[0]["url"] if incomplete_entries else base_url
                    ),
                    "snippet": "FAQPage schema lacks acceptedAnswer text for questions",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No FAQPage schema with Q&A structure detected",
            }
        ],
    }


def check_core_web_vitals_signals(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    total_pages = len(pages)
    if total_pages == 0:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "No pages available to evaluate Core Web Vitals signals",
                }
            ],
        }

    viewport_count = 0
    hint_count = 0
    for page in pages:
        meta = page.get("meta", {})
        if isinstance(meta, dict) and meta.get("viewport"):
            viewport_count += 1
        for link in page.get("link_tags", []):
            rels = link.get("rel", [])
            if any(rel in {"preload", "preconnect", "dns-prefetch"} for rel in rels):
                hint_count += 1
                break

    viewport_ratio = viewport_count / total_pages

    if viewport_ratio >= 0.8 and hint_count >= 1:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "Viewport meta configured on most pages with preload/preconnect hints detected",
                }
            ],
        }

    if viewport_ratio >= 0.5 or hint_count >= 1:
        missing_viewport = [
            {
                "url": page.get("url", base_url),
                "snippet": "Missing responsive viewport meta tag",
            }
            for page in pages
            if not (isinstance(page.get("meta"), dict) and page["meta"].get("viewport"))
        ]
        return {
            "status": "partial",
            "evidence": missing_viewport[:1]
            or [
                {
                    "url": base_url,
                    "snippet": "Performance hints detected but viewport meta missing on several pages",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "Missing mobile viewport meta and performance preload/preconnect hints",
            }
        ],
    }


def check_social_presence_signals(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    total_pages = len(pages)
    if total_pages == 0:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "No pages available to evaluate social presence signals",
                }
            ],
        }

    qualified = []
    og_only = []

    for page in pages:
        meta = page.get("meta", {}) if isinstance(page.get("meta"), dict) else {}
        og_meta = meta.get("og", {}) if isinstance(meta, dict) else {}
        twitter_meta = meta.get("twitter", {}) if isinstance(meta, dict) else {}
        has_og = all(og_meta.get(key) for key in ("title", "description", "type"))
        has_twitter = bool(twitter_meta.get("card"))
        has_social = _page_has_social_link(page)
        if has_og and has_twitter and has_social:
            qualified.append(page.get("url", base_url))
        elif has_og and has_twitter:
            og_only.append(page.get("url", base_url))

    ratio = len(qualified) / total_pages

    if ratio >= 0.6:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": qualified[0],
                    "snippet": "Open Graph/Twitter meta present with verified social profile links",
                }
            ],
        }

    if qualified:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": qualified[0],
                    "snippet": "Some pages include OG/Twitter meta with social profiles but coverage <60%",
                }
            ],
        }

    if og_only:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": og_only[0],
                    "snippet": "Open Graph/Twitter meta found but no verified social profile links detected",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "Missing Open Graph/Twitter meta or verified social profile links",
            }
        ],
    }


def check_content_freshness_recent(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    threshold = datetime.utcnow() - timedelta(days=365)
    dates = []

    for page in pages:
        dates.extend(_gather_candidate_dates(page))

    if any(dt >= threshold for dt in dates):
        latest = max(dt for dt in dates if dt >= threshold)
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": f"Content updated recently on {latest.date().isoformat()}",
                }
            ],
        }

    if dates:
        latest = max(dates)
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": f"Latest update {latest.date().isoformat()} is older than 12 months",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No dateModified/article:modified_time metadata found",
            }
        ],
    }


def check_multimodal_accessibility(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    total_images = 0
    images_with_alt = 0
    has_captions = False
    has_transcript = False

    for page in pages:
        media = page.get("media", {}) if isinstance(page.get("media"), dict) else {}
        images = (
            media.get("images", {}) if isinstance(media.get("images"), dict) else {}
        )
        videos = (
            media.get("videos", {}) if isinstance(media.get("videos"), dict) else {}
        )
        total_images += images.get("total", 0)
        images_with_alt += images.get("with_alt", 0)
        has_captions = has_captions or videos.get("has_captions", False)
        has_transcript = has_transcript or media.get("has_transcript_section", False)

    alt_ratio = images_with_alt / total_images if total_images else 1.0
    media_schema_present = any(
        any(schema_type in ("ImageObject", "VideoObject") for schema_type in types)
        for _, _, types in _iter_jsonld(pages)
    )
    transcript_available = has_captions or has_transcript

    if alt_ratio >= 0.8 and media_schema_present and transcript_available:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": f"Image alt coverage {int(alt_ratio * 100)}% with multimedia schema and captions/transcripts",
                }
            ],
        }

    if alt_ratio >= 0.5 and (media_schema_present or transcript_available):
        missing = []
        if alt_ratio < 0.8:
            missing.append("ALT text coverage below 80%")
        if not media_schema_present:
            missing.append("Missing ImageObject/VideoObject schema")
        if not transcript_available:
            missing.append("Missing captions/transcripts")
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "; ".join(missing),
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "Insufficient multimedia accessibility (ALT text, schema, or captions)",
            }
        ],
    }


def check_main_entity_present(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    main_entities = []
    missing = []

    for page, item, _ in _iter_jsonld(pages):
        main_entity = item.get("mainEntity")
        if not main_entity:
            continue
        for entry in _as_list(main_entity):
            if isinstance(entry, dict):
                if entry.get("@id") or entry.get("url") or entry.get("name"):
                    main_entities.append(page.get("url", base_url))
                else:
                    missing.append(page.get("url", base_url))
            elif isinstance(entry, str) and entry.strip():
                main_entities.append(page.get("url", base_url))
            else:
                missing.append(page.get("url", base_url))

    if main_entities:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": main_entities[0],
                    "snippet": "mainEntity present referencing core subject",
                }
            ],
        }

    if missing:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": missing[0],
                    "snippet": "mainEntity present but missing @id/url/name details",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No mainEntity property detected to identify central subject",
            }
        ],
    }


def check_about_mentions_entities(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    related_entities = []
    missing = []

    for page, item, _ in _iter_jsonld(pages):
        for field in ("about", "mentions"):
            entries = _as_list(item.get(field))
            if not entries:
                continue
            has_uri = False
            for entry in entries:
                if isinstance(entry, dict):
                    if entry.get("@id") or entry.get("sameAs") or entry.get("url"):
                        has_uri = True
                        break
                elif isinstance(entry, str) and entry.strip().startswith("http"):
                    has_uri = True
                    break
            if has_uri:
                related_entities.append(
                    {
                        "url": page.get("url", base_url),
                        "field": field,
                    }
                )
            else:
                missing.append(
                    {
                        "url": page.get("url", base_url),
                        "field": field,
                    }
                )

    if related_entities:
        entry = related_entities[0]
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": entry["url"],
                    "snippet": f'{entry["field"]} field references related entity URIs',
                }
            ],
        }

    if missing:
        entry = missing[0]
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": entry["url"],
                    "snippet": f'{entry["field"]} field lacks entity URIs in @id/sameAs/url',
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No about or mentions relationships found in structured data",
            }
        ],
    }


def check_page_level_type_specific(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    if not pages:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "No pages available to evaluate page-level schema types",
                }
            ],
        }

    specific_types = {
        "AboutPage",
        "ContactPage",
        "FAQPage",
        "BlogPosting",
        "Article",
        "Product",
        "Service",
        "HowTo",
        "CollectionPage",
        "LandingPage",
    }
    pages_with_specific = []
    missing_expected = []

    for page in pages:
        url = page.get("url", base_url) or ""
        path = urlparse(url).path.lower()
        types_on_page = set()
        for _, item, types in _iter_jsonld([page]):
            types_on_page.update(types)
        expected = None
        if "about" in path:
            expected = "AboutPage"
        elif "contact" in path:
            expected = "ContactPage"
        elif "blog" in path or "news" in path:
            expected = "BlogPosting"

        if expected:
            if expected in types_on_page:
                pages_with_specific.append(url)
            else:
                missing_expected.append({"url": url, "expected": expected})
            continue

        if any(t in specific_types and t != "WebPage" for t in types_on_page):
            pages_with_specific.append(url)

    ratio = len(pages_with_specific) / len(pages)

    if ratio >= 0.6 and not missing_expected:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": pages_with_specific[0] if pages_with_specific else base_url,
                    "snippet": "Pages use specific @type definitions (AboutPage/ContactPage/BlogPosting/etc.)",
                }
            ],
        }

    if pages_with_specific:
        evidence = []
        if missing_expected:
            evidence.append(
                {
                    "url": missing_expected[0]["url"],
                    "snippet": f"Expected {missing_expected[0]['expected']} schema missing for this page",
                }
            )
        return {
            "status": "partial",
            "evidence": evidence
            or [
                {
                    "url": base_url,
                    "snippet": "Specific @type detected but coverage below 60% of pages",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "All pages rely on generic WebPage schema without specific @type",
            }
        ],
    }


def check_article_headline_description(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    complete_articles = []
    incomplete_articles = []

    for page, item, types in _iter_jsonld(pages):
        if not any(t in ("Article", "BlogPosting") for t in types):
            continue
        headline = item.get("headline")
        description = item.get("description")
        if headline and description:
            complete_articles.append(page.get("url", base_url))
        else:
            incomplete_articles.append(page.get("url", base_url))

    if complete_articles:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": complete_articles[0],
                    "snippet": "Article/BlogPosting schema includes headline and description",
                }
            ],
        }

    if incomplete_articles:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": incomplete_articles[0],
                    "snippet": "Article/BlogPosting schema missing headline or description",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "No Article or BlogPosting schema detected",
            }
        ],
    }


def check_semantic_html_coverage(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    if not pages:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "No pages available to evaluate semantic HTML coverage",
                }
            ],
        }

    qualifying = []
    lacking = []
    for page in pages:
        semantic_tags = (
            page.get("semantic_tags", {})
            if isinstance(page.get("semantic_tags"), dict)
            else {}
        )
        tag_usage = sum(1 for count in semantic_tags.values() if count)
        if tag_usage >= 3:
            qualifying.append(page.get("url", base_url))
        else:
            lacking.append(page.get("url", base_url))

    ratio = len(qualifying) / len(pages)

    if ratio >= 0.8:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": qualifying[0],
                    "snippet": "Semantic HTML (article/section/header/footer) used extensively",
                }
            ],
        }

    if qualifying:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": lacking[0] if lacking else qualifying[0],
                    "snippet": "Semantic HTML present but coverage below 80% of pages",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "Pages lack semantic HTML structure (article/section/header/footer)",
            }
        ],
    }


def check_canonical_indexable_pages(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    indexable = _indexable_pages(pages)
    if not indexable:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "No indexable pages detected (likely all marked noindex)",
                }
            ],
        }

    missing = [page for page in indexable if not page.get("canonical")]

    if not missing:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": indexable[0].get("url", base_url),
                    "snippet": "All indexable pages declare canonical URLs",
                }
            ],
        }

    ratio = (len(indexable) - len(missing)) / len(indexable)

    if ratio >= 0.8:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": page.get("url", base_url),
                    "snippet": "Missing canonical link on indexable page",
                }
                for page in missing[:3]
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": page.get("url", base_url),
                "snippet": "Missing canonical link on indexable page",
            }
            for page in missing[:3]
        ],
    }


def check_social_meta_completeness(pages: List[Dict], site_meta: Dict) -> Dict:
    base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
    if not pages:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": base_url,
                    "snippet": "No pages available to evaluate social meta tags",
                }
            ],
        }

    required_og = {"title", "description", "type"}
    complete = []
    incomplete = []

    for page in pages:
        meta = page.get("meta", {}) if isinstance(page.get("meta"), dict) else {}
        og_meta = meta.get("og", {}) if isinstance(meta, dict) else {}
        twitter_meta = meta.get("twitter", {}) if isinstance(meta, dict) else {}
        if all(og_meta.get(key) for key in required_og) and twitter_meta.get("card"):
            complete.append(page.get("url", base_url))
        else:
            incomplete.append(page.get("url", base_url))

    ratio = len(complete) / len(pages)

    if ratio >= 0.8:
        return {
            "status": "pass",
            "evidence": [
                {
                    "url": complete[0],
                    "snippet": "Open Graph and Twitter card meta tags populated",
                }
            ],
        }

    if complete:
        return {
            "status": "partial",
            "evidence": [
                {
                    "url": incomplete[0] if incomplete else complete[0],
                    "snippet": "Some pages missing required Open Graph/Twitter meta tags",
                }
            ],
        }

    return {
        "status": "fail",
        "evidence": [
            {
                "url": base_url,
                "snippet": "Missing og:type, og:title, og:description, or twitter:card meta tags",
            }
        ],
    }


def check_breadcrumb_aio(pages: List[Dict], site_meta: Dict) -> Dict:
    result = check_breadcrumb(pages, site_meta)
    if result["status"] == "fail":
        base_url = site_meta.get("base_url") or (pages[0].get("url") if pages else "")
        result["evidence"] = [
            {
                "url": base_url,
                "snippet": "No BreadcrumbList schema found (required for AI Optimization pack)",
            }
        ]
    return result


# Enhanced rule definitions
RULES = {
    "CRW-ROB-001": {
        "id": "CRW-ROB-001",
        "title": "robots.txt allows AI bots (GPTBot, Claude, etc.)",
        "category": "Crawlability",
        "why": "AI bots need access to crawl and index content.",
        "fix": "Allow GPTBot, Claude-Web, PerplexityBot in robots.txt.",
        "check": check_robots_gptbot,
    },
    "CRW-SMP-001": {
        "id": "CRW-SMP-001",
        "title": "Sitemap present",
        "category": "Crawlability",
        "why": "Sitemaps guide bots to discover all key pages.",
        "fix": "Add /sitemap.xml and reference in robots.txt.",
        "check": check_sitemap,
    },
    "CRW-CAN-001": {
        "id": "CRW-CAN-001",
        "title": "Canonical tags present",
        "category": "Crawlability",
        "why": "Prevents duplication issues in AI training data.",
        "fix": "Add rel=canonical on each page.",
        "check": check_canonicals,
    },
    "SCH-ORG-001": {
        "id": "SCH-ORG-001",
        "title": "Organization schema on homepage",
        "category": "Schema",
        "why": "Establishes entity identity for AI knowledge graphs.",
        "fix": "Add Organization JSON-LD with sameAs to authoritative profiles.",
        "check": check_org_schema,
    },
    "SCH-FAQ-001": {
        "id": "SCH-FAQ-001",
        "title": "FAQ/QAPage schema present",
        "category": "Schema",
        "why": "FAQs get 30-40% higher AI visibility and citation rate.",
        "fix": "Add FAQPage/QAPage JSON-LD with question/answer pairs.",
        "check": check_faq_schema,
    },
    "SCH-BRD-001": {
        "id": "SCH-BRD-001",
        "title": "BreadcrumbList present",
        "category": "Schema",
        "why": "Clarifies site structure for AI systems.",
        "fix": "Add BreadcrumbList JSON-LD on content pages.",
        "check": check_breadcrumb,
    },
    "SCH-ART-001": {
        "id": "SCH-ART-001",
        "title": "Article schema with author/date",
        "category": "Schema",
        "why": "Signals content freshness and E-E-A-T authority.",
        "fix": "Add Article/BlogPosting schema with author and datePublished.",
        "check": check_article_schema,
    },
    "ANS-HDR-001": {
        "id": "ANS-HDR-001",
        "title": "Clean H2/H3 heading structure",
        "category": "Answerability",
        "why": "Hierarchical headings help AI extract structured information.",
        "fix": "Use H2/H3 tags for section organization.",
        "check": check_headings,
    },
    "ANS-TLD-001": {
        "id": "ANS-TLD-001",
        "title": "TL;DR or Quick Takeaway sections",
        "category": "Answerability",
        "why": "AI prioritizes content with clear summary sections for citations.",
        "fix": "Add TL;DR sections at top of articles and key pages.",
        "check": check_tldr_sections,
    },
    "ANS-LEN-001": {
        "id": "ANS-LEN-001",
        "title": "Substantial content length",
        "category": "Answerability",
        "why": "AI prefers comprehensive, detailed answers over thin content.",
        "fix": "Expand content with depth, examples, and multiple sections.",
        "check": check_content_length,
    },
    "CTX-REV-001": {
        "id": "CTX-REV-001",
        "title": "Review/AggregateRating schema",
        "category": "Context",
        "why": "Reviews have 13-31% impact on AI recommendations.",
        "fix": "Add Review/AggregateRating JSON-LD with ratings data.",
        "check": check_review_schema,
    },
    "CTX-AUT-001": {
        "id": "CTX-AUT-001",
        "title": "Author information with credentials",
        "category": "Context",
        "why": "Author expertise signals are critical for E-E-A-T.",
        "fix": "Add author schema with name, URL, and credentials.",
        "check": check_author_authority,
    },
    "ECM-PRO-001": {
        "id": "ECM-PRO-001",
        "title": "Product schema present",
        "category": "E-comm",
        "why": "Makes products discoverable in AI shopping recommendations.",
        "fix": "Add Product JSON-LD on product pages.",
        "check": check_product_schema,
    },
    "ECM-OFR-001": {
        "id": "ECM-OFR-001",
        "title": "Complete Offer data (price/currency/availability)",
        "category": "E-comm",
        "why": "Complete product data enables AI price comparisons.",
        "fix": "Include all Offer fields in Product schema.",
        "check": check_offer_fields,
    },
    "ECM-REV-001": {
        "id": "ECM-REV-001",
        "title": "Product reviews schema",
        "category": "E-comm",
        "why": "31% impact on AI product recommendations.",
        "fix": "Add review/aggregateRating to Product schema.",
        "check": check_product_reviews,
    },
    "ECM-AGG-001": {
        "id": "ECM-AGG-001",
        "title": "AggregateRating with count",
        "category": "E-comm",
        "why": "Rating counts signal product popularity to AI.",
        "fix": "Add aggregateRating with ratingValue and reviewCount.",
        "check": check_aggregate_rating,
    },
    "DOC-OAS-001": {
        "id": "DOC-OAS-001",
        "title": "OpenAPI spec discoverable",
        "category": "Docs",
        "why": "Makes API documentation quotable by AI coding assistants.",
        "fix": "Link OpenAPI spec from docs index page.",
        "check": check_openapi,
    },
    "DOC-EXM-001": {
        "id": "DOC-EXM-001",
        "title": "Code examples in documentation",
        "category": "Docs",
        "why": "Usage examples increase developer tool citations.",
        "fix": "Add code snippets and examples to all API endpoints.",
        "check": check_code_examples,
    },
    "DOC-TUT-001": {
        "id": "DOC-TUT-001",
        "title": "HowTo schema on tutorials",
        "category": "Docs",
        "why": "Tutorial content has highest AI citation rate.",
        "fix": "Add HowTo JSON-LD with step-by-step instructions.",
        "check": check_tutorial_content,
    },
    "AIO-ENT-001": {
        "id": "AIO-ENT-001",
        "title": "Authority sameAs profiles for Organization",
        "category": "Entity Linking & Brand Consistency",
        "why": "Authoritative sameAs links help AI systems connect the brand to trusted knowledge graphs.",
        "fix": "Add sameAs URLs for Wikipedia, Wikidata, and LinkedIn profiles to the Organization JSON-LD block.",
        "confidence": 0.8,
        "check": check_org_sameas_authority,
    },
    "AIO-ENT-002": {
        "id": "AIO-ENT-002",
        "title": "Author schema links to expert profile",
        "category": "Entity Linking & Brand Consistency",
        "why": "Robust author entities reinforce expertise and experience signals for AI rankers.",
        "fix": "Populate author objects with name, canonical profile URL, and a persistent @id.",
        "confidence": 0.7,
        "check": check_author_profile_links,
    },
    "AIO-ENTITY-006": {
        "id": "AIO-ENTITY-006",
        "title": "Internal anchors to entity hubs",
        "category": "Entity Linking & Brand Consistency",
        "why": "Optimized internal anchors help AI crawlers follow entity relationships across the site.",
        "fix": "Add internal links with descriptive anchor text to the About, Team, or Product entity hubs.",
        "confidence": 0.65,
        "check": check_internal_entity_links,
    },
    "AIO-ENT-011": {
        "id": "AIO-ENT-011",
        "title": "Consistent @id for recurring entities",
        "category": "Entity Linking & Brand Consistency",
        "why": "Stable identifiers prevent AI knowledge graphs from fragmenting entity representations.",
        "fix": "Audit schema entries and ensure each recurring entity reuses a single canonical @id.",
        "confidence": 0.85,
        "check": check_entity_id_consistency,
    },
    "AIO-ENT-012": {
        "id": "AIO-ENT-012",
        "title": "@id and URL populated on schema nodes",
        "category": "Entity Linking & Brand Consistency",
        "why": "Complete identifiers ensure AI agents can dereference entities and crawl canonical pages.",
        "fix": "Add @id and url values to each top-level JSON-LD node, using canonical URLs.",
        "confidence": 0.8,
        "check": check_schema_node_ids,
    },
    "AIO-ENT-013": {
        "id": "AIO-ENT-013",
        "title": "Person schema lists expertise or employer",
        "category": "Entity Linking & Brand Consistency",
        "why": "Explicit topical expertise reinforces E-E-A-T for AI systems.",
        "fix": "Populate knowsAbout topics or worksFor organization on each Person JSON-LD entity.",
        "confidence": 0.75,
        "check": check_person_expertise,
    },
    "AIO-ENT-014": {
        "id": "AIO-ENT-014",
        "title": "Organization contact or investment profiles",
        "category": "Entity Linking & Brand Consistency",
        "why": "Reliable contact and investment signals help AI assess legitimacy and scale.",
        "fix": "Add a ContactPoint block or sameAs links for LinkedIn and Crunchbase profiles.",
        "confidence": 0.8,
        "check": check_org_contact_profiles,
    },
    "AIO-ENT-015": {
        "id": "AIO-ENT-015",
        "title": "Wikidata or Wikipedia sameAs linkage",
        "category": "Entity Linking & Brand Consistency",
        "why": "Knowledge graph alignment accelerates citation and summarization in AI assistants.",
        "fix": "Append the official Wikidata or Wikipedia URL to the sameAs list for the primary entity.",
        "confidence": 0.9,
        "check": check_sameas_wikidata,
    },
    "AIO-ENT-016": {
        "id": "AIO-ENT-016",
        "title": "Founder relationship between Person and Organization",
        "category": "Entity Linking & Brand Consistency",
        "why": "Explicit founder relationships tie leadership authority to the brand.",
        "fix": "Add founder references that point to fully populated Person JSON-LD nodes.",
        "confidence": 0.75,
        "check": check_org_founder,
    },
    "AIO-ENT-017": {
        "id": "AIO-ENT-017",
        "title": "Brand attribution on Product or Service schema",
        "category": "Entity Linking & Brand Consistency",
        "why": "Brand attribution lets AI assistants trace offerings back to the company.",
        "fix": "Populate brand on Product or Service schema, ideally referencing the Organization @id.",
        "confidence": 0.8,
        "check": check_product_brand_linking,
    },
    "AIO-SCHEMA-003": {
        "id": "AIO-SCHEMA-003",
        "title": "Use specific schema types",
        "category": "Schema/Structured Data",
        "why": "Specific schema types unlock richer AI answer surfaces and product cards.",
        "fix": "Update JSON-LD to use the most specific applicable Schema.org type for each page.",
        "confidence": 0.75,
        "check": check_specific_schema_types,
    },
    "AIO-SCHEMA-004": {
        "id": "AIO-SCHEMA-004",
        "title": "Essential schema fields populated",
        "category": "Schema/Structured Data",
        "why": "Complete structured data improves alignment with AI knowledge bases.",
        "fix": "Audit each JSON-LD entity and fill required name, url, @id, sameAs, headline, and description fields.",
        "confidence": 0.8,
        "check": check_schema_field_coverage,
    },
    "AIO-CONTENT-005": {
        "id": "AIO-CONTENT-005",
        "title": "FAQPage schema with questions and answers",
        "category": "Content Structure",
        "why": "Structured FAQs power conversational answers and featured snippets in AI tools.",
        "fix": "Add FAQPage schema covering each question with a concise acceptedAnswer.",
        "confidence": 0.6,
        "check": check_faqpage_detail,
    },
    "AIO-UX-007": {
        "id": "AIO-UX-007",
        "title": "Mobile-friendly and performant markup",
        "category": "Performance & UX",
        "why": "Responsive, fast-loading pages improve AI ranking signals derived from user satisfaction.",
        "fix": "Add a meta viewport tag and performance resource hints (preload/preconnect) for critical assets.",
        "confidence": 0.5,
        "check": check_core_web_vitals_signals,
    },
    "AIO-SOCIAL-008": {
        "id": "AIO-SOCIAL-008",
        "title": "Open Graph with verified social profiles",
        "category": "Social Presence",
        "why": "Rich social metadata boosts credibility in AI answer cards and knowledge panels.",
        "fix": "Ensure og:title, og:type, og:description, and twitter:card meta tags exist alongside verified social sameAs links.",
        "confidence": 0.6,
        "check": check_social_presence_signals,
    },
    "AIO-FRESH-009": {
        "id": "AIO-FRESH-009",
        "title": "Recent last updated metadata",
        "category": "Content Freshness",
        "why": "Fresh content is prioritized by AI systems seeking current information.",
        "fix": "Update and publish dateModified/article:modified_time values whenever content is refreshed.",
        "confidence": 0.55,
        "check": check_content_freshness_recent,
    },
    "AIO-MULTI-010": {
        "id": "AIO-MULTI-010",
        "title": "Multimodal accessibility signals",
        "category": "Multimodal Experience",
        "why": "Accessible multimedia is surfaced more readily by AI assistants and search engines.",
        "fix": "Add descriptive alt text, provide caption tracks or transcripts, and include matching schema for multimedia assets.",
        "confidence": 0.7,
        "check": check_multimodal_accessibility,
    },
    "AIO-SEM-018": {
        "id": "AIO-SEM-018",
        "title": "mainEntity defined for primary topic",
        "category": "Semantic/Intent",
        "why": "mainEntity helps AI models summarize and properly attribute information.",
        "fix": "Add mainEntity to WebPage or Article schema referencing the canonical entity @id.",
        "confidence": 0.85,
        "check": check_main_entity_present,
    },
    "AIO-SEM-019": {
        "id": "AIO-SEM-019",
        "title": "about and mentions with entity URIs",
        "category": "Semantic/Intent",
        "why": "Rich entity relationships teach AI systems how topics interrelate.",
        "fix": "Populate about or mentions arrays with objects that include @id or sameAs URLs.",
        "confidence": 0.8,
        "check": check_about_mentions_entities,
    },
    "AIO-SEM-020": {
        "id": "AIO-SEM-020",
        "title": "Specific page-level @type",
        "category": "Semantic/Intent",
        "why": "Precise page @types guide AI assistants on intent and audience.",
        "fix": "Update page-level JSON-LD to use AboutPage/ContactPage/BlogPosting or similar specific types.",
        "confidence": 0.75,
        "check": check_page_level_type_specific,
    },
    "AIO-SEM-021": {
        "id": "AIO-SEM-021",
        "title": "Article headline and description populated",
        "category": "Semantic/Intent",
        "why": "Headline and description metadata enable accurate summarization in AI results.",
        "fix": "Populate headline and description on Article or BlogPosting schema entries.",
        "confidence": 0.8,
        "check": check_article_headline_description,
    },
    "AIO-SEM-022": {
        "id": "AIO-SEM-022",
        "title": "Semantic HTML coverage",
        "category": "Semantic/Intent",
        "why": "Semantic markup helps AI segment content and extract key answers.",
        "fix": "Wrap primary content in semantic elements (article/section/header/footer) instead of generic divs.",
        "confidence": 0.65,
        "check": check_semantic_html_coverage,
    },
    "AIO-SEM-023": {
        "id": "AIO-SEM-023",
        "title": "Canonical URL on every indexable page",
        "category": "Semantic/Intent",
        "why": "Canonical tags help AI models resolve duplicates and consolidate authority.",
        "fix": 'Add rel="canonical" links to every indexable page, excluding those marked noindex.',
        "confidence": 0.9,
        "check": check_canonical_indexable_pages,
    },
    "AIO-SEM-024": {
        "id": "AIO-SEM-024",
        "title": "Comprehensive social meta tags",
        "category": "Semantic/Intent",
        "why": "Consistent open graph data improves AI snippet rendering and sharing fidelity.",
        "fix": "Ensure required Open Graph and Twitter card meta tags are present and descriptive.",
        "confidence": 0.7,
        "check": check_social_meta_completeness,
    },
    "AIO-SEM-025": {
        "id": "AIO-SEM-025",
        "title": "BreadcrumbList schema implemented",
        "category": "Semantic/Intent",
        "why": "Breadcrumbs help AI agents understand navigation context and improve answer grounding.",
        "fix": "Add BreadcrumbList JSON-LD describing the page's position in the site hierarchy.",
        "confidence": 0.75,
        "check": check_breadcrumb_aio,
    },
}


def evaluate(
    pages: List[Dict], site_meta: Dict, packs: List[str]
) -> Tuple[List[Dict], Dict]:
    """
    Evaluates all relevant rules and calculates scores.
    Enhanced with 2025 AI visibility best practices.
    """
    # Determine which rules to run
    rules_to_run = []
    for pack in packs:
        if pack in RULE_PACKS:
            rules_to_run.extend(RULE_PACKS[pack])

    # Deduplicate
    rules_to_run = list(set(rules_to_run))

    # Run each rule
    findings = []
    for rule_id in rules_to_run:
        if rule_id not in RULES:
            continue  # Skip if rule not defined

        rule = RULES[rule_id]
        result = rule["check"](pages, site_meta)

        finding = {
            "id": rule["id"],
            "title": rule["title"],
            "category": rule["category"],
            "status": result["status"],
            "confidence": rule.get("confidence"),
            "evidence": result["evidence"],
            "why": rule["why"],
            "fix": rule["fix"],
        }
        findings.append(finding)

    # Calculate scores
    category_scores = {}
    categories = set(f["category"] for f in findings)

    for category in categories:
        category_findings = [f for f in findings if f["category"] == category]
        total = len(category_findings)
        if total == 0:
            continue

        passed = sum(1 for f in category_findings if f["status"] == "pass")
        partial = sum(1 for f in category_findings if f["status"] == "partial")

        score = ((passed + (partial * 0.5)) / total) * 100
        category_scores[category] = score

    # Calculate overall score
    overall_score = (
        sum(category_scores.values()) / len(category_scores) if category_scores else 0
    )

    scores = {"overall": overall_score, "by_category": category_scores}

    return findings, scores
