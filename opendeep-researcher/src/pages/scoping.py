import streamlit as st
import pandas as pd
from src.utils.ollama_client import OllamaClient
from src.utils.data_manager import load_config, get_project_dir, load_projects, save_projects

def show(logger):
    """Scoping & Planning page."""
    st.subheader("Scoping & Planning")

    # Check if project is selected
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        st.warning("Please select a project from the Dashboard first.")
        return

    logger.info(f"Loading scoping page for project: {project_id}")

    # Load project details
    projects_df = load_projects()
    current_project = projects_df[projects_df['project_id'] == project_id].iloc[0]

    # Load saved scoping data if available
    project_dir = get_project_dir(project_id)
    
    # Load PICO framework if exists
    pico_file = project_dir / "pico_framework.json"
    if pico_file.exists() and 'pico_data' not in st.session_state:
        try:
            import json
            with open(pico_file, 'r') as f:
                st.session_state.pico_data = json.load(f)
                logger.info("Loaded saved PICO framework")
        except Exception as e:
            logger.error(f"Error loading PICO framework: {str(e)}")
    
    # Load keywords if exists
    keywords_file = project_dir / "keywords.csv"
    if keywords_file.exists() and 'keywords' not in st.session_state:
        try:
            keywords_df = pd.read_csv(keywords_file)
            st.session_state.keywords = keywords_df['keyword'].tolist()
            st.session_state.keyword_states = {
                row['keyword']: {'include': row.get('include', True), 'category': row.get('category', '')}
                for _, row in keywords_df.iterrows()
            }
            logger.info(f"Loaded {len(st.session_state.keywords)} saved keywords")
        except Exception as e:
            logger.error(f"Error loading keywords: {str(e)}")

    # Initialize Ollama client
    config = load_config()
    ollama_client = OllamaClient()

    # Create tabs for different scoping phases
    tab1, tab2, tab3, tab4 = st.tabs(["Problem Formulation", "PICO Framework", "Keywords", "Sources"])

    with tab1:
        st.subheader("Problem Formulation")
        st.markdown("Define and refine your research question for the systematic review.")
        
        # Display current research question
        st.markdown("**Current Research Question:**")
        research_question = st.text_area(
            "Research Question",
            value=current_project.get('research_question', ''),
            height=100,
            help="Your main research question that will guide the systematic review"
        )
        
        # Save updated research question
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Update Research Question"):
                projects_df.loc[projects_df['project_id'] == project_id, 'research_question'] = research_question
                save_projects(projects_df)
                logger.success("Research question updated and saved")
                st.success("Research question updated successfully!")
        
        with col2:
            # Show save status
            if research_question and research_question == current_project.get('research_question', ''):
                st.success("✅ Saved")
            elif research_question != current_project.get('research_question', ''):
                st.warning("⚠️ Unsaved changes")
        
        # Research question guidelines
        with st.expander("Research Question Guidelines"):
            st.markdown("""
            **A good research question should be:**
            - **Specific**: Clearly defined population, intervention, and outcome
            - **Answerable**: Feasible to answer with available evidence
            - **Relevant**: Important to the field and practice
            - **Structured**: Following the PICO framework when applicable
            
            **Examples:**
            - "What are the effects of cognitive behavioral therapy on anxiety symptoms in adults with generalized anxiety disorder?"
            - "How does exercise intervention compare to standard care in improving depression scores in elderly patients?"
            """)

    with tab2:
        st.subheader("PICO Framework Breakdown")
        st.markdown("Break down your research question into structured components.")
        
        if not research_question:
            st.warning("Please enter a research question in the Problem Formulation tab first.")
        else:
            # Check if AI model is configured
            screening_model = config.get("screening_model", "")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Research Question:** {research_question}")
            
            with col2:
                if not screening_model:
                    st.error("No model configured")
                    st.markdown("Please configure a model in Settings")
                else:
                    if st.button("Generate PICO", use_container_width=True):
                        with st.spinner("Generating PICO framework..."):
                            pico_data = ollama_client.generate_pico_framework(research_question)
                            
                            if "error" not in pico_data:
                                st.session_state.pico_data = pico_data
                                logger.success("PICO framework generated successfully")
                                st.success("PICO framework generated!")
                                st.rerun()
                            else:
                                logger.error(f"PICO generation failed: {pico_data['error']}")
                                st.error(f"Failed to generate PICO: {pico_data['error']}")
            
            # Display PICO results
            if 'pico_data' in st.session_state:
                pico_data = st.session_state.pico_data
                
                st.markdown("**Generated PICO Framework:**")
                
                pico_fields = ["Population", "Intervention", "Comparison", "Outcome"]
                updated_pico = {}
                
                for field in pico_fields:
                    updated_pico[field] = st.text_area(
                        f"**{field}**",
                        value=pico_data.get(field, ""),
                        height=80,
                        key=f"pico_{field.lower()}"
                    )
                
                # Save PICO data
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if st.button("Save PICO Framework"):
                        # Save to project directory
                        project_dir = get_project_dir(project_id)
                        pico_file = project_dir / "pico_framework.json"
                        
                        import json
                        with open(pico_file, 'w') as f:
                            json.dump(updated_pico, f, indent=2)
                        
                        st.session_state.pico_data = updated_pico
                        logger.success("PICO framework saved successfully")
                        st.success("PICO framework saved successfully!")
                
                with col2:
                    # Show save status
                    pico_file = get_project_dir(project_id) / "pico_framework.json"
                    if pico_file.exists():
                        st.success("✅ Saved")
                    else:
                        st.warning("⚠️ Not saved")

    with tab3:
        st.subheader("Search Keywords Generation")
        st.markdown("Generate and refine search keywords based on your PICO framework.")
        
        # Check if PICO data exists
        pico_data = st.session_state.get('pico_data', {})
        
        if not pico_data:
            st.warning("Please generate the PICO framework first.")
        else:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Current PICO Components:**")
                for field, value in pico_data.items():
                    if value:
                        st.markdown(f"• **{field}:** {value[:100]}{'...' if len(value) > 100 else ''}")
            
            with col2:
                if st.button("Generate Keywords", use_container_width=True):
                    with st.spinner("Generating keywords..."):
                        keywords = ollama_client.generate_keywords(pico_data)
                        
                        if keywords and keywords[0] != "Failed to generate keywords":
                            st.session_state.keywords = keywords
                            logger.success(f"Generated {len(keywords)} keywords")
                            st.success(f"Generated {len(keywords)} keywords!")
                            st.rerun()
                        else:
                            logger.error("Keyword generation failed")
                            st.error("Failed to generate keywords")
            
            # Display and edit keywords
            if 'keywords' in st.session_state:
                st.markdown("**Generated Keywords:**")
                
                # Initialize keyword states if not exists
                if 'keyword_states' not in st.session_state:
                    st.session_state.keyword_states = {
                        kw: {'include': True, 'category': ''} 
                        for kw in st.session_state.keywords
                    }
                
                # Display keywords with checkboxes and category selection
                updated_keywords = []
                
                for i, keyword in enumerate(st.session_state.keywords):
                    col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
                    
                    with col1:
                        # Allow editing the keyword text
                        edited_kw = st.text_input(
                            f"Keyword {i+1}",
                            value=keyword,
                            key=f"kw_text_{i}",
                            label_visibility="collapsed"
                        )
                    
                    with col2:
                        # Include checkbox
                        include = st.checkbox(
                            "Include",
                            value=st.session_state.keyword_states.get(keyword, {}).get('include', True),
                            key=f"kw_include_{i}"
                        )
                    
                    with col3:
                        # Category selection
                        category = st.selectbox(
                            "Category",
                            options=["", "Population", "Intervention", "Comparison", "Outcome", "General"],
                            index=0,
                            key=f"kw_category_{i}",
                            label_visibility="collapsed"
                        )
                    
                    with col4:
                        # Delete button
                        if st.button("Delete", key=f"kw_delete_{i}", help="Delete keyword"):
                            continue  # Skip adding this keyword
                    
                    # Add to updated list if not deleted
                    updated_keywords.append({
                        'keyword': edited_kw,
                        'include': include,
                        'category': category
                    })
                
                # Add new keyword section
                st.markdown("**Add New Keywords:**")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    new_keyword = st.text_input("New keyword", key="new_keyword_input")
                
                with col2:
                    if st.button("Add") and new_keyword:
                        updated_keywords.append({
                            'keyword': new_keyword,
                            'include': True,
                            'category': ''
                        })
                        st.rerun()
                
                # Update session state
                st.session_state.keywords = [kw['keyword'] for kw in updated_keywords]
                st.session_state.keyword_states = {
                    kw['keyword']: {'include': kw['include'], 'category': kw['category']}
                    for kw in updated_keywords
                }
                
                # Save keywords
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    if st.button("Save Keywords"):
                        project_dir = get_project_dir(project_id)
                        keywords_file = project_dir / "keywords.csv"
                        # Create DataFrame from current keyword data
                        keywords_df = pd.DataFrame([
                            {
                                'keyword': kw,
                                'include': st.session_state.keyword_states.get(kw, {}).get('include', True),
                                'category': st.session_state.keyword_states.get(kw, {}).get('category', '')
                            }
                            for kw in st.session_state.keywords
                        ])
                        keywords_df.to_csv(keywords_file, index=False)
                        
                        logger.success("Keywords saved successfully")
                        st.success("Keywords saved successfully!")
                
                with col2:
                    if st.button("Export Search String"):
                        # Generate search strings for different databases
                        included_keywords = [
                            kw for kw in st.session_state.keywords
                            if st.session_state.keyword_states.get(kw, {}).get('include', True)
                        ]
                        
                        # Basic search string (OR combination)
                        search_string = " OR ".join([f'"{kw}"' for kw in included_keywords])
                        
                        st.text_area(
                            "Search String (Basic)",
                            value=search_string,
                            height=100
                        )
                        
                        logger.info("Search string generated")
                
                with col3:
                    # Show save status
                    keywords_file = get_project_dir(project_id) / "keywords.csv"
                    if keywords_file.exists():
                        st.success("✅ Saved")
                    else:
                        st.warning("⚠️ Not saved")

    with tab4:
        st.subheader("Data Source Selection")
        st.markdown("Select databases and sources to search for relevant literature.")
        
        # Load saved search configuration if exists
        search_config_file = project_dir / "search_config.json"
        saved_search_config = {}
        if search_config_file.exists():
            try:
                import json
                with open(search_config_file, 'r') as f:
                    saved_search_config = json.load(f)
                    logger.info("Loaded saved search configuration")
            except Exception as e:
                logger.error(f"Error loading search configuration: {str(e)}")
        
        # Available sources
        available_sources = {
            "PubMed/MEDLINE": {
                "description": "Biomedical literature database",
                "best_for": "Medical and health sciences research",
                "coverage": "1946-present"
            },
            "Google Scholar": {
                "description": "Broad academic search engine",
                "best_for": "Multidisciplinary research, grey literature",
                "coverage": "Varies"
            },
            "Scopus": {
                "description": "Abstract and citation database",
                "best_for": "Science, technology, medicine, social sciences",
                "coverage": "1970-present"
            },
            "Web of Science": {
                "description": "Citation database",
                "best_for": "Cross-disciplinary research",
                "coverage": "1900-present"
            },
            "EMBASE": {
                "description": "Biomedical database",
                "best_for": "Pharmacology, clinical medicine",
                "coverage": "1947-present"
            },
            "PsycINFO": {
                "description": "Psychology database",
                "best_for": "Psychology and behavioral sciences",
                "coverage": "1800s-present"
            }
        }
        
        # Load saved selections or use defaults
        default_sources = saved_search_config.get("selected_sources", 
                                                 config.get("search_sources", ["PubMed/MEDLINE", "Google Scholar"]))
        
        st.markdown("**Select databases to search:**")
        
        selected_sources = []
        for source, details in available_sources.items():
            col1, col2 = st.columns([1, 3])
            
            with col1:
                selected = st.checkbox(
                    source,
                    value=source in default_sources,
                    key=f"source_{source}"
                )
                if selected:
                    selected_sources.append(source)
            
            with col2:
                with st.expander(f"About {source}"):
                    st.markdown(f"**Description:** {details['description']}")
                    st.markdown(f"**Best for:** {details['best_for']}")
                    st.markdown(f"**Coverage:** {details['coverage']}")
        
        # Search parameters
        st.markdown("---")
        st.markdown("**Search Parameters:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_results = st.number_input(
                "Maximum results per database",
                min_value=10,
                max_value=1000,
                value=saved_search_config.get("max_results_per_source", 
                                             config.get("max_results_per_source", 100)),
                step=10
            )
        
        with col2:
            date_filter_options = ["No filter", "Last 5 years", "Last 10 years", "Last 20 years", "Custom range"]
            saved_date_filter = saved_search_config.get("date_filter", "No filter")
            date_filter_index = date_filter_options.index(saved_date_filter) if saved_date_filter in date_filter_options else 0
            
            date_filter = st.selectbox(
                "Publication date filter",
                options=date_filter_options,
                index=date_filter_index
            )
        
        # Custom date range
        if date_filter == "Custom range":
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.number_input(
                    "Start year", 
                    min_value=1900, 
                    max_value=2025, 
                    value=saved_search_config.get("start_year", 2000)
                )
            with col2:
                end_year = st.number_input(
                    "End year", 
                    min_value=1900, 
                    max_value=2025, 
                    value=saved_search_config.get("end_year", 2025)
                )
        
        # Inclusion/Exclusion criteria
        st.markdown("---")
        st.markdown("**Inclusion/Exclusion Criteria:**")
        
        inclusion_criteria = st.text_area(
            "Inclusion Criteria",
            value=saved_search_config.get("inclusion_criteria", ""),
            placeholder="e.g., Randomized controlled trials, adult participants, published in English...",
            height=100
        )
        
        exclusion_criteria = st.text_area(
            "Exclusion Criteria",
            value=saved_search_config.get("exclusion_criteria", ""),
            placeholder="e.g., Animal studies, case reports, non-English publications...",
            height=100
        )
        
        # Save configuration
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("Save Search Configuration", use_container_width=True):
                search_config = {
                    "selected_sources": selected_sources,
                    "max_results_per_source": max_results,
                    "date_filter": date_filter,
                    "inclusion_criteria": inclusion_criteria,
                    "exclusion_criteria": exclusion_criteria
                }
                
                if date_filter == "Custom range":
                    search_config["start_year"] = start_year
                    search_config["end_year"] = end_year
                
                # Save to project directory
                project_dir = get_project_dir(project_id)
                import json
                with open(project_dir / "search_config.json", 'w') as f:
                    json.dump(search_config, f, indent=2)
                
                logger.success("Search configuration saved successfully")
                st.success("Search configuration saved successfully!")
                
                # Update project status
                projects_df.loc[projects_df['project_id'] == project_id, 'status'] = 'Ready for Data Collection'
                save_projects(projects_df)
        
        with col2:
            # Show save status
            search_config_file = project_dir / "search_config.json"
            if search_config_file.exists():
                st.success("✅ Saved")
                st.caption("Configuration saved")
            else:
                st.warning("⚠️ Not saved")
                st.caption("Please save configuration")

# Legacy function for backward compatibility
def display_scoping_page():
    """Legacy function - use show() instead."""
    if 'logger' not in st.session_state:
        from components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)