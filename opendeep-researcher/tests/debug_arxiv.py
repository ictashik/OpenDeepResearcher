#!/usr/bin/env python3
"""
Debug arXiv API response
"""

import requests
from urllib.parse import quote_plus

def debug_arxiv_api():
    """Debug the arXiv API response"""
    print("🔍 Testing arXiv API Response")
    print("=" * 40)
    
    # Simple test query
    search_query = 'all:"machine learning"'
    base_url = "http://export.arxiv.org/api/query"
    
    params = {
        'search_query': search_query,
        'start': 0,
        'max_results': 2,
        'sortBy': 'relevance',
        'sortOrder': 'descending'
    }
    
    # Build URL with parameters
    param_string = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
    url = f"{base_url}?{param_string}"
    
    print(f"URL: {url}")
    print()
    
    try:
        headers = {
            'User-Agent': 'OpenDeepResearcher/1.0 (systematic-review-tool; test@example.com)'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type', 'Unknown')}")
        print()
        
        if response.status_code == 200:
            print("Raw Response (first 1000 chars):")
            print("-" * 40)
            print(response.text[:1000])
            print("-" * 40)
            
            # Try to parse XML
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(response.text)
                print("✅ XML parsing successful!")
                
                # Check for entries
                namespaces = {
                    'atom': 'http://www.w3.org/2005/Atom',
                    'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'
                }
                
                total_results = root.find('.//opensearch:totalResults', namespaces)
                if total_results is not None:
                    print(f"Total results: {total_results.text}")
                
                entries = root.findall('.//atom:entry', namespaces)
                print(f"Number of entries: {len(entries)}")
                
                if entries:
                    first_entry = entries[0]
                    title_elem = first_entry.find('atom:title', namespaces)
                    if title_elem is not None:
                        print(f"First article title: {title_elem.text[:100]}...")
                
            except Exception as e:
                print(f"❌ XML parsing failed: {e}")
                print("Raw content:")
                print(response.text[:500])
        
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    debug_arxiv_api()
