#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def test_direct_parsing():
    """Test the XML parsing directly"""
    
    print("🔍 Testing Direct arXiv XML Parsing")
    print("========================================")
    
    # Get data directly from arXiv
    query = urllib.parse.quote_plus('optimization machine learning')
    url = f'http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=1'
    
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
        
        # Parse XML
        root = ET.fromstring(content)
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        # Find entries
        entries = root.findall('atom:entry', namespaces)
        print(f"Found {len(entries)} entries")
        
        for entry in entries:
            # Title
            title_elem = entry.find('atom:title', namespaces)
            title = title_elem.text.strip() if title_elem is not None else 'Unknown'
            
            # Authors - let's test our parsing logic
            print(f"\\nTitle: {title}")
            
            # Test author parsing logic from our implementation
            try:
                author_elems = entry.findall('atom:author', namespaces)
                if not author_elems:
                    author_elems = entry.findall('author')
                
                print(f"Found {len(author_elems)} author elements")
                
                authors = []
                for i, author_elem in enumerate(author_elems):
                    print(f"  Processing author {i+1}:")
                    print(f"    XML: {ET.tostring(author_elem, encoding='unicode')}")
                    
                    # Try different possible name elements
                    name_elem = None
                    
                    # Check for standard 'name' element with namespace
                    name_elem = author_elem.find('atom:name', namespaces)
                    print(f"    atom:name result: {name_elem.text if name_elem is not None else 'None'}")
                    
                    # Check for standard 'name' element without namespace
                    if name_elem is None:
                        name_elem = author_elem.find('name')
                        print(f"    name result: {name_elem.text if name_elem is not None else 'None'}")
                    
                    # Check for arXiv's 'n' element (shortened name)
                    if name_elem is None:
                        name_elem = author_elem.find('n')
                        print(f"    n result: {name_elem.text if name_elem is not None else 'None'}")
                        
                    if name_elem is not None and name_elem.text:
                        author_name = name_elem.text.strip()
                        authors.append(author_name)
                        print(f"    ✅ Found author: {author_name}")
                    else:
                        print(f"    ❌ No name found for this author")
                
                final_authors = ', '.join(authors) if authors else 'Unknown'
                print(f"\\n📝 Final authors: {final_authors}")
                
            except Exception as e:
                print(f"❌ Error parsing authors: {e}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        print(f"❌ Error in direct parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_parsing()
