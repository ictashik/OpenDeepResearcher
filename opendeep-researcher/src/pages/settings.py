import streamlit as st
from src.utils.data_manager import load_config, save_config
from src.utils.ollama_client import OllamaClient
from src.utils.config_manager import config_manager

def show(logger):
    """Settings page for configuration."""
    st.title("⚙️ Settings")
    
    # Create tabs for different settings categories
    tab1, tab2, tab3 = st.tabs(["🔑 API Keys", "🤖 Ollama Configuration", "🔍 Search Settings"])
    
    with tab1:
        st.subheader("API Keys Configuration")
        st.markdown("Configure API keys for enhanced data collection capabilities.")
        
        # API Keys section
        st.markdown("---")
        
        # CORE API
        st.markdown("**🌐 CORE API** - Open Access Research Papers")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            current_core_key = config_manager.get_core_api_key() or ""
            core_api_key = st.text_input(
                "CORE API Key",
                value=current_core_key,
                type="password",
                help="Get a free API key at: https://core.ac.uk/api-keys/register"
            )
            
            if core_api_key != current_core_key:
                if st.button("Save CORE API Key", key="save_core"):
                    config_manager.set_api_key("core_api_key", core_api_key)
                    st.success("✅ CORE API key saved!")
                    logger.info("CORE API key updated")
        
        with col2:
            if current_core_key:
                st.success("✅ Configured")
            else:
                st.info("ℹ️ Not configured")
        
        # Semantic Scholar API
        st.markdown("**🧠 Semantic Scholar API** - AI-Powered Academic Search")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            current_semantic_key = config_manager.get_semantic_scholar_api_key() or ""
            semantic_api_key = st.text_input(
                "Semantic Scholar API Key (Optional)",
                value=current_semantic_key,
                type="password",
                help="Optional: Get higher rate limits at: https://www.semanticscholar.org/product/api"
            )
            
            if semantic_api_key != current_semantic_key:
                if st.button("Save Semantic Scholar API Key", key="save_semantic"):
                    config_manager.set_api_key("semantic_scholar_api_key", semantic_api_key)
                    st.success("✅ Semantic Scholar API key saved!")
                    logger.info("Semantic Scholar API key updated")
        
        with col2:
            if current_semantic_key:
                st.success("✅ Configured")
            else:
                st.info("ℹ️ Optional")
        
        # Info about API benefits
        st.markdown("---")
        st.markdown("**🎯 API Benefits:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**CORE API:**")
            st.markdown("• Access to 200M+ open access papers")
            st.markdown("• Full-text content when available")
            st.markdown("• Structured metadata")
            st.markdown("• Free tier: 1000 requests/day")
        
        with col2:
            st.markdown("**Semantic Scholar API:**")
            st.markdown("• AI-powered search relevance")
            st.markdown("• Citation networks")
            st.markdown("• Influence metrics")
            st.markdown("• Higher rate limits with API key")
        
        # Test API connections
        st.markdown("---")
        st.markdown("**🧪 Test API Connections:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Test CORE API", disabled=not config_manager.get_core_api_key()):
                with st.spinner("Testing CORE API..."):
                    # Simple test search
                    try:
                        from src.utils.academic_search import RobustAcademicSearcher
                        searcher = RobustAcademicSearcher()
                        articles, method = searcher.search_core_api(["machine learning"], logger)
                        
                        if articles:
                            st.success(f"✅ CORE API working! Found {len(articles)} test results")
                        else:
                            st.warning("⚠️ CORE API responded but no results found")
                    except Exception as e:
                        st.error(f"❌ CORE API test failed: {str(e)}")
        
        with col2:
            if st.button("Test Semantic Scholar API"):
                with st.spinner("Testing Semantic Scholar API..."):
                    try:
                        from src.utils.academic_search import RobustAcademicSearcher
                        searcher = RobustAcademicSearcher()
                        articles, method = searcher.search_semantic_scholar_api(["machine learning"], logger)
                        
                        if articles:
                            st.success(f"✅ Semantic Scholar API working! Found {len(articles)} test results")
                        else:
                            st.warning("⚠️ Semantic Scholar API responded but no results found")
                    except Exception as e:
                        st.error(f"❌ Semantic Scholar API test failed: {str(e)}")
    
    with tab2:
        st.subheader("Ollama Configuration")
        
        # Load current configuration for Ollama section
        config = load_config()
    
    # Migrate old config values to new format
    if "search_sources" in config:
        old_to_new_mapping = {
            "PubMed": "PubMed/MEDLINE",
            "Google Scholar": "Google Scholar",
            "Scopus": "Scopus", 
            "Web of Science": "Web of Science",
            "EMBASE": "EMBASE"
        }
        
        updated_sources = []
        needs_update = False
        
        for source in config["search_sources"]:
            if source in old_to_new_mapping:
                new_source = old_to_new_mapping[source]
                updated_sources.append(new_source)
                if new_source != source:
                    needs_update = True
            else:
                updated_sources.append(source)
        
        if needs_update:
            config["search_sources"] = updated_sources
            save_config(config)
            logger.info("Updated search source names in configuration")
    
        # Ollama Configuration Section
    st.markdown("#### Ollama Configuration")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        ollama_endpoint = st.text_input(
            "Ollama Endpoint URL",
            value=config.get("ollama_endpoint", "http://localhost:11434"),
            help="The URL where your Ollama server is running"
        )
        
        api_key = st.text_input(
            "API Key (optional)",
            value=config.get("api_key", ""),
            type="password",
            help="Optional API key if your Ollama server requires authentication"
        )
    
    with col2:
        st.markdown("**Connection Status**")
        
        # Show current status
        models_list = config.get("models_list", [])
        if models_list:
            st.success(f"Connected ({len(models_list)} models)")
            st.info("Models ready for use")
        else:
            st.warning("Not connected")
        
        # Test connection button
        if st.button("Test Connection"):
            with st.spinner("Testing connection..."):
                # Update config temporarily for testing
                temp_config = config.copy()
                temp_config["ollama_endpoint"] = ollama_endpoint
                temp_config["api_key"] = api_key
                save_config(temp_config)
                
                client = OllamaClient()
                
                if client.test_connection():
                    st.success("Connection successful!")
                    logger.success("Ollama connection test successful")
                    
                    # Fetch available models
                    with st.spinner("Fetching models..."):
                        models = client.get_models()
                        
                        if models:
                            # Update and save config with models and connection settings
                            config["ollama_endpoint"] = ollama_endpoint
                            config["api_key"] = api_key
                            config["models_list"] = models
                            save_config(config)
                            
                            st.success(f"Found {len(models)} models")
                            logger.info(f"Fetched {len(models)} models from Ollama")
                            st.rerun()  # Refresh to show model selection
                        else:
                            st.warning("No models found")
                            logger.warning("No models found on Ollama server")
                else:
                    st.error("Connection failed")
                    logger.error("Failed to connect to Ollama server")
    
    # Model Selection Section
    st.markdown("---")
    st.markdown("#### Model Selection")
    
    models_list = config.get("models_list", [])
    
    if models_list:
        col1, col2 = st.columns(2)
        
        with col1:
            screening_model = st.selectbox(
                "Screening Model",
                options=[""] + models_list,
                index=models_list.index(config.get("screening_model", "")) + 1 if config.get("screening_model") in models_list else 0,
                help="Model used for article screening and PICO framework generation",
                key="screening_model_select"
            )
        
        with col2:
            extraction_model = st.selectbox(
                "Data Extraction Model", 
                options=[""] + models_list,
                index=models_list.index(config.get("extraction_model", "")) + 1 if config.get("extraction_model") in models_list else 0,
                help="Model used for data extraction and report generation",
                key="extraction_model_select"
            )
        
        # Auto-save model selections when they change
        if screening_model != config.get("screening_model", "") or extraction_model != config.get("extraction_model", ""):
            config["screening_model"] = screening_model
            config["extraction_model"] = extraction_model
            save_config(config)
            logger.info(f"Updated model selections: Screening={screening_model}, Extraction={extraction_model}")
        
    else:
        st.info("Please test the connection first to fetch available models.")
    
    # Data Extraction Prompts Section
    st.markdown("---")
    st.markdown("#### Custom Extraction Prompts")
    
    st.markdown("Define custom prompts for extracting specific information from research papers:")
    
    # Default extraction prompts
    default_prompts = {
        "sample_size": "What is the sample size of this study? Extract only the number.",
        "study_design": "What is the study design (e.g., RCT, cohort study, case-control)?",
        "intervention": "What is the main intervention or exposure being studied?",
        "primary_outcome": "What is the primary outcome measure?",
        "effect_size": "What are the main results or effect sizes reported?",
        "limitations": "What limitations does the study report?"
    }
    
    extraction_prompts = config.get("extraction_prompts", default_prompts)
    
    # Allow users to edit prompts
    updated_prompts = {}
    for field, prompt in extraction_prompts.items():
        updated_prompts[field] = st.text_area(
            f"**{field.replace('_', ' ').title()}**",
            value=prompt,
            height=60,
            key=f"prompt_{field}"
        )
    
    # Add new prompt
    st.markdown("**Add New Extraction Field:**")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        new_field = st.text_input("Field Name", placeholder="e.g., funding_source")
    
    with col2:
        new_prompt = st.text_input("Extraction Prompt", placeholder="e.g., What is the funding source for this study?")
    
    if st.button("Add Field") and new_field and new_prompt:
        updated_prompts[new_field] = new_prompt
        st.success(f"Added field: {new_field}")
    
    config["extraction_prompts"] = updated_prompts
    
    # Search Configuration Section  
    st.markdown("---")
    st.markdown("#### Search Configuration")
    
    # Map old config values to new option names
    available_options = ["PubMed/MEDLINE", "Google Scholar", "Google Scholar (Scholarly)", "Scopus", "Web of Science", "EMBASE", "PsycINFO", "DuckDuckGo Academic", "arXiv", "ResearchGate"]
    
    # Get current config with fallback
    current_sources = config.get("search_sources", ["PubMed/MEDLINE", "Google Scholar"])
    
    # Map old values to new values
    mapping = {
        "PubMed": "PubMed/MEDLINE",
        "Google Scholar": "Google Scholar",
        "Scopus": "Scopus",
        "Web of Science": "Web of Science",
        "EMBASE": "EMBASE"
    }
    
    # Convert old config values to new format
    mapped_sources = []
    for source in current_sources:
        mapped_source = mapping.get(source, source)
        if mapped_source in available_options:
            mapped_sources.append(mapped_source)
    
    # Ensure we have at least some defaults
    if not mapped_sources:
        mapped_sources = ["PubMed/MEDLINE", "Google Scholar"]
    
    search_sources = st.multiselect(
        "Default Search Sources",
        options=available_options,
        default=mapped_sources,
        help="Select which databases to search by default"
    )
    
    max_results_per_source = st.number_input(
        "Maximum Results per Source",
        min_value=10,
        max_value=1000,
        value=config.get("max_results_per_source", 100),
        step=10,
        help="Maximum number of articles to retrieve from each database"
    )
    
    config["search_sources"] = search_sources
    config["max_results_per_source"] = max_results_per_source
    
    # Save Settings
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("Save Settings", use_container_width=True):
            # Update config with current form values
            config["ollama_endpoint"] = ollama_endpoint
            config["api_key"] = api_key
            
            save_config(config)
            logger.success("Settings saved successfully")
            st.success("Settings saved successfully!")
    
    with col2:
        if st.button("Reset to Defaults", use_container_width=True):
            default_config = {
                "ollama_endpoint": "http://localhost:11434",
                "api_key": "",
                "screening_model": "",
                "extraction_model": "",
                "models_list": [],
                "extraction_prompts": default_prompts,
                "search_sources": ["PubMed/MEDLINE", "Google Scholar"],
                "max_results_per_source": 100
            }
            save_config(default_config)
            logger.info("Settings reset to defaults")
            st.success("Settings reset to defaults!")
            st.rerun()
    
    with col3:
        if st.button("Test Models", use_container_width=True):
            if not config.get("screening_model") or not config.get("extraction_model"):
                st.error("Please select both models first")
            else:
                with st.spinner("Testing models..."):
                    client = OllamaClient()
                    
                    # Test screening model
                    test_response = client.generate_completion(
                        config["screening_model"], 
                        "Test prompt", 
                        "You are a test assistant. Respond with 'Test successful'"
                    )
                    
                    if test_response:
                        st.success("Models are working correctly!")
                        logger.success("Model test successful")
                    else:
                        st.error("Model test failed")
                        logger.error("Model test failed")
    
    with tab3:
        st.subheader("Search Settings")
        st.markdown("Configure default search behavior and data collection settings.")
        
        # Data collection settings
        st.markdown("---")
        st.markdown("**📊 Data Collection Settings:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_settings = config_manager.get_data_collection_settings()
            
            max_results = st.number_input(
                "Max results per source",
                min_value=10,
                max_value=500,
                value=current_settings.get('max_results_per_source', 100),
                step=10,
                help="Maximum number of articles to collect from each data source"
            )
            
            delay_between = st.number_input(
                "Delay between requests (seconds)",
                min_value=0.5,
                max_value=5.0,
                value=current_settings.get('delay_between_requests', 1.5),
                step=0.1,
                help="Delay between API requests to avoid rate limiting"
            )
        
        with col2:
            st.markdown("**🎯 Default Sources:**")
            default_sources = config_manager.get_default_sources()
            
            available_sources = [
                "Semantic Scholar",
                "PubMed API", 
                "CORE API",
                "Google Scholar (Scholarly)",
                "DuckDuckGo Academic",
                "arXiv",
                "ResearchGate"
            ]
            
            selected_defaults = st.multiselect(
                "Default search sources",
                options=available_sources,
                default=default_sources,
                help="These sources will be selected by default for new searches"
            )
        
        # Save search settings
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Save Search Settings", use_container_width=True):
                # Update data collection settings
                current_config = config_manager.load_config()
                if 'data_collection' not in current_config:
                    current_config['data_collection'] = {}
                if 'search' not in current_config:
                    current_config['search'] = {}
                
                current_config['data_collection']['max_results_per_source'] = max_results
                current_config['data_collection']['delay_between_requests'] = delay_between
                current_config['search']['default_sources'] = selected_defaults
                
                config_manager.save_config(current_config)
                st.success("✅ Search settings saved!")
                logger.success("Search settings updated")
        
        with col2:
            if st.button("Reset Search Settings", use_container_width=True):
                # Reset to defaults
                current_config = config_manager.load_config()
                current_config['data_collection'] = {
                    'max_results_per_source': 100,
                    'delay_between_requests': 1.5
                }
                current_config['search'] = {
                    'default_sources': ["Semantic Scholar", "Google Scholar (Scholarly)", "DuckDuckGo Academic"]
                }
                
                config_manager.save_config(current_config)
                st.success("✅ Settings reset to defaults!")
                logger.info("Search settings reset to defaults")
                st.rerun()

# Legacy function for backward compatibility
def settings_page():
    """Legacy function - use show() instead."""
    if 'logger' not in st.session_state:
        from components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)