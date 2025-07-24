import streamlit as st
import pandas as pd
from utils.data_manager import load_projects, create_project, ensure_data_structure

def show(logger):
    """Dashboard page for project management."""
    st.subheader("Project Dashboard")
    
    # Ensure data structure exists
    ensure_data_structure()
    
    # Load existing projects
    projects_df = load_projects()
    
    # Create two columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Existing Projects")
        
        if not projects_df.empty:
            # Display projects in a nice format
            for _, project in projects_df.iterrows():
                with st.container():
                    st.markdown(f"**{project['title']}**")
                    st.markdown(f"*{project['description']}*")
                    st.markdown(f"Created: {project['created_date']} | Status: {project['status']}")
                    
                    col_select, col_details = st.columns([1, 3])
                    
                    with col_select:
                        if st.button(f"Select", key=f"select_{project['project_id']}"):
                            st.session_state.current_project_id = project['project_id']
                            st.session_state.current_project_title = project['title']
                            logger.success(f"Selected project: {project['title']}")
                            st.rerun()
                    
                    with col_details:
                        with st.expander("Research Question"):
                            st.write(project.get('research_question', 'No research question defined'))
                    
                    st.markdown("---")
        else:
            st.info("No projects found. Create your first project to get started!")
    
    with col2:
        st.markdown("#### Create New Project")
        
        with st.form("create_project_form"):
            title = st.text_input("Project Title", placeholder="e.g., Effects of Exercise on Mental Health")
            description = st.text_area("Description", placeholder="Brief description of your systematic review...")
            research_question = st.text_area(
                "Research Question", 
                placeholder="e.g., What are the effects of regular exercise on symptoms of depression in adults?"
            )
            
            submitted = st.form_submit_button("Create Project")
            
            if submitted:
                if title and description and research_question:
                    try:
                        project_id = create_project(title, description, research_question)
                        st.session_state.current_project_id = project_id
                        st.session_state.current_project_title = title
                        logger.success(f"Created new project: {title} (ID: {project_id})")
                        st.success("Project created successfully!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Failed to create project: {str(e)}")
                        st.error(f"Failed to create project: {str(e)}")
                else:
                    st.error("Please fill in all fields")
    
    # Current project status
    if st.session_state.get("current_project_id"):
        st.markdown("---")
        st.markdown("#### Current Project")
        
        current_project_id = st.session_state.current_project_id
        current_project = projects_df[projects_df['project_id'] == current_project_id].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Project", current_project['title'])
        
        with col2:
            st.metric("Status", current_project['status'])
        
        with col3:
            st.metric("Created", current_project['created_date'])
        
        # Progress indicators
        st.markdown("#### Progress Overview")
        
        progress_steps = [
            {"name": "Scoping", "status": "Complete" if current_project['status'] != "Planning" else "Pending"},
            {"name": "Data Collection", "status": "Pending"},
            {"name": "Screening", "status": "Pending"},
            {"name": "Full-Text Analysis", "status": "Pending"},
            {"name": "Report Generation", "status": "Pending"}
        ]
        
        for step in progress_steps:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{step['name']}**")
            with col2:
                st.write(step['status'])
        
        # Quick actions
        st.markdown("#### Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Start Scoping", use_container_width=True):
                st.session_state.page = "Scoping"
                st.rerun()
        
        with col2:
            if st.button("Configure Settings", use_container_width=True):
                st.session_state.page = "Settings"
                st.rerun()
        
        with col3:
            if st.button("View Progress", use_container_width=True):
                st.info("Detailed progress tracking coming soon!")
    else:
        st.info("Select or create a project to get started!")

# Legacy function for backward compatibility
def dashboard():
    """Legacy function - use show() instead.""" 
    if 'logger' not in st.session_state:
        from components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)