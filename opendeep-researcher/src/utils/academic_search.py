"""
Enhanced academic search utility with multiple fallback strategies.
Specifically designed to work with Google Scholar and other academic databases.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import quote_plus, urljoin
from typing import List, Dict, Optional
import json
import random
import logging
from pathlib import Path

# Import scholarly package
try:
    from scholarly import scholarly
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False

class RobustAcademicSearcher:
    """
    A robust academic paper searcher with multiple strategies and fallbacks.
    Designed to actually find papers when other methods fail.
    """
    
    def __init__(self, max_results_per_source: int = 100, delay_range: tuple = (1, 3)):
        self.max_results_per_source = max_results_per_source
        self.delay_range = delay_range
        self.session = requests.Session()
        
        # Rotate through different user agents to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]
        
        self.setup_session()
        self.setup_logging()
        
        # Track what actually works
        self.successful_methods = []
        self.failed_methods = []
        
    def setup_session(self):
        """Setup session with headers that work better for academic sites."""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def setup_logging(self):
        """Setup logging for debugging."""
        self.logger = logging.getLogger('robust_academic_searcher')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def random_delay(self):
        """Add random delay to avoid rate limiting."""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
    
    def search_all_sources(self, keywords: List[str], sources: List[str], logger=None) -> pd.DataFrame:
        """
        Search all sources with multiple fallback strategies.
        """
        all_articles = []
        
        if not keywords:
            if logger:
                logger.error("❌ No keywords provided")
            return pd.DataFrame(columns=['id', 'title', 'authors', 'abstract', 'source', 'url', 'year'])
        
        # Clean and prepare keywords
        clean_keywords = [kw.strip() for kw in keywords if kw.strip()]
        
        # Create different keyword combinations for better coverage
        keyword_combinations = self.create_keyword_combinations(clean_keywords)
        
        if logger:
            logger.info(f"🔍 Starting search with {len(clean_keywords)} keywords across {len(sources)} sources")
            logger.info(f"Keywords: {', '.join(clean_keywords[:5])}{'...' if len(clean_keywords) > 5 else ''}")
            logger.info(f"📝 Created {len(keyword_combinations)} keyword combinations for broader search")
        
        for source in sources:
            if logger:
                logger.info(f"🎯 Searching {source}...")
            
            articles = []
            method_used = "none"
            
            try:
                if source == "Google Scholar":
                    # Try multiple approaches for Google Scholar
                    articles_gs, method_gs = self.search_google_scholar_robust(clean_keywords, logger)
                    articles = articles_gs
                    method_used = method_gs
                    
                    # If we didn't get many results, try with different keyword combinations
                    if len(articles) < self.max_results_per_source // 2:
                        for combo in keyword_combinations[:2]:  # Try 2 more combinations
                            additional_articles, _ = self.search_google_scholar_robust(combo, logger)
                            articles.extend(additional_articles)
                            if len(articles) >= self.max_results_per_source:
                                break
                        method_used = f"{method_gs}_extended"
                        
                elif source == "Google Scholar (Scholarly)":
                    articles, method_used = self.search_scholarly_api(clean_keywords, logger)
                elif source == "PubMed/MEDLINE":
                    articles, method_used = self.search_pubmed_robust(clean_keywords, logger)
                elif source == "DuckDuckGo Academic":
                    articles, method_used = self.search_duckduckgo_robust(clean_keywords, logger)
                elif source == "arXiv":
                    articles, method_used = self.search_arxiv_robust(clean_keywords, logger)
                elif source == "ResearchGate":
                    articles, method_used = self.search_researchgate_robust(clean_keywords, logger)
                else:
                    # Universal fallback for any source
                    articles, method_used = self.search_universal_fallback(clean_keywords, source, logger)
                
                # Add metadata to articles
                for article in articles:
                    article['source'] = source
                    article['search_method'] = method_used
                    article['keywords_used'] = ', '.join(clean_keywords)
                
                all_articles.extend(articles)
                
                if articles:
                    self.successful_methods.append(f"{source}:{method_used}")
                    if logger:
                        logger.success(f"✅ {source}: Found {len(articles)} articles using {method_used}")
                else:
                    self.failed_methods.append(f"{source}:{method_used}")
                    if logger:
                        logger.warning(f"⚠️ {source}: No articles found using {method_used}")
                
                # Random delay between sources
                if len(sources) > 1:
                    self.random_delay()
                    
            except Exception as e:
                self.failed_methods.append(f"{source}:error")
                if logger:
                    logger.error(f"❌ {source} failed: {str(e)}")
                continue
        
        # Process results
        if all_articles:
            try:
                df = pd.DataFrame(all_articles)
                df['id'] = range(1, len(df) + 1)
                
                # Remove duplicates
                df = self.remove_duplicates(df, logger)
                
                # Clean data
                df = self.clean_article_data(df)
                
                if logger:
                    logger.success(f"🎉 Total articles found: {len(df)}")
                    logger.info(f"📊 Successful methods: {', '.join(self.successful_methods)}")
                
                return df
                
            except Exception as e:
                if logger:
                    logger.error(f"❌ Error processing results: {str(e)}")
        
        if logger:
            logger.warning("⚠️ No articles found across all sources and methods")
            logger.info(f"Failed methods: {', '.join(self.failed_methods)}")
        
        return pd.DataFrame(columns=['id', 'title', 'authors', 'abstract', 'source', 'url', 'year'])
    
    def search_single_source(self, keywords: List[str], source: str, logger=None) -> List[Dict]:
        """
        Search a single source and return articles for live progress tracking.
        """
        articles = []
        method_used = "none"
        
        if not keywords:
            if logger:
                logger.error("❌ No keywords provided")
            return []
        
        # Clean and prepare keywords
        clean_keywords = [kw.strip() for kw in keywords if kw.strip()]
        
        try:
            if source == "Google Scholar":
                # Try multiple approaches for Google Scholar
                articles_gs, method_gs = self.search_google_scholar_robust(clean_keywords, logger)
                articles = articles_gs
                method_used = method_gs
                
                # If we didn't get many results, try with different keyword combinations
                if len(articles) < self.max_results_per_source // 2:
                    keyword_combinations = self.create_keyword_combinations(clean_keywords)
                    for combo in keyword_combinations[:2]:  # Try 2 more combinations
                        additional_articles, _ = self.search_google_scholar_robust(combo, logger)
                        articles.extend(additional_articles)
                        if len(articles) >= self.max_results_per_source:
                            break
                    method_used = f"{method_gs}_extended"
                    
            elif source == "Google Scholar (Scholarly)":
                articles, method_used = self.search_scholarly_api(clean_keywords, logger)
            elif source == "PubMed/MEDLINE":
                articles, method_used = self.search_pubmed_robust(clean_keywords, logger)
            elif source == "DuckDuckGo Academic":
                articles, method_used = self.search_duckduckgo_robust(clean_keywords, logger)
            elif source == "arXiv":
                articles, method_used = self.search_arxiv_robust(clean_keywords, logger)
            elif source == "ResearchGate":
                articles, method_used = self.search_researchgate_robust(clean_keywords, logger)
            else:
                # Universal fallback for any source
                articles, method_used = self.search_universal_fallback(clean_keywords, source, logger)
            
            # Add metadata to articles
            for article in articles:
                article['source'] = source
                article['search_method'] = method_used
                article['keywords_used'] = ', '.join(clean_keywords)
            
            if articles:
                self.successful_methods.append(f"{source}:{method_used}")
            else:
                self.failed_methods.append(f"{source}:{method_used}")
                
        except Exception as e:
            self.failed_methods.append(f"{source}:error")
            if logger:
                logger.error(f"❌ {source} failed: {str(e)}")
        
        return articles
    
    def search_google_scholar_robust(self, keywords: List[str], logger=None) -> tuple[List[Dict], str]:
        """
        Multiple strategies to search Google Scholar.
        """
        articles = []
        
        # Strategy 1: Direct Google Scholar search with simple query
        try:
            if logger:
                logger.info("🔄 Trying direct Google Scholar search...")
            
            query = " ".join(keywords[:3])  # Use first 3 keywords to avoid overly complex queries
            encoded_query = quote_plus(query)
            
            # Use a simple Google Scholar URL
            url = f"https://scholar.google.com/scholar?q={encoded_query}&hl=en&as_sdt=0%2C5"
            
            # Rotate user agent
            self.session.headers['User-Agent'] = random.choice(self.user_agents)
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                articles = self.parse_google_scholar_html(response.content, logger)
                if articles:
                    return articles, "direct_scholar"
            
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Direct Scholar failed: {str(e)}")
        
        # Strategy 2: Use DuckDuckGo to search Scholar
        try:
            if logger:
                logger.info("🔄 Trying DuckDuckGo -> Scholar search...")
            
            articles = self.search_via_duckduckgo("scholar.google.com", keywords, logger)
            if articles:
                return articles, "duckduckgo_scholar"
                
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ DuckDuckGo Scholar failed: {str(e)}")
        
        # Strategy 3: Search for academic papers with specific terms
        try:
            if logger:
                logger.info("🔄 Trying academic paper search...")
            
            # Add academic terms to improve results
            academic_query = f"{' '.join(keywords[:2])} research study paper"
            articles = self.search_via_duckduckgo("", [academic_query], logger, academic_sites=True)
            if articles:
                return articles, "academic_terms"
                
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Academic terms search failed: {str(e)}")
        
        return [], "failed"
    
    def search_scholarly_api(self, keywords: List[str], logger=None) -> tuple[List[Dict], str]:
        """
        Search using the scholarly package for Google Scholar.
        This provides more reliable and structured access to Google Scholar.
        """
        if not SCHOLARLY_AVAILABLE:
            if logger:
                logger.warning("⚠️ Scholarly package not available")
            return [], "scholarly_unavailable"
        
        articles = []
        
        try:
            if logger:
                logger.info("🔄 Trying scholarly API search...")
            
            # Construct search query - use first few keywords to avoid overly complex queries
            query = " ".join(keywords[:3])
            
            if logger:
                logger.info(f"📚 Searching scholarly for: {query}")
            
            # Search using scholarly
            search_query = scholarly.search_pubs(query)
            
            count = 0
            for pub in search_query:
                if count >= min(self.max_results_per_source, 50):  # Limit to prevent timeout, but allow more results
                    break
                
                try:
                    # Fill in publication details
                    pub_filled = scholarly.fill(pub)
                    
                    # Extract article information
                    article = {
                        'title': pub_filled.get('title', '').strip(),
                        'authors': self.format_scholarly_authors(pub_filled.get('author', [])),
                        'abstract': pub_filled.get('abstract', '').strip(),
                        'url': pub_filled.get('pub_url', ''),
                        'year': self.extract_year_from_scholarly(pub_filled),
                        'doi': self.extract_doi_from_scholarly(pub_filled),
                        'journal': pub_filled.get('journal', ''),
                        'citations': pub_filled.get('num_citations', 0),
                        'venue': pub_filled.get('venue', '')
                    }
                    
                    # Validate article
                    if self.is_valid_scholarly_article(article):
                        articles.append(article)
                        count += 1
                        
                        if logger and count % 5 == 0:
                            logger.info(f"📄 Found {count} articles via scholarly...")
                    
                    # Add delay to be respectful
                    time.sleep(random.uniform(1, 2))
                    
                except Exception as e:
                    if logger:
                        logger.warning(f"⚠️ Error processing scholarly result: {str(e)}")
                    continue
            
            if articles:
                if logger:
                    logger.success(f"✅ Scholarly API found {len(articles)} articles")
                return articles, "scholarly_api"
            else:
                if logger:
                    logger.warning("⚠️ Scholarly API returned no valid articles")
                return [], "scholarly_no_results"
                
        except Exception as e:
            if logger:
                logger.error(f"❌ Scholarly API search failed: {str(e)}")
            return [], "scholarly_error"
    
    def format_scholarly_authors(self, author_list: List) -> str:
        """Format author list from scholarly into a readable string."""
        if not author_list:
            return "Unknown"
        
        try:
            authors = []
            for author in author_list[:5]:  # Limit to first 5 authors
                if isinstance(author, dict):
                    name = author.get('name', '')
                elif isinstance(author, str):
                    name = author
                else:
                    name = str(author)
                
                if name and name.strip():
                    authors.append(name.strip())
            
            if authors:
                if len(author_list) > 5:
                    return ", ".join(authors) + " et al."
                else:
                    return ", ".join(authors)
            else:
                return "Unknown"
                
        except Exception:
            return "Unknown"
    
    def extract_year_from_scholarly(self, pub: Dict) -> Optional[int]:
        """Extract year from scholarly publication data."""
        try:
            # Try different year fields
            year_fields = ['year', 'pub_year', 'bib']
            
            for field in year_fields:
                if field in pub and pub[field]:
                    if field == 'bib' and isinstance(pub[field], dict):
                        # Look in bibliography data
                        bib_year = pub[field].get('pub_year')
                        if bib_year:
                            return int(bib_year)
                    else:
                        # Direct year field
                        year_val = pub[field]
                        if isinstance(year_val, (int, str)):
                            year = int(str(year_val)[:4])  # Take first 4 digits
                            if 1900 <= year <= 2030:
                                return year
            
            # Fallback: extract from title or venue
            title_text = pub.get('title', '') + ' ' + pub.get('venue', '')
            return self.extract_year(title_text)
            
        except (ValueError, TypeError):
            return None
    
    def extract_doi_from_scholarly(self, pub: Dict) -> Optional[str]:
        """Extract DOI from scholarly publication data."""
        try:
            # Check direct DOI field
            if 'doi' in pub and pub['doi']:
                return pub['doi']
            
            # Check in bibliography data
            if 'bib' in pub and isinstance(pub['bib'], dict):
                bib_doi = pub['bib'].get('doi')
                if bib_doi:
                    return bib_doi
            
            # Check URL for DOI pattern
            url = pub.get('pub_url', '')
            if url and 'doi.org' in url:
                doi_match = re.search(r'doi\.org/(.+)', url)
                if doi_match:
                    return doi_match.group(1)
            
            # Extract from abstract or title
            text = pub.get('abstract', '') + ' ' + pub.get('title', '')
            return self.extract_doi(text)
            
        except Exception:
            return None
    
    def is_valid_scholarly_article(self, article: Dict) -> bool:
        """Check if a scholarly article is valid."""
        if not article.get('title') or len(article['title']) < 10:
            return False
        
        # Check for reasonable title length
        title_len = len(article['title'])
        if title_len < 10 or title_len > 300:
            return False
        
        # Should have some basic information
        has_info = bool(article.get('authors') and article['authors'] != "Unknown")
        
        return has_info
    
    def create_keyword_combinations(self, keywords: List[str]) -> List[List[str]]:
        """Create different keyword combinations for broader search coverage."""
        if not keywords:
            return []
        
        combinations = []
        
        # Original full list
        combinations.append(keywords[:])
        
        # Top 5 keywords
        if len(keywords) > 5:
            combinations.append(keywords[:5])
        
        # Top 3 keywords
        if len(keywords) > 3:
            combinations.append(keywords[:3])
        
        # Split into chunks of 4-6 keywords
        chunk_size = 5
        for i in range(0, len(keywords), chunk_size):
            chunk = keywords[i:i + chunk_size]
            if len(chunk) >= 2:  # Only add chunks with at least 2 keywords
                combinations.append(chunk)
        
        return combinations[:4]  # Limit to 4 combinations to avoid too many requests
    
    def search_arxiv_robust(self, keywords: List[str], logger=None) -> tuple[List[Dict], str]:
        """Search arXiv preprint server."""
        try:
            if logger:
                logger.info("🔄 Trying arXiv search...")
            
            articles = self.search_via_duckduckgo("arxiv.org", keywords, logger)
            if articles:
                return articles, "arxiv_search"
                
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ arXiv search failed: {str(e)}")
        
        return [], "failed"
    
    def search_researchgate_robust(self, keywords: List[str], logger=None) -> tuple[List[Dict], str]:
        """Search ResearchGate academic network."""
        try:
            if logger:
                logger.info("🔄 Trying ResearchGate search...")
            
            articles = self.search_via_duckduckgo("researchgate.net", keywords, logger)
            if articles:
                return articles, "researchgate_search"
                
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ ResearchGate search failed: {str(e)}")
        
        return [], "failed"
    
    def search_pubmed_robust(self, keywords: List[str], logger=None) -> tuple[List[Dict], str]:
        """
        Multiple strategies to search PubMed.
        """
        # Strategy 1: Direct PubMed search via DuckDuckGo
        try:
            if logger:
                logger.info("🔄 Trying PubMed via DuckDuckGo...")
            
            articles = self.search_via_duckduckgo("pubmed.ncbi.nlm.nih.gov", keywords, logger)
            if articles:
                return articles, "duckduckgo_pubmed"
                
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ DuckDuckGo PubMed failed: {str(e)}")
        
        # Strategy 2: Search NIH sites
        try:
            if logger:
                logger.info("🔄 Trying NIH sites search...")
            
            articles = self.search_via_duckduckgo("nih.gov", keywords, logger)
            if articles:
                return articles, "nih_sites"
                
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ NIH sites search failed: {str(e)}")
        
        return [], "failed"
    
    def search_duckduckgo_robust(self, keywords: List[str], logger=None) -> tuple[List[Dict], str]:
        """
        Enhanced DuckDuckGo search with academic focus and multiple strategies.
        """
        articles = []
        
        # Strategy 1: Academic sites search
        try:
            if logger:
                logger.info("🔄 Trying enhanced DuckDuckGo academic search...")
            
            articles = self.search_via_duckduckgo("", keywords, logger, academic_sites=True)
            if articles:
                if logger:
                    logger.info(f"📚 Found {len(articles)} articles from academic sites")
                
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Enhanced DuckDuckGo failed: {str(e)}")
        
        # Strategy 2: If we need more results, try broader search
        if len(articles) < self.max_results_per_source // 2:
            try:
                if logger:
                    logger.info("🔄 Trying broader DuckDuckGo search for more results...")
                
                # Add research-specific terms
                research_keywords = keywords[:3] + ["research", "study", "paper"]
                additional_articles = self.search_via_duckduckgo("", research_keywords, logger, academic_sites=False)
                
                # Filter to keep only academic-looking results
                filtered_additional = [art for art in additional_articles if self.is_valid_article(art)]
                articles.extend(filtered_additional)
                
                if logger and filtered_additional:
                    logger.info(f"📄 Added {len(filtered_additional)} more articles from broader search")
                    
            except Exception as e:
                if logger:
                    logger.warning(f"⚠️ Broader DuckDuckGo search failed: {str(e)}")
        
        if articles:
            return articles[:self.max_results_per_source], "enhanced_duckduckgo"
        else:
            return [], "failed"
    
    def search_universal_fallback(self, keywords: List[str], source: str, logger=None) -> tuple[List[Dict], str]:
        """
        Universal fallback that works for any source with multiple strategies.
        """
        articles = []
        
        try:
            if logger:
                logger.info(f"🔄 Trying universal fallback for {source}...")
            
            # Map source to likely domains
            domain_mapping = {
                "Scopus": "scopus.com",
                "Web of Science": ["webofknowledge.com", "webofscience.com"],
                "EMBASE": "embase.com",
                "PsycINFO": "psycnet.apa.org",
                "arXiv": "arxiv.org",
                "ResearchGate": "researchgate.net"
            }
            
            domains = domain_mapping.get(source, "")
            if isinstance(domains, str):
                domains = [domains] if domains else []
            
            # Strategy 1: Try specific domain search
            for domain in domains:
                try:
                    domain_articles = self.search_via_duckduckgo(domain, keywords, logger, academic_sites=True)
                    articles.extend(domain_articles)
                    if len(articles) >= self.max_results_per_source // 2:
                        break
                except Exception:
                    continue
            
            # Strategy 2: If no domain or few results, try general academic search with source name
            if len(articles) < self.max_results_per_source // 2:
                try:
                    # Add source name to search terms
                    enhanced_keywords = keywords[:3] + [source.split()[0].lower()]  # Add first word of source
                    general_articles = self.search_via_duckduckgo("", enhanced_keywords, logger, academic_sites=True)
                    articles.extend(general_articles)
                except Exception:
                    pass
            
            # Remove duplicates
            seen_titles = set()
            unique_articles = []
            for article in articles:
                title_key = article.get('title', '').lower().strip()
                if title_key and title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_articles.append(article)
            
            if unique_articles:
                return unique_articles[:self.max_results_per_source], "universal_fallback_enhanced"
                
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Universal fallback failed: {str(e)}")
        
        return [], "failed"
    
    def search_via_duckduckgo(self, site_filter: str, keywords: List[str], logger=None, academic_sites: bool = False) -> List[Dict]:
        """
        Search using DuckDuckGo with site filtering and academic focus.
        """
        articles = []
        
        try:
            # Construct query
            query_parts = []
            
            # Add keywords
            main_query = " ".join(keywords[:3])  # Limit to avoid overly complex queries
            query_parts.append(main_query)
            
            # Add site filter if specified
            if site_filter:
                query_parts.append(f"site:{site_filter}")
            elif academic_sites:
                # Search multiple academic sites
                academic_domains = [
                    "scholar.google.com", "pubmed.ncbi.nlm.nih.gov", "arxiv.org", 
                    "researchgate.net", "sciencedirect.com", "springer.com"
                ]
                site_query = " OR ".join([f"site:{domain}" for domain in academic_domains])
                query_parts.append(f"({site_query})")
            
            # Add academic terms to improve relevance
            if not site_filter or academic_sites:
                query_parts.append("(research OR study OR analysis OR paper OR journal)")
            
            final_query = " ".join(query_parts)
            
            if logger:
                logger.info(f"🔍 Searching: {final_query[:100]}...")
            
            # Perform search
            encoded_query = quote_plus(final_query)
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            
            # Rotate user agent
            self.session.headers['User-Agent'] = random.choice(self.user_agents)
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            articles = self.parse_duckduckgo_html(response.content, logger)
            
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ DuckDuckGo search error: {str(e)}")
            raise
        
        return articles
    
    def parse_google_scholar_html(self, html_content: bytes, logger=None) -> List[Dict]:
        """
        Parse Google Scholar HTML to extract paper information.
        """
        articles = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for Scholar result containers
            result_containers = soup.find_all('div', class_='gs_ri') or soup.find_all('div', class_='gs_r')
            
            if not result_containers:
                if logger:
                    logger.warning("⚠️ No Scholar result containers found")
                return articles
            
            for container in result_containers[:self.max_results_per_source]:
                try:
                    article = self.extract_scholar_article(container)
                    if article and self.is_valid_article(article):
                        articles.append(article)
                        
                except Exception as e:
                    if logger:
                        logger.warning(f"⚠️ Error parsing Scholar result: {str(e)}")
                    continue
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Error parsing Scholar HTML: {str(e)}")
        
        return articles
    
    def parse_duckduckgo_html(self, html_content: bytes, logger=None) -> List[Dict]:
        """
        Parse DuckDuckGo HTML to extract academic paper information.
        """
        articles = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for result containers - try multiple selectors
            result_selectors = [
                'div.result',
                'div.web-result',
                'div[class*="result"]',
                'article',
                'div.serp-result'
            ]
            
            result_containers = []
            for selector in result_selectors:
                containers = soup.select(selector)
                if containers:
                    result_containers = containers
                    break
            
            if not result_containers:
                if logger:
                    logger.warning("⚠️ No result containers found in DuckDuckGo HTML")
                return articles
            
            if logger:
                logger.info(f"📄 Found {len(result_containers)} result containers")
            
            for container in result_containers[:self.max_results_per_source]:
                try:
                    article = self.extract_duckduckgo_article(container)
                    if article and self.is_valid_article(article):
                        articles.append(article)
                        
                except Exception as e:
                    continue  # Silently skip failed extractions
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Error parsing DuckDuckGo HTML: {str(e)}")
        
        return articles
    
    def extract_scholar_article(self, container) -> Optional[Dict]:
        """Extract article info from Google Scholar result container."""
        try:
            # Title
            title_elem = container.find('h3', class_='gs_rt') or container.find('a')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Link
            link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
            url = link_elem.get('href', '') if link_elem else ''
            
            # Abstract/snippet
            abstract_elem = container.find('div', class_='gs_rs')
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
            
            # Authors and publication info
            auth_elem = container.find('div', class_='gs_a')
            auth_text = auth_elem.get_text(strip=True) if auth_elem else ""
            
            # Extract year
            year = self.extract_year(title + " " + abstract + " " + auth_text)
            
            # Extract authors (first part before dash or comma)
            authors = self.extract_authors_from_text(auth_text)
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'url': url,
                'year': year,
                'doi': self.extract_doi(abstract + " " + auth_text)
            }
            
        except Exception:
            return None
    
    def extract_duckduckgo_article(self, container) -> Optional[Dict]:
        """Extract article info from DuckDuckGo result container."""
        try:
            # Title - try multiple selectors
            title_selectors = [
                'a.result__a',
                'h3 a',
                'h2 a', 
                'a[href]',
                '.result-title a',
                '.result__title a'
            ]
            
            title_elem = None
            for selector in title_selectors:
                title_elem = container.select_one(selector)
                if title_elem:
                    break
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
            
            # Snippet/abstract - try multiple selectors
            snippet_selectors = [
                '.result__snippet',
                '.result-snippet',
                '.snippet',
                '.description',
                '.result__body'
            ]
            
            abstract = ""
            for selector in snippet_selectors:
                snippet_elem = container.select_one(selector)
                if snippet_elem:
                    abstract = snippet_elem.get_text(strip=True)
                    break
            
            # Extract year and authors
            full_text = title + " " + abstract
            year = self.extract_year(full_text)
            authors = self.extract_authors_from_text(full_text)
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract[:500],  # Limit length
                'url': url,
                'year': year,
                'doi': self.extract_doi(full_text)
            }
            
        except Exception:
            return None
    
    def is_valid_article(self, article: Dict) -> bool:
        """Check if an article looks like a valid academic paper."""
        if not article.get('title') or len(article['title']) < 10:
            return False
        
        title = article['title'].lower()
        abstract = article.get('abstract', '').lower()
        url = article.get('url', '').lower()
        
        # Academic indicators
        academic_terms = [
            'research', 'study', 'analysis', 'investigation', 'journal', 'paper',
            'findings', 'results', 'method', 'systematic', 'clinical', 'trial',
            'evidence', 'data', 'university', 'institute', 'department'
        ]
        
        # Check for academic terms
        text = title + " " + abstract
        academic_score = sum(1 for term in academic_terms if term in text)
        
        # Check for academic domains
        academic_domains = [
            'scholar.google', 'pubmed', 'arxiv', 'researchgate', 'sciencedirect',
            'springer', 'wiley', 'nature.com', 'science.org', 'ieee.org', 'acm.org'
        ]
        
        domain_score = sum(1 for domain in academic_domains if domain in url)
        
        # Exclude obvious non-academic content
        excluded_terms = ['wikipedia', 'facebook', 'twitter', 'youtube', 'shopping', 'news']
        if any(term in url for term in excluded_terms):
            return False
        
        # Must have some academic indicators
        return academic_score >= 1 or domain_score >= 1
    
    def extract_year(self, text: str) -> Optional[int]:
        """Extract publication year from text."""
        year_pattern = r'\b(19\d{2}|20[0-2]\d)\b'
        matches = re.findall(year_pattern, text)
        
        if matches:
            years = [int(year) for year in matches]
            return max(years)  # Return most recent year
        
        return None
    
    def extract_authors_from_text(self, text: str) -> str:
        """Extract authors from text with better patterns."""
        if not text:
            return "Unknown"
        
        # Look for author patterns
        patterns = [
            r'^([^-•]+?)(?:\s*[-•]\s*)',  # Text before dash or bullet
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Capitalized names
            r'by\s+([^,]+)',  # "by Author"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                author = matches[0].strip()
                if len(author) > 3 and len(author) < 100:
                    return author
        
        # Fallback: take first reasonable part
        parts = text.split('-')[0].split(',')[0].strip()
        if len(parts) > 3 and len(parts) < 100:
            return parts
        
        return "Unknown"
    
    def extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text."""
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        matches = re.findall(doi_pattern, text)
        return matches[0] if matches else None
    
    def remove_duplicates(self, df: pd.DataFrame, logger=None) -> pd.DataFrame:
        """Remove duplicate articles based on title similarity."""
        if df.empty:
            return df
        
        # Simple deduplication based on title
        initial_count = len(df)
        df_clean = df.drop_duplicates(subset=['title'], keep='first')
        final_count = len(df_clean)
        
        if logger and initial_count > final_count:
            logger.info(f"🧹 Removed {initial_count - final_count} duplicate articles")
        
        return df_clean.reset_index(drop=True)
    
    def clean_article_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize article data."""
        if df.empty:
            return df
        
        # Fill missing values
        df['authors'] = df['authors'].fillna('Unknown')
        df['abstract'] = df['abstract'].fillna('')
        df['year'] = df['year'].fillna(0)
        df['url'] = df['url'].fillna('')
        
        # Clean title
        df['title'] = df['title'].str.strip()
        df['title'] = df['title'].str.replace(r'\s+', ' ', regex=True)
        
        # Clean abstract
        df['abstract'] = df['abstract'].str.strip()
        df['abstract'] = df['abstract'].str.replace(r'\s+', ' ', regex=True)
        df['abstract'] = df['abstract'].str[:1000]  # Limit length
        
        # Ensure required columns
        required_columns = ['id', 'title', 'authors', 'abstract', 'source', 'url', 'year']
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        return df[required_columns]
    
    def get_statistics(self) -> Dict:
        """Get search statistics."""
        return {
            'successful_methods': self.successful_methods,
            'failed_methods': self.failed_methods,
            'success_rate': len(self.successful_methods) / max(1, len(self.successful_methods) + len(self.failed_methods))
        }
