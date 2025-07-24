"""
Configuration manager for OpenDeep Researcher.
Handles loading of API keys and other configuration settings.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Optional
import streamlit as st

class ConfigManager:
    """Manages configuration settings and API keys."""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent.parent / "config.yaml"
        self._config_cache = None
    
    def load_config(self) -> Dict:
        """Load configuration from YAML file."""
        if self._config_cache is not None:
            return self._config_cache
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self._config_cache = yaml.safe_load(f) or {}
            else:
                self._config_cache = {}
        except Exception as e:
            st.warning(f"⚠️ Error loading config: {e}")
            self._config_cache = {}
        
        return self._config_cache
    
    def save_config(self, config: Dict):
        """Save configuration to YAML file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            self._config_cache = config
        except Exception as e:
            st.error(f"❌ Error saving config: {e}")
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get API keys from configuration."""
        config = self.load_config()
        return config.get('api_keys', {})
    
    def set_api_key(self, service: str, api_key: str):
        """Set an API key for a specific service."""
        config = self.load_config()
        if 'api_keys' not in config:
            config['api_keys'] = {}
        
        config['api_keys'][service] = api_key
        self.save_config(config)
    
    def get_core_api_key(self) -> Optional[str]:
        """Get CORE API key."""
        api_keys = self.get_api_keys()
        key = api_keys.get('core_api_key', '').strip()
        return key if key else None
    
    def get_semantic_scholar_api_key(self) -> Optional[str]:
        """Get Semantic Scholar API key."""
        api_keys = self.get_api_keys()
        key = api_keys.get('semantic_scholar_api_key', '').strip()
        return key if key else None
    
    def get_data_collection_settings(self) -> Dict:
        """Get data collection settings."""
        config = self.load_config()
        defaults = {
            'max_results_per_source': 100,
            'delay_between_requests': 1.5
        }
        return config.get('data_collection', defaults)
    
    def get_default_sources(self) -> list:
        """Get default search sources."""
        config = self.load_config()
        search_config = config.get('search', {})
        return search_config.get('default_sources', [
            "Semantic Scholar",
            "Google Scholar (Scholarly)",
            "DuckDuckGo Academic"
        ])

# Global instance
config_manager = ConfigManager()
