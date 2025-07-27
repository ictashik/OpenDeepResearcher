#!/usr/bin/env python3
"""
Test script for arXiv API implementation
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.academic_search import RobustAcademicSearcher

class TestLogger:
    """Simple logger for testing"""
    def info(self, message):
        print(f"INFO: {message}")
    
    def success(self, message):
        print(f"SUCCESS: {message}")
    
    def warning(self, message):
        print(f"WARNING: {message}")
    
    def error(self, message):
        print(f"ERROR: {message}")

def test_arxiv_api():
    """Test the arXiv API implementation"""
    print("🧪 Testing arXiv API Implementation")
    print("=" * 50)
    
    # Initialize searcher
    searcher = RobustAcademicSearcher(max_results_per_source=5)
    logger = TestLogger()
    
    # Test keywords
    test_keywords = ["machine learning", "neural networks", "artificial intelligence"]
    
    print(f"🔍 Testing with keywords: {test_keywords}")
    print()
    
    # Test direct API call
    print("📡 Testing direct arXiv API call...")
    articles = searcher.search_arxiv_api(test_keywords, logger)
    
    if articles:
        print(f"✅ Found {len(articles)} articles!")
        print()
        
        # Display first article as example
        if len(articles) > 0:
            article = articles[0]
            print("📄 Sample Article:")
            print(f"  Title: {article.get('title', 'N/A')}")
            print(f"  Authors: {article.get('authors', 'N/A')}")
            print(f"  Year: {article.get('year', 'N/A')}")
            print(f"  Categories: {article.get('categories', 'N/A')}")
            print(f"  Abstract: {article.get('abstract', 'N/A')[:200]}...")
            print(f"  URL: {article.get('url', 'N/A')}")
            print(f"  PDF URL: {article.get('pdf_url', 'N/A')}")
            print()
    else:
        print("❌ No articles found")
        print()
    
    # Test through search_single_source
    print("🔄 Testing through search_single_source...")
    articles, method = searcher.search_single_source(test_keywords, "arXiv API", logger)
    
    if articles:
        print(f"✅ Found {len(articles)} articles using method: {method}")
    else:
        print(f"❌ No articles found using method: {method}")
    
    print()
    print("🧪 Test completed!")

if __name__ == "__main__":
    test_arxiv_api()
