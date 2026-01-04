"""
Ingestion Layer for Cognitive Representation Mapping System

Responsibility: Get text into the system without interpretation.
Key principle: Ingestion should be dumb, repeatable, and reversible.

This module handles:
- RSS feed fetching (with fallback to RSS descriptions)
- News API integration (NewsAPI, Guardian API)
- URL-based article extraction (with multiple fallback methods)
- Document storage with deduplication
- Minimal, mechanical text extraction (no semantic processing)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
import os
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import feedparser
from urllib.parse import urljoin, urlparse

# Try to import optional dependencies
try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("newspaper3k not available, will use fallback methods")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_PATH = Path("../ingested_data")
BASE_PATH.mkdir(exist_ok=True)
DOCUMENTS_PATH = BASE_PATH / "documents.parquet"
CONFIG_PATH = Path("ingestion_config.json")

# Minimum text length to filter out noise (as per architecture section 4.4)
MIN_TEXT_LENGTH = 200

# Default User-Agent for requests
DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)

# Load API keys from config file if it exists
API_KEYS = {}
if CONFIG_PATH.exists():
    try:
        with open(CONFIG_PATH, 'r') as f:
            API_KEYS = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load config file: {e}")

# Source configuration
# Types: "rss", "newsapi", "guardian", "html"
SOURCES = {
    # Guardian API - completely free, no API key needed
    "Guardian": {
        "type": "guardian",
        "section": "us-news",  # Options: us-news, world, politics, business, etc.
        "max_items": 20
    },
    # NewsAPI - requires free API key (get from newsapi.org)
    # "NewsAPI_US": {
    #     "type": "newsapi",
    #     "country": "us",
    #     "category": "general",  # general, business, technology, etc.
    #     "max_items": 20
    # },
    # Working RSS feeds
    "BBC_News": {
        "type": "rss",
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "max_items": 20,
        "use_rss_description": True  # Fallback to RSS description if article fetch fails
    },
    "NPR": {
        "type": "rss",
        "url": "https://feeds.npr.org/1001/rss.xml",  # NPR News
        "max_items": 20,
        "use_rss_description": True
    },
    "AP_News": {
        "type": "rss",
        "url": "https://feeds.apnews.com/rss/topnews",
        "max_items": 20,
        "use_rss_description": True
    },
    # NYT RSS (may require better headers)
    "NYT": {
        "type": "rss",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "max_items": 20,
        "use_rss_description": True
    }
}


class DocumentIngester:
    """
    Handles ingestion of documents from various sources.
    
    Follows architecture principles:
    - Raw text is sacred (no aggressive cleaning)
    - No topic inference
    - No summarization
    - Repeatable and reversible
    """
    
    def __init__(self, base_path: Path = BASE_PATH):
        self.base_path = base_path
        self.documents_path = base_path / "documents.parquet"
        self.log_path = base_path / "ingestion_log.json"
        self.existing_documents: Optional[pd.DataFrame] = None
        self.existing_ids: set = set()
        
        # Load existing documents for deduplication
        self._load_existing_documents()
    
    def _load_existing_documents(self):
        """Load existing documents to enable deduplication."""
        if self.documents_path.exists():
            try:
                self.existing_documents = pd.read_parquet(self.documents_path)
                self.existing_ids = set(self.existing_documents['id'].values)
                logger.info(f"Loaded {len(self.existing_documents)} existing documents")
            except Exception as e:
                logger.warning(f"Could not load existing documents: {e}")
                self.existing_documents = pd.DataFrame()
                self.existing_ids = set()
        else:
            self.existing_documents = pd.DataFrame()
            self.existing_ids = set()
    
    def generate_document_id(self, url: str, source_id: str) -> str:
        """Generate a deterministic document ID."""
        key = f"{source_id}:{url}".encode('utf-8')
        return hashlib.md5(key).hexdigest()
    
    def fetch_article_with_newspaper(self, url: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[datetime]]:
        """Fetch article using newspaper3k library."""
        if not NEWSPAPER_AVAILABLE:
            return None, None, None, None
        
        try:
            article = Article(url)
            article.config.browser_user_agent = DEFAULT_USER_AGENT
            article.config.request_timeout = timeout
            article.download()
            article.parse()
            
            text = article.text.strip() if article.text else None
            title = article.title.strip() if article.title else None
            authors = article.authors if article.authors else []
            publish_date = article.publish_date
            
            if text and len(text) >= MIN_TEXT_LENGTH:
                return text, title, authors, publish_date
            
        except Exception as e:
            logger.debug(f"newspaper3k failed for {url}: {e}")
        
        return None, None, None, None
    
    def fetch_article_with_requests(self, url: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[datetime]]:
        """Fallback: Fetch article using requests + BeautifulSoup."""
        try:
            headers = {
                'User-Agent': DEFAULT_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Try to find main content area
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find('div', class_=lambda x: x and ('content' in x.lower() or 'article' in x.lower() or 'post' in x.lower())) or
                soup.find('body')
            )
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
            
            # Get title
            title = None
            title_tag = soup.find('title') or soup.find('h1')
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # Try to find publish date
            publish_date = None
            time_tag = soup.find('time')
            if time_tag and time_tag.get('datetime'):
                try:
                    publish_date = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                except:
                    pass
            
            if text and len(text) >= MIN_TEXT_LENGTH:
                return text, title, [], publish_date
            
        except Exception as e:
            logger.debug(f"requests method failed for {url}: {e}")
        
        return None, None, None, None
    
    def fetch_article(self, url: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[datetime]]:
        """
        Fetch article content from a URL with multiple fallback methods.
        
        Returns: (text, title, authors, publish_date)
        """
        # Try newspaper3k first
        result = self.fetch_article_with_newspaper(url, timeout)
        if result[0]:
            return result
        
        # Fallback to requests + BeautifulSoup
        result = self.fetch_article_with_requests(url, timeout)
        if result[0]:
            return result
        
        return None, None, None, None
    
    def fetch_rss_feed(self, feed_url: str, max_items: Optional[int] = None, use_rss_description: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch articles from an RSS feed.
        
        If use_rss_description is True, will use RSS description as fallback
        when full article fetch fails.
        """
        try:
            # Add headers for RSS feeds that might block
            headers = {'User-Agent': DEFAULT_USER_AGENT}
            feed = feedparser.parse(feed_url, request_headers=headers)
            
            if not feed.entries:
                logger.warning(f"No entries found in RSS feed: {feed_url}")
                return []
            
            articles = []
            entries = feed.entries[:max_items] if max_items else feed.entries
            
            logger.info(f"Processing {len(entries)} entries from RSS feed: {feed_url}")
            
            for entry in tqdm(entries, desc="Processing RSS entries"):
                url = entry.get('link', '')
                if not url:
                    continue
                
                # Get metadata from RSS entry
                title = entry.get('title', '')
                description = entry.get('description', '')
                summary = entry.get('summary', description)
                
                # Parse publish date
                publish_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        publish_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # Try to fetch full article
                text, fetched_title, authors, fetched_date = self.fetch_article(url)
                
                # Fallback to RSS description if article fetch failed
                if not text and use_rss_description and summary:
                    # Clean HTML from summary if present
                    soup_desc = BeautifulSoup(summary, 'html.parser')
                    text = soup_desc.get_text(separator=' ', strip=True)
                    logger.debug(f"Using RSS description for {url}")
                
                if not text or len(text) < MIN_TEXT_LENGTH:
                    continue
                
                # Use best available title and date
                title = fetched_title if not title else title
                publish_date = fetched_date if not publish_date else publish_date
                
                articles.append({
                    "url": url,
                    "title": title or "",
                    "authors": authors or [],
                    "published_at": publish_date,
                    "raw_text": text
                })
            
            logger.info(f"Successfully processed {len(articles)} articles from RSS feed")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
            return []
    
    def fetch_guardian_api(self, section: str = "us-news", max_items: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch articles from Guardian API (completely free, no API key needed).
        
        Sections: us-news, world, politics, business, technology, etc.
        """
        try:
            base_url = "https://content.guardianapis.com/search"
            params = {
                "section": section,
                "page-size": min(max_items, 50),  # API max is 50
                "show-fields": "body,byline,publication",
                "api-key": "test"  # Guardian API works with any key, even "test"
            }
            
            logger.info(f"Fetching from Guardian API (section: {section})")
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('response', {}).get('status') != 'ok':
                logger.error(f"Guardian API error: {data}")
                return []
            
            results = data.get('response', {}).get('results', [])
            articles = []
            
            for item in results[:max_items]:
                url = item.get('webUrl', '')
                title = item.get('webTitle', '')
                fields = item.get('fields', {})
                body = fields.get('body', '')
                byline = fields.get('byline', '')
                
                # Parse publish date
                publish_date = None
                if item.get('webPublicationDate'):
                    try:
                        publish_date = datetime.fromisoformat(item['webPublicationDate'].replace('Z', '+00:00'))
                    except:
                        pass
                
                # Extract authors from byline
                authors = []
                if byline:
                    # Byline format: "By Author Name" or "Author Name"
                    byline_clean = byline.replace('By ', '').strip()
                    authors = [byline_clean] if byline_clean else []
                
                # Clean HTML from body
                if body:
                    soup = BeautifulSoup(body, 'html.parser')
                    text = soup.get_text(separator='\n', strip=True)
                else:
                    text = ""
                
                if text and len(text) >= MIN_TEXT_LENGTH:
                    articles.append({
                        "url": url,
                        "title": title,
                        "authors": authors,
                        "published_at": publish_date,
                        "raw_text": text
                    })
            
            logger.info(f"Successfully fetched {len(articles)} articles from Guardian API")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch from Guardian API: {e}")
            return []
    
    def fetch_newsapi(self, country: str = "us", category: str = "general", max_items: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch articles from NewsAPI (requires free API key from newsapi.org).
        
        Categories: general, business, technology, health, science, sports, entertainment
        """
        api_key = API_KEYS.get('newsapi')
        if not api_key:
            logger.warning("NewsAPI key not found in config. Skipping NewsAPI sources.")
            logger.info("To use NewsAPI, add your free API key to ingestion_config.json")
            return []
        
        try:
            base_url = "https://newsapi.org/v2/top-headlines"
            params = {
                "country": country,
                "category": category,
                "pageSize": min(max_items, 100),  # API max is 100
                "apiKey": api_key
            }
            
            logger.info(f"Fetching from NewsAPI (country: {country}, category: {category})")
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"NewsAPI error: {data}")
                return []
            
            articles_data = data.get('articles', [])
            articles = []
            
            for item in articles_data[:max_items]:
                url = item.get('url', '')
                title = item.get('title', '')
                author = item.get('author', '')
                description = item.get('description', '')
                content = item.get('content', '')
                published_at = item.get('publishedAt', '')
                
                # Parse publish date
                publish_date = None
                if published_at:
                    try:
                        publish_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Use content if available, otherwise description
                text = content or description or ""
                
                # Clean up text (remove [+XXX chars] at end that NewsAPI sometimes adds)
                if text:
                    text = text.split('[+')[0].strip()
                
                authors = [author] if author else []
                
                if text and len(text) >= MIN_TEXT_LENGTH:
                    articles.append({
                        "url": url,
                        "title": title or "",
                        "authors": authors,
                        "published_at": publish_date,
                        "raw_text": text
                    })
            
            logger.info(f"Successfully fetched {len(articles)} articles from NewsAPI")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch from NewsAPI: {e}")
            return []
    
    def create_document(self, article_data: Dict[str, Any], source_id: str, source_type: str = "unknown") -> Dict[str, Any]:
        """Create a Document object matching the architecture schema."""
        url = article_data['url']
        doc_id = self.generate_document_id(url, source_id)
        
        # Convert authors list to string
        authors = article_data.get('authors', [])
        author_str = ', '.join(authors) if authors else ''
        
        # Create ingestion metadata
        ingestion_metadata = {
            "ingested_at": datetime.now().isoformat(),
            "ingestion_method": "automated",
            "source_type": source_type
        }
        
        document = {
            "id": doc_id,
            "source_id": source_id,
            "title": article_data.get('title', ''),
            "author": author_str,
            "published_at": article_data.get('published_at'),
            "raw_text": article_data['raw_text'],
            "url": url,
            "ingestion_metadata": json.dumps(ingestion_metadata)
        }
        
        return document
    
    def ingest_source(self, source_id: str, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ingest documents from a single source."""
        logger.info(f"Starting ingestion for source: {source_id}")
        
        source_type = source_config['type']
        articles = []
        
        # Fetch articles based on source type
        if source_type == "rss":
            url = source_config['url']
            max_items = source_config.get('max_items')
            use_rss_description = source_config.get('use_rss_description', False)
            articles = self.fetch_rss_feed(url, max_items, use_rss_description)
            
        elif source_type == "guardian":
            section = source_config.get('section', 'us-news')
            max_items = source_config.get('max_items', 20)
            articles = self.fetch_guardian_api(section, max_items)
            
        elif source_type == "newsapi":
            country = source_config.get('country', 'us')
            category = source_config.get('category', 'general')
            max_items = source_config.get('max_items', 20)
            articles = self.fetch_newsapi(country, category, max_items)
            
        else:
            logger.warning(f"Unknown source type: {source_type} for {source_id}")
            return []
        
        # Convert to documents and filter duplicates
        new_documents = []
        skipped_count = 0
        
        for article in articles:
            document = self.create_document(article, source_id, source_type)
            
            # Check for duplicates
            if document['id'] in self.existing_ids:
                skipped_count += 1
                continue
            
            new_documents.append(document)
            self.existing_ids.add(document['id'])
        
        logger.info(
            f"Source {source_id}: {len(new_documents)} new documents, "
            f"{skipped_count} duplicates skipped"
        )
        
        return new_documents
    
    def ingest_all_sources(self, sources: Optional[Dict[str, Dict[str, Any]]] = None) -> pd.DataFrame:
        """Ingest documents from all configured sources."""
        if sources is None:
            sources = SOURCES
        
        all_new_documents = []
        
        for source_id, source_config in sources.items():
            try:
                new_docs = self.ingest_source(source_id, source_config)
                all_new_documents.extend(new_docs)
            except Exception as e:
                logger.error(f"Error ingesting source {source_id}: {e}")
                continue
        
        # Combine with existing documents
        if all_new_documents:
            new_df = pd.DataFrame(all_new_documents)
            
            if not self.existing_documents.empty:
                combined_df = pd.concat([self.existing_documents, new_df], ignore_index=True)
            else:
                combined_df = new_df
            
            # Save to disk
            combined_df.to_parquet(self.documents_path, index=False)
            logger.info(f"Saved {len(combined_df)} total documents to {self.documents_path}")
            
            self.existing_documents = combined_df
            return combined_df
        else:
            logger.info("No new documents to add")
            return self.existing_documents if not self.existing_documents.empty else pd.DataFrame()
    
    def get_documents(self) -> pd.DataFrame:
        """Get all ingested documents."""
        if self.existing_documents is not None and not self.existing_documents.empty:
            return self.existing_documents
        else:
            self._load_existing_documents()
            return self.existing_documents if not self.existing_documents.empty else pd.DataFrame()


def main():
    """Main entry point for ingestion."""
    ingester = DocumentIngester()
    
    logger.info("Starting ingestion process...")
    df = ingester.ingest_all_sources()
    
    if not df.empty:
        logger.info(f"\nIngestion complete!")
        logger.info(f"Total documents: {len(df)}")
        logger.info(f"Sources: {df['source_id'].value_counts().to_dict()}")
        logger.info(f"Documents saved to: {ingester.documents_path}")
    else:
        logger.warning("No documents were ingested.")


if __name__ == "__main__":
    main()
