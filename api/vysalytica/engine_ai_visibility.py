"""
AI Citation Tracker (P0-2)
Query ChatGPT and Claude to check if a brand is cited for specific queries
"""

from datetime import datetime
from typing import Dict, List

from api.vysalytica.config import (
    create_anthropic_client_safe,
    create_openai_client_safe,
    debug_openai_client_info,
    get_anthropic_api_key,
    get_openai_api_key,
    get_routellm_api_key,
    get_routellm_base_url,
    get_routellm_model,
)

# Resolve configuration using centralized helper (Streamlit secrets > env vars)
ROUTELLM_API_KEY = get_routellm_api_key()
ROUTELLM_BASE_URL = get_routellm_base_url()
ROUTELLM_MODEL = get_routellm_model()
OPENAI_API_KEY = get_openai_api_key()
ANTHROPIC_API_KEY = get_anthropic_api_key()

# Initialize client variables (always defined for testing)
openai_client = None
OPENAI_AVAILABLE = False

# Prioritize RouteLLM if configured, otherwise use OpenAI
if ROUTELLM_API_KEY:
    try:
        # Debug client parameters to help diagnose version conflicts
        debug_openai_client_info()

        openai_client = create_openai_client_safe(
            api_key=ROUTELLM_API_KEY, base_url=ROUTELLM_BASE_URL
        )

        OPENAI_AVAILABLE = True
        print(
            f"[OK] RouteLLM configured for citations (base_url: {ROUTELLM_BASE_URL}, model: {ROUTELLM_MODEL})"
        )
    except TypeError as e:
        if "proxies" in str(e):
            print(f"[FAIL] RouteLLM still receiving 'proxies' argument: {e}")
            print(f"[FAIL] This suggests an external library is passing 'proxies'")
        else:
            print(f"[FAIL] RouteLLM initialization failed: {e}")
        openai_client = None
    except (ImportError, Exception) as e:
        print(f"[FAIL] RouteLLM initialization failed: {e}")
        openai_client = None
elif OPENAI_API_KEY:
    try:
        openai_client = create_openai_client_safe(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
        print("[OK] OpenAI configured for citations")
    except TypeError as e:
        if "proxies" in str(e):
            print(f"[FAIL] OpenAI still receiving 'proxies' argument: {e}")
        else:
            print(f"[FAIL] OpenAI initialization failed: {e}")
        openai_client = None
    except (ImportError, Exception) as e:
        print(f"[FAIL] OpenAI initialization failed: {e}")
        openai_client = None
else:
    print(
        "[WARN] RouteLLM/OpenAI API key not configured. Citation tracking for ChatGPT will be unavailable."
    )

# For Anthropic/Claude - RouteLLM can handle this too via OpenAI-compatible API
if ROUTELLM_API_KEY:
    ANTHROPIC_AVAILABLE = True
    print("[OK] RouteLLM will handle Claude queries")
elif ANTHROPIC_API_KEY:
    try:
        import anthropic

        ANTHROPIC_AVAILABLE = True
        print("[OK] Anthropic configured")
    except ImportError:
        ANTHROPIC_AVAILABLE = False
        print(
            "[WARN] Anthropic SDK not installed; Claude citation tracking disabled despite configured API key."
        )
else:
    ANTHROPIC_AVAILABLE = False
    print(
        "[WARN] Claude citation tracking disabled. Configure ROUTELLM_API_KEY or ANTHROPIC_API_KEY to enable it."
    )


def query_chatgpt(intent: str, brand: str) -> Dict:
    """
    Query ChatGPT to check if brand is cited.

    Args:
        intent: The query/intent to test (e.g., "best project management tools")
        brand: The brand to check for citation (e.g., "Asana")

    Returns:
        {
            "assistant": "ChatGPT",
            "intent": str,
            "brand": str,
            "cited": bool,
            "response": str (truncated to 600 chars),
            "timestamp": ISO datetime string,
            "error": str (if error occurred)
        }
    """
    if not OPENAI_AVAILABLE:
        return {
            "assistant": "ChatGPT",
            "intent": intent,
            "brand": brand,
            "cited": False,
            "response": "",
            "timestamp": datetime.utcnow().isoformat(),
            "error": "OpenAI API not configured",
        }

    try:
        # Construct the query
        query = f"{intent} {brand}".strip()

        # Call OpenAI API (v1 style)
        response = openai_client.chat.completions.create(
            model=ROUTELLM_MODEL if ROUTELLM_API_KEY else "gpt-3.5-turbo",
            messages=[{"role": "user", "content": query}],
            max_tokens=300,
            temperature=0.7,
        )

        # Extract response text
        response_text = response.choices[0].message.content

        # Check if brand is cited (case-insensitive)
        cited = brand.lower() in response_text.lower()

        return {
            "assistant": "ChatGPT",
            "intent": intent,
            "brand": brand,
            "cited": cited,
            "response": response_text[:600],  # Truncate for storage
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "assistant": "ChatGPT",
            "intent": intent,
            "brand": brand,
            "cited": False,
            "response": "",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


def query_claude(intent: str, brand: str) -> Dict:
    """
    Query Claude to check if brand is cited.

    Args:
        intent: The query/intent to test
        brand: The brand to check for citation

    Returns:
        {
            "assistant": "Claude",
            "intent": str,
            "brand": str,
            "cited": bool,
            "response": str (truncated to 600 chars),
            "timestamp": ISO datetime string,
            "error": str (if error occurred)
        }
    """
    if not ANTHROPIC_AVAILABLE:
        return {
            "assistant": "Claude",
            "intent": intent,
            "brand": brand,
            "cited": False,
            "response": "",
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Anthropic API not configured",
        }

    try:
        # Construct the query
        query = f"{intent} {brand}".strip()

        # If using RouteLLM, use OpenAI-compatible API with Claude model
        if ROUTELLM_API_KEY:
            response = openai_client.chat.completions.create(
                model="claude-3-haiku-20240307",  # RouteLLM supports Claude models
                messages=[{"role": "user", "content": query}],
                max_tokens=300,
                temperature=0.7,
            )
            response_text = response.choices[0].message.content
        else:
            # Call Anthropic API directly using safe wrapper
            client = create_anthropic_client_safe(api_key=ANTHROPIC_API_KEY)
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{"role": "user", "content": query}],
            )
            response_text = message.content[0].text

        # Check if brand is cited (case-insensitive)
        cited = brand.lower() in response_text.lower()

        return {
            "assistant": "Claude",
            "intent": intent,
            "brand": brand,
            "cited": cited,
            "response": response_text[:600],  # Truncate for storage
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "assistant": "Claude",
            "intent": intent,
            "brand": brand,
            "cited": False,
            "response": "",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


def track_citations(intent: str, brand: str, assistants: List[str] = None) -> List[Dict]:
    """
    Track citations across multiple AI assistants.

    Args:
        intent: The query/intent to test
        brand: The brand to check for citation
        assistants: List of assistants to query (default: ["chatgpt", "claude"])

    Returns:
        List of citation results from each assistant
    """
    if assistants is None:
        assistants = ["chatgpt", "claude"]

    results = []

    for assistant in assistants:
        assistant_lower = assistant.lower()

        if assistant_lower == "chatgpt":
            result = query_chatgpt(intent, brand)
            results.append(result)

        elif assistant_lower == "claude":
            result = query_claude(intent, brand)
            results.append(result)

    return results


def get_citation_rate(brand: str, db_session) -> Dict:
    """
    Calculate citation rate from historical data.

    Args:
        brand: The brand name
        db_session: Database session

    Returns:
        {
            "brand": str,
            "total_queries": int,
            "chatgpt_citations": int,
            "chatgpt_rate": float,
            "claude_citations": int,
            "claude_rate": float,
            "overall_rate": float
        }
    """
    from api.vysalytica.db.models import CitationSnapshot

    try:
        # Query all citations for this brand
        citations = db_session.query(CitationSnapshot).filter(CitationSnapshot.brand == brand).all()

        if not citations:
            return {
                "brand": brand,
                "total_queries": 0,
                "chatgpt_citations": 0,
                "chatgpt_rate": 0.0,
                "claude_citations": 0,
                "claude_rate": 0.0,
                "overall_rate": 0.0,
            }

        # Calculate rates by assistant
        chatgpt_total = sum(1 for c in citations if c.assistant == "ChatGPT")
        chatgpt_cited = sum(1 for c in citations if c.assistant == "ChatGPT" and c.cited)

        claude_total = sum(1 for c in citations if c.assistant == "Claude")
        claude_cited = sum(1 for c in citations if c.assistant == "Claude" and c.cited)

        total_queries = len(citations)
        total_cited = sum(1 for c in citations if c.cited)

        return {
            "brand": brand,
            "total_queries": total_queries,
            "chatgpt_citations": chatgpt_cited,
            "chatgpt_rate": ((chatgpt_cited / chatgpt_total * 100) if chatgpt_total > 0 else 0.0),
            "claude_citations": claude_cited,
            "claude_rate": ((claude_cited / claude_total * 100) if claude_total > 0 else 0.0),
            "overall_rate": ((total_cited / total_queries * 100) if total_queries > 0 else 0.0),
        }

    except Exception as e:
        return {"brand": brand, "error": str(e)}
