"""
Data Collection page for systematic review.
Implements web scraping and article collection functionality.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
import time
from src.utils.data_manager import (
    load_raw_articles, save_raw_articles, get_project_dir, 
    load_config, load_projects, save_projects
)
from src.utils.academic_search import RobustAcademicSearcher
from src.utils.web_scraper import PDFDownloader


def show(logger):
    """Data collection page."""
    st.title("📊 Data Collection")
    st.markdown("---")

    # Check if project is selected
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        st.warning("⚠️ Please select a project from the Dashboard first.")
        return

    logger.info(f"Loading data collection page for project: {project_id}")

    # Load project configuration
    project_dir = get_project_dir(project_id)
    
    # Check if scoping is complete
    pico_file = project_dir / "pico_framework.json"
    keywords_file = project_dir / "keywords.csv"
    search_config_file = project_dir / "search_config.json"
    
    if not all([pico_file.exists(), keywords_file.exists(), search_config_file.exists()]):
        st.error("❌ Please complete the Scoping phase first!")
        st.info("📋 Required steps:")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if pico_file.exists():
                st.success("✅ PICO Framework")
            else:
                st.error("❌ PICO Framework")
        
        with col2:
            if keywords_file.exists():
                st.success("✅ Keywords")
            else:
                st.error("❌ Keywords")
        
        with col3:
            if search_config_file.exists():
                st.success("✅ Search Config")
            else:
                st.error("❌ Search Config")
        
        return

    # Load scoping data
    try:
        with open(pico_file, 'r') as f:
            pico_data = json.load(f)
        
        keywords_df = pd.read_csv(keywords_file)
        if 'include' in keywords_df.columns:
            included_keywords = keywords_df[keywords_df['include'] == True]['keyword'].tolist()
        else:
            included_keywords = keywords_df['keyword'].tolist()
        
        with open(search_config_file, 'r') as f:
            search_config = json.load(f)
        
        logger.success("Loaded scoping configuration successfully")
        
    except Exception as e:
        st.error(f"❌ Error loading scoping data: {str(e)}")
        logger.error(f"Error loading scoping data: {str(e)}")
        return

    # Create tabs for different collection phases
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Search Configuration", 
        "🌐 Web Search", 
        "📄 PDF Management", 
        "📊 Collection Summary"
    ])

    with tab1:
        st.subheader("Search Configuration Review")
        
        # Display current configuration
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📋 PICO Framework:**")
            for component, value in pico_data.items():
                if value:
                    st.markdown(f"• **{component}:** {value[:100]}{'...' if len(value) > 100 else ''}")
        
        with col2:
            st.markdown("**🔑 Keywords:**")
            st.markdown(f"• **Total Keywords:** {len(included_keywords)}")
            if included_keywords:
                keyword_preview = ", ".join(included_keywords[:5])
                if len(included_keywords) > 5:
                    keyword_preview += f", ... (+{len(included_keywords) - 5} more)"
                st.markdown(f"• **Preview:** {keyword_preview}")
        
        # Search configuration
        st.markdown("**⚙️ Search Configuration:**")
        
        selected_sources = search_config.get("selected_sources", [])
        max_results = search_config.get("max_results_per_source", 100)
        date_filter = search_config.get("date_filter", "No filter")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Data Sources", len(selected_sources))
            for source in selected_sources:
                st.markdown(f"• {source}")
        
        with col2:
            st.metric("Max Results/Source", max_results)
            st.metric("Date Filter", date_filter)
        
        with col3:
            estimated_total = len(selected_sources) * max_results
            st.metric("Est. Total Results", estimated_total)
        
        # Show inclusion/exclusion criteria
        if search_config.get("inclusion_criteria"):
            with st.expander("📝 Inclusion Criteria"):
                st.write(search_config["inclusion_criteria"])
        
        if search_config.get("exclusion_criteria"):
            with st.expander("❌ Exclusion Criteria"):
                st.write(search_config["exclusion_criteria"])

    with tab2:
        st.subheader("Web Search & Article Collection")
        
        # Check existing articles
        existing_articles = load_raw_articles(project_id)
        
        if not existing_articles.empty:
            st.info(f"📚 Found {len(existing_articles)} existing articles from previous searches.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Append New Results", use_container_width=True):
                    st.session_state.append_mode = True
            
            with col2:
                if st.button("🆕 Start Fresh Search", use_container_width=True):
                    st.session_state.append_mode = False
        
        # Search configuration panel
        st.markdown("**🎯 Search Execution:**")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Allow user to modify search parameters
            search_sources = st.multiselect(
                "Select sources to search:",
                options=search_config.get("selected_sources", []),
                default=search_config.get("selected_sources", []),
                help="Choose which databases to search"
            )
            
            max_results_override = st.number_input(
                "Max results per source:",
                min_value=10,
                max_value=500,
                value=max_results,
                step=10,
                help="Maximum number of articles to collect from each source"
            )
        
        with col2:
            st.markdown("**🔍 Search Preview:**")
            search_query_preview = " OR ".join([f'"{kw}"' for kw in included_keywords[:3]])
            if len(included_keywords) > 3:
                search_query_preview += " OR ..."
            
            st.code(search_query_preview, language="text")
            
            estimated_results = len(search_sources) * max_results_override
            st.metric("Estimated Results", estimated_results)
        
                # Start search button
        if search_sources:
            if st.button("🚀 Start Web Search", use_container_width=True, type="primary"):
                
                # Initialize searcher
                searcher = RobustAcademicSearcher(
                    max_results_per_source=max_results_override,
                    delay_range=(1, 2)
                )
                
                # Show progress
                progress_container = st.empty()
                status_container = st.empty()
                
                with progress_container.container():
                    st.markdown("**🔄 Search Progress:**")
                    progress_bar = st.progress(0)
                    
                    # Start search
                    start_time = time.time()
                    
                    try:
                        new_articles_df = searcher.search_all_sources(
                            keywords=included_keywords,
                            sources=search_sources,
                            logger=logger
                        )
                        
                        # Update progress
                        progress_bar.progress(1.0)
                        
                        # Get search statistics
                        search_stats = searcher.get_statistics()
                        
                        if not new_articles_df.empty:
                            # Handle append vs replace
                            if not existing_articles.empty and st.session_state.get("append_mode", True):
                                # Combine with existing articles
                                combined_df = pd.concat([existing_articles, new_articles_df], ignore_index=True)
                                
                                # Remove duplicates
                                combined_df = searcher.remove_duplicates(combined_df, logger)
                                
                                # Reassign IDs
                                combined_df['id'] = range(1, len(combined_df) + 1)
                                
                                final_df = combined_df
                                new_count = len(new_articles_df)
                                total_count = len(final_df)
                                
                                logger.success(f"Added {new_count} new articles. Total: {total_count}")
                                
                            else:
                                final_df = new_articles_df
                                new_count = len(final_df)
                                total_count = new_count
                                
                                logger.success(f"Collected {new_count} articles")
                            
                            # Save articles
                            save_raw_articles(project_id, final_df)
                            
                            # Update project status
                            projects_df = load_projects()
                            projects_df.loc[projects_df['project_id'] == project_id, 'status'] = 'Data Collected'
                            save_projects(projects_df)
                            
                            # Show results
                            elapsed_time = time.time() - start_time
                            
                            with status_container.container():
                                st.success(f"✅ Search completed in {elapsed_time:.1f} seconds!")
                                
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("New Articles", new_count)
                                
                                with col2:
                                    st.metric("Total Articles", total_count)
                                
                                with col3:
                                    successful_methods = len(search_stats.get('successful_methods', []))
                                    st.metric("Successful Methods", successful_methods)
                                
                                with col4:
                                    failed_methods = len(search_stats.get('failed_methods', []))
                                    st.metric("Failed Methods", failed_methods)
                                
                                # Show detailed statistics
                                if search_stats.get('failed_methods'):
                                    with st.expander("🔍 Search Details"):
                                        st.markdown("**Successful Methods:**")
                                        for method in search_stats.get('successful_methods', []):
                                            st.markdown(f"✅ {method}")
                                        
                                        st.markdown("**Failed Methods:**")
                                        for method in search_stats.get('failed_methods', []):
                                            st.markdown(f"❌ {method}")
                                        
                                        success_rate = search_stats.get('success_rate', 0)
                                        st.metric("Success Rate", f"{success_rate:.1%}")
                                
                                st.info("🔄 **Next Steps:** Go to the Screening tab to review and filter the collected articles.")
                        
                        else:
                            with status_container.container():
                                st.warning("⚠️ No articles found with the current search parameters.")
                                
                                # Show detailed error information
                                if search_stats.get('failed_methods'):
                                    st.error("🚨 **Search methods that failed:**")
                                    
                                    with st.expander("📋 Failed Methods"):
                                        for method in search_stats['failed_methods']:
                                            st.markdown(f"❌ {method}")
                                        
                                        st.markdown("**Common Solutions:**")
                                        st.markdown("• Check your internet connection")
                                        st.markdown("• Try different or broader keywords")
                                        st.markdown("• Reduce the number of results per source")
                                        st.markdown("• Wait a few minutes and try again (rate limiting)")
                                        st.markdown("• Some academic sites may be temporarily unavailable")
                                
                                st.info("💡 **Suggestions:**")
                                st.markdown("• Try broadening your keywords")
                                st.markdown("• Add more data sources")
                                st.markdown("• Check your inclusion criteria")
                                st.markdown("• Consider using more general search terms")
                    
                    except Exception as e:
                        progress_bar.progress(1.0)
                        with status_container.container():
                            st.error(f"❌ Search failed: {str(e)}")
                            logger.error(f"Web search failed: {str(e)}")
                            
                            # Try to get partial statistics
                            try:
                                search_stats = searcher.get_statistics()
                                if search_stats.get('failed_methods'):
                                    with st.expander("🔍 Error Analysis"):
                                        st.write("**Failed Methods:**")
                                        for method in search_stats['failed_methods']:
                                            st.markdown(f"• {method}")
                            except:
                                pass
        
        else:
            st.warning("⚠️ Please select at least one data source to search.")
        
        # Show recent search results if available
        if not existing_articles.empty:
            st.markdown("---")
            st.markdown("**📄 Recent Search Results Preview:**")
            
            # Show summary stats
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Articles", len(existing_articles))
            
            with col2:
                sources = existing_articles['source'].value_counts()
                st.metric("Sources", len(sources))
            
            with col3:
                years = existing_articles['year'].dropna()
                if not years.empty:
                    latest_year = int(years.max()) if years.max() > 0 else "Unknown"
                    st.metric("Latest Year", latest_year)
                else:
                    st.metric("Latest Year", "Unknown")
            
            with col4:
                abstracts_count = (existing_articles['abstract'].str.len() > 10).sum()
                st.metric("With Abstracts", abstracts_count)
            
            # Show sample articles
            st.markdown("**📋 Sample Articles:**")
            sample_articles = existing_articles.head(5)[['title', 'authors', 'year', 'source']]
            st.dataframe(sample_articles, use_container_width=True)

    with tab3:
        st.subheader("PDF Management")
        
        # Check if we have collected articles
        articles_df = load_raw_articles(project_id)
        
        if articles_df.empty:
            st.warning("⚠️ No articles collected yet. Please complete the web search first.")
            return
        
        # Initialize PDF downloader
        pdf_downloader = PDFDownloader(project_dir)
        
        # Show PDF download status
        st.markdown("**📄 PDF Download Status:**")
        
        # Add PDF status columns if they don't exist
        if 'pdf_status' not in articles_df.columns:
            articles_df['pdf_status'] = 'Not Attempted'
        
        if 'pdf_path' not in articles_df.columns:
            articles_df['pdf_path'] = ''
        
        # Count PDF statuses
        status_counts = articles_df['pdf_status'].value_counts()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Articles", len(articles_df))
        
        with col2:
            downloaded = status_counts.get('Downloaded', 0)
            st.metric("PDFs Downloaded", downloaded)
        
        with col3:
            failed = status_counts.get('Failed', 0)
            st.metric("Download Failed", failed)
        
        with col4:
            not_attempted = status_counts.get('Not Attempted', 0)
            st.metric("Not Attempted", not_attempted)
        
        # Bulk PDF download
        if not_attempted > 0:
            st.markdown("**🔄 Bulk PDF Download:**")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                max_downloads = st.number_input(
                    "Maximum PDFs to download:",
                    min_value=1,
                    max_value=min(50, not_attempted),
                    value=min(10, not_attempted),
                    help="Limit downloads to avoid overwhelming servers"
                )
            
            with col2:
                if st.button("📥 Download PDFs", use_container_width=True):
                    
                    # Get articles that need PDF download
                    to_download = articles_df[articles_df['pdf_status'] == 'Not Attempted'].head(max_downloads)
                    
                    if not to_download.empty:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for idx, (_, article) in enumerate(to_download.iterrows()):
                            status_text.text(f"Downloading: {article['title'][:50]}...")
                            
                            try:
                                pdf_path = pdf_downloader.download_pdf(
                                    article['url'],
                                    str(article['id']),
                                    article['title'],
                                    logger
                                )
                                
                                if pdf_path:
                                    articles_df.loc[articles_df['id'] == article['id'], 'pdf_status'] = 'Downloaded'
                                    articles_df.loc[articles_df['id'] == article['id'], 'pdf_path'] = pdf_path
                                else:
                                    articles_df.loc[articles_df['id'] == article['id'], 'pdf_status'] = 'Failed'
                            
                            except Exception as e:
                                articles_df.loc[articles_df['id'] == article['id'], 'pdf_status'] = 'Failed'
                                logger.error(f"PDF download failed for {article['title'][:50]}: {str(e)}")
                            
                            progress_bar.progress((idx + 1) / len(to_download))
                            time.sleep(1)  # Respectful delay
                        
                        # Save updated article data
                        save_raw_articles(project_id, articles_df)
                        
                        status_text.text("✅ PDF download completed!")
                        logger.success("Bulk PDF download completed")
                        
                        st.rerun()
        
        # Manual PDF upload section
        st.markdown("---")
        st.markdown("**📤 Manual PDF Upload:**")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Select article for PDF upload
            articles_without_pdf = articles_df[articles_df['pdf_status'] != 'Downloaded']
            
            if not articles_without_pdf.empty:
                selected_article_title = st.selectbox(
                    "Select article for PDF upload:",
                    options=articles_without_pdf['title'].tolist(),
                    key="pdf_upload_article"
                )
                
                uploaded_file = st.file_uploader(
                    "Upload PDF file:",
                    type=['pdf'],
                    key="manual_pdf_upload"
                )
                
                if uploaded_file and selected_article_title:
                    if st.button("💾 Save PDF"):
                        try:
                            # Get article info
                            article_row = articles_df[articles_df['title'] == selected_article_title].iloc[0]
                            article_id = article_row['id']
                            
                            # Save uploaded PDF
                            filename = f"{article_id}_{pdf_downloader.sanitize_filename(selected_article_title)}.pdf"
                            filepath = pdf_downloader.uploads_dir / filename
                            
                            with open(filepath, 'wb') as f:
                                f.write(uploaded_file.getvalue())
                            
                            # Update article data
                            articles_df.loc[articles_df['id'] == article_id, 'pdf_status'] = 'Downloaded'
                            articles_df.loc[articles_df['id'] == article_id, 'pdf_path'] = str(filepath)
                            
                            save_raw_articles(project_id, articles_df)
                            
                            st.success("✅ PDF uploaded successfully!")
                            logger.success(f"Manual PDF uploaded for: {selected_article_title[:50]}")
                            
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ Error uploading PDF: {str(e)}")
                            logger.error(f"Manual PDF upload failed: {str(e)}")
            else:
                st.info("✅ All articles already have PDFs!")
        
        with col2:
            # Show uploaded files
            uploaded_pdfs = pdf_downloader.get_uploaded_pdfs()
            
            if uploaded_pdfs:
                st.markdown("**📁 Uploaded Files:**")
                for pdf in uploaded_pdfs[:5]:  # Show first 5
                    size_mb = pdf['size'] / (1024 * 1024)
                    st.markdown(f"• {pdf['filename'][:30]}... ({size_mb:.1f} MB)")
                
                if len(uploaded_pdfs) > 5:
                    st.markdown(f"... and {len(uploaded_pdfs) - 5} more files")

    with tab4:
        st.subheader("Collection Summary")
        
        # Load final data
        articles_df = load_raw_articles(project_id)
        
        if articles_df.empty:
            st.info("📊 No data collected yet. Complete the web search to see summary statistics.")
            return
        
        # Overall statistics
        st.markdown("**📊 Collection Statistics:**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Articles", len(articles_df))
        
        with col2:
            unique_sources = articles_df['source'].nunique()
            st.metric("Data Sources", unique_sources)
        
        with col3:
            years = articles_df['year'].dropna()
            year_range = f"{int(years.min())}-{int(years.max())}" if not years.empty and years.min() > 0 else "Unknown"
            st.metric("Year Range", year_range)
        
        with col4:
            if 'pdf_status' in articles_df.columns:
                pdf_count = (articles_df['pdf_status'] == 'Downloaded').sum()
            else:
                pdf_count = 0
            st.metric("PDFs Available", pdf_count)
        
        # Source breakdown
        if 'source' in articles_df.columns:
            st.markdown("**📈 Articles by Source:**")
            source_counts = articles_df['source'].value_counts()
            
            # Create a simple bar chart
            chart_data = pd.DataFrame({
                'Source': source_counts.index,
                'Count': source_counts.values
            })
            
            st.bar_chart(chart_data.set_index('Source'))
        
        # Year distribution
        if 'year' in articles_df.columns:
            valid_years = articles_df[articles_df['year'] > 1900]['year']
            
            if not valid_years.empty:
                st.markdown("**📅 Publication Year Distribution:**")
                
                # Group by decade for better visualization
                decade_groups = (valid_years // 10) * 10
                decade_counts = decade_groups.value_counts().sort_index()
                
                decade_chart = pd.DataFrame({
                    'Decade': [f"{int(d)}s" for d in decade_counts.index],
                    'Count': decade_counts.values
                })
                
                st.bar_chart(decade_chart.set_index('Decade'))
        
        # Export options
        st.markdown("---")
        st.markdown("**📤 Export Options:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📝 Proceed to Screening", use_container_width=True):
                st.session_state.page = "Screening"
                logger.info("Proceeding to screening phase")
                st.rerun()
        
        with col2:
            # Export CSV
            csv_data = articles_df.to_csv(index=False)
            st.download_button(
                "💾 Download CSV",
                data=csv_data,
                file_name=f"collected_articles_{project_id}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col3:
            # Export metadata
            metadata = {
                "project_id": project_id,
                "collection_date": pd.Timestamp.now().isoformat(),
                "total_articles": len(articles_df),
                "sources": articles_df['source'].value_counts().to_dict(),
                "keywords_used": included_keywords,
                "search_config": search_config
            }
            
            metadata_json = json.dumps(metadata, indent=2)
            st.download_button(
                "📋 Download Metadata",
                data=metadata_json,
                file_name=f"collection_metadata_{project_id}.json",
                mime="application/json",
                use_container_width=True
            )


# Legacy function for backward compatibility
def display_data_collection_page():
    """Legacy function - use show() instead."""
    if 'logger' not in st.session_state:
        from src.components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)
