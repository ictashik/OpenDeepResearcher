import streamlit as st
import pandas as pd
from src.utils.data_manager import load_raw_articles, save_screened_articles, save_raw_articles, get_project_dir
from src.utils.ollama_client import OllamaClient
from src.utils.data_manager import load_config
from src.utils.streamlit_utils import safe_bar_chart, safe_download_button

def show(logger):
    """Article screening page."""
    st.title("🔍 Article Screening")
    st.markdown("---")

    # Check if project is selected
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        st.warning("⚠️ Please select a project from the Dashboard first.")
        return

    logger.info(f"Loading screening page for project: {project_id}")

    # Load collected articles
    articles_df = load_raw_articles(project_id)
    
    if articles_df.empty:
        st.warning("⚠️ No articles found. Please complete the Data Collection phase first.")
        return
    
    # Ensure DataFrame has the basic structure
    if not isinstance(articles_df, pd.DataFrame):
        st.error("❌ Invalid data format. Please check the collected articles.")
        logger.error("Articles data is not a proper DataFrame")
        return
    
    # Initialize required columns safely
    required_columns = ['ai_recommendation', 'ai_reasoning', 'final_decision', 'reviewer_notes']
    for col in required_columns:
        if col not in articles_df.columns:
            articles_df[col] = ""
    
    # Ensure data types are correct and handle any problematic values
    try:
        # Convert critical columns to string type to avoid type issues
        articles_df['ai_recommendation'] = articles_df['ai_recommendation'].astype(str)
        articles_df['ai_reasoning'] = articles_df['ai_reasoning'].astype(str)
        articles_df['final_decision'] = articles_df['final_decision'].astype(str)
        articles_df['reviewer_notes'] = articles_df['reviewer_notes'].astype(str)
        
        # Replace 'nan' strings with empty strings
        for col in required_columns:
            articles_df.loc[articles_df[col] == 'nan', col] = ""
            
    except Exception as e:
        st.error(f"Error initializing columns: {str(e)}")
        logger.error(f"Column initialization error: {str(e)}")
        return
    
    logger.info(f"Loaded {len(articles_df)} articles for screening")
    
    st.success(f"📚 Found {len(articles_df)} articles ready for screening")

    # Initialize Ollama client
    config = load_config()
    ollama_client = OllamaClient()

    # Load inclusion criteria
    project_dir = get_project_dir(project_id)
    search_config_file = project_dir / "search_config.json"
    
    inclusion_criteria = ""
    if search_config_file.exists():
        import json
        with open(search_config_file, 'r') as f:
            search_config = json.load(f)
            inclusion_criteria = search_config.get("inclusion_criteria", "")

    # Create tabs for different screening phases
    tab1, tab2, tab3 = st.tabs([" AI Screening", "👤 Manual Review", " Results"])

    with tab1:
        st.subheader("AI-Powered Initial Screening")
        
        # Check if screening model is configured
        screening_model = config.get("screening_model", "")
        if not screening_model:
            st.error(" No screening model configured. Please configure models in Settings.")
            return
        
        st.info(f"Using model: **{screening_model}**")
        
        # Display inclusion criteria
        if inclusion_criteria:
            with st.expander(" Inclusion Criteria"):
                st.write(inclusion_criteria)
        else:
            st.warning(" No inclusion criteria found. Please complete the Scoping phase first.")
        
        # Count articles already screened
        screened_count = (articles_df['ai_recommendation'] != "").sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Articles", len(articles_df))
        
        with col2:
            st.metric("AI Screened", screened_count)
        
        with col3:
            st.metric("Remaining", len(articles_df) - screened_count)
        
        # Bulk AI screening
        if screened_count < len(articles_df):
            if st.button(" Run AI Screening for All Articles", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, (_, article) in enumerate(articles_df.iterrows()):
                    if article['ai_recommendation'] == "":  # Only screen unscreened articles
                        status_text.text(f"Screening: {article['title'][:50]}...")
                        
                        try:
                            result = ollama_client.screen_article(
                                article['title'],
                                article.get('abstract', ''),
                                inclusion_criteria
                            )
                            
                            articles_df.loc[idx, 'ai_recommendation'] = result.get('recommendation', 'Unknown')
                            articles_df.loc[idx, 'ai_reasoning'] = result.get('reasoning', 'No reasoning provided')
                            
                            logger.info(f"AI screened: {article['title'][:50]}... -> {result.get('recommendation')}")
                            
                        except Exception as e:
                            logger.error(f"Error screening {article['title'][:50]}...: {str(e)}")
                            articles_df.loc[idx, 'ai_recommendation'] = 'Error'
                            articles_df.loc[idx, 'ai_reasoning'] = f'Error: {str(e)}'
                    
                    progress_bar.progress((idx + 1) / len(articles_df))
                
                status_text.text(" AI screening complete!")
                
                # Save results
                save_raw_articles(project_id, articles_df)
                logger.success("AI screening completed and saved")
                st.success("AI screening completed!")
                st.rerun()
        
        # Individual article screening
        if screened_count > 0:
            st.markdown("---")
            st.markdown("**Individual Article Processing:**")
            
            # Filter for unscreened articles
            unscreened_articles = articles_df[articles_df['ai_recommendation'] == ""]
            
            if not unscreened_articles.empty:
                for idx, (_, article) in enumerate(unscreened_articles.iterrows()):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f" {article['title'][:80]}...")
                    
                    with col2:
                        if st.button(f"Screen", key=f"screen_{idx}"):
                            with st.spinner("Screening..."):
                                try:
                                    result = ollama_client.screen_article(
                                        article['title'],
                                        article.get('abstract', ''),
                                        inclusion_criteria
                                    )
                                    
                                    article_idx = articles_df[articles_df['title'] == article['title']].index[0]
                                    articles_df.loc[article_idx, 'ai_recommendation'] = result.get('recommendation', 'Unknown')
                                    articles_df.loc[article_idx, 'ai_reasoning'] = result.get('reasoning', 'No reasoning provided')
                                    
                                    save_raw_articles(project_id, articles_df)
                                    
                                    st.success(f" {result.get('recommendation')}")
                                    logger.success(f"Screened: {article['title'][:50]}... -> {result.get('recommendation')}")
                                    
                                except Exception as e:
                                    st.error(f" Error: {str(e)}")
                                    logger.error(f"Error screening {article['title'][:50]}...: {str(e)}")

    with tab2:
        st.subheader("Manual Review & Final Decisions")
        
        # Filter articles that have AI recommendations
        screened_articles = articles_df[articles_df['ai_recommendation'] != ""].copy()
        
        if screened_articles.empty:
            st.warning("📋 No AI-screened articles available. Please run AI screening first.")
        else:
            # Add final decision column if it doesn't exist
            if 'final_decision' not in screened_articles.columns:
                screened_articles['final_decision'] = screened_articles['ai_recommendation']
            
            if 'reviewer_notes' not in screened_articles.columns:
                screened_articles['reviewer_notes'] = ""
            
            st.markdown(f"**Review {len(screened_articles)} AI-screened articles:**")
            
            # Summary of AI recommendations
            ai_include = (screened_articles['ai_recommendation'] == 'Include').sum()
            ai_exclude = (screened_articles['ai_recommendation'] == 'Exclude').sum()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("AI Recommended Include", ai_include)
            
            with col2:
                st.metric("AI Recommended Exclude", ai_exclude)
            
            with col3:
                st.metric("Uncertain/Error", len(screened_articles) - ai_include - ai_exclude)
            
            # Interactive table for manual review
            st.markdown("**Manual Review Table:**")
            
            # Prepare data for editing
            display_df = screened_articles[['title', 'authors', 'year', 'ai_recommendation', 'ai_reasoning', 'final_decision', 'reviewer_notes']].copy()
            
            edited_df = st.data_editor(
                display_df,
                use_container_width=True,
                column_config={
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "authors": st.column_config.TextColumn("Authors", width="medium"),
                    "year": st.column_config.NumberColumn("Year", width="small"),
                    "ai_recommendation": st.column_config.TextColumn("AI Recommendation", width="small", disabled=True),
                    "ai_reasoning": st.column_config.TextColumn("AI Reasoning", width="large", disabled=True),
                    "final_decision": st.column_config.SelectboxColumn(
                        "Final Decision",
                        options=["Include", "Exclude", "Uncertain"],
                        width="small"
                    ),
                    "reviewer_notes": st.column_config.TextColumn("Reviewer Notes", width="large")
                },
                disabled=["ai_recommendation", "ai_reasoning"],
                key="manual_review_table"
            )
            
            # Save manual review decisions
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button(" Save Manual Review", use_container_width=True):
                    # Update the original dataframe with manual decisions
                    for idx, row in edited_df.iterrows():
                        mask = (articles_df['title'] == row['title']) & (articles_df['authors'] == row['authors'])
                        articles_df.loc[mask, 'final_decision'] = row['final_decision']
                        articles_df.loc[mask, 'reviewer_notes'] = row['reviewer_notes']
                    
                    # Save screened articles
                    save_screened_articles(project_id, articles_df)
                    
                    logger.success("Manual review decisions saved")
                    st.success("Manual review decisions saved successfully!")
            
            with col2:
                if st.button(" Generate Screening Report", use_container_width=True):
                    try:
                        # Generate screening statistics with safe comparisons
                        final_include = (edited_df['final_decision'].str.lower() == 'include').sum()
                        final_exclude = (edited_df['final_decision'].str.lower() == 'exclude').sum()
                        uncertain = (edited_df['final_decision'].str.lower() == 'uncertain').sum()
                        
                        # Safe comparisons for agreement analysis
                        ai_include_manual_include = ((edited_df['ai_recommendation'].str.lower() == 'include') & 
                                                   (edited_df['final_decision'].str.lower() == 'include')).sum()
                        ai_exclude_manual_exclude = ((edited_df['ai_recommendation'].str.lower() == 'exclude') & 
                                                   (edited_df['final_decision'].str.lower() == 'exclude')).sum()
                        disagreements = (edited_df['ai_recommendation'].str.lower() != edited_df['final_decision'].str.lower()).sum()
                        
                        report = f"""
                        ## Screening Report
                        
                        **Total Articles Screened:** {len(edited_df)}
                        
                        **Final Decisions:**
                        - Include: {final_include}
                        - Exclude: {final_exclude}
                        - Uncertain: {uncertain}
                        
                        **AI vs Manual Agreement:**
                        - AI Include → Manual Include: {ai_include_manual_include}
                        - AI Exclude → Manual Exclude: {ai_exclude_manual_exclude}
                        - Disagreements: {disagreements}
                        """
                        
                        st.markdown(report)
                        
                    except Exception as e:
                        st.error(f"Error generating screening report: {str(e)}")
                        logger.error(f"Screening report error: {str(e)}")

    with tab3:
        st.subheader("Screening Results Summary")
        
        try:
            # Ensure final_decision column exists and has proper values
            if 'final_decision' not in articles_df.columns:
                articles_df['final_decision'] = ""
            
            # Convert any non-string values to strings
            articles_df['final_decision'] = articles_df['final_decision'].astype(str)
            
            # Replace 'nan' strings with empty strings
            articles_df.loc[articles_df['final_decision'] == 'nan', 'final_decision'] = ""
            
            # Load final screened results with safer filtering
            mask = (articles_df['final_decision'].notna()) & (articles_df['final_decision'] != "") & (articles_df['final_decision'] != 'nan')
            screened_articles = articles_df[mask].copy()
            
            if screened_articles.empty:
                st.info("📋 No final screening decisions available yet.")
            else:
                # Summary statistics with safe comparisons
                total_screened = len(screened_articles)
                included = (screened_articles['final_decision'].str.lower() == 'include').sum()
                excluded = (screened_articles['final_decision'].str.lower() == 'exclude').sum()
                uncertain = (screened_articles['final_decision'].str.lower() == 'uncertain').sum()
                
        except Exception as e:
            st.error(f"Error in screening summary: {str(e)}")
            logger.error(f"Screening summary error: {str(e)}")
            # Debug information
            st.write("Debug info:")
            st.write(f"DataFrame columns: {list(articles_df.columns)}")
            if 'final_decision' in articles_df.columns:
                st.write(f"final_decision unique values: {articles_df['final_decision'].unique()}")
                st.write(f"final_decision data type: {articles_df['final_decision'].dtype}")
            return
        
        if screened_articles is not None and not screened_articles.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Screened", total_screened)
            
            with col2:
                st.metric("Included", included, delta=f"{included/total_screened*100:.1f}%")
            
            with col3:
                st.metric("Excluded", excluded, delta=f"{excluded/total_screened*100:.1f}%")
            
            with col4:
                st.metric("Uncertain", uncertain, delta=f"{uncertain/total_screened*100:.1f}%")
            
            # Visualizations
            st.markdown("**Screening Results Visualization:**")
            
            # Create a simple bar chart using Streamlit
            chart_data = pd.DataFrame({
                'Decision': ['Include', 'Exclude', 'Uncertain'],
                'Count': [included, excluded, uncertain]
            })
            
            safe_bar_chart(chart_data.set_index('Decision'))
            
            # Show included articles
            if included > 0:
                st.markdown("**Articles Selected for Full-Text Review:**")
                
                # Safe filtering for included articles
                try:
                    included_articles = screened_articles[screened_articles['final_decision'].str.lower() == 'include']
                except Exception as e:
                    st.error(f"Error filtering included articles: {str(e)}")
                    included_articles = pd.DataFrame()  # Empty dataframe as fallback
                
                for _, article in included_articles.iterrows():
                    with st.expander(f" {article['title']}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**Authors:** {article.get('authors', 'Unknown')}")
                            st.markdown(f"**Year:** {article.get('year', 'Unknown')}")
                            if 'abstract' in article and article['abstract']:
                                st.markdown(f"**Abstract:** {article['abstract'][:300]}...")
                        
                        with col2:
                            st.markdown(f"**AI Rec:** {article.get('ai_recommendation', 'None')}")
                            st.markdown(f"**Source:** {article.get('source', 'Unknown')}")
                            if article.get('reviewer_notes'):
                                st.markdown(f"**Notes:** {article['reviewer_notes']}")
            
            # Export options
            st.markdown("---")
            st.markdown("**Export Options:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(" Proceed to Full-Text Analysis", use_container_width=True):
                    if included > 0:
                        # Add full-text status column
                        articles_df['full_text_status'] = 'Awaiting'
                        save_screened_articles(project_id, articles_df)
                        
                        # Navigate to analysis page
                        st.session_state.page = "Analysis"
                        logger.success("Proceeding to full-text analysis phase")
                        st.rerun()
                    else:
                        st.error("No articles included for full-text analysis")
            
            with col2:
                if st.button(" Export Results", use_container_width=True):
                    # Create downloadable CSV
                    csv = screened_articles.to_csv(index=False)
                    safe_download_button(
                        label="⬇️ Download Screening Results",
                        data=csv,
                        file_name=f"screening_results_{project_id}.csv",
                        mime="text/csv"
                    )

# Legacy function for backward compatibility
def display_screening_page():
    """Legacy function - use show() instead."""
    if 'logger' not in st.session_state:
        from src.components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)