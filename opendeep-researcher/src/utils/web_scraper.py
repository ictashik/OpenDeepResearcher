"""
Web scraping utilities for academic paper collection.
Uses BeautifulSoup4 and DuckDuckGo search to find academic papers.
Enhanced with proper error handling and API fallbacks.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse, quote_plus
from typing import List, Dict, Optional
import json
from pathlib import Path
import traceback
import logging

# Try to import DuckDuckGo search API
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False
        print("Warning: DuckDuckGo search API not available, falling back to HTML scraping")


class AcademicScraper:
    """Scraper for academic papers from various sources with enhanced error handling."""
    
    def __init__(self, max_results_per_source: int = 100, delay_between_requests: float = 1.0):
        self.max_results_per_source = max_results_per_source
        self.delay = delay_between_requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Setup internal logging
        self.setup_logging()
        
        # Track statistics
        self.search_stats = {
            'total_attempts': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'articles_found': 0,
            'errors': []
        }
    
    def setup_logging(self):
        """Setup internal logging for debugging."""
        self.logger = logging.getLogger('academic_scraper')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
    
    def log_error(self, source: str, error: Exception, context: str = "", logger=None):
        """Enhanced error logging with context."""
        error_msg = f"Error in {source} ({context}): {str(error)}"
        error_details = {
            'source': source,
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': time.time()
        }
        
        # Log to internal logger
        self.logger.error(error_msg)
        self.logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        # Log to provided logger (terminal)
        if logger:
            logger.error(error_msg)
            logger.warning(f"Full error details: {error_details['error_type']}")
        
        # Store for statistics
        self.search_stats['errors'].append(error_details)
        self.search_stats['failed_searches'] += 1
    
    def search_all_sources(self, keywords: List[str], sources: List[str], 
                          project_id: str, logger=None) -> pd.DataFrame:
        """Search all selected sources for papers with enhanced error handling."""
        all_articles = []
        
        # Reset statistics
        self.search_stats = {
            'total_attempts': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'articles_found': 0,
            'errors': []
        }
        
        # Create search query from keywords
        if not keywords:
            if logger:
                logger.error("No keywords provided for search")
            return pd.DataFrame(columns=['id', 'title', 'authors', 'abstract', 'source', 'url', 'year'])
        
        search_query = " OR ".join([f'"{keyword.strip()}"' for keyword in keywords if keyword.strip()])
        
        if logger:
            logger.info(f"Starting search with query: {search_query[:100]}...")
            logger.info(f"Searching {len(sources)} sources: {', '.join(sources)}")
        
        for source in sources:
            self.search_stats['total_attempts'] += 1
            
            if logger:
                logger.info(f"🔍 Searching {source}...")
            
            try:
                articles = []
                
                if source == "Google Scholar":
                    articles = self.search_google_scholar(search_query, logger)
                elif source == "PubMed/MEDLINE":
                    articles = self.search_pubmed(search_query, logger)
                elif source == "DuckDuckGo Academic":
                    articles = self.search_duckduckgo_academic(search_query, logger)
                elif source == "Scopus":
                    articles = self.search_scopus_fallback(search_query, logger)
                elif source == "Web of Science":
                    articles = self.search_wos_fallback(search_query, logger)
                elif source == "EMBASE":
                    articles = self.search_embase_fallback(search_query, logger)
                elif source == "PsycINFO":
                    articles = self.search_psycinfo_fallback(search_query, logger)
                else:
                    if logger:
                        logger.warning(f"⚠️ Source {source} not fully implemented, using DuckDuckGo fallback")
                    articles = self.search_duckduckgo_fallback(search_query, source, logger)
                
                # Add source information
                for article in articles:
                    article['source'] = source
                    article['search_query'] = search_query
                
                all_articles.extend(articles)
                self.search_stats['articles_found'] += len(articles)
                self.search_stats['successful_searches'] += 1
                
                if logger:
                    logger.success(f"✅ Found {len(articles)} articles from {source}")
                
                # Delay between sources
                if len(sources) > 1:  # Only delay if searching multiple sources
                    time.sleep(self.delay)
                
            except Exception as e:
                self.log_error(source, e, "search_all_sources", logger)
                
                # Try fallback search
                if logger:
                    logger.warning(f"⚠️ Attempting fallback search for {source}")
                
                try:
                    fallback_articles = self.search_duckduckgo_fallback(search_query, source, logger)
                    for article in fallback_articles:
                        article['source'] = f"{source} (Fallback)"
                        article['search_query'] = search_query
                    
                    all_articles.extend(fallback_articles)
                    self.search_stats['articles_found'] += len(fallback_articles)
                    
                    if fallback_articles:
                        self.search_stats['successful_searches'] += 1
                        if logger:
                            logger.success(f"✅ Fallback found {len(fallback_articles)} articles for {source}")
                    else:
                        if logger:
                            logger.warning(f"⚠️ Fallback found no articles for {source}")
                
                except Exception as fallback_error:
                    self.log_error(source, fallback_error, "fallback_search", logger)
                
                continue
        
        # Log final statistics
        if logger:
            logger.info(f"📊 Search complete. Attempts: {self.search_stats['total_attempts']}, "
                       f"Successful: {self.search_stats['successful_searches']}, "
                       f"Failed: {self.search_stats['failed_searches']}, "
                       f"Articles found: {self.search_stats['articles_found']}")
        
        # Convert to DataFrame and remove duplicates
        if all_articles:
            try:
                df = pd.DataFrame(all_articles)
                
                # Add unique ID
                df['id'] = range(1, len(df) + 1)
                
                # Remove duplicates based on title similarity
                df = self.remove_duplicate_papers(df, logger)
                
                # Clean and standardize data
                df = self.clean_article_data(df)
                
                if logger:
                    logger.success(f"🎉 Total unique articles found: {len(df)}")
                
                return df
                
            except Exception as e:
                self.log_error("DataFrame Processing", e, "data_processing", logger)
                return pd.DataFrame(columns=['id', 'title', 'authors', 'abstract', 'source', 'url', 'year'])
        else:
            if logger:
                logger.warning("⚠️ No articles found across all sources")
                if self.search_stats['errors']:
                    logger.error("🚨 Errors encountered during search:")
                    for error in self.search_stats['errors'][-3:]:  # Show last 3 errors
                        logger.error(f"  - {error['source']}: {error['error_type']}")
            
            return pd.DataFrame(columns=['id', 'title', 'authors', 'abstract', 'source', 'url', 'year'])
    
    def search_duckduckgo_fallback(self, query: str, target_source: str, logger=None) -> List[Dict]:
        """Enhanced DuckDuckGo fallback search with site-specific targeting."""
        articles = []
        
        try:
            # Map sources to site restrictions
            site_mapping = {
                "Google Scholar": "site:scholar.google.com",
                "PubMed/MEDLINE": "site:pubmed.ncbi.nlm.nih.gov",
                "Scopus": "site:scopus.com OR site:sciencedirect.com",
                "Web of Science": "site:webofknowledge.com OR site:clarivate.com",
                "EMBASE": "site:embase.com OR site:elsevier.com",
                "PsycINFO": "site:psycnet.apa.org OR site:apa.org"
            }
            
            # Construct targeted search
            site_restriction = site_mapping.get(target_source, 
                "site:scholar.google.com OR site:pubmed.ncbi.nlm.nih.gov OR site:arxiv.org OR site:researchgate.net")
            
            academic_query = f"{query} {site_restriction}"
            
            if logger:
                logger.info(f"🔄 Fallback search: {academic_query[:100]}...")
            
            # Try API first if available
            if DDGS_AVAILABLE:
                try:
                    articles = self.search_duckduckgo_api(academic_query, logger)
                    if articles:
                        if logger:
                            logger.success(f"✅ DuckDuckGo API returned {len(articles)} results")
                        return articles
                except Exception as api_error:
                    if logger:
                        logger.warning(f"⚠️ DuckDuckGo API failed: {str(api_error)}, falling back to HTML scraping")
            
            # Fallback to HTML scraping
            articles = self.search_duckduckgo_html(academic_query, logger)
            
        except Exception as e:
            self.log_error("DuckDuckGo Fallback", e, f"target_source={target_source}", logger)
        
        return articles
    
    def search_duckduckgo_api(self, query: str, logger=None) -> List[Dict]:
        """Search using DuckDuckGo API."""
        articles = []
        
        try:
            with DDGS() as ddgs:
                results = ddgs.text(
                    query, 
                    max_results=min(self.max_results_per_source, 50),  # API has limits
                    safesearch='off',
                    region='us-en'
                )
                
                for result in results:
                    try:
                        title = result.get('title', '')
                        body = result.get('body', '')
                        href = result.get('href', '')
                        
                        # Extract year from title or body
                        year = self.extract_year(title + " " + body)
                        
                        # Basic filtering for academic content
                        if self.is_likely_academic(title, body, href):
                            articles.append({
                                'title': title,
                                'authors': self.extract_authors(title, body),
                                'abstract': body[:500],  # Limit abstract length
                                'url': href,
                                'year': year,
                                'doi': self.extract_doi(body + " " + href)
                            })
                    
                    except Exception as e:
                        if logger:
                            logger.warning(f"⚠️ Error parsing API result: {str(e)}")
                        continue
        
        except Exception as e:
            if logger:
                logger.error(f"❌ DuckDuckGo API error: {str(e)}")
            raise
        
        return articles
    
    def search_duckduckgo_html(self, query: str, logger=None) -> List[Dict]:
        """Fallback HTML scraping for DuckDuckGo."""
        articles = []
        
        try:
            encoded_query = quote_plus(query)
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            
            if logger:
                logger.info(f"🌐 HTML scraping: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find search result elements
            result_elements = soup.find_all('div', class_='result') or soup.find_all('div', class_='web-result')
            
            if not result_elements:
                if logger:
                    logger.warning("⚠️ No result elements found in HTML")
                return articles
            
            count = 0
            for result in result_elements:
                if count >= self.max_results_per_source:
                    break
                
                try:
                    # Extract title - try multiple selectors
                    title_elem = (result.find('a', class_='result__a') or 
                                 result.find('h3') or 
                                 result.find('a', href=True))
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    
                    # Extract snippet/abstract - try multiple selectors
                    snippet_elem = (result.find('a', class_='result__snippet') or 
                                   result.find('span', class_='result__snippet') or
                                   result.find('div', class_='snippet'))
                    
                    abstract = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Try to extract year from title or snippet
                    year = self.extract_year(title + " " + abstract)
                    
                    # Basic filtering for academic content
                    if title and self.is_likely_academic(title, abstract, link):
                        articles.append({
                            'title': title,
                            'authors': self.extract_authors(title, abstract),
                            'abstract': abstract[:500],
                            'url': link,
                            'year': year,
                            'doi': self.extract_doi(abstract + " " + link)
                        })
                        count += 1
                
                except Exception as e:
                    if logger:
                        logger.warning(f"⚠️ Error parsing HTML result: {str(e)}")
                    continue
                
                time.sleep(0.3)  # Small delay between results
            
        except Exception as e:
            if logger:
                logger.error(f"❌ HTML scraping error: {str(e)}")
            raise
        
        return articles
    
    def search_duckduckgo_academic(self, query: str, logger=None) -> List[Dict]:
        """Search academic papers using DuckDuckGo with enhanced error handling."""
        try:
            return self.search_duckduckgo_fallback(query, "DuckDuckGo Academic", logger)
        except Exception as e:
            self.log_error("DuckDuckGo Academic", e, "primary_search", logger)
            return []
    
    def search_google_scholar(self, query: str, logger=None) -> List[Dict]:
        """Search Google Scholar with enhanced error handling."""
        try:
            return self.search_duckduckgo_fallback(query, "Google Scholar", logger)
        except Exception as e:
            self.log_error("Google Scholar", e, "primary_search", logger)
            return []
    
    def search_pubmed(self, query: str, logger=None) -> List[Dict]:
        """Search PubMed with enhanced error handling."""
        try:
            return self.search_duckduckgo_fallback(query, "PubMed/MEDLINE", logger)
        except Exception as e:
            self.log_error("PubMed", e, "primary_search", logger)
            return []
    
    def search_scopus_fallback(self, query: str, logger=None) -> List[Dict]:
        """Search Scopus using DuckDuckGo fallback."""
        try:
            return self.search_duckduckgo_fallback(query, "Scopus", logger)
        except Exception as e:
            self.log_error("Scopus", e, "fallback_search", logger)
            return []
    
    def search_wos_fallback(self, query: str, logger=None) -> List[Dict]:
        """Search Web of Science using DuckDuckGo fallback."""
        try:
            return self.search_duckduckgo_fallback(query, "Web of Science", logger)
        except Exception as e:
            self.log_error("Web of Science", e, "fallback_search", logger)
            return []
    
    def search_embase_fallback(self, query: str, logger=None) -> List[Dict]:
        """Search EMBASE using DuckDuckGo fallback."""
        try:
            return self.search_duckduckgo_fallback(query, "EMBASE", logger)
        except Exception as e:
            self.log_error("EMBASE", e, "fallback_search", logger)
            return []
    
    def search_psycinfo_fallback(self, query: str, logger=None) -> List[Dict]:
        """Search PsycINFO using DuckDuckGo fallback."""
        try:
            return self.search_duckduckgo_fallback(query, "PsycINFO", logger)
        except Exception as e:
            self.log_error("PsycINFO", e, "fallback_search", logger)
            return []
    
    def is_likely_academic(self, title: str, abstract: str, url: str) -> bool:
        """Enhanced check if content is likely academic with better filtering."""
        if not title or len(title.strip()) < 10:
            return False
        
        # Academic indicators with weights
        academic_indicators = {
            'study': 2, 'research': 2, 'analysis': 2, 'investigation': 2, 'trial': 2,
            'method': 1, 'results': 1, 'conclusion': 1, 'systematic': 3, 'meta-analysis': 3,
            'journal': 2, 'publication': 1, 'doi': 3, 'abstract': 1, 'clinical': 2,
            'review': 2, 'findings': 1, 'evidence': 2, 'data': 1, 'patients': 2,
            'treatment': 2, 'therapy': 2, 'intervention': 2, 'outcomes': 2, 'university': 2,
            'college': 1, 'department': 1, 'institute': 2, 'laboratory': 2, 'lab': 1
        }
        
        # Strong academic domains
        strong_academic_domains = [
            'scholar.google.com', 'pubmed.ncbi.nlm.nih.gov', 'arxiv.org', 'researchgate.net',
            'sciencedirect.com', 'springer.com', 'wiley.com', 'nature.com', 'science.org',
            'tandfonline.com', 'ieee.org', 'acm.org', 'jstor.org', 'ncbi.nlm.nih.gov'
        ]
        
        # Weak academic domains (give some points but not decisive)
        weak_academic_domains = [
            'academia.edu', 'semanticscholar.org', 'pubmed.gov', 'nih.gov', 'edu',
            'elsevier.com', 'sage.com', 'cambridge.org', 'oxford.com'
        ]
        
        # Non-academic indicators (negative points)
        non_academic_indicators = {
            'blog': -2, 'news': -1, 'wikipedia': -2, 'forum': -2, 'comment': -1,
            'social': -1, 'facebook': -3, 'twitter': -3, 'instagram': -3, 'reddit': -2,
            'youtube': -2, 'tiktok': -3, 'shopping': -3, 'buy': -2, 'sale': -2,
            'advertisement': -3, 'ad': -1, 'spam': -3
        }
        
        text = (title + " " + abstract).lower()
        score = 0
        
        # Score based on academic indicators
        for indicator, weight in academic_indicators.items():
            if indicator in text:
                score += weight
        
        # Score based on non-academic indicators
        for indicator, weight in non_academic_indicators.items():
            if indicator in text:
                score += weight
        
        # Strong boost for strong academic domains
        url_lower = url.lower()
        for domain in strong_academic_domains:
            if domain in url_lower:
                score += 5
                break
        else:
            # Check weak academic domains
            for domain in weak_academic_domains:
                if domain in url_lower:
                    score += 2
                    break
        
        # Additional checks
        if re.search(r'\b(doi|pmid|isbn|issn):', text):
            score += 3
        
        if re.search(r'\b(volume|issue|pages?):\s*\d+', text):
            score += 2
        
        if re.search(r'\b(published|journal|conference|proceedings)', text):
            score += 2
        
        # Title pattern checks
        if re.search(r'^[A-Z][^.!?]*[:.]\s*[A-Z]', title):  # Title with subtitle
            score += 1
        
        if len(title.split()) > 8:  # Long descriptive titles are often academic
            score += 1
        
        # Minimum threshold for academic content
        return score >= 3
    
    def get_search_statistics(self) -> Dict:
        """Get detailed search statistics for debugging."""
        return {
            'summary': self.search_stats,
            'error_details': [
                {
                    'source': error['source'],
                    'error_type': error['error_type'],
                    'error_message': error['error_message'][:200],
                    'context': error['context']
                }
                for error in self.search_stats.get('errors', [])
            ]
        }
    
    def extract_year(self, text: str) -> Optional[int]:
        """Extract publication year from text."""
        # Look for 4-digit years between 1900 and current year + 1
        year_pattern = r'\b(19\d{2}|20[0-2]\d)\b'
        matches = re.findall(year_pattern, text)
        
        if matches:
            # Return the most recent year found
            years = [int(year) for year in matches]
            return max(years)
        
        return None
    
    def extract_authors(self, title: str, abstract: str) -> str:
        """Extract authors from title or abstract."""
        # This is a simplified extraction - in practice, this would be more sophisticated
        text = title + " " + abstract
        
        # Look for common author patterns
        author_patterns = [
            r'by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+et\s+al\.?)?)',
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)(?:\s+et\s+al\.?)?'
        ]
        
        for pattern in author_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return "Unknown"
    
    def extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text."""
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        matches = re.findall(doi_pattern, text)
        return matches[0] if matches else None
    
    def extract_pmid(self, url: str) -> Optional[str]:
        """Extract PubMed ID from URL."""
        pmid_pattern = r'/(\d+)/?$'
        matches = re.findall(pmid_pattern, url)
        return matches[0] if matches else None
    
    def remove_duplicate_papers(self, df: pd.DataFrame, logger=None) -> pd.DataFrame:
        """Remove duplicate papers based on title similarity."""
        if df.empty:
            return df
        
        # Simple deduplication based on title
        df_clean = df.drop_duplicates(subset=['title'], keep='first')
        
        # More sophisticated deduplication could be added here
        # (e.g., fuzzy string matching for similar titles)
        
        removed_count = len(df) - len(df_clean)
        if logger and removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate articles")
        
        return df_clean.reset_index(drop=True)
    
    def clean_article_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize article data."""
        if df.empty:
            return df
        
        # Fill missing values
        df['authors'] = df['authors'].fillna('Unknown')
        df['abstract'] = df['abstract'].fillna('')
        df['year'] = df['year'].fillna(0)
        
        # Clean title
        df['title'] = df['title'].str.strip()
        df['title'] = df['title'].str.replace(r'\s+', ' ', regex=True)
        
        # Clean abstract
        df['abstract'] = df['abstract'].str.strip()
        df['abstract'] = df['abstract'].str.replace(r'\s+', ' ', regex=True)
        
        # Limit abstract length
        df['abstract'] = df['abstract'].str[:1000]
        
        # Ensure required columns exist
        required_columns = ['id', 'title', 'authors', 'abstract', 'source', 'url', 'year']
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        return df[required_columns]


class PDFDownloader:
    """Downloads and manages PDF files for articles."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.uploads_dir = project_dir / "uploads"
        self.uploads_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def download_pdf(self, article_url: str, article_id: str, title: str, logger=None) -> Optional[str]:
        """Attempt to download PDF for an article."""
        try:
            # Try to find direct PDF link
            pdf_url = self.find_pdf_url(article_url, logger)
            
            if not pdf_url:
                if logger:
                    logger.warning(f"No PDF found for: {title[:50]}...")
                return None
            
            # Download PDF
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not pdf_url.endswith('.pdf'):
                if logger:
                    logger.warning(f"Downloaded content is not a PDF for: {title[:50]}...")
                return None
            
            # Save PDF
            filename = f"{article_id}_{self.sanitize_filename(title)}.pdf"
            filepath = self.uploads_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            if logger:
                logger.success(f"Downloaded PDF: {title[:50]}...")
            
            return str(filepath)
            
        except Exception as e:
            if logger:
                logger.error(f"Error downloading PDF for {title[:50]}...: {str(e)}")
            return None
    
    def find_pdf_url(self, article_url: str, logger=None) -> Optional[str]:
        """Find direct PDF URL from article page."""
        try:
            response = self.session.get(article_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Common PDF link patterns
            pdf_selectors = [
                'a[href$=".pdf"]',
                'a[href*="pdf"]',
                'a[title*="PDF"]',
                'a[aria-label*="PDF"]',
                'a.pdf-link',
                '.pdf-download a',
                '.download-pdf a'
            ]
            
            for selector in pdf_selectors:
                pdf_links = soup.select(selector)
                for link in pdf_links:
                    href = link.get('href')
                    if href:
                        # Convert relative URLs to absolute
                        pdf_url = urljoin(article_url, href)
                        if self.is_valid_pdf_url(pdf_url):
                            return pdf_url
            
            # Try to find PDF in meta tags
            meta_pdf = soup.find('meta', {'name': 'citation_pdf_url'})
            if meta_pdf and meta_pdf.get('content'):
                return meta_pdf['content']
            
        except Exception as e:
            if logger:
                logger.warning(f"Error finding PDF URL: {str(e)}")
        
        return None
    
    def is_valid_pdf_url(self, url: str) -> bool:
        """Check if URL looks like a valid PDF URL."""
        return (url.endswith('.pdf') or 
                'pdf' in url.lower() or 
                'download' in url.lower())
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem."""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip()
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename
    
    def get_uploaded_pdfs(self) -> List[Dict]:
        """Get list of uploaded PDF files."""
        pdfs = []
        
        for pdf_file in self.uploads_dir.glob("*.pdf"):
            pdfs.append({
                'filename': pdf_file.name,
                'filepath': str(pdf_file),
                'size': pdf_file.stat().st_size,
                'modified': pdf_file.stat().st_mtime
            })
        
        return sorted(pdfs, key=lambda x: x['modified'], reverse=True)
