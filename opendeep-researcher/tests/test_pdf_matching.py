#!/usr/bin/env python3
"""
Test the new PDF number-based matching strategy
"""

import re

def test_pdf_number_matching():
    # Sample PDF filenames and article indices
    test_cases = [
        ("12_Graphs where Search Methods are Indistinguishable.pdf", 11),  # Should match (12 -> index 11)
        ("1_Search for Neutral MSSM Higgs Bosons at LEP.pdf", 0),        # Should match (1 -> index 0)
        ("99_Some Article.pdf", 98),                                      # Should match (99 -> index 98)
        ("67_Construction of Hierarchical Neural Architecture.pdf", 66),  # Should match (67 -> index 66)
        ("no_number_article.pdf", 5),                                     # Should not match
    ]
    
    print("=== PDF NUMBER MATCHING TEST ===")
    
    for pdf_name, article_idx in test_cases:
        print(f"\n📄 PDF: {pdf_name}")
        print(f"📋 Article Index: {article_idx}")
        
        # Extract number from PDF filename
        pdf_number_match = re.match(r'^(\d+)_', pdf_name)
        
        if pdf_number_match:
            pdf_number = int(pdf_number_match.group(1))
            print(f"🔢 PDF Number: {pdf_number}")
            
            # Check if matches (PDF numbers are 1-based, indices are 0-based)
            if pdf_number == article_idx + 1:
                print(f"✅ MATCH! PDF number {pdf_number} matches article index {article_idx} (position {article_idx + 1})")
                confidence = 98
            else:
                print(f"❌ No match. PDF number {pdf_number} != article position {article_idx + 1}")
                confidence = 0
        else:
            print(f"❌ No number prefix found")
            confidence = 0
        
        print(f"📊 Confidence: {confidence}%")

if __name__ == "__main__":
    test_pdf_number_matching()
