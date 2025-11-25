#!/usr/bin/env python3
"""
Test script to verify crawler can discover and fetch up to 5 pages
"""

import os
import sys

# Add api directory to path
api_dir = os.path.join(os.path.dirname(__file__), 'api')
sys.path.insert(0, api_dir)

# Import engine_crawl directly without importing api package
import engine_crawl

def test_crawler_with_5_pages():
    """Test crawler discovers up to 5 pages"""
    
    # Test with a well-known website
    test_url = "https://example.com"
    
    print(f"Testing crawler with URL: {test_url}")
    print("=" * 60)
    
    # Test 1: Default behavior (should be 5 pages)
    print("\nTest 1: Default behavior (max_pages not specified)")
    pages = engine_crawl.discover_pages(test_url)
    print(f"Discovered {len(pages)} pages:")
    for i, page in enumerate(pages, 1):
        print(f"  {i}. {page}")
    assert len(pages) <= 5, f"Expected max 5 pages, got {len(pages)}"
    print(f"✓ Test 1 passed: Discovered {len(pages)} pages (max 5)")
    
    # Test 2: Explicit max_pages=5
    print("\nTest 2: Explicit max_pages=5")
    pages = engine_crawl.discover_pages(test_url, max_pages=5)
    print(f"Discovered {len(pages)} pages:")
    for i, page in enumerate(pages, 1):
        print(f"  {i}. {page}")
    assert len(pages) <= 5, f"Expected max 5 pages, got {len(pages)}"
    print(f"✓ Test 2 passed: Discovered {len(pages)} pages (max 5)")
    
    # Test 3: Explicit max_pages=3
    print("\nTest 3: Explicit max_pages=3")
    pages = engine_crawl.discover_pages(test_url, max_pages=3)
    print(f"Discovered {len(pages)} pages:")
    for i, page in enumerate(pages, 1):
        print(f"  {i}. {page}")
    assert len(pages) <= 3, f"Expected max 3 pages, got {len(pages)}"
    print(f"✓ Test 3 passed: Discovered {len(pages)} pages (max 3)")
    
    # Test 4: Explicit max_pages=10
    print("\nTest 4: Explicit max_pages=10")
    pages = engine_crawl.discover_pages(test_url, max_pages=10)
    print(f"Discovered {len(pages)} pages:")
    for i, page in enumerate(pages, 1):
        print(f"  {i}. {page}")
    assert len(pages) <= 10, f"Expected max 10 pages, got {len(pages)}"
    print(f"✓ Test 4 passed: Discovered {len(pages)} pages (max 10)")
    
    # Test 5: Environment variable override
    print("\nTest 5: Environment variable override (CRAWL_MAX_PAGES=7)")
    os.environ["CRAWL_MAX_PAGES"] = "7"
    pages = engine_crawl.discover_pages(test_url)
    print(f"Discovered {len(pages)} pages:")
    for i, page in enumerate(pages, 1):
        print(f"  {i}. {page}")
    assert len(pages) <= 7, f"Expected max 7 pages, got {len(pages)}"
    print(f"✓ Test 5 passed: Discovered {len(pages)} pages (max 7)")
    
    # Clean up
    del os.environ["CRAWL_MAX_PAGES"]
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_crawler_with_5_pages()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
