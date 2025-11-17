"""
Auto-Fix Generator (P0-3)
Generates code fixes and acceptance tests for failed rules using LLMs
"""

import json
from typing import Dict

from api.vysalytica.config import (
    create_openai_client_safe,
    debug_openai_client_info,
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

# Initialize client variable (always defined for testing)
client = None
OPENAI_AVAILABLE = False

# Prioritize RouteLLM if configured, otherwise fall back to OpenAI
if ROUTELLM_API_KEY:
    try:
        # Debug client parameters to help diagnose version conflicts
        debug_openai_client_info()

        client = create_openai_client_safe(
            api_key=ROUTELLM_API_KEY,
            base_url=ROUTELLM_BASE_URL
        )
        OPENAI_AVAILABLE = True
        print(
            f"✓ RouteLLM configured (base_url: {ROUTELLM_BASE_URL}, model: {ROUTELLM_MODEL})"
        )
    except TypeError as e:
        if 'proxies' in str(e):
            print(f"✗ RouteLLM still receiving 'proxies' argument: {e}")
            print(f"✗ This suggests an external library is passing 'proxies'")
        else:
            print(f"✗ RouteLLM initialization failed: {e}")
        client = None
    except (ImportError, Exception) as e:
        print(f"✗ RouteLLM initialization failed: {e}")
        client = None
elif OPENAI_API_KEY:
    try:
        client = create_openai_client_safe(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
        print("✓ OpenAI configured")
    except TypeError as e:
        if 'proxies' in str(e):
            print(f"✗ OpenAI still receiving 'proxies' argument: {e}")
        else:
            print(f"✗ OpenAI initialization failed: {e}")
        client = None
    except (ImportError, Exception) as e:
        print(f"✗ OpenAI initialization failed: {e}")
        client = None
else:
    print("⚠️ RouteLLM/OpenAI API key not configured. Auto-fix generation is disabled.")

# Prompt template for fix generation
FIX_GENERATION_TEMPLATE = """You are an expert web developer specializing in AI visibility optimization.

A website failed the following rule:

Rule ID: {rule_id}
Rule Title: {title}
Category: {category}
Why it matters: {why}
How to fix: {fix}

Generate a solution with:
1. A compact code snippet (HTML, JSON-LD, or other format) that fixes this issue
2. A pytest acceptance test that validates the fix

Return ONLY valid JSON in this exact format:
{
  "fix_snippet": "<your fix code here>",
  "acceptance_test": "def test_{rule_id_clean}():\n    # test code here"
}}

Requirements:
- fix_snippet: Complete, copy-paste ready code (HTML tags, JSON-LD, robots.txt rules, etc.)
- acceptance_test: Valid pytest function that checks if the fix works
- Keep both compact and production-ready
- Use real, working code examples

Return ONLY the JSON object, no explanation or markdown."""


def generate_fix(finding: Dict) -> Dict:
    """
    Generate a fix snippet and acceptance test for a failed finding.

    Args:
        finding: Finding dict with keys: id, title, category, status, why, fix

    Returns:
        {
            "fix_snippet": str,
            "acceptance_test": str,
            "error": str (if generation failed)
        }
    """
    if not OPENAI_AVAILABLE:
        return {
            "fix_snippet": "",
            "acceptance_test": "",
            "error": "OpenAI API not configured",
        }

    # Only generate fixes for failed rules
    if finding.get("status") != "fail":
        return {
            "fix_snippet": "",
            "acceptance_test": "",
            "message": "No fix needed - rule passed or partially passed",
        }

    try:
        # Build prompt
        rule_id = finding.get("id", "UNKNOWN")
        rule_id_clean = rule_id.replace("-", "_").lower()

        prompt = FIX_GENERATION_TEMPLATE.format(
            rule_id=rule_id,
            rule_id_clean=rule_id_clean,
            title=finding.get("title", ""),
            category=finding.get("category", ""),
            why=finding.get("why", ""),
            fix=finding.get("fix", ""),
        )

        # Call OpenAI API (v1 style)
        response = client.chat.completions.create(
            model=ROUTELLM_MODEL if ROUTELLM_API_KEY else "gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates code fixes and tests. Always return valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.3,  # Lower temperature for more consistent output
        )

        # Extract response
        content = response.choices[0].message.content.strip()

        # Parse JSON from response
        # Handle cases where LLM wraps JSON in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Find JSON object in response
        start_idx = content.find("{")
        end_idx = content.rfind("}") + 1

        if start_idx == -1 or end_idx == 0:
            return {
                "fix_snippet": "",
                "acceptance_test": "",
                "error": "Failed to parse JSON from LLM response",
            }

        json_str = content[start_idx:end_idx]
        result = json.loads(json_str)

        # Validate required fields
        if "fix_snippet" not in result or "acceptance_test" not in result:
            return {
                "fix_snippet": result.get("fix_snippet", ""),
                "acceptance_test": result.get("acceptance_test", ""),
                "error": "Incomplete response from LLM",
            }

        # Sanitize fix snippet (basic XSS prevention)
        fix_snippet = result["fix_snippet"]
        if "<script" in fix_snippet.lower() and "json-ld" not in fix_snippet.lower():
            # Allow <script type="application/ld+json"> but block other scripts
            fix_snippet = fix_snippet.replace("<script", "&lt;script")

        return {
            "fix_snippet": fix_snippet,
            "acceptance_test": result["acceptance_test"],
        }

    except json.JSONDecodeError as e:
        return {
            "fix_snippet": "",
            "acceptance_test": "",
            "error": f"JSON parsing error: {str(e)}",
        }
    except Exception as e:
        return {
            "fix_snippet": "",
            "acceptance_test": "",
            "error": f"Fix generation failed: {str(e)}",
        }


def generate_fixes_bulk(findings: list) -> list:
    """
    Generate fixes for multiple findings.

    Args:
        findings: List of finding dicts

    Returns:
        List of findings with fix_snippet and acceptance_test added
    """
    enhanced_findings = []

    for finding in findings:
        # Only generate for failed rules
        if finding.get("status") == "fail":
            fix_data = generate_fix(finding)

            # Add fix data to finding
            finding_copy = finding.copy()
            finding_copy["fix_snippet"] = fix_data.get("fix_snippet", "")
            finding_copy["acceptance_test"] = fix_data.get("acceptance_test", "")

            if "error" in fix_data:
                finding_copy["fix_generation_error"] = fix_data["error"]

            enhanced_findings.append(finding_copy)
        else:
            # Pass through without modification
            enhanced_findings.append(finding)

    return enhanced_findings


def validate_fix_syntax(fix_snippet: str, fix_type: str = "html") -> Dict:
    """
    Basic syntax validation for fix snippets.

    Args:
        fix_snippet: The generated fix code
        fix_type: Type of fix ("html", "json-ld", "robots", etc.)

    Returns:
        {
            "valid": bool,
            "errors": list of error strings
        }
    """
    errors = []

    if not fix_snippet or len(fix_snippet.strip()) == 0:
        errors.append("Fix snippet is empty")
        return {"valid": False, "errors": errors}

    # Basic validation based on type
    if fix_type == "json-ld":
        # Check for valid JSON-LD structure
        if '<script type="application/ld+json">' not in fix_snippet:
            errors.append("Missing JSON-LD script tag")

        try:
            # Try to extract and parse JSON
            start = fix_snippet.find("{")
            end = fix_snippet.rfind("}") + 1
            if start != -1 and end > start:
                json.loads(fix_snippet[start:end])
        except json.JSONDecodeError:
            errors.append("Invalid JSON in JSON-LD snippet")

    elif fix_type == "html":
        # Check for basic HTML validity
        if "<" in fix_snippet and ">" in fix_snippet:
            # Count opening and closing tags (basic check)
            opens = fix_snippet.count("<") - fix_snippet.count("</")
            closes = fix_snippet.count("</")
            if opens < closes:
                errors.append("Possible unclosed HTML tags")

    elif fix_type == "robots":
        # Check robots.txt format
        if "User-agent:" not in fix_snippet and "Sitemap:" not in fix_snippet:
            errors.append("Missing User-agent or Sitemap directive")

    return {"valid": len(errors) == 0, "errors": errors}
