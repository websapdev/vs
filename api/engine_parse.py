"""
Parsing engine for AI Visibility MVP
Extracts structured data and content from HTML pages
"""

from bs4 import BeautifulSoup
import lxml.etree as _etree

# Compatibility shim for lxml >=5 where _ElementStringResult was removed
if not hasattr(_etree, "_ElementStringResult") and hasattr(
    _etree, "_ElementUnicodeResult"
):
    _etree._ElementStringResult = _etree._ElementUnicodeResult  # type: ignore

import extruct
from typing import Dict, List
from urllib.parse import urljoin, urlparse
from api import engine_crawl
import os


def parse_page(url: str, html: str) -> Dict:
    """
    Parses a single page's HTML and extracts relevant data for rule evaluation.

    Args:
        url: Page URL
        html: HTML content

    Returns:
        Dict with extracted data including structured meta, headings, links, and JSON-LD
    """
    default_meta = {
        "viewport": None,
        "robots": None,
        "og": {},
        "twitter": {},
        "article": {},
        "http_equiv_last_modified": None,
    }
    empty_semantic = {
        tag: 0 for tag in ["article", "section", "header", "footer", "main", "nav"]
    }
    empty_media = {
        "images": {"total": 0, "with_alt": 0},
        "videos": {"count": 0, "has_captions": False},
        "has_transcript_section": False,
    }

    # Handle empty HTML
    if not html:
        return {
            "url": url,
            "domain": urlparse(url).netloc if url else None,
            "title": None,
            "meta_desc": None,
            "canonical": None,
            "h_tags": {"h1": [], "h2": [], "h3": []},
            "jsonld": [],
            "meta": default_meta,
            "link_tags": [],
            "internal_links": [],
            "links": [],
            "semantic_tags": empty_semantic,
            "media": empty_media,
            "structured_types": [],
            "error": True,
        }

    try:
        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc.lower()

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else None

        # Extract meta description
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

        # Extract canonical (handle both string and list for rel attribute)
        canonical = None
        canonical_tag = soup.find("link", rel="canonical")
        if not canonical_tag:
            # Try finding any link tag and checking if canonical is in rel
            for link in soup.find_all("link"):
                rel_attr = link.get("rel", [])
                if isinstance(rel_attr, list) and "canonical" in [
                    r.lower() for r in rel_attr
                ]:
                    canonical_tag = link
                    break
                elif isinstance(rel_attr, str) and rel_attr.lower() == "canonical":
                    canonical_tag = link
                    break
        canonical = canonical_tag.get("href", "").strip() if canonical_tag else None

        # Extract heading tags
        h_tags = {
            "h1": [h.get_text().strip() for h in soup.find_all("h1")],
            "h2": [h.get_text().strip() for h in soup.find_all("h2")],
            "h3": [h.get_text().strip() for h in soup.find_all("h3")],
        }

        # Collect meta tags of interest
        meta_info = {
            "viewport": None,
            "robots": None,
            "og": {},
            "twitter": {},
            "article": {},
            "http_equiv_last_modified": None,
        }
        for meta in soup.find_all("meta"):
            name_attr = (meta.get("name") or "").lower()
            prop_attr = (meta.get("property") or "").lower()
            content = (meta.get("content") or "").strip() or None
            if name_attr == "viewport":
                meta_info["viewport"] = content
            if name_attr == "robots":
                meta_info["robots"] = content
            if name_attr.startswith("twitter:"):
                key = name_attr.split(":", 1)[1]
                meta_info["twitter"][key] = content
            if prop_attr.startswith("og:"):
                key = prop_attr.split(":", 1)[1]
                meta_info["og"][key] = content
            if prop_attr.startswith("twitter:"):
                key = prop_attr.split(":", 1)[1]
                meta_info["twitter"][key] = content
            if prop_attr.startswith("article:"):
                key = prop_attr.split(":", 1)[1]
                meta_info["article"][key] = content
            http_equiv = (meta.get("http-equiv") or "").lower()
            if http_equiv == "last-modified":
                meta_info["http_equiv_last_modified"] = content

        # Collect link rel tags
        link_tags = []
        for link in soup.find_all("link"):
            rel_attr = link.get("rel", [])
            if isinstance(rel_attr, list):
                rels = [r.lower() for r in rel_attr]
            elif isinstance(rel_attr, str):
                rels = [rel_attr.lower()]
            else:
                rels = []
            href = link.get("href")
            if rels:
                link_tags.append({"rel": rels, "href": href})

        # Collect links for internal linking analysis
        links = []
        internal_links = []
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            resolved = urljoin(url, href)
            parsed_href = urlparse(resolved)
            is_internal = parsed_href.netloc.lower() == base_domain
            text = anchor.get_text(strip=True)
            link_info = {
                "href": resolved,
                "text": text,
                "internal": is_internal,
            }
            links.append(link_info)
            if is_internal:
                internal_links.append(link_info)

        # Semantic HTML tag counts
        semantic_tags = {
            tag: len(soup.find_all(tag))
            for tag in ["article", "section", "header", "footer", "main", "nav"]
        }

        # Media accessibility data
        images = soup.find_all("img")
        total_images = len(images)
        images_with_alt = sum(1 for img in images if (img.get("alt") or "").strip())
        videos = soup.find_all("video")
        has_captions = any(
            (track.get("kind") or "").lower() in {"captions", "subtitles"}
            for video in videos
            for track in video.find_all("track")
        )
        transcript_section = has_captions or any(
            "transcript" in (element.get_text() or "").lower()
            for element in soup.find_all(["div", "p", "section"])
        )
        media_info = {
            "images": {"total": total_images, "with_alt": images_with_alt},
            "videos": {"count": len(videos), "has_captions": has_captions},
            "has_transcript_section": transcript_section,
        }

        # Extract JSON-LD
        jsonld = []
        try:
            extracted = extruct.extract(html, base_url=url, syntaxes=["json-ld"])
            jsonld = extracted.get("json-ld", [])
        except Exception:
            jsonld = []

        flattened_jsonld = []
        for item in jsonld:
            if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                flattened_jsonld.extend(item["@graph"])
            else:
                flattened_jsonld.append(item)
        jsonld = flattened_jsonld

        structured_types = set()
        for item in jsonld:
            item_type = item.get("@type")
            if isinstance(item_type, list):
                structured_types.update(item_type)
            elif item_type:
                structured_types.add(item_type)

        return {
            "url": url,
            "domain": base_domain,
            "title": title,
            "meta_desc": meta_desc,
            "canonical": canonical,
            "h_tags": h_tags,
            "jsonld": jsonld,
            "meta": meta_info,
            "link_tags": link_tags,
            "internal_links": internal_links,
            "links": links,
            "semantic_tags": semantic_tags,
            "media": media_info,
            "structured_types": sorted(structured_types),
            "error": False,
        }

    except Exception:
        return {
            "url": url,
            "domain": urlparse(url).netloc if url else None,
            "title": None,
            "meta_desc": None,
            "canonical": None,
            "h_tags": {"h1": [], "h2": [], "h3": []},
            "jsonld": [],
            "meta": default_meta,
            "link_tags": [],
            "internal_links": [],
            "links": [],
            "semantic_tags": empty_semantic,
            "media": empty_media,
            "structured_types": [],
            "error": True,
        }


def parse_site(urls: List[str]) -> List[Dict]:
    """
    Parses multiple pages from URL list.

    Args:
        urls: List of URLs to parse

    Returns:
        List of parsed page data dicts
    """
    pages: List[Dict] = []

    # Optional concurrency via env toggle
    concurrent = os.getenv("CRAWL_CONCURRENT", "false").lower() == "true"

    if concurrent:
        try:
            results = engine_crawl.fetch_many(urls)
            for url, html in results:
                pages.append(parse_page(url, html))
            return pages
        except Exception:
            # Fallback to sequential on any failure
            pass

    for url in urls:
        _, html = engine_crawl.fetch(url)
        pages.append(parse_page(url, html))

    return pages
