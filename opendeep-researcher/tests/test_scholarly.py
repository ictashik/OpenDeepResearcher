#!/usr/bin/env python3
"""
Test script to verify scholarly package functionality.
"""

import sys
import time

def test_scholarly_import():
    """Test if scholarly can be imported."""
    try:
        from scholarly import scholarly
        print("✅ Scholarly package imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import scholarly: {e}")
        return False

def test_basic_search():
    """Test basic scholarly search functionality."""
    try:
        from scholarly import scholarly
        
        print("🔍 Testing basic search with 'machine learning'...")
        
        # Search for publications
        search_query = scholarly.search_pubs('machine learning')
        
        # Try to get first result
        first_pub = next(search_query)
        print(f"📄 Found publication: {first_pub.get('title', 'No title')}")
        
        # Fill in details
        print("📋 Filling publication details...")
        pub_filled = scholarly.fill(first_pub)
        
        print(f"   Title: {pub_filled.get('title', 'N/A')}")
        print(f"   Authors: {len(pub_filled.get('author', []))} authors")
        print(f"   Abstract: {len(pub_filled.get('abstract', ''))} characters")
        print(f"   Citations: {pub_filled.get('num_citations', 0)}")
        
        print("✅ Basic search test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Basic search test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Scholarly Package Integration")
    print("=" * 50)
    
    # Test import
    if not test_scholarly_import():
        sys.exit(1)
    
    print()
    
    # Test basic functionality
    if not test_basic_search():
        sys.exit(1)
    
    print()
    print("🎉 All tests passed! Scholarly integration is working correctly.")

if __name__ == "__main__":
    main()
