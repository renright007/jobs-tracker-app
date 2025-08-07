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
            # Configure scraping options
            scrape_params = {
                'formats': ['markdown', 'html'],
                'onlyMainContent': True,  # Extract main content only
                'includeHtml': True,      # Include HTML for better parsing
                'waitFor': 2000,          # Wait for dynamic content (2 seconds)
            }
            
            # Perform the scrape
            result = self.client.scrape_url(url, scrape_params)
            
            if result and 'success' in result and result['success']:
                # Extract content from result
                content = ""
                
                # Prefer markdown content for cleaner text
                if 'markdown' in result.get('data', {}):
                    content = result['data']['markdown']
                elif 'content' in result.get('data', {}):
                    content = result['data']['content']
                elif 'html' in result.get('data', {}):
                    content = result['data']['html']
                else:
                    return None, "No content found in Firecrawl response"
                
                # Clean and validate content
                content = content.strip()
                if len(content) < 100:  # Very short content might indicate an error
                    return None, f"Content too short ({len(content)} chars). May indicate scraping failure."
                
                return content, None
                
            else:
                error_msg = result.get('error', 'Unknown error from Firecrawl API')
                return None, f"Firecrawl API error: {error_msg}"
                
        except Exception as e:
            return None, f"Error during Firecrawl scraping: {str(e)}"
    
    def extract_job_info_with_ai(self, content: str) -> str:
        """
        Extract job information using OpenAI agent (reuses existing logic).
        
        Args:
            content (str): Raw content from Firecrawl
            
        Returns:
            str: JSON string with extracted job information
        """
        # Initialize OpenAI client
        client = init_openai_client()
        if client is None:
            return json.dumps({"error": "OpenAI client initialization failed"})

        # Define the extraction prompt (same as selenium_scraper.py)
        system_message = f"""
        You are an intelligent extraction agent. Given a snippet of **text**, scrape detailed information about the relevant below information:

            - Company Name
            - Job Title
            - Job Description - 
                Usually this will be the entirity of the text chunk. Ideally you want to cut the headers and footers.
                MUST INCLUDE ALL DESCRIPTION TEXT RELATED TO THE JOB DESCRIPTION.
                DO NOT MISS ANYTHING WITHIN THE LARGE DESCRIPTION TEXT, USUALLY ENDING WITH A LINK TO APPLY or BENEFIT INFORMATION. 
                The job description should be word for word and include any large chunks of text the company, role, tasks, skills, pay, external or additional information, location details or anything else of interest to a potential candidate. 
                DO NOT MISS ANYTHING!!!!!!!
            - Job Location - Include city and country for example: "New York, USA"
            - Job Salary - Include salary range for example: "$100,000 - $120,000 per year"

        Your task is to analyze the text and return the information that best applies. Do not return duplicate information.

            Text: "{content}"  

        Return only the following information in a dictionary format: Company Name, Job Title, Job Description, Job Location, Job Salary.
        """

        try:
            # Generate AI response using OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": "Please help me extract the information from the text the unstructured text provided."}
                ]
            )

            return response.choices[0].message.content
            
        except Exception as e:
            return json.dumps({"error": f"AI extraction failed: {str(e)}"})
    
    def scrape_job_url(self, url: str) -> Dict:
        """
        Complete job scraping pipeline: scrape URL + extract job info.
        
        Args:
            url (str): Job listing URL
            
        Returns:
            Dict: Job information or error details
        """
        # Step 1: Scrape the URL
        content, error = self.scrape_url(url)
        
        if error:
            return {
                "success": False,
                "error": error,
                "source": "firecrawl_scraping"
            }
        
        # Step 2: Extract job information with AI
        ai_result = self.extract_job_info_with_ai(content)
        
        try:
            # Try to parse AI result as JSON
            job_info = json.loads(ai_result) if isinstance(ai_result, str) else ai_result
            
            return {
                "success": True,
                "data": {
                    "company_name": job_info.get("Company Name", ""),
                    "job_title": job_info.get("Job Title", ""),
                    "job_description": job_info.get("Job Description", ""),
                    "job_location": job_info.get("Job Location", ""),
                    "job_salary": job_info.get("Job Salary", ""),
                    "scraped_content": content[:1000] + "..." if len(content) > 1000 else content,  # Preview
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source_url": url
                },
                "source": "firecrawl_ai_extraction"
            }
            
        except json.JSONDecodeError:
            # AI didn't return valid JSON, return raw result
            return {
                "success": True,
                "data": {
                    "raw_ai_response": ai_result,
                    "scraped_content": content[:1000] + "..." if len(content) > 1000 else content,
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source_url": url
                },
                "source": "firecrawl_raw_extraction"
            }


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


# Test function
if __name__ == "__main__":
    # Test the scraper
    print("🔥 Firecrawl Scraper Test")
    print("=" * 40)
    
    scraper = FirecrawlScraper()
    
    if not scraper.is_available():
        print("❌ Firecrawl not available. Check API key configuration.")
    else:
        print("✅ Firecrawl scraper initialized successfully")
        
        # Test with a sample URL (replace with actual job URL)
        test_url = "https://jobs.example.com/sample-job"
        print(f"🧪 Testing with: {test_url}")
        
        result = scraper.scrape_job_url(test_url)
        print("\n📄 Result:")
        print(json.dumps(result, indent=2))