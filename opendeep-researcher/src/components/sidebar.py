import streamlit as st

def render_sidebar():
    """Render the project information sidebar."""
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
        
        # Main navigation - radio buttons
        st.markdown("### 📋 Navigation")
        pages = [
            "Dashboard",
            "Settings", 
            "Scoping",
            "Data Collection",
            "Screening",
            "Analysis",
            "Report"
        ]
        
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
        
        st.markdown("---")
        
        # Project status and workflow guide
        if current_project_id:
            st.markdown("### � Workflow Guide")
            current_page = st.session_state.get("page", "Dashboard")
            
            workflow_steps = [
                ("🏠", "Dashboard", "Manage projects"),
                ("⚙️", "Settings", "Configure AI models"),
                ("🎯", "Scoping", "Define research scope"),
                ("�", "Data Collection", "Search & collect articles"),
                ("�🔍", "Screening", "Filter articles"),
                ("📊", "Analysis", "Extract data"),
                ("📄", "Report", "Generate final report")
            ]
            
            for icon, page, description in workflow_steps:
                if page == current_page:
                    st.markdown(f"**{icon} {page}** ← Current")
                    st.caption(f"   {description}")
                else:
                    st.markdown(f"{icon} {page}")
                    st.caption(f"   {description}")
        else:
            st.markdown("### 💡 Getting Started")
            st.markdown("""
            1. **Create a project** on the Dashboard
            2. **Configure AI models** in Settings
            3. **Define your scope** in Scoping
            4. **Screen articles** in Screening
            5. **Extract data** in Analysis
            6. **Generate report** in Report
            """)
        
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.caption("OpenDeepResearcher v1.0")
        st.caption("AI-Powered Systematic Reviews")
    
    return selected_page  # Return the selected page for navigation