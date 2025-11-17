#!/usr/bin/env python3
"""
Test script to verify automatic .docx download functionality
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:5000"
TEST_URL = "https://example.com"

def test_json_response():
    """Test that default JSON response still works"""
    print("Testing JSON response (default)...")
    
    response = requests.post(
        f"{BASE_URL}/api/audit",
        json={
            "url": TEST_URL,
            "packs": ["base"],
            "plan": "quickscan"
        },
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("✓ JSON response working correctly")
            return True
        else:
            print(f"✗ JSON response failed: {data.get('error')}")
            return False
    else:
        print(f"✗ HTTP error: {response.status_code}")
        return False

def test_docx_response():
    """Test that DOCX download works with format=docx parameter"""
    print("\nTesting DOCX download (format=docx)...")
    
    response = requests.post(
        f"{BASE_URL}/api/audit?format=docx",
        json={
            "url": TEST_URL,
            "packs": ["base"],
            "plan": "quickscan"
        },
        timeout=120
    )
    
    if response.status_code == 200:
        # Check if response is a DOCX file
        content_type = response.headers.get('Content-Type', '')
        content_disposition = response.headers.get('Content-Disposition', '')
        
        if 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
            print("✓ Content-Type is correct for DOCX")
        else:
            print(f"✗ Unexpected Content-Type: {content_type}")
            return False
        
        if 'attachment' in content_disposition:
            print("✓ Content-Disposition header is set to attachment")
        else:
            print(f"✗ Content-Disposition not set correctly: {content_disposition}")
            return False
        
        # Check if content is binary (DOCX file)
        if len(response.content) > 0:
            print(f"✓ DOCX file generated ({len(response.content)} bytes)")
            
            # Save to file for manual inspection
            filename = "test_audit_report.docx"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ Saved test file to {filename}")
            return True
        else:
            print("✗ Empty response content")
            return False
    else:
        print(f"✗ HTTP error: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Automatic DOCX Download Functionality")
    print("=" * 60)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Test URL: {TEST_URL}\n")
    
    # Check if server is running
    try:
        health_check = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if health_check.status_code != 200:
            print("✗ Server is not responding to health check")
            print("Please start the Flask server first:")
            print("  cd /home/ubuntu/github_repos/vysalytica/api")
            print("  python api.py")
            sys.exit(1)
        print("✓ Server is running\n")
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to server: {e}")
        print("\nPlease start the Flask server first:")
        print("  cd /home/ubuntu/github_repos/vysalytica/api")
        print("  python api.py")
        sys.exit(1)
    
    # Run tests
    results = []
    results.append(("JSON Response", test_json_response()))
    results.append(("DOCX Download", test_docx_response()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
