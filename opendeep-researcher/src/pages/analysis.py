import streamlit as st
import pandas as pd
from pathlib import Path
from utils.pdf_processor import PDFProcessor
from utils.data_manager import load_screened_articles, save_extracted_data, get_project_dir
from utils.ollama_client import OllamaClient
from utils.data_manager import load_config

def show(logger):
    """Full-text analysis page."""
    st.title("🔍 Full-Text Analysis")
    st.markdown("---")

    # Check if project is selected
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        st.warning("⚠️ Please select a project from the Dashboard first.")
        return

    logger.info(f"Loading full-text analysis for project: {project_id}")

    # Load screened articles
    articles_df = load_screened_articles(project_id)
    
    if articles_df.empty:
        st.warning("📝 No screened articles found. Please complete the screening phase first.")
        return

    # Filter for included articles only
    if 'final_decision' in articles_df.columns:
        included_articles = articles_df[articles_df['final_decision'] == 'Include']
    else:
        included_articles = articles_df
    
    if included_articles.empty:
        st.warning("📝 No articles were included during screening. Please review your screening results.")
        return

    st.success(f"Found {len(included_articles)} articles ready for full-text analysis")

    # Initialize PDF processor and Ollama client
    pdf_processor = PDFProcessor()
    ollama_client = OllamaClient()
    config = load_config()

    # Create tabs for different analysis phases
    tab1, tab2, tab3 = st.tabs(["📄 Document Management", "🧠 AI Extraction", "📊 Results Review"])

    with tab1:
        st.subheader("Document Management")
        
        # Show articles and their full-text status
        for idx, (_, article) in enumerate(included_articles.iterrows()):
            with st.expander(f"📄 {article['title'][:100]}...", expanded=False):
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
                        f"Upload PDF", 
                        type=["pdf"],
                        key=f"pdf_upload_{idx}",
                        help="Upload the full-text PDF for this article"
                    )
                    
                    if pdf_file is not None:
                        # Save uploaded file
                        project_dir = get_project_dir(project_id)
                        uploads_dir = project_dir / "uploads"
                        uploads_dir.mkdir(exist_ok=True)
                        
                        file_path = uploads_dir / f"{article.get('id', idx)}_{pdf_file.name}"
                        
                        with open(file_path, "wb") as f:
                            f.write(pdf_file.getbuffer())
                        
                        # Update article status
                        articles_df.loc[articles_df['id'] == article.get('id', idx), 'full_text_status'] = 'Acquired'
                        articles_df.loc[articles_df['id'] == article.get('id', idx), 'pdf_path'] = str(file_path)
                        
                        logger.success(f"Uploaded PDF for: {article['title'][:50]}...")
                        st.success("PDF uploaded successfully!")
                        st.rerun()

    with tab2:
        st.subheader("AI-Powered Data Extraction")
        
        # Check if extraction model is configured
        extraction_model = config.get("extraction_model", "")
        if not extraction_model:
            st.error("❌ No extraction model configured. Please configure models in Settings.")
            return
        
        st.info(f"Using model: **{extraction_model}**")
        
        # Get extraction prompts
        extraction_prompts = config.get("extraction_prompts", {})
        
        if not extraction_prompts:
            st.warning("⚠️ No extraction prompts configured. Please configure extraction prompts in Settings.")
            return
        
        # Show what will be extracted
        st.markdown("**Data to be extracted:**")
        for field in extraction_prompts.keys():
            st.write(f"• {field.replace('_', ' ').title()}")
        
        # Articles with full text available
        full_text_articles = included_articles[included_articles['full_text_status'] == 'Acquired']
        
        if full_text_articles.empty:
            st.warning("📄 No articles with full text available. Please upload PDFs in the Document Management tab.")
        else:
            st.success(f"Ready to extract data from {len(full_text_articles)} articles")
            
            # Bulk extraction button
            if st.button("🚀 Start Bulk Extraction", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, (_, article) in enumerate(full_text_articles.iterrows()):
                    status_text.text(f"Processing: {article['title'][:50]}...")
                    
                    try:
                        # Load PDF
                        pdf_path = article.get('pdf_path', '')
                        if pdf_path and Path(pdf_path).exists():
                            # Extract text from PDF
                            extracted_data = pdf_processor.extract_text_from_pdf(pdf_path)
                            
                            if extracted_data['status'] == 'success':
                                # Use AI to extract specific data
                                ai_extracted = ollama_client.extract_data(
                                    extracted_data['full_text'], 
                                    extraction_prompts
                                )
                                
                                # Add metadata
                                ai_extracted.update({
                                    'article_id': article.get('id', idx),
                                    'title': article['title'],
                                    'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'pdf_pages': extracted_data.get('page_count', 0)
                                })
                                
                                # Save extracted data
                                save_extracted_data(project_id, article.get('id', idx), ai_extracted)
                                
                                logger.success(f"Extracted data from: {article['title'][:50]}...")
                            else:
                                logger.error(f"Failed to process PDF: {article['title'][:50]}...")
                                
                    except Exception as e:
                        logger.error(f"Error processing {article['title'][:50]}...: {str(e)}")
                    
                    # Update progress
                    progress_bar.progress((idx + 1) / len(full_text_articles))
                
                status_text.text("✅ Extraction complete!")
                st.success("Data extraction completed!")
                st.rerun()
            
            # Individual article extraction
            st.markdown("---")
            st.markdown("**Individual Article Processing:**")
            
            for idx, (_, article) in enumerate(full_text_articles.iterrows()):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"📄 {article['title'][:80]}...")
                
                with col2:
                    if st.button(f"Extract", key=f"extract_{idx}"):
                        with st.spinner("Extracting data..."):
                            try:
                                pdf_path = article.get('pdf_path', '')
                                if pdf_path and Path(pdf_path).exists():
                                    extracted_data = pdf_processor.extract_text_from_pdf(pdf_path)
                                    
                                    if extracted_data['status'] == 'success':
                                        ai_extracted = ollama_client.extract_data(
                                            extracted_data['full_text'], 
                                            extraction_prompts
                                        )
                                        
                                        ai_extracted.update({
                                            'article_id': article.get('id', idx),
                                            'title': article['title'],
                                            'extraction_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                                            'pdf_pages': extracted_data.get('page_count', 0)
                                        })
                                        
                                        save_extracted_data(project_id, article.get('id', idx), ai_extracted)
                                        
                                        st.success("✅ Data extracted!")
                                        logger.success(f"Extracted data from: {article['title'][:50]}...")
                                    else:
                                        st.error("❌ Failed to process PDF")
                                        
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                                logger.error(f"Error processing {article['title'][:50]}...: {str(e)}")

    with tab3:
        st.subheader("Extraction Results Review")
        
        # Load extracted data
        from utils.data_manager import load_extracted_data
        extracted_df = load_extracted_data(project_id)
        
        if extracted_df.empty:
            st.info("📊 No extracted data available yet. Please run the extraction process first.")
        else:
            st.success(f"📊 Found extracted data for {len(extracted_df)} articles")
            
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
                if st.button("💾 Save Changes", use_container_width=True):
                    # Save the edited data back
                    data_file = get_project_dir(project_id) / "data_extracted.csv"
                    edited_df.to_csv(data_file, index=False)
                    
                    logger.success("Extracted data saved successfully")
                    st.success("Changes saved successfully!")
            
            with col2:
                if st.button("📊 Generate Summary", use_container_width=True):
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