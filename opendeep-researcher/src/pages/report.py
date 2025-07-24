import streamlit as st
import pandas as pd
from utils.data_manager import load_extracted_data, save_final_report, load_final_report, get_project_dir
from utils.ollama_client import OllamaClient
from utils.data_manager import load_config
from datetime import datetime

def show(logger):
    """Report generation page."""
    st.title("📄 Report Generation")
    st.markdown("---")

    # Check if project is selected
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        st.warning("⚠️ Please select a project from the Dashboard first.")
        return

    logger.info(f"Loading report generation for project: {project_id}")

    # Load extracted data
    extracted_data = load_extracted_data(project_id)
    
    if extracted_data.empty:
        st.warning("📊 No extracted data available for report generation.")
        st.info("💡 **Next steps:** Complete the Full-Text Analysis phase to extract data from your articles.")
        return

    st.success(f"Found extracted data from {len(extracted_data)} articles")

    # Initialize Ollama client
    config = load_config()
    ollama_client = OllamaClient()

    # Create tabs for different report aspects
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Data Summary", "📝 Report Generation", "✏️ Manual Editing", "💾 Export"])

    with tab1:
        st.subheader("Extracted Data Summary")
        
        # Show data overview
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Articles Analyzed", len(extracted_data))
        
        with col2:
            if 'extraction_date' in extracted_data.columns:
                latest_extraction = extracted_data['extraction_date'].max()
                st.metric("Latest Extraction", latest_extraction.split(' ')[0] if latest_extraction else "Unknown")
        
        with col3:
            total_fields = len([col for col in extracted_data.columns if col not in ['article_id', 'title', 'extraction_date']])
            st.metric("Data Fields", total_fields)
        
        # Data completeness analysis
        st.markdown("**Data Completeness Analysis:**")
        
        completeness_data = []
        for col in extracted_data.columns:
            if col not in ['article_id', 'title', 'extraction_date']:
                non_empty = extracted_data[col].notna().sum()
                completeness = (non_empty / len(extracted_data)) * 100
                completeness_data.append({
                    'Field': col.replace('_', ' ').title(),
                    'Articles with Data': non_empty,
                    'Total Articles': len(extracted_data),
                    'Completeness %': f"{completeness:.1f}%"
                })
        
        completeness_df = pd.DataFrame(completeness_data)
        st.dataframe(completeness_df, use_container_width=True)
        
        # Show extracted data table
        st.markdown("**Extracted Data Preview:**")
        
        # Prepare display data
        display_columns = ['title'] + [col for col in extracted_data.columns if col not in ['article_id', 'title', 'extraction_date']]
        display_data = extracted_data[display_columns].head(10)
        
        st.dataframe(display_data, use_container_width=True)
        
        if len(extracted_data) > 10:
            st.info(f"Showing first 10 rows of {len(extracted_data)} total articles")

    with tab2:
        st.subheader("AI-Generated Report")
        
        # Check if extraction model is configured
        extraction_model = config.get("extraction_model", "")
        if not extraction_model:
            st.error("❌ No extraction model configured. Please configure models in Settings.")
            return
        
        st.info(f"Using model: **{extraction_model}**")
        
        # Report generation options
        st.markdown("**Report Configuration:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_type = st.selectbox(
                "Report Type",
                options=["Systematic Review", "Meta-Analysis", "Narrative Review", "Scoping Review"],
                index=0
            )
        
        with col2:
            include_tables = st.checkbox("Include Data Tables", value=True)
        
        report_sections = st.multiselect(
            "Report Sections to Include",
            options=["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion", "Limitations", "References"],
            default=["Abstract", "Methods", "Results", "Discussion", "Conclusion"]
        )
        
        # Additional instructions
        additional_instructions = st.text_area(
            "Additional Instructions for AI",
            placeholder="e.g., Focus on clinical implications, include statistical analysis, emphasize methodological quality...",
            height=100
        )
        
        # Generate report button
        if st.button("🤖 Generate AI Report", use_container_width=True):
            with st.spinner("Generating comprehensive report... This may take a few minutes."):
                try:
                    # Prepare data for report generation
                    data_summary = extracted_data.to_string(index=False)
                    
                    # Create enhanced prompt
                    prompt_context = f"""
                    Report Type: {report_type}
                    Sections to Include: {', '.join(report_sections)}
                    Include Tables: {include_tables}
                    Additional Instructions: {additional_instructions}
                    
                    Number of Studies: {len(extracted_data)}
                    Data Fields: {', '.join([col for col in extracted_data.columns if col not in ['article_id', 'title', 'extraction_date']])}
                    """
                    
                    generated_report = ollama_client.generate_report(f"{prompt_context}\n\nExtracted Data:\n{data_summary}")
                    
                    if generated_report and "Failed to generate report" not in generated_report:
                        st.session_state.generated_report = generated_report
                        logger.success("AI report generated successfully")
                        st.success("✅ Report generated successfully!")
                        st.rerun()
                    else:
                        logger.error("Failed to generate AI report")
                        st.error("❌ Failed to generate report. Please try again.")
                        
                except Exception as e:
                    logger.error(f"Error generating report: {str(e)}")
                    st.error(f"❌ Error generating report: {str(e)}")
        
        # Display generated report
        if 'generated_report' in st.session_state:
            st.markdown("**Generated Report:**")
            
            report_content = st.session_state.generated_report
            
            # Show report in a text area for preview
            st.markdown(report_content)
            
            # Save generated report
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("💾 Save Generated Report"):
                    save_final_report(project_id, report_content)
                    logger.success("Generated report saved")
                    st.success("Report saved successfully!")
            
            with col2:
                if st.button("✏️ Edit Report"):
                    st.session_state.manual_report = report_content
                    logger.info("Report moved to manual editing")
                    st.info("Report moved to Manual Editing tab for further customization")

    with tab3:
        st.subheader("Manual Report Editing")
        
        # Load existing report or start with generated report
        existing_report = load_final_report(project_id)
        
        if 'manual_report' not in st.session_state:
            if existing_report:
                st.session_state.manual_report = existing_report
            else:
                st.session_state.manual_report = ""
        
        # Manual editing interface
        st.markdown("**Edit your report manually:**")
        
        manual_report = st.text_area(
            "Report Content (Markdown supported)",
            value=st.session_state.manual_report,
            height=600,
            help="You can use Markdown formatting for headers, lists, tables, etc."
        )
        
        # Update session state
        st.session_state.manual_report = manual_report
        
        # Report metadata
        col1, col2 = st.columns(2)
        
        with col1:
            report_title = st.text_input(
                "Report Title",
                value=f"Systematic Review: {st.session_state.get('current_project_title', 'Untitled Project')}"
            )
        
        with col2:
            authors = st.text_input(
                "Authors",
                placeholder="e.g., Smith, J., Doe, A."
            )
        
        # Additional metadata
        keywords = st.text_input(
            "Keywords",
            placeholder="e.g., systematic review, meta-analysis, healthcare"
        )
        
        # Save manual report
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Draft", use_container_width=True):
                # Add metadata to report
                full_report = f"""# {report_title}

**Authors:** {authors}
**Keywords:** {keywords}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{manual_report}
"""
                
                save_final_report(project_id, full_report)
                st.session_state.manual_report = full_report
                logger.success("Report draft saved")
                st.success("Draft saved successfully!")
        
        with col2:
            if st.button("👁️ Preview", use_container_width=True):
                st.markdown("**Preview:**")
                st.markdown(manual_report)
        
        with col3:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.manual_report = existing_report or ""
                st.rerun()

    with tab4:
        st.subheader("Export & Download")
        
        # Load final report
        final_report = load_final_report(project_id)
        
        if not final_report:
            st.warning("📄 No report available for export. Please generate or create a report first.")
        else:
            st.success("📄 Report ready for export")
            
            # Export options
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Download Options:**")
                
                # Download as Markdown
                st.download_button(
                    label="📁 Download as Markdown (.md)",
                    data=final_report,
                    file_name=f"systematic_review_{project_id}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                
                # Download extracted data as CSV
                if not extracted_data.empty:
                    csv_data = extracted_data.to_csv(index=False)
                    st.download_button(
                        label="📊 Download Extracted Data (.csv)",
                        data=csv_data,
                        file_name=f"extracted_data_{project_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with col2:
                st.markdown("**Report Statistics:**")
                
                word_count = len(final_report.split())
                char_count = len(final_report)
                line_count = len(final_report.split('\n'))
                
                st.metric("Word Count", word_count)
                st.metric("Character Count", char_count)
                st.metric("Line Count", line_count)
            
            # Report preview
            st.markdown("---")
            st.markdown("**Final Report Preview:**")
            
            with st.expander("📖 View Full Report", expanded=False):
                st.markdown(final_report)
            
            # Quality checklist
            st.markdown("---")
            st.markdown("**Quality Checklist:**")
            
            checklist_items = [
                "Research question clearly stated",
                "Search strategy described",
                "Inclusion/exclusion criteria defined",
                "Study selection process documented",
                "Data extraction methods explained",
                "Results appropriately synthesized",
                "Limitations acknowledged",
                "Conclusions supported by evidence"
            ]
            
            for item in checklist_items:
                st.checkbox(item, key=f"checklist_{item}")
            
            # Final actions
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📧 Prepare for Submission", use_container_width=True):
                    st.info("""
                    **Submission Preparation Checklist:**
                    - [ ] Format according to journal guidelines
                    - [ ] Include required sections
                    - [ ] Check citation format
                    - [ ] Review word count limits
                    - [ ] Prepare supplementary materials
                    """)
            
            with col2:
                if st.button("🎯 Project Complete", use_container_width=True):
                    # Mark project as complete
                    from utils.data_manager import load_projects, save_projects
                    projects_df = load_projects()
                    projects_df.loc[projects_df['project_id'] == project_id, 'status'] = 'Complete'
                    save_projects(projects_df)
                    
                    logger.success("Project marked as complete")
                    st.success("🎉 Project marked as complete! Congratulations on finishing your systematic review!")

# Legacy function for backward compatibility
def display_report():
    """Legacy function - use show() instead."""
    if 'logger' not in st.session_state:
        from components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)