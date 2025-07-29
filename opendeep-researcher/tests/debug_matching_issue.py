#!/usr/bin/env python3
"""
Debug script to understand why only 9 PDFs are being matched instead of more.
This will show us exactly what's happening in the matching process.
"""

import pandas as pd
import hashlib
import re
from pathlib import Path

# Add the project to Python path
import sys
sys.path.append('/Users/deepthysaji/Documents/GitHub/OpenDeepResearcher/opendeep-researcher')

from src.utils.data_manager import load_screened_articles, get_project_dir

def get_safe_article_id(article, idx):
    """Get article ID with graceful fallback."""
    try:
        # Try to get ID from article if column exists
        if hasattr(article, 'index') and 'id' in article.index and pd.notna(article.get('id')):
            return str(article['id'])
        # Fallback to title-based ID
        elif hasattr(article, 'index') and 'title' in article.index and article.get('title'):
            # Create a simple hash-based ID from title
            title_hash = hashlib.md5(str(article.get('title', f'untitled_{idx}')).encode()).hexdigest()[:8]
            return f"article_{title_hash}"
        # Final fallback to index
        else:
            return f"article_{idx}"
    except Exception:
        # Ultimate fallback
        return f"article_{idx}"

def try_match_pdf_to_article(pdf_path, articles):
    """Try multiple strategies to match PDF to articles."""
    pdf_name = pdf_path.name.lower()
    pdf_stem = pdf_path.stem.lower()  # filename without extension
    
    matches = []
    
    for idx, (_, article) in enumerate(articles.iterrows()):
        article_id = get_safe_article_id(article, idx)
        title = str(article.get('title', '')).lower()
        authors = str(article.get('authors', '')).lower()
        year = str(article.get('year', ''))
        
        # Strategy 1: Exact article ID match
        if str(article_id).lower() in pdf_name:
            matches.append((article, idx, 'article_id', 95))
            continue
        
        # Strategy 1.5: Special handling for search-related content
        # Since all your articles are about "search", give bonus points for search-related PDFs
        if 'search' in pdf_stem and 'search' in title:
            search_bonus = 20
        else:
            search_bonus = 0
        
        # Strategy 2: Very gentle title matching - focus on first few words
        if title and len(title) > 5:
            # Get first 3-5 words from title (much more gentle approach)
            title_words = title.split()[:5]  # Just first 5 words
            title_words = [w.lower() for w in title_words if len(w) > 2]  # Shorter words allowed
            
            if len(title_words) >= 1:  # Even 1 word match is OK
                # Count how many of these first words appear in PDF name
                matches_found = sum(1 for word in title_words if word in pdf_stem)
                
                if matches_found >= 1:  # Just need 1 word from first few words
                    # Very generous confidence scoring
                    base_confidence = 40 + (matches_found * 15)  # Start higher
                    confidence = min(95, base_confidence + search_bonus)
                    matches.append((article, idx, f'first_words({matches_found}/{len(title_words)})', confidence))
        
        # Strategy 2.5: Even gentler - any significant word match
        if title and len(title) > 10:
            # Extract ANY significant words from title (>2 chars, not common words)
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'under', 'within', 'without', 'against', 'toward', 'upon', 'concerning', 'per', 'an', 'a', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can'}
            title_words = [w for w in title.split() if len(w) > 2 and w not in stop_words]
            
            if len(title_words) >= 1:
                # Count how many title words appear in PDF name
                matches_found = sum(1 for word in title_words if word in pdf_stem)
                
                if matches_found >= 1:  # Just need ANY word match
                    match_ratio = matches_found / len(title_words)
                    confidence = min(85, 30 + (match_ratio * 30) + (matches_found * 5) + search_bonus)
                    matches.append((article, idx, f'any_words({matches_found}/{len(title_words)})', confidence))
        
        # Strategy 3: Author lastname + year combination
        if authors and year:
            # Extract first author's last name
            first_author = authors.split(',')[0].split(';')[0].strip()
            if first_author and len(first_author) > 2:
                author_lastname = first_author.split()[-1] if ' ' in first_author else first_author
                
                if len(author_lastname) > 3 and author_lastname.lower() in pdf_stem and year in pdf_stem:
                    matches.append((article, idx, f'author_year({author_lastname}_{year})', 80))
        
        # Strategy 4: Sequential numbering (if PDF name contains numbers that might correspond to article order)
        # Extract numbers from PDF filename
        pdf_numbers = re.findall(r'\d+', pdf_stem)
        if pdf_numbers:
            # Check if any number matches the article index (1-based or 0-based)
            for num_str in pdf_numbers:
                num = int(num_str)
                if num == idx + 1 or num == idx:  # 1-based or 0-based indexing
                    matches.append((article, idx, f'index_number({num})', 50))
                    break
    
    # Return the best match (highest confidence)
    if matches:
        return max(matches, key=lambda x: x[3])
    return None

def main():
    print("=== PDF MATCHING DIAGNOSTIC ===")
    print()
    
    # Get project ID - using the one that has screened articles
    project_id = "65de9413"
    
    print(f"🔍 Analyzing project: {project_id}")
    
    # Load articles directly from the file path since data_manager might be using wrong paths
    try:
        project_dir = Path(f"/Users/deepthysaji/Documents/GitHub/OpenDeepResearcher/data/{project_id}")
        articles_file = project_dir / "articles_screened.csv"
        
        if articles_file.exists():
            articles_df = pd.read_csv(articles_file)
            print(f"📊 Total articles loaded: {len(articles_df)}")
        else:
            print(f"❌ Articles file not found: {articles_file}")
            return
        
        # Filter for included articles only
        if 'final_decision' in articles_df.columns:
            included_articles = articles_df[articles_df['final_decision'] == 'Include']
        else:
            included_articles = articles_df
        
        print(f"📋 Included articles: {len(included_articles)}")
        
        # Check existing status
        if 'full_text_status' in included_articles.columns:
            status_counts = included_articles['full_text_status'].value_counts()
            print("📈 Current status distribution:")
            for status, count in status_counts.items():
                print(f"   • {status}: {count}")
        else:
            print("⚠️ No full_text_status column found")
        
    except Exception as e:
        print(f"❌ Error loading articles: {e}")
        return
    
    # Load PDFs
    try:
        uploads_dir = project_dir / "uploads"
        existing_pdfs = list(uploads_dir.glob("*.pdf"))
        print(f"📁 PDF files found: {len(existing_pdfs)}")
    except Exception as e:
        print(f"❌ Error loading PDFs: {e}")
        return
    
    print("\n=== DETAILED MATCHING ANALYSIS ===")
    
    # Track all matches
    all_matches = []
    articles_already_assigned = 0
    
    for i, pdf_path in enumerate(existing_pdfs):
        print(f"\n📄 PDF {i+1}/{len(existing_pdfs)}: {pdf_path.name}")
        
        # Try to find a match
        match_result = try_match_pdf_to_article(pdf_path, included_articles)
        
        if match_result:
            article, idx, match_type, confidence = match_result
            title = article.get('title', 'Unknown')[:60]
            
            # Check if this article already has a PDF assigned
            current_status = article.get('full_text_status', 'Awaiting')
            
            print(f"   🎯 Best match: {title}...")
            print(f"   📊 Confidence: {confidence:.1f}% (via {match_type})")
            print(f"   📋 Current status: {current_status}")
            
            if current_status == 'Acquired':
                print(f"   ⚠️ Already assigned!")
                articles_already_assigned += 1
            elif confidence >= 40:
                print(f"   ✅ Would auto-match (≥40% confidence)")
                all_matches.append({
                    'pdf': pdf_path.name,
                    'article_title': title,
                    'confidence': confidence,
                    'match_type': match_type,
                    'current_status': current_status
                })
            else:
                print(f"   ❌ Too low confidence (<40%)")
        else:
            print(f"   ❌ No match found")
    
    print(f"\n=== SUMMARY ===")
    print(f"📊 Total PDFs: {len(existing_pdfs)}")
    print(f"🎯 PDFs that would auto-match: {len(all_matches)}")
    print(f"📝 Articles already assigned: {articles_already_assigned}")
    print(f"❌ PDFs with no matches: {len(existing_pdfs) - len(all_matches) - articles_already_assigned}")
    
    if all_matches:
        print(f"\n=== MATCHES THAT SHOULD BE ASSIGNED ===")
        for i, match in enumerate(all_matches[:20], 1):  # Show first 20
            print(f"{i:2d}. {match['pdf'][:40]:<40} → {match['article_title'][:40]:<40} ({match['confidence']:.0f}%)")
        
        if len(all_matches) > 20:
            print(f"... and {len(all_matches) - 20} more matches")
    
    # Check if there are duplicate assignments
    assigned_titles = [match['article_title'] for match in all_matches]
    duplicate_assignments = len(assigned_titles) - len(set(assigned_titles))
    
    if duplicate_assignments > 0:
        print(f"\n⚠️ WARNING: {duplicate_assignments} potential duplicate assignments detected!")
        
        # Show duplicates
        from collections import Counter
        title_counts = Counter(assigned_titles)
        duplicates = {title: count for title, count in title_counts.items() if count > 1}
        
        for title, count in duplicates.items():
            print(f"   📄 '{title[:50]}...' matched {count} times")

if __name__ == "__main__":
    main()
