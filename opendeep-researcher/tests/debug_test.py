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

def test_with_debugging():
    print('🔍 arXiv API Test with Debugging')
    print('========================================')

    # Create searcher
    searcher = RobustAcademicSearcher()
    
    # Create a logger for debugging
    logger = TestLogger()

    # Test the complete integration
    keywords = ['machine learning']
    
    try:
        print(f"Calling search_arxiv_api with keywords: {keywords}")
        results = searcher.search_arxiv_api(keywords, logger=logger)
        
        print(f'✅ Found {len(results)} articles from arXiv API')
        
        if results:
            article = results[0]
            print(f'\\n📄 First Article:')
            print(f'  Title: {article.get("title", "Unknown")}')
            print(f'  Authors: {article.get("authors", "Unknown")}')
            print(f'  URL: {article.get("url", "Unknown")}')
        else:
            print("❌ No results returned")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_debugging()
