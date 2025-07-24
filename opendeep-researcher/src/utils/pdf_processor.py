import fitz  # PyMuPDF
import io
from typing import Dict, List, Optional
import re

class PDFProcessor:
    def __init__(self):
        pass

    def extract_text_from_pdf(self, pdf_file) -> Dict[str, str]:
        """Extract text from a PDF file and organize by sections."""
        try:
            # Handle both file path and file-like objects
            if hasattr(pdf_file, 'read'):
                # It's a file-like object (e.g., from st.file_uploader)
                pdf_bytes = pdf_file.read()
                pdf_file.seek(0)  # Reset file pointer
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            else:
                # It's a file path
                doc = fitz.open(pdf_file)

            full_text = ""
            sections = {}
            
            # Extract text from all pages
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                full_text += page_text + "\n"

            doc.close()

            # Organize text into sections
            sections = self._identify_sections(full_text)
            
            return {
                "full_text": full_text,
                "sections": sections,
                "page_count": len(doc) if doc else 0,
                "status": "success"
            }

        except Exception as e:
            return {
                "full_text": "",
                "sections": {},
                "page_count": 0,
                "status": "error",
                "error": str(e)
            }

    def _identify_sections(self, text: str) -> Dict[str, str]:
        """Identify and extract common academic paper sections."""
        sections = {}
        
        # Common section patterns
        section_patterns = {
            "abstract": r"(abstract|summary)[\s\n]*(.*?)(?=\n\s*(?:keywords|introduction|1\.?\s+introduction))",
            "introduction": r"(1\.?\s*introduction|introduction)[\s\n]*(.*?)(?=\n\s*(?:2\.?\s*|methods|methodology|literature review))",
            "methods": r"(2\.?\s*methods?|methodology|materials and methods)[\s\n]*(.*?)(?=\n\s*(?:3\.?\s*|results|findings))",
            "results": r"(3\.?\s*results?|findings)[\s\n]*(.*?)(?=\n\s*(?:4\.?\s*|discussion|conclusion))",
            "discussion": r"(4\.?\s*discussion)[\s\n]*(.*?)(?=\n\s*(?:5\.?\s*|conclusion|limitations))",
            "conclusion": r"(conclusion|conclusions?)[\s\n]*(.*?)(?=\n\s*(?:references|bibliography|acknowledgments?))",
            "limitations": r"(limitations?)[\s\n]*(.*?)(?=\n\s*(?:conclusion|references|bibliography))"
        }

        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                sections[section_name] = match.group(2).strip()[:2000]  # Limit length
            else:
                sections[section_name] = ""

        return sections

    def extract_specific_content(self, pdf_file, extraction_rules: Dict[str, str]) -> Dict[str, str]:
        """Extract specific content based on custom extraction rules."""
        extracted_data = self.extract_text_from_pdf(pdf_file)
        
        if extracted_data["status"] != "success":
            return extracted_data

        full_text = extracted_data["full_text"]
        sections = extracted_data["sections"]
        results = {}

        for field_name, rule in extraction_rules.items():
            # Rule can specify a section or a regex pattern
            if rule.lower() in sections:
                results[field_name] = sections[rule.lower()]
            else:
                # Try to find content using regex
                pattern_match = re.search(rule, full_text, re.IGNORECASE | re.DOTALL)
                results[field_name] = pattern_match.group(1) if pattern_match else "Not found"

        return results

    def extract_tables_and_figures(self, pdf_file) -> Dict[str, List]:
        """Extract information about tables and figures in the PDF."""
        try:
            if hasattr(pdf_file, 'read'):
                pdf_bytes = pdf_file.read()
                pdf_file.seek(0)
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            else:
                doc = fitz.open(pdf_file)

            tables = []
            figures = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()

                # Find table references
                table_matches = re.findall(r'(table\s+\d+[:\.]?\s*[^\n]*)', page_text, re.IGNORECASE)
                for match in table_matches:
                    tables.append({
                        "page": page_num + 1,
                        "reference": match.strip(),
                        "context": self._get_context(page_text, match)
                    })

                # Find figure references
                figure_matches = re.findall(r'(figure\s+\d+[:\.]?\s*[^\n]*)', page_text, re.IGNORECASE)
                for match in figure_matches:
                    figures.append({
                        "page": page_num + 1,
                        "reference": match.strip(),
                        "context": self._get_context(page_text, match)
                    })

            doc.close()

            return {
                "tables": tables,
                "figures": figures,
                "status": "success"
            }

        except Exception as e:
            return {
                "tables": [],
                "figures": [],
                "status": "error",
                "error": str(e)
            }

    def _get_context(self, text: str, match: str, context_chars: int = 200) -> str:
        """Get surrounding context for a match."""
        match_pos = text.lower().find(match.lower())
        if match_pos == -1:
            return ""
        
        start = max(0, match_pos - context_chars)
        end = min(len(text), match_pos + len(match) + context_chars)
        
        return text[start:end].strip()

    def extract_citations(self, pdf_file) -> List[Dict[str, str]]:
        """Extract citations and references from the PDF."""
        try:
            extracted_data = self.extract_text_from_pdf(pdf_file)
            if extracted_data["status"] != "success":
                return []

            full_text = extracted_data["full_text"]
            citations = []

            # Look for references section
            ref_pattern = r"references[\s\n]+(.*?)(?=\n\s*(?:appendix|acknowledgments?|$))"
            ref_match = re.search(ref_pattern, full_text, re.IGNORECASE | re.DOTALL)
            
            if ref_match:
                references_text = ref_match.group(1)
                
                # Split into individual references (basic approach)
                ref_lines = references_text.split('\n')
                current_ref = ""
                
                for line in ref_lines:
                    line = line.strip()
                    if re.match(r'^\d+\.', line) or re.match(r'^\[\d+\]', line):
                        # New reference starts
                        if current_ref:
                            citations.append({"reference": current_ref.strip()})
                        current_ref = line
                    else:
                        current_ref += " " + line
                
                # Add the last reference
                if current_ref:
                    citations.append({"reference": current_ref.strip()})

            return citations

        except Exception as e:
            return []

# Legacy functions for backward compatibility
def extract_text_from_pdf(pdf_path, prompts=None):
    """Legacy function - use PDFProcessor class instead."""
    processor = PDFProcessor()
    if prompts:
        # Handle legacy prompts parameter
        extracted_data = processor.extract_text_from_pdf(pdf_path)
        if extracted_data["status"] == "success":
            return {prompt: extracted_data["full_text"] for prompt in prompts}
        else:
            return {prompt: f"Error: {extracted_data.get('error', 'Unknown error')}" for prompt in prompts}
    else:
        return processor.extract_text_from_pdf(pdf_path)

def parse_pdf_sections(pdf_path, section_prompts):
    """Legacy function - use PDFProcessor class instead."""
    return extract_text_from_pdf(pdf_path, section_prompts)