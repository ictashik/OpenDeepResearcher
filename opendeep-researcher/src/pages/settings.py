import streamlit as st
from utils.data_manager import load_config, save_config
from utils.ollama_client import OllamaClient

def show(logger):
    """Settings page for configuration."""
    st.title("⚙️ Settings")
    st.markdown("---")
    
    # Load current configuration
    config = load_config()
    
    # Ollama Configuration Section
    st.subheader("🤖 Ollama Configuration")
    
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
        
        # Test connection button
        if st.button("🔍 Test Connection"):
            with st.spinner("Testing connection..."):
                # Update config temporarily for testing
                temp_config = config.copy()
                temp_config["ollama_endpoint"] = ollama_endpoint
                temp_config["api_key"] = api_key
                save_config(temp_config)
                
                client = OllamaClient()
                
                if client.test_connection():
                    st.success("✅ Connection successful!")
                    logger.success("Ollama connection test successful")
                    
                    # Fetch available models
                    with st.spinner("Fetching models..."):
                        models = client.get_models()
                        
                        if models:
                            config["models_list"] = models
                            st.success(f"Found {len(models)} models")
                            logger.info(f"Fetched {len(models)} models from Ollama")
                        else:
                            st.warning("No models found")
                            logger.warning("No models found on Ollama server")
                else:
                    st.error("❌ Connection failed")
                    logger.error("Failed to connect to Ollama server")
    
    # Model Selection Section
    st.markdown("---")
    st.subheader("🧠 Model Selection")
    
    models_list = config.get("models_list", [])
    
    if models_list:
        col1, col2 = st.columns(2)
        
        with col1:
            screening_model = st.selectbox(
                "Screening Model",
                options=[""] + models_list,
                index=models_list.index(config.get("screening_model", "")) + 1 if config.get("screening_model") in models_list else 0,
                help="Model used for article screening and PICO framework generation"
            )
        
        with col2:
            extraction_model = st.selectbox(
                "Data Extraction Model", 
                options=[""] + models_list,
                index=models_list.index(config.get("extraction_model", "")) + 1 if config.get("extraction_model") in models_list else 0,
                help="Model used for data extraction and report generation"
            )
        
        # Update config with selected models
        config["screening_model"] = screening_model
        config["extraction_model"] = extraction_model
        
    else:
        st.info("Please test the connection first to fetch available models.")
    
    # Data Extraction Prompts Section
    st.markdown("---")
    st.subheader("📝 Custom Extraction Prompts")
    
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
    st.subheader("🔍 Search Configuration")
    
    search_sources = st.multiselect(
        "Default Search Sources",
        options=["PubMed", "Google Scholar", "Scopus", "Web of Science", "EMBASE"],
        default=config.get("search_sources", ["PubMed", "Google Scholar"]),
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
        if st.button("💾 Save Settings", use_container_width=True):
            # Update config with current form values
            config["ollama_endpoint"] = ollama_endpoint
            config["api_key"] = api_key
            
            save_config(config)
            logger.success("Settings saved successfully")
            st.success("Settings saved successfully!")
    
    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            default_config = {
                "ollama_endpoint": "http://localhost:11434",
                "api_key": "",
                "screening_model": "",
                "extraction_model": "",
                "models_list": [],
                "extraction_prompts": default_prompts,
                "search_sources": ["PubMed", "Google Scholar"],
                "max_results_per_source": 100
            }
            save_config(default_config)
            logger.info("Settings reset to defaults")
            st.success("Settings reset to defaults!")
            st.rerun()
    
    with col3:
        if st.button("🧪 Test Models", use_container_width=True):
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

# Legacy function for backward compatibility
def settings_page():
    """Legacy function - use show() instead."""
    if 'logger' not in st.session_state:
        from components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)