import streamlit as st

def render_sidebar():
    """Render the main navigation sidebar."""
    with st.sidebar:
        # Current project display
        st.markdown("### 🔬 Current Project")
        current_project_id = st.session_state.get("current_project_id", None)
        current_project_title = st.session_state.get("current_project_title", "No project selected")
        
        if current_project_id:
            st.success(f"**{current_project_title}**")
            st.caption(f"ID: {current_project_id}")
        else:
            st.warning("**No project selected**")
            st.caption("Select a project from Dashboard")
        
        st.markdown("---")
        
        # Main navigation - radio buttons that work reliably
        st.markdown("### 📋 Navigation")
        pages = [
            "Dashboard",
            "Settings", 
            "Scoping",
            "Screening",
            "Analysis",
            "Report"
        ]
        
        # Use radio buttons for reliable navigation
        current_page = st.session_state.get("page", "Dashboard")
        try:
            current_index = pages.index(current_page)
        except ValueError:
            current_index = 0
        
        selected_page = st.radio(
            "Navigate to:",
            pages,
            index=current_index,
            key="sidebar_navigation"
        )
        
        # Project workflow guide if project selected
        if current_project_id:
            st.markdown("---")
            st.markdown("### 📈 Current Step")
            st.caption(f"You are on: **{selected_page}**")
        
        return selected_page
