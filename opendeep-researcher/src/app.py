import streamlit as st
from pathlib import Path
from components.sidebar import render_sidebar
from components.logger import Logger
from pages import dashboard, settings, scoping, screening, analysis, report

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
    
    # Update session state with selected page
    if selected_page:
        st.session_state.page = selected_page

    # Main content area
    page = st.session_state.get("page", "Dashboard")
    
    if page == "Dashboard":
        dashboard.show(logger)
    elif page == "Settings":
        settings.show(logger)
    elif page == "Scoping":
        scoping.show(logger)
    elif page == "Screening":
        screening.show(logger)
    elif page == "Analysis":
        analysis.show(logger)
    elif page == "Report":
        report.show(logger)

    # Fixed log panel at bottom - like VS Code terminal
    st.markdown("---")
    
    # Create a fixed-height log panel container
    log_container = st.container()
    with log_container:
        st.markdown("### 📟 Terminal")
        logger.display(height=200)  # Fixed height like VS Code terminal

if __name__ == "__main__":
    main()