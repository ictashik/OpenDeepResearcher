import requests
import json
import re
from typing import Dict, List, Optional
from src.utils.data_manager import load_config

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class OllamaClient:
    def __init__(self):
        self.config = load_config()
        self.base_url = self.config.get("ollama_endpoint", "http://10.60.23.102:11434")
        self.api_key = self.config.get("api_key", "")
        
        # Initialize OpenAI client for Ollama if available
        if OPENAI_AVAILABLE:
            self.openai_client = OpenAI(
                base_url=f"{self.base_url}/v1",
                api_key="ollama"  # Ollama doesn't require a real API key
            )
        else:
            self.openai_client = None

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
        """Generate completion using Ollama via OpenAI client or direct API."""
        try:
            # Try OpenAI client first if available (more reliable)
            if self.openai_client:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,  # Lower temperature for more consistent responses
                    max_tokens=2000
                )
                return response.choices[0].message.content
            
            # Fallback to direct API
            else:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
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
                
        except Exception as e:
            print(f"Error in generate_completion: {e}")
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
        
        Respond ONLY with a valid JSON object in this exact format:
        {{
            "recommendation": "Include" or "Exclude",
            "reasoning": "Brief explanation for your decision"
        }}
        
        Do not include any other text or explanations."""

        user_prompt = f"""Title: {title}
        
        Abstract: {abstract}
        
        Based on the inclusion criteria, should this article be included in the systematic review?
        Respond with valid JSON only."""

        response = self.generate_completion(model, user_prompt, system_prompt)
        
        if response:
            # Try to extract JSON from response
            result = self._extract_json_from_response(response)
            
            if result and "recommendation" in result:
                return {
                    "recommendation": result.get("recommendation", "Unknown"),
                    "reasoning": result.get("reasoning", response)
                }
            else:
                # Fallback parsing if JSON extraction fails
                if "include" in response.lower() and "exclude" not in response.lower():
                    return {"recommendation": "Include", "reasoning": response}
                elif "exclude" in response.lower():
                    return {"recommendation": "Exclude", "reasoning": response}
                else:
                    return {"recommendation": "Uncertain", "reasoning": response}
        
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

    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """Extract JSON from AI response, handling various formats."""
        if not response:
            return None
            
        # Clean the response
        response = response.strip()
        
        # Try to find JSON block within markdown code fences
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object directly
        json_pattern = r'\{.*?\}'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        # Try parsing the entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # If all else fails, try to extract key-value pairs manually
        try:
            result = {}
            lines = response.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().replace('-', '').replace('*', '').strip()
                    value = value.strip().strip('"\'')
                    if key and value:
                        result[key] = value
            
            if result:
                return result
        except:
            pass
        
        return None

    def generate_pico_framework(self, research_question: str) -> Dict[str, str]:
        """Break down research question into PICO framework."""
        model = self.config.get("screening_model", "")
        if not model:
            return {"error": "No model configured"}

        system_prompt = """You are an expert in evidence-based medicine and systematic reviews.
        Break down the research question into the PICO framework.

        Respond ONLY with a valid JSON object in this exact format:
        {
            "Population": "description of the population",
            "Intervention": "description of the intervention",
            "Comparison": "description of the comparison",
            "Outcome": "description of the outcome"
        }

        Do not include any other text or explanations."""

        user_prompt = f"""Research Question: {research_question}

        Break this down into PICO components and respond with valid JSON only."""

        response = self.generate_completion(model, user_prompt, system_prompt)
        
        if response:
            # Try to extract JSON from response
            pico_data = self._extract_json_from_response(response)
            
            if pico_data and all(key in pico_data for key in ["Population", "Intervention", "Comparison", "Outcome"]):
                return pico_data
            else:
                # Fallback: try to parse manually
                try:
                    fallback_result = {
                        "Population": "Not specified",
                        "Intervention": "Not specified", 
                        "Comparison": "Not specified",
                        "Outcome": "Not specified"
                    }
                    
                    # Simple keyword extraction as fallback
                    response_lower = response.lower()
                    if "population" in response_lower:
                        pop_match = re.search(r'population[:\-\s]+(.*?)(?:\n|intervention|comparison|outcome|$)', response_lower, re.IGNORECASE | re.DOTALL)
                        if pop_match:
                            fallback_result["Population"] = pop_match.group(1).strip()[:200]
                    
                    if "intervention" in response_lower:
                        int_match = re.search(r'intervention[:\-\s]+(.*?)(?:\n|population|comparison|outcome|$)', response_lower, re.IGNORECASE | re.DOTALL)
                        if int_match:
                            fallback_result["Intervention"] = int_match.group(1).strip()[:200]
                    
                    if "comparison" in response_lower:
                        comp_match = re.search(r'comparison[:\-\s]+(.*?)(?:\n|population|intervention|outcome|$)', response_lower, re.IGNORECASE | re.DOTALL)
                        if comp_match:
                            fallback_result["Comparison"] = comp_match.group(1).strip()[:200]
                    
                    if "outcome" in response_lower:
                        out_match = re.search(r'outcome[:\-\s]+(.*?)(?:\n|population|intervention|comparison|$)', response_lower, re.IGNORECASE | re.DOTALL)
                        if out_match:
                            fallback_result["Outcome"] = out_match.group(1).strip()[:200]
                    
                    return fallback_result
                    
                except Exception as e:
                    return {"error": f"Failed to parse PICO response: {str(e)}"}
        
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