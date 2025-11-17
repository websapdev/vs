"""
Rules engine for AI Visibility MVP
Evaluates pages against rule packs and generates findings
"""

from typing import Dict, List, Tuple


# Rule pack definitions
RULE_PACKS = {
    "base": [
        "CRW-ROB-001",
        "CRW-SMP-001",
        "CRW-CAN-001",
        "SCH-ORG-001",
        "SCH-FAQ-001",
        "SCH-BRD-001",
        "ANS-HDR-001",
    ],
    "ecomm": ["ECM-PRO-001", "ECM-OFR-001"],
    "docs": ["DOC-OAS-001"],
}


def check_robots_gptbot(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if robots.txt allows GPTBot."""
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

    # Parse robots.txt for GPTBot rules
    lines = robots_txt.lower().split("\n")
    current_agent = None
    gptbot_disallowed = False

    for line in lines:
        line = line.strip()
        if line.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            current_agent = agent
        elif line.startswith("disallow:") and current_agent in ["gptbot", "*"]:
            disallow_path = line.split(":", 1)[1].strip()
            if disallow_path == "/":
                gptbot_disallowed = True

    if gptbot_disallowed:
        return {
            "status": "fail",
            "evidence": [
                {
                    "url": f"{site_meta['base_url']}/robots.txt",
                    "snippet": "GPTBot is disallowed",
                }
            ],
        }

    return {"status": "pass", "evidence": []}


def check_sitemap(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if sitemap.xml exists."""
    if site_meta.get("sitemap_url"):
        return {"status": "pass", "evidence": []}

    # Check if referenced in robots.txt
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

    # Collect URLs without canonical
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
        # Handle both string and list types
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
    """Checks if FAQPage or QAPage schema exists on at least one page."""
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
                "snippet": "No FAQPage or QAPage schema found on any page",
            }
        ],
    }


def check_breadcrumb(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if BreadcrumbList schema exists on at least one page."""
    for page in pages:
        for jsonld in page.get("jsonld", []):
            jsonld_type = jsonld.get("@type", "")
            types = [jsonld_type] if isinstance(jsonld_type, str) else jsonld_type

            if "BreadcrumbList" in types:
                return {"status": "pass", "evidence": []}

    return {
        "status": "fail",
        "evidence": [
            {
                "url": site_meta["base_url"],
                "snippet": "No BreadcrumbList schema found on any page",
            }
        ],
    }


def check_headings(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if at least 50% of pages have both H2 and H3 tags."""
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

    # Collect URLs without proper headings
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


def check_product_schema(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if Product schema exists on at least one page."""
    # Identify potential product pages
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
            {
                "url": site_meta["base_url"],
                "snippet": "No Product schema found (checked product/shop pages)",
            }
        ],
    }


def check_offer_fields(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if Product schema includes Offer with price, priceCurrency, and availability."""
    # Find pages with Product schema
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
                    # Handle both single offer and array of offers
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
                                "snippet": "Product schema found but Offer missing price/currency/availability",
                            }
                        ],
                    }

    return {
        "status": "fail",
        "evidence": [
            {"url": site_meta["base_url"], "snippet": "No Product schema found"}
        ],
    }


def check_openapi(pages: List[Dict], site_meta: Dict) -> Dict:
    """Checks if OpenAPI spec is discoverable."""
    # Identify docs pages
    docs_pages = [
        p for p in pages if "/docs" in p["url"].lower() or "/api" in p["url"].lower()
    ]

    if docs_pages:
        # Check for OpenAPI/Swagger mentions
        for page in docs_pages:
            # This is a simplified check - in real implementation would check HTML content
            # For now, we'll mark as partial if docs exist
            return {
                "status": "partial",
                "evidence": [
                    {
                        "url": page["url"],
                        "snippet": "Docs pages found but OpenAPI spec discoverability unclear",
                    }
                ],
            }
    else:
        return {
            "status": "fail",
            "evidence": [
                {"url": site_meta["base_url"], "snippet": "No docs pages found"}
            ],
        }


# Rule definitions
RULES = {
    "CRW-ROB-001": {
        "id": "CRW-ROB-001",
        "title": "robots.txt allows GPTBot",
        "category": "Crawlability",
        "why": "AI bots need access to crawl.",
        "fix": "Allow GPTBot in robots.txt for public pages.",
        "check": check_robots_gptbot,
    },
    "CRW-SMP-001": {
        "id": "CRW-SMP-001",
        "title": "Sitemap present",
        "category": "Crawlability",
        "why": "Sitemaps guide bots to key pages.",
        "fix": "Add /sitemap.xml and reference in robots.txt.",
        "check": check_sitemap,
    },
    "CRW-CAN-001": {
        "id": "CRW-CAN-001",
        "title": "Canonical tags present",
        "category": "Crawlability",
        "why": "Prevents duplication issues.",
        "fix": "Add rel=canonical per page.",
        "check": check_canonicals,
    },
    "SCH-ORG-001": {
        "id": "SCH-ORG-001",
        "title": "Organization schema on homepage",
        "category": "Schema",
        "why": "Aligns entity and trust.",
        "fix": "Add Organization JSON-LD with sameAs to authoritative profiles.",
        "check": check_org_schema,
    },
    "SCH-FAQ-001": {
        "id": "SCH-FAQ-001",
        "title": "FAQ/QAPage present",
        "category": "Schema",
        "why": "Improves answerability and citations.",
        "fix": "Add FAQPage/QAPage with acceptedAnswer text.",
        "check": check_faq_schema,
    },
    "SCH-BRD-001": {
        "id": "SCH-BRD-001",
        "title": "BreadcrumbList present",
        "category": "Schema",
        "why": "Clarifies structure for bots.",
        "fix": "Add BreadcrumbList JSON-LD.",
        "check": check_breadcrumb,
    },
    "ANS-HDR-001": {
        "id": "ANS-HDR-001",
        "title": "Clean H2/H3 sections",
        "category": "Answerability",
        "why": "Chunked content is easier to cite.",
        "fix": "Use H2/H3 with 60–150 word sections.",
        "check": check_headings,
    },
    "ECM-PRO-001": {
        "id": "ECM-PRO-001",
        "title": "Product schema present",
        "category": "E-comm",
        "why": "Products become machine-readable.",
        "fix": "Add Product JSON-LD on PDPs.",
        "check": check_product_schema,
    },
    "ECM-OFR-001": {
        "id": "ECM-OFR-001",
        "title": "Offer with price/currency/availability",
        "category": "E-comm",
        "why": "Enables retrievability in answers.",
        "fix": "Include Offer fields in JSON-LD.",
        "check": check_offer_fields,
    },
    "DOC-OAS-001": {
        "id": "DOC-OAS-001",
        "title": "OpenAPI discoverable",
        "category": "Docs",
        "why": "APIs become answerable and citable.",
        "fix": "Link a crawlable OpenAPI spec from docs index.",
        "check": check_openapi,
    },
}


def evaluate(
    pages: List[Dict], site_meta: Dict, packs: List[str]
) -> Tuple[List[Dict], Dict]:
    """
    Evaluates all relevant rules and calculates scores.

    Args:
        pages: List of parsed page data
        site_meta: Site metadata dict
        packs: List of pack identifiers to evaluate

    Returns:
        Tuple of (findings list, scores dict)
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
