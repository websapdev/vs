"""
Plan Enforcement (P0-5)
Defines and enforces audit plan tiers (QuickScan, Full, Agency)
"""

from typing import Dict, List

# Plan definitions
PLANS = {
    "quickscan": {
        "name": "QuickScan",
        "description": "Free quick scan of up to 3 pages",
        "max_pages": 3,
        "rule_packs": ["base"],
        "price": 0,
        "features": {
            "audit_history": False,
            "fix_generation": False,
            "citations_tracking": False,
            "pdf_reports": False,
        },
    },
    "full": {
        "name": "Full Audit",
        "description": "Comprehensive audit of up to 5 pages",
        "max_pages": 5,
        "rule_packs": ["base", "aio", "ecomm", "docs"],
        "price": 49,
        "features": {
            "audit_history": True,
            "fix_generation": True,
            "citations_tracking": False,
            "pdf_reports": True,
        },
    },
    "agency": {
        "name": "Agency",
        "description": "Full features with API access",
        "max_pages": 12,
        "rule_packs": ["base", "aio", "ecomm", "docs"],
        "price": 199,
        "features": {
            "audit_history": True,
            "fix_generation": True,
            "citations_tracking": True,
            "pdf_reports": True,
            "api_access": True,
        },
    },
}


def get_plan(plan_name: str) -> Dict:
    """
    Get plan configuration by name.

    Args:
        plan_name: Plan identifier (quickscan, full, agency)

    Returns:
        Plan configuration dict, or quickscan plan if not found
    """
    plan_name_lower = plan_name.lower() if plan_name else "quickscan"
    return PLANS.get(plan_name_lower, PLANS["quickscan"])


def get_plan_limits(plan_name: str) -> Dict:
    """
    Get just the limits for a plan (pages and packs).

    Args:
        plan_name: Plan identifier

    Returns:
        {
            "max_pages": int,
            "rule_packs": list,
            "features": dict
        }
    """
    plan = get_plan(plan_name)
    return {
        "max_pages": plan["max_pages"],
        "rule_packs": plan["rule_packs"],
        "features": plan["features"],
    }


def enforce_plan(plan_name: str, pages: List, packs: List[str]) -> Dict:
    """
    Enforce plan limits on pages and rule packs.

    Args:
        plan_name: Plan identifier
        pages: List of page URLs or page data
        packs: Requested rule packs

    Returns:
        {
            "plan": str,
            "pages": list (limited),
            "packs": list (filtered),
            "limits": dict,
            "limited": bool (whether limiting occurred)
        }
    """
    limits = get_plan_limits(plan_name)

    # Enforce page limit
    original_page_count = len(pages)
    limited_pages = pages[: limits["max_pages"]]

    # Enforce pack restrictions
    allowed_packs = limits["rule_packs"]
    filtered_packs = [p for p in packs if p in allowed_packs]

    # Default to base pack if no valid packs
    if not filtered_packs:
        filtered_packs = ["base"]

    # Check if limiting occurred
    limited = len(limited_pages) < original_page_count or set(filtered_packs) != set(
        packs
    )

    return {
        "plan": plan_name,
        "pages": limited_pages,
        "packs": filtered_packs,
        "limits": limits,
        "limited": limited,
        "original_page_count": original_page_count,
        "original_packs": packs,
    }


def check_feature_access(plan_name: str, feature: str) -> bool:
    """
    Check if a plan has access to a specific feature.

    Args:
        plan_name: Plan identifier
        feature: Feature name (e.g., "fix_generation", "api_access")

    Returns:
        True if feature is available, False otherwise
    """
    plan = get_plan(plan_name)
    return plan.get("features", {}).get(feature, False)


def get_all_plans() -> List[Dict]:
    """
    Get all available plans with their details.

    Returns:
        List of plan configuration dicts
    """
    return [{"id": plan_id, **plan_config} for plan_id, plan_config in PLANS.items()]


def validate_plan_upgrade(from_plan: str, to_plan: str) -> Dict:
    """
    Validate if an upgrade path is valid.

    Args:
        from_plan: Current plan
        to_plan: Target plan

    Returns:
        {
            "valid": bool,
            "reason": str,
            "price_difference": int
        }
    """
    plan_order = ["quickscan", "full", "agency"]

    from_index = plan_order.index(from_plan) if from_plan in plan_order else 0
    to_index = plan_order.index(to_plan) if to_plan in plan_order else 0

    if to_index <= from_index:
        return {
            "valid": False,
            "reason": "Cannot downgrade or upgrade to same plan",
            "price_difference": 0,
        }

    from_price = PLANS[from_plan]["price"]
    to_price = PLANS[to_plan]["price"]

    return {
        "valid": True,
        "reason": f"Upgrade from {PLANS[from_plan]['name']} to {PLANS[to_plan]['name']}",
        "price_difference": to_price - from_price,
    }


def get_plan_recommendation(pages_needed: int, packs_needed: List[str]) -> str:
    """
    Recommend a plan based on requirements.

    Args:
        pages_needed: Number of pages to audit
        packs_needed: Required rule packs

    Returns:
        Recommended plan identifier
    """
    # If only need base pack and <=3 pages, quickscan is fine
    if pages_needed <= 3 and set(packs_needed).issubset({"base"}):
        return "quickscan"

    # If need more pages or additional packs, need full
    if pages_needed <= 5 and (pages_needed > 3 or len(packs_needed) > 1):
        return "full"

    # If need API access or more than 5 pages, need agency
    return "agency"


# Plan comparison for frontend display
def compare_plans() -> List[Dict]:
    """
    Generate a comparison matrix of all plans.

    Returns:
        List of feature comparisons across plans
    """
    features = [
        {
            "name": "Pages Scanned",
            "quickscan": "Up to 3",
            "full": "Up to 5",
            "agency": "Up to 12",
        },
        {
            "name": "Rule Packs",
            "quickscan": "Base only",
            "full": "All packs (Base + AI Optimization + E-comm + Docs)",
            "agency": "All packs (Base + AI Optimization + E-comm + Docs)",
        },
        {"name": "Audit History", "quickscan": "❌", "full": "✓", "agency": "✓"},
        {"name": "Auto-Fix Generation", "quickscan": "❌", "full": "✓", "agency": "✓"},
        {"name": "PDF Reports", "quickscan": "❌", "full": "✓", "agency": "✓"},
        {"name": "Citation Tracking", "quickscan": "❌", "full": "❌", "agency": "✓"},
        {"name": "API Access", "quickscan": "❌", "full": "❌", "agency": "✓"},
        {"name": "Price", "quickscan": "Free", "full": "$49", "agency": "$199/mo"},
    ]

    return features
