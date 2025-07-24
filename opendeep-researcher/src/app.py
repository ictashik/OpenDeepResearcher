import streamlit as st
from pathlib import Path
from src.components.sidebar import render_sidebar
from src.components.logger import Logger
from src.pages import dashboard, settings, scoping, data_collection, screening, analysis, report

def main():
    st.set_page_config(
        page_title="OpenDeepResearcher", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Ensure data directory exists
    data_dir = Path("../data")
    data_dir.mkdir(exist_ok=True)
    
    # Initialize logger
    if 'logger' not in st.session_state:
        st.session_state.logger = Logger()
    
    logger = st.session_state.logger
    
    # App title at the top
    st.title("OpenDeepResearcher")
    st.markdown("---")
    
    # Render sidebar for navigation
    selected_page = render_sidebar()
    
    # Update session state with selected page and force rerun if changed
    current_page = st.session_state.get("page", "Dashboard")
    if selected_page and selected_page != current_page:
        st.session_state.page = selected_page
        st.rerun()
    elif not st.session_state.get("page"):
        st.session_state.page = "Dashboard"

    # Main content area
    page = st.session_state.get("page", "Dashboard")
    
    # Create main content container
    main_container = st.container()
    with main_container:
        if page == "Dashboard":
            dashboard.show(logger)
        elif page == "Settings":
            settings.show(logger)
        elif page == "Scoping":
            scoping.show(logger)
        elif page == "Data Collection":
            data_collection.show(logger)
        elif page == "Screening":
            screening.show(logger)
        elif page == "Analysis":
            analysis.show(logger)
        elif page == "Report":
            report.show(logger)

    # Terminal at bottom - simpler approach
    st.markdown("---")
    st.markdown("### 📟 Terminal")
    
    # Simple terminal styling
    st.markdown("""
    <style>
    /* Terminal styling */
    .terminal-area textarea {
        background-color: #1e1e1e !important;
        color: #d4d4d4 !important;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
        font-size: 12px !important;
        border: 1px solid #404040 !important;
        border-radius: 4px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display logger - wrapped in a div for styling
    st.markdown('<div class="terminal-area">', unsafe_allow_html=True)
    logger.display(height=180)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()