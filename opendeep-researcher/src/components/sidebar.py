import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.title("🔬 OpenDeepResearcher")
        st.markdown("---")
        
        # Project selection
        st.subheader("📁 Current Project")
        current_project = st.session_state.get("current_project_id", "No project selected")
        st.write(f"**{current_project}**")
        
        st.markdown("---")
        
        # Navigation
        st.subheader("🧭 Navigation")
        pages = [
            "Dashboard",
            "Settings", 
            "Scoping",
            "Screening",
            "Analysis",
            "Report"
        ]
        
        # Use radio buttons for navigation
        selected_page = st.radio(
            "Go to:",
            pages,
            index=pages.index(st.session_state.get("page", "Dashboard"))
        )
        
        return selected_page