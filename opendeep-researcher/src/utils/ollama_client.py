import requests
import json
from typing import Dict, List, Optional
from utils.data_manager import load_config

class OllamaClient:
    def __init__(self):
        self.config = load_config()
        self.base_url = self.config.get("ollama_endpoint", "http://localhost:11434")
        self.api_key = self.config.get("api_key", "")

    def test_connection(self) -> bool:
        """Test if Ollama server is accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_models(self) -> List[str]:
        """Get available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except requests.RequestException:
            return []

    def generate_completion(self, model: str, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Generate completion using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            return None
        except requests.RequestException:
            return None

    def screen_article(self, title: str, abstract: str, inclusion_criteria: str) -> Dict[str, str]:
        """Screen an article for inclusion/exclusion."""
        model = self.config.get("screening_model", "")
        if not model:
            return {"recommendation": "Unknown", "reasoning": "No screening model configured"}

        system_prompt = f"""You are an expert researcher conducting a systematic review. 
        Your task is to screen articles for inclusion based on specific criteria.
        
        Inclusion Criteria:
        {inclusion_criteria}
        
        Respond with a JSON object containing:
        - "recommendation": "Include" or "Exclude"
        - "reasoning": Brief explanation for your decision
        """

        user_prompt = f"""
        Title: {title}
        
        Abstract: {abstract}
        
        Based on the inclusion criteria, should this article be included in the systematic review?
        """

        response = self.generate_completion(model, user_prompt, system_prompt)
        
        if response:
            try:
                # Try to parse JSON response
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                if "include" in response.lower():
                    return {"recommendation": "Include", "reasoning": response}
                else:
                    return {"recommendation": "Exclude", "reasoning": response}
        
        return {"recommendation": "Unknown", "reasoning": "Failed to get AI response"}

    def extract_data(self, text: str, extraction_prompts: Dict[str, str]) -> Dict[str, str]:
        """Extract specific data from article text."""
        model = self.config.get("extraction_model", "")
        if not model:
            return {"error": "No extraction model configured"}

        results = {}
        
        for field, prompt in extraction_prompts.items():
            system_prompt = f"""You are an expert researcher extracting specific information from academic papers.
            Extract only the requested information. If the information is not found, respond with "Not found".
            Be concise and accurate."""

            user_prompt = f"""
            {prompt}
            
            Text to analyze:
            {text[:4000]}  # Limit text to avoid token limits
            """

            response = self.generate_completion(model, user_prompt, system_prompt)
            results[field] = response if response else "Failed to extract"

        return results

    def generate_pico_framework(self, research_question: str) -> Dict[str, str]:
        """Break down research question into PICO framework."""
        model = self.config.get("screening_model", "")
        if not model:
            return {"error": "No model configured"}

        system_prompt = """You are an expert in evidence-based medicine and systematic reviews.
        Break down the research question into the PICO framework:
        - Population: Who are the participants?
        - Intervention: What intervention is being studied?
        - Comparison: What is the comparison group?
        - Outcome: What outcomes are measured?
        
        Respond with a JSON object containing these four fields."""

        user_prompt = f"Research Question: {research_question}"

        response = self.generate_completion(model, user_prompt, system_prompt)
        
        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"error": "Failed to parse PICO response"}
        
        return {"error": "Failed to generate PICO framework"}

    def generate_keywords(self, pico_data: Dict[str, str]) -> List[str]:
        """Generate search keywords from PICO framework."""
        model = self.config.get("screening_model", "")
        if not model:
            return ["No model configured"]

        system_prompt = """You are an expert in systematic review methodology.
        Generate a comprehensive list of search keywords and terms based on the PICO framework.
        Include synonyms, alternative terms, and relevant MeSH terms.
        Return only the keywords, one per line."""

        user_prompt = f"""
        Population: {pico_data.get('Population', '')}
        Intervention: {pico_data.get('Intervention', '')}
        Comparison: {pico_data.get('Comparison', '')}
        Outcome: {pico_data.get('Outcome', '')}
        """

        response = self.generate_completion(model, user_prompt, system_prompt)
        
        if response:
            keywords = [kw.strip() for kw in response.split('\n') if kw.strip()]
            return keywords
        
        return ["Failed to generate keywords"]

    def generate_report(self, extracted_data: str) -> str:
        """Generate a systematic review report from extracted data."""
        model = self.config.get("extraction_model", "")
        if not model:
            return "No model configured for report generation"

        system_prompt = """You are an expert researcher writing a systematic review report.
        Create a comprehensive, well-structured report in Markdown format.
        Include sections for: Introduction, Methods, Results, Discussion, and Conclusion.
        Use proper academic language and cite the data appropriately."""

        user_prompt = f"""
        Generate a systematic review report based on the following extracted data:
        
        {extracted_data}
        """

        response = self.generate_completion(model, user_prompt, system_prompt)
        return response if response else "Failed to generate report"

    # Legacy methods for backward compatibility
    def fetch_models(self):
        """Legacy method - use get_models() instead."""
        return [{"name": model} for model in self.get_models()]

    def send_request(self, model, data):
        """Legacy method - use generate_completion() instead."""
        return {"response": self.generate_completion(model, str(data))}