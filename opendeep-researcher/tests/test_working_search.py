#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.academic_search import RobustAcademicSearcher

class TestLogger:
    def info(self, msg):
        print(f"INFO: {msg}")
    def success(self, msg):
        print(f"SUCCESS: {msg}")
    def error(self, msg):
        print(f"ERROR: {msg}")
    def warning(self, msg):
        print(f"WARNING: {msg}")

def test_working_search():
    """Test with simpler, known working queries"""
    
    print('🔍 Testing arXiv API with Simple Queries')
    print('========================================')

    searcher = RobustAcademicSearcher()
    logger = TestLogger()

    # Test 1: Simple keywords that should return results
    print("🧪 Test 1: Simple keyword search...")
    simple_keywords = ['optimization', 'machine learning']
    
    try:
        results = searcher.search_arxiv_api(simple_keywords, logger)
        print(f"✅ Found {len(results)} articles with simple keywords")
        
        if results:
            article = results[0]
            print(f"\\n📄 Sample Article:")
            print(f"  Title: {article.get('title', 'Unknown')}")
            print(f"  Authors: {article.get('authors', 'Unknown')}")
            print(f"  PDF URL: {article.get('pdf_url', 'Not available')}")
            
            # Check PDF URL format
            pdf_url = article.get('pdf_url', '')
            if pdf_url:
                print(f"✅ PDF URL format: {pdf_url}")
                if 'arxiv.org/pdf/' in pdf_url:
                    print("✅ PDF URL is in correct arXiv format")
                else:
                    print("⚠️ PDF URL format unexpected")
            else:
                print("❌ No PDF URL found")
        
    except Exception as e:
        print(f"❌ Simple search failed: {e}")
    
    print("\\n" + "="*50)
    
    # Test 2: Integration with comprehensive search strategy
    print("🧪 Test 2: Comprehensive search strategy...")
    
    try:
        # Test search_single_source method (used by data collection)
        source_results = searcher.search_single_source(
            keywords=simple_keywords,
            source="arXiv API",
            logger=logger
        )
        
        print(f"✅ search_single_source found {len(source_results)} articles")
        
        if source_results:
            article = source_results[0]
            print(f"  Source field: {article.get('source', 'Unknown')}")
            print(f"  Has PDF URL: {'Yes' if article.get('pdf_url') else 'No'}")
            
        # Test with search terms
        results_with_terms, method = searcher.search_single_source_with_terms(
            search_terms=simple_keywords,
            source="arXiv API",
            logger=logger
        )
        
        print(f"✅ search_single_source_with_terms found {len(results_with_terms)} articles")
        print(f"  Method used: {method}")
        
    except Exception as e:
        print(f"❌ Comprehensive search failed: {e}")
    
    print("\\n" + "="*50)
    
    # Test 3: Data structure validation
    print("🧪 Test 3: Data structure validation...")
    
    if results:
        article = results[0]
        required_fields = ['title', 'authors', 'abstract', 'url', 'year', 'source']
        optional_fields = ['pdf_url', 'doi', 'categories', 'arxiv_id']
        
        print("📋 Required fields:")
        for field in required_fields:
            value = article.get(field, 'MISSING')
            status = "✅" if value != 'MISSING' and value else "❌"
            print(f"  {status} {field}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
        
        print("📋 Optional fields:")
        for field in optional_fields:
            value = article.get(field, 'Not set')
            status = "✅" if value != 'Not set' and value else "⚪"
            print(f"  {status} {field}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
    
    print(f"\\n🎉 arXiv API comprehensive integration test complete!")

if __name__ == "__main__":
    test_working_search()
