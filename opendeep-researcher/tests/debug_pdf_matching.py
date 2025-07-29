#!/usr/bin/env python3
"""
Debug script to help diagnose PDF matching issues in OpenDeepResearcher
"""

import sys
import pandas as pd
from pathlib import Path

# Project ID - you can change this if needed
PROJECT_ID = "65de9413"

print("🔍 PDF Matching Diagnostic Tool")
print("=" * 50)

try:
    # Try direct file loading first
    project_dir = Path(f"data/{PROJECT_ID}")
    print(f"📁 Project directory: {project_dir}")
    
    # Check if files exist
    screened_file = project_dir / "articles_screened.csv"
    raw_file = project_dir / "articles_raw.csv"
    
    print(f"📄 Checking files:")
    print(f"  - articles_screened.csv: {'✅ exists' if screened_file.exists() else '❌ missing'}")
    print(f"  - articles_raw.csv: {'✅ exists' if raw_file.exists() else '❌ missing'}")
    
    # Load articles directly
    if screened_file.exists():
        articles_df = pd.read_csv(screened_file)
        print(f"✅ Loaded {len(articles_df)} articles from screened file")
    elif raw_file.exists():
        articles_df = pd.read_csv(raw_file)
        print(f"✅ Loaded {len(articles_df)} articles from raw file")
    else:
        print("❌ No article files found")
        sys.exit(1)
    
    print(f"✅ Found {len(articles_df)} total articles")
    
    # Filter for included articles
    if 'final_decision' in articles_df.columns:
        included_articles = articles_df[articles_df['final_decision'] == 'Include']
        print(f"✅ Found {len(included_articles)} included articles")
    else:
        included_articles = articles_df
        print(f"⚠️ No 'final_decision' column found, using all articles")
    
    # Check uploads directory
    uploads_dir = project_dir / "uploads"
    
    print(f"\n📁 Checking uploads directory: {uploads_dir}")
    
    if not uploads_dir.exists():
        print("❌ Uploads directory does not exist")
        sys.exit(1)
    
    existing_pdfs = list(uploads_dir.glob("*.pdf"))
    print(f"✅ Found {len(existing_pdfs)} PDF files")
    
    # Show sample PDF filenames
    print(f"\n📄 Sample PDF files (first 10):")
    for i, pdf in enumerate(existing_pdfs[:10]):
        print(f"  {i+1}. {pdf.name}")
    
    if len(existing_pdfs) > 10:
        print(f"  ... and {len(existing_pdfs) - 10} more files")
    
    # Check current PDF status
    print(f"\n📊 Current PDF Status:")
    if 'full_text_status' in included_articles.columns:
        status_counts = included_articles['full_text_status'].value_counts()
        for status, count in status_counts.items():
            print(f"  {status}: {count} articles")
    else:
        print("  ❌ No 'full_text_status' column found")
    
    # Show sample article titles and IDs
    print(f"\n📝 Sample Articles (first 5):")
    import hashlib
    
    def get_safe_article_id(article, idx):
        try:
            if hasattr(article, 'index') and 'id' in article.index and pd.notna(article.get('id')):
                return str(article['id'])
            elif hasattr(article, 'index') and 'title' in article.index and article.get('title'):
                title_hash = hashlib.md5(str(article.get('title', f'untitled_{idx}')).encode()).hexdigest()[:8]
                return f"article_{title_hash}"
            else:
                return f"article_{idx}"
        except Exception:
            return f"article_{idx}"
    
    for idx, (_, article) in enumerate(included_articles.head(5).iterrows()):
        article_id = get_safe_article_id(article, idx)
        title = article.get('title', 'Unknown')[:60]
        authors = article.get('authors', 'Unknown')[:30]
        year = article.get('year', 'Unknown')
        
        print(f"  {idx+1}. ID: {article_id}")
        print(f"     Title: {title}...")
        print(f"     Authors: {authors}...")
        print(f"     Year: {year}")
        print()
    
    # Try to match some PDFs manually
    print(f"\n🎯 Manual Matching Test:")
    print("Trying to match first few PDFs to articles...")
    
    import re
    
    for pdf_idx, pdf_path in enumerate(existing_pdfs[:5]):
        print(f"\n📄 PDF: {pdf_path.name}")
        pdf_stem = pdf_path.stem.lower()
        
        # Look for potential matches
        potential_matches = []
        
        for art_idx, (_, article) in enumerate(included_articles.head(10).iterrows()):
            article_id = get_safe_article_id(article, art_idx)
            title = str(article.get('title', '')).lower()
            authors = str(article.get('authors', '')).lower()
            year = str(article.get('year', ''))
            
            match_reasons = []
            
            # Check article ID match
            if str(article_id).lower() in pdf_stem:
                match_reasons.append(f"ID match ({article_id})")
            
            # Check title words
            if title and len(title) > 10:
                title_words = [w for w in title.split() if len(w) > 3]
                matches_found = sum(1 for word in title_words[:5] if word in pdf_stem)
                if matches_found > 0:
                    match_reasons.append(f"Title words ({matches_found}/{min(5, len(title_words))})")
            
            # Check author + year
            if authors and year:
                first_author = authors.split(',')[0].split(';')[0].strip()
                if first_author and len(first_author) > 2:
                    author_lastname = first_author.split()[-1] if ' ' in first_author else first_author
                    if len(author_lastname) > 3 and author_lastname.lower() in pdf_stem and year in pdf_stem:
                        match_reasons.append(f"Author+Year ({author_lastname}_{year})")
            
            # Check numbers
            pdf_numbers = re.findall(r'\d+', pdf_stem)
            for num_str in pdf_numbers:
                num = int(num_str)
                if num == art_idx + 1 or num == art_idx:
                    match_reasons.append(f"Sequential ({num})")
                    break
            
            if match_reasons:
                potential_matches.append((article, match_reasons))
        
        if potential_matches:
            print(f"  🎯 Potential matches found:")
            for article, reasons in potential_matches[:3]:  # Top 3 matches
                print(f"    - {article.get('title', 'Unknown')[:40]}... | Reasons: {', '.join(reasons)}")
        else:
            print(f"  ❌ No obvious matches found")
    
    print(f"\n🔧 Recommendations:")
    
    if len(existing_pdfs) > len(included_articles):
        print(f"  • You have {len(existing_pdfs)} PDFs but only {len(included_articles)} articles")
        print(f"    Consider removing extra PDFs or checking if all articles are included")
    
    current_matched = len(included_articles[included_articles.get('full_text_status', '') == 'Acquired'])
    unmatched_pdfs = len(existing_pdfs) - current_matched
    
    if unmatched_pdfs > 0:
        print(f"  • {unmatched_pdfs} PDFs appear unmatched")
        print(f"    Try using the enhanced 'Scan for Existing PDFs' button in the app")
        print(f"    Check the 'PDF Matching Diagnostics' section for more details")
    
    print(f"\n✅ Diagnostic complete!")
    print(f"Next steps:")
    print(f"1. Go to the Document Management tab in your app")
    print(f"2. Click 'PDF Matching Diagnostics' to see this info in the app")
    print(f"3. Click 'Scan for Existing PDFs' to run the enhanced matching")

except Exception as e:
    print(f"❌ Error running diagnostic: {e}")
    import traceback
    traceback.print_exc()
