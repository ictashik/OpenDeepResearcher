#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.academic_search import RobustAcademicSearcher
from utils.config_manager import ConfigManager

print('🔍 Final arXiv API Integration Test')
print('========================================')

# Create searcher
config_manager = ConfigManager()
searcher = RobustAcademicSearcher(config_manager, None)

# Test the complete integration
keywords = ['machine learning', 'neural networks']
results = searcher.search_arxiv_api(keywords)

print(f'✅ Found {len(results)} articles from arXiv API')

# Show first few results
for i, article in enumerate(results[:3]):
    print(f'\\n📄 Article {i+1}:')
    print(f'  Title: {article.get("title", "Unknown")}')
    print(f'  Authors: {article.get("authors", "Unknown")}')
    print(f'  Year: {article.get("year", "Unknown")}')
    print(f'  Categories: {article.get("categories", "Unknown")}')
    
print(f'\\n🎉 arXiv API integration complete!')

if __name__ == "__main__":
    pass
