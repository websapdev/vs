#!/usr/bin/env python3
"""
Detailed test to verify crawler discovers multiple pages from a real website
"""

import os
import sys

# Add api directory to path
api_dir = os.path.join(os.path.dirname(__file__), 'api')
sys.path.insert(0, api_dir)

# Import engine_crawl directly
import engine_crawl

def test_crawler_detailed():
    """Test crawler with various websites to see internal link discovery"""
    
    test_cases = [
        ("https://www.python.org", 5, "Python.org - should have multiple pages"),
        ("https://www.wikipedia.org", 3, "Wikipedia - limited to 3 pages"),
        ("https://example.com", 5, "Example.com - simple site (may only have 1 page)"),
    ]
    
    print("Testing crawler with multiple websites")
    print("=" * 70)
    
    for url, max_pages, description in test_cases:
        print(f"\nTest: {description}")
        print(f"URL: {url}")
        print(f"Max pages: {max_pages}")
        print("-" * 70)
        
        try:
            pages = engine_crawl.discover_pages(url, max_pages=max_pages)
            print(f"✓ Discovered {len(pages)} pages (max {max_pages}):")
            for i, page in enumerate(pages, 1):
                print(f"  {i}. {page}")
            
            # Verify the limit is respected
            if len(pages) > max_pages:
                print(f"✗ ERROR: Expected max {max_pages} pages, got {len(pages)}")
                return False
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            return False
        
        print()
    
    print("=" * 70)
    print("✓ All tests completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = test_crawler_detailed()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
