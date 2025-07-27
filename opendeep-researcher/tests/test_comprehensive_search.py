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

def test_comprehensive_search():
    """Test the comprehensive search strategy with arXiv API"""
    
    print('🔍 Testing Comprehensive Search Strategy with arXiv API')
    print('========================================')

    # Create searcher
    searcher = RobustAcademicSearcher()
    logger = TestLogger()

    # Test the comprehensive search strategy
    keywords = ['machine learning', 'neural networks', 'artificial intelligence']
    research_question = "How do neural networks improve machine learning performance in artificial intelligence applications?"
    
    print(f"📋 Keywords: {keywords}")
    print(f"🎯 Research Question: {research_question}")
    print()
    
    # Test 1: Prepare search terms
    print("🔧 Testing search term preparation...")
    search_terms_sets = searcher.prepare_search_terms(keywords, research_question, logger)
    
    for i, term_set in enumerate(search_terms_sets):
        print(f"  {i+1}. {term_set['description']}: {term_set['terms'][:5]}{'...' if len(term_set['terms']) > 5 else ''}")
    
    print()
    
    # Test 2: Test arXiv API with comprehensive search strategy
    print("🚀 Testing arXiv API with comprehensive search strategy...")
    
    try:
        # Test the single source search with terms method
        results, method = searcher.search_single_source_with_terms(
            search_terms_sets[0]['terms'], 
            "arXiv API", 
            logger
        )
        
        print(f"✅ Found {len(results)} articles using method: {method}")
        
        if results:
            article = results[0]
            print(f"\\n📄 Sample Article:")
            print(f"  Title: {article.get('title', 'Unknown')}")
            print(f"  Authors: {article.get('authors', 'Unknown')}")
            print(f"  Year: {article.get('year', 'Unknown')}")
            print(f"  Categories: {article.get('categories', 'Unknown')}")
            print(f"  PDF URL: {article.get('pdf_url', 'Not available')}")
            print(f"  Abstract URL: {article.get('url', 'Not available')}")
            
            # Check if PDF URL is properly stored
            if article.get('pdf_url'):
                print(f"✅ PDF URL properly stored: {article['pdf_url'][:50]}...")
            else:
                print(f"❌ PDF URL not found")
        
        print()
        
        # Test 3: Test research question-based search
        print("🎯 Testing research question-based search...")
        rq_results = searcher.search_single_source_with_research_question(
            keywords, 
            "arXiv API", 
            research_question, 
            logger
        )
        
        print(f"✅ Found {len(rq_results)} articles using research question method")
        
        if rq_results:
            article = rq_results[0]
            search_method = article.get('search_method', 'Unknown')
            print(f"  Search method used: {search_method}")
            
            if 'research_question' in search_method:
                print("✅ Successfully used research question for search")
            else:
                print("⚠️ Fell back to keyword search")
        
        print()
        
        # Test 4: Compare results
        print("📊 Comparing search strategies...")
        print(f"  Direct keyword search: {len(results)} articles")
        print(f"  Research question search: {len(rq_results)} articles")
        
        # Check for duplicates
        if results and rq_results:
            result_titles = set(article.get('title', '') for article in results)
            rq_titles = set(article.get('title', '') for article in rq_results)
            overlap = len(result_titles.intersection(rq_titles))
            print(f"  Overlap between methods: {overlap} articles")
        
    except Exception as e:
        print(f"❌ Error in comprehensive search test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comprehensive_search()
