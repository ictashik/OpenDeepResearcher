#!/usr/bin/env python3
"""
Test just the XML parsing part using the actual parser
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.academic_search import RobustAcademicSearcher

class TestLogger:
    def info(self, message):
        print(f"INFO: {message}")
    def success(self, message):
        print(f"SUCCESS: {message}")
    def warning(self, message):
        print(f"WARNING: {message}")
    def error(self, message):
        print(f"ERROR: {message}")

def test_xml_parsing():
    """Test XML parsing with real arXiv response using actual parser"""
    
    # This is the actual XML response from arXiv API
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <link href="http://arxiv.org/api/query?search_query%3Dall%3A%22machine%20learning%22%26id_list%3D%26start%3D0%26max_results%3D1" rel="self" type="application/atom+xml"/>
  <title type="html">ArXiv Query: search_query=all:"machine learning"&amp;id_list=&amp;start=0&amp;max_results=1</title>
  <id>http://arxiv.org/api/wpjNCRoEPsLisogb8venjS+VcEM</id>
  <updated>2025-07-27T00:00:00-04:00</updated>
  <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">272438</opensearch:totalResults>
  <opensearch:startIndex xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:startIndex>
  <opensearch:itemsPerPage xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/1909.03550v1</id>
    <updated>2019-09-08T21:49:42Z</updated>
    <published>2019-09-08T21:49:42Z</published>
    <title>Lecture Notes: Optimization for Machine Learning</title>
    <summary>  Lecture notes on optimization for machine learning, derived from a course at
Princeton University and tutorials given in MLSS, Buenos Aires, as well as
Simons Foundation, Berkeley.
</summary>
    <author>
      <n>Elad Hazan</n>
    </author>
    <link href="http://arxiv.org/abs/1909.03550v1" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1909.03550v1" rel="related" type="application/pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
    <category term="stat.ML" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>'''

    print("🔍 Testing arXiv XML Parser")
    print("=" * 40)
    
    searcher = RobustAcademicSearcher()
    logger = TestLogger()
    
    # Test the actual parser
    articles = searcher._parse_arxiv_atom_feed(xml_content, logger)
    
    print(f"✅ Parser returned {len(articles)} articles")
    
    if articles:
        article = articles[0]
        print("\n📄 Parsed Article:")
        for key, value in article.items():
            print(f"  {key}: {value}")
    else:
        print("❌ No articles parsed")

if __name__ == "__main__":
    test_xml_parsing()
