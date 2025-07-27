#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.academic_search import RobustAcademicSearcher
from utils.config_manager import ConfigManager

def test_author_parsing():
    """Test arXiv author parsing specifically"""
    
    # Create searcher
    config_manager = ConfigManager()
    searcher = RobustAcademicSearcher(config_manager, None)
    
    # Run search for a specific query
    keywords = ["optimization", "machine learning"]
    results = searcher.search_arxiv_api(keywords)
    
    if results:
        article = results[0]
        print(f"🔍 Testing Author Parsing")
        print(f"========================================")
        print(f"Title: {article.get('title', 'Unknown')}")
        print(f"Authors: {article.get('authors', 'Unknown')}")
        print(f"URL: {article.get('url', 'Unknown')}")
        
        if article.get('authors') != 'Unknown':
            print("✅ Author parsing successful!")
        else:
            print("❌ Author parsing failed!")
    else:
        print("❌ No results returned")

if __name__ == "__main__":
    test_author_parsing()
