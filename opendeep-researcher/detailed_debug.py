#!/usr/bin/env python3
"""
More detailed debug of arXiv API XML parsing
"""

import requests
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

def detailed_debug():
    """Debug XML parsing in detail"""
    print("🔍 Detailed arXiv XML Debug")
    print("=" * 40)
    
    # Simple test query
    search_query = 'all:"machine learning"'
    base_url = "http://export.arxiv.org/api/query"
    
    params = {
        'search_query': search_query,
        'start': 0,
        'max_results': 1
    }
    
    # Build URL with parameters
    param_string = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
    url = f"{base_url}?{param_string}"
    
    try:
        headers = {
            'User-Agent': 'OpenDeepResearcher/1.0 (test)'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("Full XML Response:")
            print("-" * 60)
            print(response.text)
            print("-" * 60)
            
            # Try manual parsing step by step
            try:
                root = ET.fromstring(response.text)
                print(f"✅ Root element: {root.tag}")
                print(f"✅ Root namespace: {root.tag.split('}')[0] if '}' in root.tag else 'None'}")
                
                # Find all elements
                all_elements = list(root.iter())
                print(f"✅ Total elements found: {len(all_elements)}")
                
                # Look for entries
                entries = root.findall('.//entry')
                print(f"✅ Entries without namespace: {len(entries)}")
                
                # Define namespaces
                namespaces = {
                    'atom': 'http://www.w3.org/2005/Atom',
                    'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
                    'arxiv': 'http://arxiv.org/schemas/atom'
                }
                
                entries_ns = root.findall('.//atom:entry', namespaces)
                print(f"✅ Entries with atom namespace: {len(entries_ns)}")
                
                # Get total results
                total_elem = root.find('.//opensearch:totalResults', namespaces)
                if total_elem is not None:
                    print(f"✅ Total results: {total_elem.text}")
                
                # Analyze first entry
                if entries:
                    first_entry = entries[0]
                    print(f"\n📄 First Entry Analysis:")
                    print(f"  Tag: {first_entry.tag}")
                    
                    # Get children
                    children = list(first_entry)
                    print(f"  Children: {len(children)}")
                    for child in children:
                        print(f"    - {child.tag}: {child.text[:50] if child.text else 'None'}...")
                
            except Exception as e:
                print(f"❌ XML parsing failed: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    detailed_debug()
