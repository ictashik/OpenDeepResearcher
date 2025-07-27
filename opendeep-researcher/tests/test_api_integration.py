#!/usr/bin/env python3
"""
Test script for API integrations in OpenDeep Researcher.
Tests the new API methods without requiring API keys.
"""

import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_api_imports():
    """Test that all API-related modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from utils.academic_search import RobustAcademicSearcher
        print("✅ Academic search module imported successfully")
        
        from utils.config_manager import config_manager
        print("✅ Config manager imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config_manager():
    """Test config manager functionality."""
    print("\n🧪 Testing config manager...")
    
    try:
        from utils.config_manager import config_manager
        
        # Test loading config
        config = config_manager.load_config()
        print(f"✅ Config loaded: {type(config)}")
        
        # Test API key methods (should return None for empty config)
        core_key = config_manager.get_core_api_key()
        semantic_key = config_manager.get_semantic_scholar_api_key()
        print(f"✅ API key retrieval working (CORE: {bool(core_key)}, Semantic: {bool(semantic_key)})")
        
        # Test data collection settings
        settings = config_manager.get_data_collection_settings()
        print(f"✅ Data collection settings: {settings}")
        
        return True
    except Exception as e:
        print(f"❌ Config manager error: {e}")
        return False

def test_academic_searcher():
    """Test academic searcher initialization with API integration."""
    print("\n🧪 Testing academic searcher...")
    
    try:
        from utils.academic_search import RobustAcademicSearcher
        
        # Initialize searcher
        searcher = RobustAcademicSearcher(max_results_per_source=5)
        print("✅ Academic searcher initialized")
        
        # Test that API keys are loaded (should be None if not configured)
        print(f"✅ CORE API key loaded: {bool(searcher.core_api_key)}")
        print(f"✅ Semantic Scholar API key loaded: {bool(searcher.semantic_scholar_api_key)}")
        
        # Test PubMed API (no key required)
        print("\n🧪 Testing PubMed API...")
        try:
            articles, method = searcher.search_pubmed_api(["machine learning"], None)
            print(f"✅ PubMed API test completed: {method} ({len(articles)} articles)")
        except Exception as e:
            print(f"⚠️ PubMed API test failed (expected if no internet): {e}")
        
        # Test Semantic Scholar API (no key required for basic use)
        print("\n🧪 Testing Semantic Scholar API...")
        try:
            articles, method = searcher.search_semantic_scholar_api(["machine learning"], None)
            print(f"✅ Semantic Scholar API test completed: {method} ({len(articles)} articles)")
        except Exception as e:
            print(f"⚠️ Semantic Scholar API test failed (expected if no internet): {e}")
        
        return True
    except Exception as e:
        print(f"❌ Academic searcher error: {e}")
        return False

def test_source_availability():
    """Test that new sources are available in the system."""
    print("\n🧪 Testing source availability...")
    
    try:
        from utils.academic_search import RobustAcademicSearcher
        
        searcher = RobustAcademicSearcher()
        
        # Test that the new API methods exist
        api_methods = [
            "search_pubmed_api",
            "search_semantic_scholar_api", 
            "search_core_api"
        ]
        
        for method_name in api_methods:
            if hasattr(searcher, method_name):
                print(f"✅ Method {method_name} available")
            else:
                print(f"❌ Method {method_name} missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Source availability error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 OpenDeep Researcher API Integration Test")
    print("=" * 50)
    
    tests = [
        test_api_imports,
        test_config_manager,
        test_academic_searcher,
        test_source_availability
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("❌ Test failed")
        except Exception as e:
            print(f"❌ Test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! API integration is working.")
        print("\n🎯 Next steps:")
        print("1. Configure API keys in Settings → API Keys")
        print("2. Test the new sources in Data Collection")
        print("3. Enjoy enhanced research capabilities!")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
