#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import urllib.request
import urllib.parse

def test_arxiv_atom_feed_parser():
    """Test the _parse_arxiv_atom_feed method directly"""
    
    from utils.academic_search import RobustAcademicSearcher
    from utils.config_manager import ConfigManager
    
    print("🔍 Testing _parse_arxiv_atom_feed Method")
    print("========================================")
    
    # Create searcher
    config_manager = ConfigManager()
    searcher = RobustAcademicSearcher(config_manager, None)
    
    # Get XML content directly
    query = urllib.parse.quote_plus('optimization machine learning')
    url = f'http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=1'
    
    try:
        with urllib.request.urlopen(url) as response:
            xml_content = response.read().decode('utf-8')
        
        print(f"✅ Got XML content ({len(xml_content)} chars)")
        
        # Test our parser
        articles = searcher._parse_arxiv_atom_feed(xml_content)
        
        print(f"✅ Parser returned {len(articles)} articles")
        
        if articles:
            article = articles[0]
            print(f"\\n📄 Parsed Article:")
            for key, value in article.items():
                print(f"  {key}: {value}")
        else:
            print("❌ No articles were parsed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_arxiv_atom_feed_parser()
