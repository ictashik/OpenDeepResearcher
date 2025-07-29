import streamlit as st
import pandas as pd
import hashlib
import re
import time
from pathlib import Path
from src.utils.pdf_processor import PDFProcessor
from src.utils.data_manager import (
    load_screened_articles, 
    save_extracted_data, 
    get_project_dir, 
    save_screened_articles, 
    load_extracted_data
)
from src.utils.ollama_client import OllamaClient
from src.utils.data_manager import load_config

def show(logger):
    """Full-text analysis page."""
    st.subheader("Full-Text Analysis")

    # Initialize session state for extraction stats
    if 'extraction_stats' not in st.session_state:
        st.session_state.extraction_stats = {
            'total_articles': 0,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

    # Check if project is selected
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        st.warning("Please select a project from the Dashboard first.")
        return

    logger.info(f"Loading full-text analysis for project: {project_id}")

    # Load screened articles
    articles_df = load_screened_articles(project_id)
    
    if articles_df.empty:
        st.warning("No screened articles found. Please complete the screening phase first.")
        return

    # Initialize required columns for analysis
    required_columns = ['full_text_status', 'pdf_path']
    for col in required_columns:
        if col not in articles_df.columns:
            articles_df[col] = 'Awaiting' if col == 'full_text_status' else ""

    # Filter for included articles only
    try:
        if 'final_decision' in articles_df.columns:
            included_articles = articles_df[articles_df['final_decision'] == 'Include']
        else:
            included_articles = articles_df
    except Exception as e:
        st.error(f"Error filtering included articles: {str(e)}")
        logger.error(f"Article filtering error: {str(e)}")
        included_articles = articles_df  # Use all articles as fallback
    
    # Initialize full_text_status column if it doesn't exist (backup safety)
    if 'full_text_status' not in included_articles.columns:
        included_articles = included_articles.copy()
        included_articles['full_text_status'] = 'Awaiting'
    
    if included_articles.empty:
        st.warning("No articles were included during screening. Please review your screening results.")
        return

    st.success(f"Found {len(included_articles)} articles ready for full-text analysis")
    
    # Show status summary
    if 'full_text_status' in included_articles.columns:
        status_summary = included_articles['full_text_status'].value_counts()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            awaiting_count = status_summary.get('Awaiting', 0)
            st.metric("📝 Awaiting PDFs", awaiting_count)
        
        with col2:
            acquired_count = status_summary.get('Acquired', 0)
            st.metric("📄 PDFs Available", acquired_count)
        
        with col3:
            abstract_count = status_summary.get('Abstract Only', 0)
            st.metric("📄 Abstract Only", abstract_count)

    # Initialize PDF processor and Ollama client
    pdf_processor = PDFProcessor()
    ollama_client = OllamaClient()
    config = load_config()

    # Create tabs for different analysis phases
    tab1, tab2, tab3 = st.tabs(["Document Management", "AI Extraction", "Results Review"])
    
    # Helper function to safely get article ID
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

    with tab1:
        st.subheader("Document Management")
        
        # Check for existing PDFs in uploads directory
        project_dir = get_project_dir(project_id)
        uploads_dir = project_dir / "uploads"
        existing_pdfs = []
        
        if uploads_dir.exists():
            existing_pdfs = list(uploads_dir.glob("*.pdf"))
            if existing_pdfs:
                st.info(f"📁 Found {len(existing_pdfs)} PDF files in uploads directory")
                
                # Quick diagnostic information
                with st.expander("🔍 PDF Matching Diagnostics", expanded=False):
                    st.markdown("**Current PDF Files:**")
                    
                    # Show sample of PDF filenames
                    sample_pdfs = existing_pdfs[:10] if len(existing_pdfs) > 10 else existing_pdfs
                    for pdf in sample_pdfs:
                        st.code(pdf.name)
                    
                    if len(existing_pdfs) > 10:
                        st.caption(f"... and {len(existing_pdfs) - 10} more files")
                    
                    st.markdown("**Article IDs being matched against:**")
                    sample_articles = included_articles.head(5)
                    for idx, (_, article) in enumerate(sample_articles.iterrows()):
                        article_id = get_safe_article_id(article, idx)
                        title = article.get('title', 'Unknown')[:50]
                        st.code(f"ID: {article_id} | Title: {title}...")
                    
                    if len(included_articles) > 5:
                        st.caption(f"... and {len(included_articles) - 5} more articles")
                    
                    # Show current matches
                    current_matches = included_articles[included_articles.get('full_text_status', '') == 'Acquired']
                    st.markdown(f"**Current Matches:** {len(current_matches)} articles have PDFs assigned")
                
                # Enhanced PDF scanning button
                col1, col2 = st.columns(2)
                
                with col1:
                    # Option to scan and update status for existing PDFs
                    scan_button = st.button("🔄 Scan for Existing PDFs", help="Check uploaded PDFs and update article status")
                        
                with col2:
                    # Reset all PDF assignments and re-scan
                    reset_button = st.button("🔄 Reset & Re-scan All", help="Clear all PDF assignments and perform fresh matching", type="secondary")
                
                # Handle reset button
                if reset_button:
                    with st.spinner("Resetting all PDF assignments..."):
                        # Reset all articles to 'Awaiting' status
                        articles_df['full_text_status'] = 'Awaiting'
                        articles_df['pdf_path'] = ""
                        save_screened_articles(project_id, articles_df)
                        st.success("✅ Reset complete! Now click 'Scan for Existing PDFs' to perform fresh matching.")
                        st.rerun()
                
                # Handle scan button
                if scan_button:
                    updated_count = 0
                    unmatched_pdfs = []
                    
                    # Show progress while scanning
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Enhanced PDF matching with multiple strategies
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
                            
                            # Strategy 1: PDF number to article index match (most reliable)
                            # Extract the number prefix from PDF filename (e.g., "12_" -> 12)
                            pdf_number_match = re.match(r'^(\d+)_', pdf_path.name)
                            if pdf_number_match:
                                pdf_number = int(pdf_number_match.group(1))
                                # Check if this number corresponds to the article's position (1-based indexing)
                                if pdf_number == idx + 1:  # idx is 0-based, PDF numbers are 1-based
                                    matches.append((article, idx, f'pdf_number({pdf_number})', 98))
                                    continue
                            
                            # Strategy 2: Exact article ID match (fallback)
                            if str(article_id).lower() in pdf_name:
                                matches.append((article, idx, 'article_id', 95))
                                continue
                            
                            # Strategy 2.5: Special handling for search-related content
                            # Since all your articles are about "search", give bonus points for search-related PDFs
                            if 'search' in pdf_stem and 'search' in title:
                                search_bonus = 20
                            else:
                                search_bonus = 0
                            
                            # Strategy 3: Very gentle title matching - focus on first few words
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
                            
                            # Strategy 3.5: Even gentler - any significant word match
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
                            
                            # Strategy 4: Author lastname + year combination
                            if authors and year:
                                # Extract first author's last name
                                first_author = authors.split(',')[0].split(';')[0].strip()
                                if first_author and len(first_author) > 2:
                                    author_lastname = first_author.split()[-1] if ' ' in first_author else first_author
                                    
                                    if len(author_lastname) > 3 and author_lastname.lower() in pdf_stem and year in pdf_stem:
                                        matches.append((article, idx, f'author_year({author_lastname}_{year})', 80))
                        
                        # Return the best match (highest confidence)
                        if matches:
                            return max(matches, key=lambda x: x[3])
                        return None
                    
                    # Process each PDF
                    assigned_articles = set()  # Track which articles have been assigned
                    
                    for i, pdf_path in enumerate(existing_pdfs):
                        progress_bar.progress((i + 1) / len(existing_pdfs))
                        status_text.text(f"Scanning {pdf_path.name}...")
                        
                        # Try to find a match
                        match_result = try_match_pdf_to_article(pdf_path, included_articles)
                        
                        if match_result:
                            article, idx, match_type, confidence = match_result
                            article_title = article.get('title', f'Article {idx}')
                            
                            # Skip if this article is already assigned to another PDF
                            if article_title in assigned_articles:
                                unmatched_pdfs.append({
                                    'pdf': pdf_path,
                                    'potential_match': article,
                                    'match_type': f'duplicate_assignment_{match_type}',
                                    'confidence': confidence
                                })
                                continue
                            
                            # Only auto-update if confidence is high enough
                            if confidence >= 40:  # Much more gentle - 40% confidence is enough
                                try:
                                    # Update the article status
                                    if 'id' in articles_df.columns and hasattr(article, 'index') and 'id' in article.index:
                                        mask = articles_df['id'] == article.get('id')
                                    else:
                                        mask = articles_df['title'] == article.get('title', '')
                                    
                                    if 'full_text_status' not in articles_df.columns:
                                        articles_df['full_text_status'] = 'Awaiting'
                                    if 'pdf_path' not in articles_df.columns:
                                        articles_df['pdf_path'] = ""
                                    
                                    # Check if not already assigned to THIS specific PDF
                                    current_status = articles_df.loc[mask, 'full_text_status'].iloc[0] if not articles_df.loc[mask].empty else 'Awaiting'
                                    current_pdf_path = articles_df.loc[mask, 'pdf_path'].iloc[0] if not articles_df.loc[mask].empty else ""
                                    
                                    # Only skip if ALREADY assigned to the SAME PDF
                                    if current_status == 'Acquired' and str(current_pdf_path) == str(pdf_path):
                                        # This article is already correctly assigned to this PDF - skip
                                        continue
                                    else:
                                        # Either not assigned or assigned to different PDF - update it
                                        articles_df.loc[mask, 'full_text_status'] = 'Acquired'
                                        articles_df.loc[mask, 'pdf_path'] = str(pdf_path)
                                        assigned_articles.add(article_title)  # Track this assignment
                                        updated_count += 1
                                
                                except Exception as e:
                                    logger.error(f"Error updating article for {pdf_path.name}: {str(e)}")
                            else:
                                # Lower confidence matches - add to manual review list
                                unmatched_pdfs.append({
                                    'pdf': pdf_path,
                                    'potential_match': article,
                                    'match_type': match_type,
                                    'confidence': confidence
                                })
                        else:
                            # No match found
                            unmatched_pdfs.append({
                                'pdf': pdf_path,
                                'potential_match': None,
                                'match_type': 'no_match',
                                'confidence': 0
                            })
                    
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Show results
                    if updated_count > 0:
                        # Save the updated articles back to file
                        save_screened_articles(project_id, articles_df)
                        st.success(f"✅ Successfully matched and updated {updated_count} articles with PDFs")
                        
                        # Show what was matched
                        with st.expander(f"📋 View {updated_count} Auto-matched PDFs"):
                            for pdf_path in existing_pdfs:
                                match_result = try_match_pdf_to_article(pdf_path, included_articles)
                                if match_result and match_result[3] >= 40:  # Much more gentle threshold
                                    article, idx, match_type, confidence = match_result
                                    st.write(f"📄 **{pdf_path.name}** → _{article.get('title', 'Unknown')[:50]}..._ (via {match_type}, {confidence:.0f}% confidence)")
                    
                    # Handle unmatched or low-confidence PDFs
                    if unmatched_pdfs:
                        st.warning(f"⚠️ {len(unmatched_pdfs)} PDFs need manual review")
                        
                        with st.expander(f"🔍 Manual PDF Matching ({len(unmatched_pdfs)} files)", expanded=True):
                            st.markdown("**These PDFs couldn't be automatically matched or have low confidence. Please review and manually assign:**")
                            
                            for unmatched in unmatched_pdfs:
                                pdf_path = unmatched['pdf']
                                potential_match = unmatched['potential_match']
                                confidence = unmatched['confidence']
                                
                                st.markdown(f"---")
                                col1, col2 = st.columns([1, 1])
                                
                                with col1:
                                    st.markdown(f"**📄 PDF File:**")
                                    st.code(pdf_path.name)
                                    
                                    if potential_match is not None:
                                        st.markdown(f"**🎯 Suggested Match ({confidence:.0f}% confidence):**")
                                        st.write(f"_{potential_match.get('title', 'Unknown')[:60]}..._")
                                        st.caption(f"Authors: {potential_match.get('authors', 'Unknown')[:40]}...")
                                
                                with col2:
                                    st.markdown("**🔗 Manual Assignment:**")
                                    
                                    # Create dropdown with all articles
                                    article_options = ["-- Select Article --"] + [
                                        f"{i+1}. {article.get('title', f'Article {i+1}')[:50]}..." 
                                        for i, (_, article) in enumerate(included_articles.iterrows())
                                    ]
                                    
                                    selected_idx = st.selectbox(
                                        "Choose article:",
                                        options=range(len(article_options)),
                                        format_func=lambda x: article_options[x],
                                        key=f"manual_match_{pdf_path.name}"
                                    )
                                    
                                    if selected_idx > 0:  # An article was selected
                                        if st.button(f"🔗 Assign PDF", key=f"assign_{pdf_path.name}"):
                                            try:
                                                # Get the selected article
                                                selected_article = included_articles.iloc[selected_idx - 1]
                                                
                                                # Update the article status
                                                if 'id' in articles_df.columns and hasattr(selected_article, 'index') and 'id' in selected_article.index:
                                                    mask = articles_df['id'] == selected_article.get('id')
                                                else:
                                                    mask = articles_df['title'] == selected_article.get('title', '')
                                                
                                                if 'full_text_status' not in articles_df.columns:
                                                    articles_df['full_text_status'] = 'Awaiting'
                                                if 'pdf_path' not in articles_df.columns:
                                                    articles_df['pdf_path'] = ""
                                                
                                                articles_df.loc[mask, 'full_text_status'] = 'Acquired'
                                                articles_df.loc[mask, 'pdf_path'] = str(pdf_path)
                                                
                                                # Save changes
                                                save_screened_articles(project_id, articles_df)
                                                
                                                st.success(f"✅ Assigned {pdf_path.name} to article!")
                                                st.rerun()
                                                
                                            except Exception as e:
                                                st.error(f"Error assigning PDF: {str(e)}")
                    
                    if updated_count == 0 and not unmatched_pdfs:
                        st.info("ℹ️ All PDFs appear to already be matched to articles")
                    
                    # Always rerun to refresh the status counts
                    if updated_count > 0:
                        st.rerun()
        
        # Show articles and their full-text status
        for idx, (_, article) in enumerate(included_articles.iterrows()):
            article_title_safe = article.get('title', f'Untitled Article {idx}')
            with st.expander(f" {article_title_safe[:100]}...", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Authors:** {article.get('authors', 'Unknown')}")
                    st.markdown(f"**Year:** {article.get('year', 'Unknown')}")
                    st.markdown(f"**Source:** {article.get('source', 'Unknown')}")
                    
                    # Show abstract preview
                    if 'abstract' in article and article['abstract']:
                        with st.expander("Abstract Preview"):
                            st.write(article['abstract'][:500] + "..." if len(str(article['abstract'])) > 500 else article['abstract'])
                
                with col2:
                    # Full-text status
                    full_text_status = article.get('full_text_status', 'Awaiting')
                    
                    if full_text_status == 'Awaiting':
                        st.error("🔴 No full text")
                    elif full_text_status == 'Acquired':
                        st.success("🟢 Full text available")
                    else:
                        st.warning("🟡 Abstract only")
                    
                    # File upload for manual PDF upload
                    pdf_file = st.file_uploader(
                        "Upload PDF", 
                        type=["pdf"],
                        key=f"pdf_upload_{idx}",
                        help="Upload the full-text PDF for this article"
                    )
                    
                    if pdf_file is not None:
                        # Validate PDF before saving
                        with st.spinner("Validating PDF..."):
                            validation_result = pdf_processor.validate_pdf(pdf_file)
                            
                            if not validation_result.get('valid', False):
                                st.error(f"❌ Invalid PDF file: {validation_result.get('error', 'Unknown error')}")
                                logger.error(f"PDF validation failed for {article.get('title', f'Article {idx}')[:50]}: {validation_result.get('error')}")
                                continue
                            
                            # Check if PDF has readable text
                            if not validation_result.get('has_text', False):
                                st.warning("⚠️ PDF appears to be image-based and may not contain extractable text. Consider using OCR tools first.")
                            
                            page_count = validation_result.get('page_count', 0)
                            st.info(f"✅ Valid PDF with {page_count} pages")
                        
                        # Save uploaded file
                        project_dir = get_project_dir(project_id)
                        uploads_dir = project_dir / "uploads"
                        uploads_dir.mkdir(exist_ok=True)
                        
                        article_id = get_safe_article_id(article, idx)
                        file_path = uploads_dir / f"{article_id}_{pdf_file.name}"
                        
                        with open(file_path, "wb") as f:
                            f.write(pdf_file.getbuffer())
                        
                        # Update article status - find a safe way to identify the article
                        try:
                            # Try to find by ID if it exists
                            if 'id' in articles_df.columns and hasattr(article, 'index') and 'id' in article.index:
                                mask = articles_df['id'] == article.get('id')
                            else:
                                # Fallback to title matching
                                mask = articles_df['title'] == article.get('title', '')
                            
                            # Ensure columns exist before updating
                            if 'full_text_status' not in articles_df.columns:
                                articles_df['full_text_status'] = 'Awaiting'
                            if 'pdf_path' not in articles_df.columns:
                                articles_df['pdf_path'] = ""
                            
                            articles_df.loc[mask, 'full_text_status'] = 'Acquired'
                            articles_df.loc[mask, 'pdf_path'] = str(file_path)
                            
                            # Save the updated articles back to file
                            save_screened_articles(project_id, articles_df)
                            
                        except Exception as e:
                            st.error(f"Error updating article status: {str(e)}")
                            logger.error(f"Article status update error: {str(e)}")
                        
                        logger.success(f"Uploaded PDF for: {article.get('title', f'Article {idx}')[:50]}...")
                        st.success("PDF uploaded successfully!")
                        st.rerun()

    with tab2:
        st.subheader("AI-Powered Data Extraction")
        
        # Reload articles to get the latest status (in case PDFs were uploaded in tab1)
        articles_df_fresh = load_screened_articles(project_id)
        
        # Re-filter for included articles with fresh data
        try:
            if 'final_decision' in articles_df_fresh.columns:
                included_articles_fresh = articles_df_fresh[articles_df_fresh['final_decision'] == 'Include']
            else:
                included_articles_fresh = articles_df_fresh
        except Exception as e:
            st.error(f"Error filtering included articles: {str(e)}")
            logger.error(f"Article filtering error: {str(e)}")
            included_articles_fresh = articles_df_fresh  # Use all articles as fallback
        
        # Initialize full_text_status column if it doesn't exist (backup safety)
        if 'full_text_status' not in included_articles_fresh.columns:
            included_articles_fresh = included_articles_fresh.copy()
            included_articles_fresh['full_text_status'] = 'Awaiting'
        
        # Check if extraction model is configured
        extraction_model = config.get("extraction_model", "")
        if not extraction_model:
            st.error(" No extraction model configured. Please configure models in Settings.")
            return
        
        st.info(f"Using model: **{extraction_model}**")
        
        # Get extraction prompts
        extraction_prompts = config.get("extraction_prompts", {})
        
        if not extraction_prompts:
            st.warning(" No extraction prompts configured. Please configure extraction prompts in Settings.")
            return
        
        # Show what will be extracted
        st.markdown("**Data to be extracted:**")
        for field in extraction_prompts.keys():
            st.write(f"• {field.replace('_', ' ').title()}")
        
        # Articles with full text available
        try:
            # Ensure full_text_status column exists
            if 'full_text_status' not in included_articles_fresh.columns:
                included_articles_fresh['full_text_status'] = 'Awaiting'
            
            full_text_articles = included_articles_fresh[included_articles_fresh['full_text_status'] == 'Acquired']
        except Exception as e:
            st.error(f"Error accessing full text status: {str(e)}")
            logger.error(f"Full text status error: {str(e)}")
            full_text_articles = pd.DataFrame()  # Empty dataframe as fallback
        
        if full_text_articles.empty:
            # Show debugging information
            st.warning("⚠️ No articles with full text available. Please upload PDFs in the Document Management tab.")
            
            # Debug information to help troubleshoot
            with st.expander("🔍 Debug Information"):
                st.write(f"Total included articles: {len(included_articles_fresh)}")
                
                if 'full_text_status' in included_articles_fresh.columns:
                    status_counts = included_articles_fresh['full_text_status'].value_counts()
                    st.write("Full text status distribution:")
                    for status, count in status_counts.items():
                        st.write(f"• {status}: {count} articles")
                else:
                    st.write("❌ No 'full_text_status' column found")
                
                if 'pdf_path' in included_articles_fresh.columns:
                    non_empty_paths = included_articles_fresh['pdf_path'].notna().sum()
                    st.write(f"Articles with PDF paths: {non_empty_paths}")
                else:
                    st.write("❌ No 'pdf_path' column found")
        else:
            st.success(f"Ready to extract data from {len(full_text_articles)} articles")
            
            # Show extraction overview
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Articles Ready", len(full_text_articles))
            
            with col2:
                # Check for existing extractions
                existing_extractions = load_extracted_data(project_id)
                already_extracted = 0
                
                if not existing_extractions.empty:
                    # Match by article ID or title
                    for idx, (_, article) in enumerate(full_text_articles.iterrows()):
                        article_id = get_safe_article_id(article, idx)
                        title = article.get('title', '')
                        
                        # Check if this article has been extracted
                        if 'article_id' in existing_extractions.columns:
                            if article_id in existing_extractions['article_id'].values:
                                already_extracted += 1
                        elif 'title' in existing_extractions.columns:
                            if title in existing_extractions['title'].values:
                                already_extracted += 1
                
                st.metric("Already Extracted", already_extracted)
            
            with col3:
                remaining = len(full_text_articles) - already_extracted
                st.metric("Remaining to Extract", remaining)
            
            # Show last extraction stats if available
            if 'extraction_stats' in st.session_state and st.session_state.extraction_stats.get('processed', 0) > 0:
                st.markdown("**📊 Last Extraction Results:**")
                last_stats = st.session_state.extraction_stats
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Last Run - Processed", last_stats.get('processed', 0))
                with col2:
                    st.metric("Last Run - Successful", last_stats.get('successful', 0))
                with col3:
                    st.metric("Last Run - Failed", last_stats.get('failed', 0))
            
            # Show what will be extracted
            st.markdown("**📋 Extraction Fields:**")
            extraction_fields = list(extraction_prompts.keys())
            field_cols = st.columns(min(3, len(extraction_fields)))
            
            for i, field in enumerate(extraction_fields):
                with field_cols[i % len(field_cols)]:
                    st.markdown(f"• {field.replace('_', ' ').title()}")
            
            # Advanced extraction options
            with st.expander("⚙️ Advanced Options"):
                col1, col2 = st.columns(2)
                
                with col1:
                    skip_existing = st.checkbox(
                        "Skip already extracted articles",
                        value=True,
                        help="Skip articles that have already been processed"
                    )
                
                with col2:
                    # Future feature: batch processing
                    st.info("💡 Batch processing options coming soon!")
            
            # Bulk extraction button with enhanced UX
            if st.button("🚀 Start Comprehensive Data Extraction", use_container_width=True, type="primary"):
                
                # Initialize extraction stats in session state
                if 'extraction_stats' not in st.session_state:
                    st.session_state.extraction_stats = {
                        'total_articles': 0,
                        'processed': 0,
                        'successful': 0,
                        'failed': 0,
                        'skipped': 0
                    }
                
                # Create progress tracking containers
                progress_container = st.empty()
                live_table_container = st.empty()
                logs_container = st.empty()
                status_container = st.empty()
                
                # Initialize progress tracking
                with progress_container.container():
                    st.markdown("**🔄 Extraction Progress:**")
                    overall_progress = st.progress(0)
                    progress_text = st.empty()
                
                # Filter articles to process
                articles_to_process = full_text_articles.copy()
                
                if skip_existing and not existing_extractions.empty:
                    # Filter out already processed articles
                    unprocessed_articles = []
                    for idx, (_, article) in enumerate(full_text_articles.iterrows()):
                        article_id = get_safe_article_id(article, idx)
                        title = article.get('title', '')
                        
                        is_processed = False
                        if 'article_id' in existing_extractions.columns and article_id:
                            is_processed = article_id in existing_extractions['article_id'].values
                        elif 'title' in existing_extractions.columns and title:
                            is_processed = title in existing_extractions['title'].values
                        
                        if not is_processed:
                            unprocessed_articles.append(article)
                    
                    if unprocessed_articles:
                        articles_to_process = pd.DataFrame(unprocessed_articles)
                    else:
                        articles_to_process = pd.DataFrame()
                
                if articles_to_process.empty:
                    with status_container.container():
                        st.info("✅ All articles have already been processed!")
                        st.balloons()
                    return
                
                # Initialize live results tracking
                live_results_data = []
                st.session_state.extraction_stats = {
                    'total_articles': len(articles_to_process),
                    'processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0
                }
                extraction_stats = st.session_state.extraction_stats
                
                # Start extraction
                import time
                start_time = time.time()
                
                # Custom logger for real-time updates
                class ExtractionLogger:
                    def __init__(self, logs_container):
                        self.logs_container = logs_container
                        self.logs = []
                        self.max_logs = 12
                    
                    def info(self, message):
                        timestamp = time.strftime("%H:%M:%S")
                        log_entry = f"[{timestamp}] ℹ️ {message}"
                        self.logs.append(log_entry)
                        self._update_display()
                        logger.info(message)
                    
                    def success(self, message):
                        timestamp = time.strftime("%H:%M:%S")
                        log_entry = f"[{timestamp}] ✅ {message}"
                        self.logs.append(log_entry)
                        self._update_display()
                        logger.success(message)
                    
                    def warning(self, message):
                        timestamp = time.strftime("%H:%M:%S")
                        log_entry = f"[{timestamp}] ⚠️ {message}"
                        self.logs.append(log_entry)
                        self._update_display()
                        logger.warning(message)
                    
                    def error(self, message):
                        timestamp = time.strftime("%H:%M:%S")
                        log_entry = f"[{timestamp}] ❌ {message}"
                        self.logs.append(log_entry)
                        self._update_display()
                        logger.error(message)
                    
                    def _update_display(self):
                        recent_logs = self.logs[-self.max_logs:]
                        with self.logs_container.container():
                            st.markdown("**📋 Live Extraction Logs:**")
                            
                            log_text = ""
                            for log in recent_logs:
                                log_text += log + "\n"
                            
                            st.code(log_text, language=None)
                
                extraction_logger = ExtractionLogger(logs_container)
                
                # Function to update live results table
                def update_live_table():
                    if live_results_data:
                        df_live = pd.DataFrame(live_results_data)
                        with live_table_container.container():
                            st.markdown("**📊 Live Extraction Results:**")
                            
                            # Style the dataframe
                            styled_df = df_live.style.apply(lambda x: [
                                'background-color: #d4edda; color: #155724' if '✅' in str(val) 
                                else 'background-color: #fff3cd; color: #856404' if '⚠️' in str(val)
                                else 'background-color: #f8d7da; color: #721c24' if '❌' in str(val)
                                else 'background-color: #cce5ff; color: #004085' if '🔄' in str(val)
                                else '' for val in x
                            ], subset=['Status'])
                            
                            st.dataframe(styled_df, use_container_width=True)
                            
                            # Add real-time statistics
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Processed", extraction_stats['processed'])
                            with col2:
                                st.metric("Successful", extraction_stats['successful'])
                            with col3:
                                st.metric("Failed", extraction_stats['failed'])
                            with col4:
                                progress_pct = (extraction_stats['processed'] / extraction_stats['total_articles']) * 100
                                st.metric("Progress", f"{progress_pct:.1f}%")
                
                try:
                    extraction_logger.info("🚀 Starting comprehensive data extraction...")
                    extraction_logger.info(f"📊 Processing {len(articles_to_process)} articles with {len(extraction_fields)} extraction fields")
                    extraction_logger.info(f"🤖 Using AI model: {extraction_model}")
                    
                    # Process articles
                    for idx, (original_idx, article) in enumerate(articles_to_process.iterrows()):
                        # Update progress
                        progress = (idx + 1) / len(articles_to_process)
                        overall_progress.progress(progress)
                        
                        article_title = article.get('title', f'Untitled Article {idx}')[:50] + "..." if len(str(article.get('title', ''))) > 50 else str(article.get('title', f'Untitled Article {idx}'))
                        progress_text.text(f"🔄 Processing article {idx + 1}/{len(articles_to_process)}: {article_title}")
                        
                        extraction_logger.info(f"🔍 Processing: {article_title}")
                        
                        # Add to live results table
                        live_results_data.append({
                            'Article': article_title,
                            'Status': '🔄 Processing...',
                            'PDF Pages': 'Checking...',
                            'Fields Extracted': 'Processing...',
                            'Time': time.strftime("%H:%M:%S")
                        })
                        update_live_table()
                        
                        try:
                            # Get safe article ID
                            article_id = get_safe_article_id(article, idx)
                            
                            # Get PDF path
                            pdf_path = article.get('pdf_path', '')
                            
                            if not pdf_path or not Path(pdf_path).exists():
                                error_msg = f"PDF not found: {pdf_path if pdf_path else 'No path specified'}"
                                extraction_logger.error(f"❌ {article_title}: {error_msg}")
                                
                                # Update live results
                                live_results_data[-1].update({
                                    'Status': '❌ PDF Missing',
                                    'PDF Pages': 'N/A',
                                    'Fields Extracted': 'N/A'
                                })
                                extraction_stats['failed'] += 1
                                continue
                            
                            # Validate PDF first
                            extraction_logger.info(f"🔍 Validating PDF: {Path(pdf_path).name}")
                            pdf_validation = pdf_processor.validate_pdf(pdf_path)
                            
                            if not pdf_validation.get('valid', False):
                                error_msg = f"PDF validation failed: {pdf_validation.get('error', 'Unknown error')}"
                                extraction_logger.error(f"❌ {article_title}: {error_msg}")
                                
                                live_results_data[-1].update({
                                    'Status': '❌ PDF Invalid',
                                    'PDF Pages': 'N/A',
                                    'Fields Extracted': 'N/A'
                                })
                                extraction_stats['failed'] += 1
                                continue
                            
                            extraction_logger.info(f"📄 Extracting text from PDF: {Path(pdf_path).name}")
                            
                            # Extract text from PDF
                            extracted_data = pdf_processor.extract_text_from_pdf(pdf_path)
                            
                            if extracted_data['status'] != 'success':
                                error_msg = f"PDF processing failed: {extracted_data.get('error', 'Unknown error')}"
                                extraction_logger.error(f"❌ {article_title}: {error_msg}")
                                
                                live_results_data[-1].update({
                                    'Status': '❌ PDF Processing Failed',
                                    'PDF Pages': extracted_data.get('page_count', 'Unknown'),
                                    'Fields Extracted': 'N/A'
                                })
                                extraction_stats['failed'] += 1
                                continue
                            
                            page_count = extracted_data.get('page_count', 0)
                            text_length = len(extracted_data.get('full_text', ''))
                            
                            extraction_logger.info(f"📊 PDF processed: {page_count} pages, {text_length:,} characters")
                            
                            # Update with PDF info
                            live_results_data[-1].update({
                                'Status': '🔄 AI Extracting...',
                                'PDF Pages': str(page_count),
                                'Fields Extracted': 'Processing...'
                            })
                            update_live_table()
                            
                            extraction_logger.info(f"🤖 Running AI extraction for {len(extraction_fields)} fields...")
                            
                            # Use AI to extract specific data
                            ai_extracted = ollama_client.extract_data(
                                extracted_data['full_text'], 
                                extraction_prompts
                            )
                            
                            if not ai_extracted:
                                extraction_logger.error(f"❌ {article_title}: AI extraction returned no data")
                                live_results_data[-1].update({
                                    'Status': '❌ AI Extraction Failed',
                                    'Fields Extracted': 'N/A'
                                })
                                extraction_stats['failed'] += 1
                                continue
                            
                            # Count successfully extracted fields
                            extracted_field_count = sum(1 for key, value in ai_extracted.items() 
                                                     if value and str(value).strip() and str(value).lower() not in ['none', 'n/a', 'not provided'])
                            
                            # Add metadata
                            ai_extracted.update({
                                'article_id': article_id,
                                'title': article.get('title', f'Article {idx}'),
                                'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'pdf_pages': page_count,
                                'text_length': text_length
                            })
                            
                            # Save extracted data
                            try:
                                save_extracted_data(project_id, article_id, ai_extracted)
                                extraction_logger.success(f"✅ {article_title}: Extracted {extracted_field_count}/{len(extraction_fields)} fields")
                                
                                # Update live results
                                live_results_data[-1].update({
                                    'Status': '✅ Completed',
                                    'Fields Extracted': f'{extracted_field_count}/{len(extraction_fields)}'
                                })
                                extraction_stats['successful'] += 1
                            except Exception as save_error:
                                extraction_logger.error(f"❌ {article_title}: Failed to save extracted data: {str(save_error)}")
                                live_results_data[-1].update({
                                    'Status': '❌ Save Failed',
                                    'Fields Extracted': f'{extracted_field_count}/{len(extraction_fields)} (not saved)'
                                })
                                extraction_stats['failed'] += 1
                            
                        except Exception as e:
                            error_msg = f"Unexpected error: {str(e)}"
                            extraction_logger.error(f"❌ {article_title}: {error_msg}")
                            
                            # Log detailed error information for debugging
                            logger.error(f"Detailed error for {article_title}: {str(e)}")
                            logger.error(f"Article data available: {list(article.index) if hasattr(article, 'index') else 'No index'}")
                            
                            live_results_data[-1].update({
                                'Status': f'❌ Error: {str(e)[:30]}...',
                                'PDF Pages': 'Unknown',
                                'Fields Extracted': 'N/A'
                            })
                            extraction_stats['failed'] += 1
                        
                        finally:
                            extraction_stats['processed'] += 1
                            update_live_table()
                            
                            # Small delay to make progress visible
                            time.sleep(0.3)
                    
                    # Finalize results
                    overall_progress.progress(1.0)
                    progress_text.text("🔄 Finalizing extraction results...")
                    
                    elapsed_time = time.time() - start_time
                    
                    # Show final results
                    with status_container.container():
                        if extraction_stats['successful'] > 0:
                            st.success(f"✅ Extraction completed in {elapsed_time:.1f} seconds!")
                            st.balloons()
                        else:
                            st.warning("⚠️ Extraction completed but no articles were successfully processed.")
                        
                        # Final statistics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Total Processed", extraction_stats['processed'])
                        
                        with col2:
                            st.metric("Successful", extraction_stats['successful'])
                        
                        with col3:
                            st.metric("Failed", extraction_stats['failed'])
                        
                        with col4:
                            success_rate = (extraction_stats['successful'] / extraction_stats['processed']) * 100 if extraction_stats['processed'] > 0 else 0
                            st.metric("Success Rate", f"{success_rate:.1f}%")
                        
                        # Show detailed results
                        if extraction_stats['successful'] > 0:
                            with st.expander("📊 Extraction Summary"):
                                st.markdown(f"**Processing Time:** {elapsed_time:.1f} seconds")
                                st.markdown(f"**Average Time per Article:** {elapsed_time/extraction_stats['processed']:.1f} seconds")
                                
                                # Load final extracted data for summary
                                final_extracted = load_extracted_data(project_id)
                                if not final_extracted.empty:
                                    st.markdown(f"**Total Articles in Database:** {len(final_extracted)}")
                                    
                                    # Show field completion rates
                                    st.markdown("**Field Completion Rates:**")
                                    for field in extraction_fields:
                                        if field in final_extracted.columns:
                                            non_empty = final_extracted[field].notna().sum()
                                            completion_rate = (non_empty / len(final_extracted)) * 100
                                            st.markdown(f"• {field.replace('_', ' ').title()}: {non_empty}/{len(final_extracted)} ({completion_rate:.1f}%)")
                        
                        if extraction_stats['failed'] > 0:
                            with st.expander("❌ Failed Extractions"):
                                st.markdown("**Common Issues and Solutions:**")
                                st.markdown("• **PDF Missing/Corrupted**: Re-upload the PDF files in Document Management")
                                st.markdown("• **PDF Invalid**: File may be corrupted or not a valid PDF")
                                st.markdown("• **Document Closed Error**: PyMuPDF concurrency issue - try processing fewer articles")
                                st.markdown("• **AI Model Issues**: Check Ollama is running and model is available")
                                st.markdown("• **Text Extraction Failed**: PDFs may be image-based (need OCR)")
                                st.markdown("• **Memory Issues**: Try processing fewer articles at once")
                                st.markdown("• **File Permission Issues**: Check that PDF files are not locked or in use")
                                
                                st.markdown("**Troubleshooting Steps:**")
                                st.markdown("1. Go to Document Management tab and re-upload problematic PDFs")
                                st.markdown("2. Check that Ollama is running: `ollama list` in terminal")
                                st.markdown("3. Verify PDF files are not corrupted by opening them manually")
                                st.markdown("4. For image-based PDFs, use OCR tools to convert to text-searchable PDFs")
                                st.markdown("5. Close any PDF viewers that might have the files open")
                        
                        st.info("🔄 **Next Steps:** Go to the Results Review tab to examine and edit the extracted data.")
                
                except Exception as e:
                    overall_progress.progress(1.0)
                    with status_container.container():
                        st.error(f"❌ Extraction process failed: {str(e)}")
                        extraction_logger.error(f"❌ Critical error: {str(e)}")
                        
                        with st.expander("🔍 Error Details"):
                            st.code(str(e))
                            st.markdown("**Possible Solutions:**")
                            st.markdown("• Check that Ollama is running")
                            st.markdown("• Verify that the extraction model is available")
                            st.markdown("• Ensure PDF files are accessible")
                            st.markdown("• Check system resources (memory, disk space)")
                            st.markdown("• Try processing fewer articles at once")
            
            # Retry failed extractions
            extraction_stats = st.session_state.get('extraction_stats', {'failed': 0})
            if extraction_stats.get('failed', 0) > 0:
                st.markdown("---")
                st.markdown("**🔄 Retry Failed Extractions**")
                
                if st.button("🔁 Retry Failed Articles", use_container_width=True):
                    st.info("💡 **Retry Feature**: This will attempt to re-process articles that failed during the last extraction run.")
                    st.warning("⚠️ **Note**: Retry functionality will be implemented in the next update. For now, please:")
                    st.markdown("1. Check the failed articles in Document Management")
                    st.markdown("2. Re-upload any corrupted PDFs")
                    st.markdown("3. Run the extraction process again")
            
            # Individual article extraction
            st.markdown("---")
            st.markdown("**Individual Article Processing:**")
            
            for idx, (_, article) in enumerate(full_text_articles.iterrows()):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    article_title = article.get('title', f'Untitled Article {idx}')
                    st.write(f" {article_title[:80]}...")
                
                with col2:
                    if st.button("Extract", key=f"extract_{idx}"):
                        with st.spinner("Extracting data..."):
                            try:
                                # Get safe article ID
                                article_id = get_safe_article_id(article, idx)
                                
                                pdf_path = article.get('pdf_path', '')
                                if pdf_path and Path(pdf_path).exists():
                                    extracted_data = pdf_processor.extract_text_from_pdf(pdf_path)
                                    
                                    if extracted_data['status'] == 'success':
                                        ai_extracted = ollama_client.extract_data(
                                            extracted_data['full_text'], 
                                            extraction_prompts
                                        )
                                        
                                        ai_extracted.update({
                                            'article_id': article_id,
                                            'title': article.get('title', f'Article {idx}'),
                                            'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                                            'pdf_pages': extracted_data.get('page_count', 0)
                                        })
                                        
                                        try:
                                            save_extracted_data(project_id, article_id, ai_extracted)
                                            st.success(" Data extracted!")
                                            logger.success(f"Extracted data from: {article.get('title', f'Article {idx}')[:50]}...")
                                        except Exception as save_error:
                                            st.error(f" Data extracted but failed to save: {str(save_error)}")
                                            logger.error(f"Failed to save extraction for {article.get('title', f'Article {idx}')[:50]}: {str(save_error)}")
                                    else:
                                        st.error(" Failed to process PDF")
                                        
                            except Exception as e:
                                st.error(f" Error: {str(e)}")
                                logger.error(f"Error processing {article.get('title', f'Article {idx}')[:50]}...: {str(e)}")

    with tab3:
        st.subheader("Extraction Results Review")
        
        # Load extracted data
        extracted_df = load_extracted_data(project_id)
        
        if extracted_df.empty:
            st.info(" No extracted data available yet. Please run the extraction process first.")
        else:
            st.success(f" Found extracted data for {len(extracted_df)} articles")
            
            # Summary statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Articles Processed", len(extracted_df))
            
            with col2:
                if 'extraction_date' in extracted_df.columns:
                    latest_extraction = extracted_df['extraction_date'].max()
                    st.metric("Latest Extraction", latest_extraction.split(' ')[0] if latest_extraction else "Unknown")
            
            with col3:
                if 'pdf_pages' in extracted_df.columns:
                    avg_pages = extracted_df['pdf_pages'].mean()
                    st.metric("Avg Pages per Article", f"{avg_pages:.1f}" if not pd.isna(avg_pages) else "Unknown")
            
            # Display extracted data table
            st.markdown("**Extracted Data:**")
            
            # Allow users to edit the extracted data
            edited_df = st.data_editor(
                extracted_df,
                use_container_width=True,
                num_rows="dynamic",
                disabled=["article_id", "extraction_date"],
                key="extracted_data_editor"
            )
            
            # Save changes
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button(" Save Changes", use_container_width=True):
                    # Save the edited data back
                    data_file = get_project_dir(project_id) / "data_extracted.csv"
                    edited_df.to_csv(data_file, index=False)
                    
                    logger.success("Extracted data saved successfully")
                    st.success("Changes saved successfully!")
            
            with col2:
                if st.button(" Generate Summary", use_container_width=True):
                    # Create a summary of the extracted data
                    summary = "## Extraction Summary\n\n"
                    summary += f"**Total Articles Processed:** {len(extracted_df)}\n\n"
                    
                    # Count non-empty fields
                    for col in extracted_df.columns:
                        if col not in ['article_id', 'title', 'extraction_date', 'pdf_pages']:
                            non_empty = extracted_df[col].notna().sum()
                            summary += f"**{col.replace('_', ' ').title()}:** {non_empty}/{len(extracted_df)} articles\n"
                    
                    st.markdown(summary)

# Legacy function for backward compatibility  
def full_text_analysis_page():
    """Legacy function - use show() instead."""
    if 'logger' not in st.session_state:
        from components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)