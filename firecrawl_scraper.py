"""
Firecrawl-based web scraper for job listings.

This module provides cloud-compatible web scraping using the Firecrawl API,
designed to replace Selenium for Streamlit Cloud deployment. It handles
JavaScript-rendered pages and returns clean, structured content for AI processing.

Dependencies:
    - firecrawl-py: Official Firecrawl Python SDK
    - utils: For OpenAI client initialization
    - streamlit: For secrets management

Usage:
    scraper = FirecrawlScraper()
    job_data = scraper.scrape_job_url("https://example.com/job-posting")
"""

import streamlit as st
import os
from datetime import datetime
from typing import Dict, Tuple, Optional
import json

# Import existing utilities
from utils import init_openai_client

try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    print("⚠️ Firecrawl not available. Install with: pip install firecrawl-py")


class FirecrawlScraper:
    """Cloud-compatible job scraper using Firecrawl API."""
    
    def __init__(self):
        """Initialize Firecrawl scraper with API key."""
        self.api_key = self._get_firecrawl_api_key()
        self.client = None
        
        if FIRECRAWL_AVAILABLE and self.api_key:
            try:
                self.client = FirecrawlApp(api_key=self.api_key)
            except Exception as e:
                st.error(f"Failed to initialize Firecrawl client: {str(e)}")
                self.client = None
    
    def _get_firecrawl_api_key(self) -> Optional[str]:
        """Get Firecrawl API key from multiple sources."""
        api_key = None
        
        # 1. Check Streamlit secrets
        try:
            if hasattr(st, 'secrets') and 'FIRECRAWL_API_KEY' in st.secrets:
                api_key = st.secrets.get('FIRECRAWL_API_KEY', '').strip()
                if api_key:
                    return api_key
        except Exception:
            pass
        
        # 2. Check environment variables
        api_key = os.getenv('FIRECRAWL_API_KEY', '').strip()
        if api_key:
            return api_key
        
        # 3. Check secrets.toml file directly (for local development)
        if os.path.exists('.streamlit/secrets.toml'):
            try:
                import toml
                with open('.streamlit/secrets.toml', 'r') as f:
                    secrets = toml.load(f)
                    api_key = secrets.get('default', {}).get('FIRECRAWL_API_KEY', '').strip()
                    if api_key:
                        return api_key
            except Exception:
                pass
        
        return None
    
    def is_available(self) -> bool:
        """Check if Firecrawl scraper is available and configured."""
        return FIRECRAWL_AVAILABLE and self.client is not None
    
    def scrape_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Scrape URL content using Firecrawl API.
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (content, error_message)
            Returns (content, None) on success, (None, error) on failure
        """
        if not self.is_available():
            return None, "Firecrawl scraper not available. Check API key configuration."
        
        try:
            # Use simple scraping parameters
            scrape_params = {
                'formats': ['markdown'],
                'onlyMainContent': True
            }
            
            # Perform the scrape
            result = self.client.scrape_url(url, scrape_params)
            
            # Extract content from Firecrawl response
            if result and hasattr(result, 'get'):
                content = result.get('markdown', '') or result.get('content', '') or result.get('data', {}).get('markdown', '')
            elif result and hasattr(result, 'markdown'):
                content = result.markdown
            elif result and hasattr(result, 'content'):
                content = result.content
            else:
                content = str(result) if result else ""
            
            if content and content.strip():
                return content, None
            else:
                return None, "No content extracted from the webpage"
                
        except Exception as e:
            return None, f"Error during Firecrawl scraping: {str(e)}"
    
    
    def scrape_job_url(self, url: str) -> Dict:
        """
        Simple job scraping: just scrape URL and return content.
        
        Args:
            url (str): Job listing URL
            
        Returns:
            Dict: Scraped content or error details
        """
        # Scrape the URL
        content, error = self.scrape_url(url)
        
        if error:
            return {
                "success": False,
                "error": error,
                "source": "firecrawl_scraping"
            }
        
        # Return the scraped content - let the UI handle AI processing
        return {
            "success": True,
            "data": {
                "scraped_content": content,
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_url": url
            },
            "source": "firecrawl_scraping"
        }


def scraper_openai_agent(text: str) -> str:
    """
    Extract job information from text using OpenAI API with proper token management.
    
    Args:
        text (str): Raw text content to analyze
        
    Returns:
        str: JSON string with extracted job information or error details
    """
    # Initialize OpenAI client
    client = init_openai_client()
    if client is None:
        return json.dumps({"error": "OpenAI client initialization failed. Please check your API key configuration."})
    
    # Define the system message (optimized for token efficiency)
    system_message = """
    You are an intelligent extraction agent. Extract detailed job information from the provided text:

    REQUIRED FIELDS:
    - Company Name
    - Job Title  
    - Job Description - Extract the entire job description text from the provided HTML, including all sections such as company introduction, context, role summary, responsibilities, requirements, benefits, equal opportunity statements, and closing remarks. Do not summarize, paraphrase, or omit any content. Return the full text exactly as it appears in a clean, continuous format, without HTML tags or other non-text elements. Each description will usually start with the company's mission and end with their hiring practices and ethics. CRITICAL: Include the COMPLETE job description with ALL details:
        * Company overview and role details
        * All responsibilities and requirements
        * Skills, qualifications, and experience needed
        * Compensation, benefits, and perks
        * Location and work arrangement details
        * Application instructions and deadlines
        * Any additional relevant information
        
        PRESERVE THE ENTIRE DESCRIPTION - DO NOT TRUNCATE OR SUMMARIZE!
        The description should be comprehensive and word-for-word from the source.
        
    - Job Location - Format: "City, Country" (e.g., "New York, USA")
    - Job Salary - Include full range if available (e.g., "$100,000 - $120,000 per year") or "Not Listed"

    Return ONLY a valid JSON dictionary with these exact keys: "Company Name", "Job Title", "Job Description", "Job Location", "Job Salary".
    """
    
    # Define the user message with the content
    user_message = f"""
    Please extract the job information from this text. Ensure the Job Description field contains the COMPLETE, UNTRUNCATED description with all details preserved:

    {text}
    """
    
    try:
        # Generate AI response using OpenAI API with proper token limits
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",  # Use 16k model for larger context
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=8000,  # Allow for longer responses
            temperature=0.1   # Low temperature for consistent, factual extraction
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return json.dumps({"error": f"OpenAI API call failed: {str(e)}"})


# Convenience functions for backward compatibility
def scrape_job_with_firecrawl(url: str) -> Dict:
    """
    Convenience function to scrape a job URL with Firecrawl.
    
    Args:
        url (str): Job listing URL
        
    Returns:
        Dict: Job information or error details
    """
    scraper = FirecrawlScraper()
    return scraper.scrape_job_url(url)


def is_firecrawl_available() -> bool:
    """Check if Firecrawl is available and configured."""
    scraper = FirecrawlScraper()
    return scraper.is_available()


# Test function for debugging
if __name__ == "__main__":
    # Test the scraper
    print("🔥 Firecrawl Scraper Test")
    print("=" * 40)
    
    scraper = FirecrawlScraper()
    
    # Debug API key availability
    api_key = scraper._get_firecrawl_api_key()
    if api_key:
        print(f"✅ API key found: {api_key[:8]}...{api_key[-4:]}")
    else:
        print("❌ No API key found")
        print("Check FIRECRAWL_API_KEY in:")
        print("  - Environment variables")
        print("  - .streamlit/secrets.toml")
        print("  - Streamlit secrets")
    
    # Check availability
    if not scraper.is_available():
        print("❌ Firecrawl not available")
        if not FIRECRAWL_AVAILABLE:
            print("  - firecrawl-py not installed")
        if not scraper.client:
            print("  - Client initialization failed")
    else:
        print("✅ Firecrawl scraper ready")
        
        # Test with a simple URL
        test_url = input("\nEnter a job URL to test (or press Enter to skip): ").strip()
        if test_url:
            print(f"🧪 Testing with: {test_url}")
            
            result = scraper.scrape_job_url(test_url)
            print("\n📄 Result:")
            print(json.dumps(result, indent=2))
            
            if result.get("success") and "scraped_content" in result.get("data", {}):
                content = result["data"]["scraped_content"]
                print(f"\n📊 Content preview ({len(content)} chars):")
                print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print("\n⏭️ Skipping URL test")