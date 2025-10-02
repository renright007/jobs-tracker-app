from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import read_secrets, init_openai_client
import time
from datetime import datetime
from utils import get_db_connection
from typing import Dict, Tuple

# Token counting for API limits
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

def open_webpage(url):
    """
    Open a webpage using Selenium WebDriver.
    
    Args:
        url (str): The URL of the webpage to open
        
    Returns:
        webdriver.Chrome: The Chrome WebDriver instance
    """
    # Set up Chrome options
    options = Options()
    options.add_argument("--start-fullscreen")  # Launch in full screen
    #options.add_argument('--headless')  # Run in headless mode
    
    # Create and configure the driver using Selenium Manager
    driver = webdriver.Chrome(options=options)
    
    try:
        # Navigate to the URL
        driver.get(url)
        print(f"Successfully opened: {url}")
        print(f"Page title: {driver.title}")
        
        # Wait for the page to load completely
        WebDriverWait(driver, 10).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete'
        )
        
        # Wait for at least one div element to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "div"))
        )
        
        # Additional wait for dynamic content
        driver.implicitly_wait(5)
        
        return driver
    except Exception as e:
        print(f"Error opening webpage: {str(e)}")
        driver.quit()
        return None

def get_page_html(driver):
    """
    Get the raw HTML of the current webpage.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance
        
    Returns:
        str: The raw HTML of the webpage
    """
    try:
        html = driver.page_source
        return html
    except Exception as e:
        print(f"Error getting page HTML: {str(e)}")
        return None

def get_div_classes(driver):
    """
    Get all unique div class names from the webpage.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance
        
    Returns:
        list: List of unique div class names
    """
    try:
        # Find all div elements
        divs = driver.find_elements(By.TAG_NAME, "div")
        
        # Extract unique class names
        class_names = set()
        for div in divs:
            class_name = div.get_attribute("class")
            if class_name:  # Only add if class exists
                class_names.add(class_name)
        
        return sorted(list(class_names))
    except Exception as e:
        print(f"Error getting div classes: {str(e)}")
        return None

def get_div_text(driver):
    """
    Get the text content of all div elements on the webpage.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance

    Returns:
        list: List of text content from div elements
    """
    try:
        # Find all div elements
        divs = driver.find_elements(By.TAG_NAME, "div")
        
        # Extract text content from each div
        text_content = [div.text for div in divs]
        
        return text_content
    except Exception as e:
        print(f"Error getting div text: {str(e)}")
        return None

def get_div_elements_with_text(driver):
    """
    Create a dictionary mapping div elements to their text content and class names.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance
        
    Returns:
        dict: Dictionary with div elements as keys and their text content and class names as values
    """
    try:
        # Wait for initial page load
        driver.implicitly_wait(3)
        
        # Quick scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Small wait for content
        time.sleep(1)
        
        # Find all div elements
        divs = driver.find_elements(By.TAG_NAME, "div")
        
        # Create dictionary with div elements and their properties
        div_dict = {}
        seen_texts = set()  # Keep track of unique text content
        longest_text = {"text": "", "class": "", "element": None}
        
        for i, div in enumerate(divs):
            text = div.text.strip()
            class_name = div.get_attribute("class")
            
            # Skip if text is blank or class name is blank
            if not text or not class_name:
                continue
                
            # Track the longest text
            if len(text) > len(longest_text["text"]):
                longest_text = {
                    "text": text,
                    "class": class_name,
                    "element": div
                }
            
            # Skip if text is too short (likely navigation/menu items)
            if len(text) < 10:
                continue
                
            # Skip if we've seen this text before
            if text in seen_texts:
                continue
                
            # Add to dictionary
            div_dict[f"div_{i}"] = {
                "class": class_name,
                "element": div,
                "text": text
            }
            seen_texts.add(text)  # Mark this text as seen
        
        # Add the longest text as the first entry
        if longest_text["text"]:
            div_dict["longest_text"] = longest_text
        
        return div_dict
    except Exception as e:
        print(f"Error getting div elements with text: {str(e)}")
        return None

def remove_duplicate_chunks(text, min_chunk_size=50):
    """
    Remove duplicate chunks of text from a string.
    
    Args:
        text (str): The input text
        min_chunk_size (int): Minimum size of text chunk to consider for duplicates
        
    Returns:
        str: Text with duplicates removed
    """
    # Split text into chunks
    chunks = []
    current_chunk = []
    current_size = 0
    
    for line in text.split('\n'):
        if current_size + len(line) > min_chunk_size:
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_size = len(line)
        else:
            current_chunk.append(line)
            current_size += len(line)
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    # Remove duplicates while preserving order
    seen_chunks = set()
    unique_chunks = []
    
    for chunk in chunks:
        # Normalize chunk for comparison (remove extra whitespace)
        normalized_chunk = ' '.join(chunk.split())
        if normalized_chunk not in seen_chunks:
            seen_chunks.add(normalized_chunk)
            unique_chunks.append(chunk)
    
    return '\n'.join(unique_chunks)

def format_for_ai_parsing(div_dict):
    """
    Format the div elements' text and class names for AI parsing.
    
    Args:
        div_dict (dict): Dictionary containing div elements and their properties
        
    Returns:
        str: Formatted string with text and class names separated by newlines
    """
    if not div_dict:
        return ""
        
    # Get all text and remove duplicates while preserving order
    seen_texts = set()
    formatted_text = []
    
    for div_id, div_info in div_dict.items():
        text = div_info['text'].strip()
        if text and text not in seen_texts:
            formatted_text.append(text)
            seen_texts.add(text)
    
    return "\n".join(formatted_text)

def count_tokens(text: str, model: str = "gpt-3.5-turbo-16k") -> int:
    """Count tokens in text for the specified model."""
    if not TIKTOKEN_AVAILABLE:
        # Rough estimation: ~4 characters per token
        return len(text) // 4
    
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback estimation
        return len(text) // 4


def validate_and_prepare_text(text: str, max_tokens: int = 12000) -> Tuple[str, Dict]:
    """
    Validate text length and prepare it for API call.
    
    Args:
        text (str): Input text to validate
        max_tokens (int): Maximum tokens allowed for input
        
    Returns:
        Tuple[str, Dict]: (processed_text, metadata)
    """
    token_count = count_tokens(text)
    
    metadata = {
        "original_length": len(text),
        "token_count": token_count,
        "truncated": False,
        "chunks": 1
    }
    
    if token_count <= max_tokens:
        return text, metadata
    
    # If text is too long, intelligently truncate
    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo-16k")
            tokens = encoding.encode(text)
            truncated_tokens = tokens[:max_tokens]
            processed_text = encoding.decode(truncated_tokens)
            metadata["truncated"] = True
            metadata["token_count"] = len(truncated_tokens)
            return processed_text, metadata
        except Exception:
            pass
    
    # Fallback: character-based truncation
    estimated_chars = max_tokens * 4
    processed_text = text[:estimated_chars]
    metadata["truncated"] = True
    metadata["token_count"] = count_tokens(processed_text)
    
    return processed_text, metadata

def scraper_openai_agent(text):
    """
    Extract job information from text using OpenAI API with proper token management.
    """
    # Initialize OpenAI client
    client = init_openai_client()
    if client is None:
        print("OpenAI client initialization failed. The AI Chat Bot feature will be disabled.")
        return None

    # Validate and prepare text
    processed_text, metadata = validate_and_prepare_text(text, max_tokens=12000)
    
    # Log token information
    print(f"Input text: {metadata['original_length']} chars, {metadata['token_count']} tokens")
    if metadata['truncated']:
        print("⚠️ Warning: Input text was truncated due to length limits")

    # Define the system message (optimized for token efficiency)
    system_message = """
    You are an intelligent extraction agent. Extract detailed job information from the provided text:

    REQUIRED FIELDS:
    - Company Name
    - Job Title  
    - Job Description - CRITICAL: Include the COMPLETE job description with ALL details:
        * Company overview and role details
        * All responsibilities and requirements
        * Skills, qualifications, and experience needed
        * Compensation, benefits, and perks
        * Location and work arrangement details
        * Application instructions and deadlines
        * Any additional relevant information
        
        PRESERVE THE ENTIRE DESCRIPTION - DO NOT TRUNCATE OR SUMMARIZE!
        
    - Job Location - Format: "City, Country" (e.g., "New York, USA")
    - Job Salary - Include full range if available (e.g., "$100,000 - $120,000 per year") or "Not Listed"

    Return ONLY a valid JSON dictionary with these exact keys: "Company Name", "Job Title", "Job Description", "Job Location", "Job Salary".
    """

    # Define the user message with the content
    truncation_note = " [NOTE: Input text was truncated due to length limits]" if metadata["truncated"] else ""
    user_message = f"""
    Please extract the job information from this text. Ensure the Job Description field contains the COMPLETE, UNTRUNCATED description:

    {processed_text}{truncation_note}
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
        print(f"Error in OpenAI API call: {str(e)}")
        return f"Error: {str(e)}"

def get_longest_text_content(driver):
    """
    Get the div element with the longest text content, which is likely to be the job description.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance
        
    Returns:
        dict: Dictionary containing the longest text content and its class name
    """
    try:
        # Wait for initial page load
        driver.implicitly_wait(3)
        
        # Quick scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Small wait for content
        time.sleep(1)
        
        # Find all div elements
        divs = driver.find_elements(By.TAG_NAME, "div")
        
        # Track the longest text
        longest_text = {"text": "", "class": "", "element": None}
        
        for div in divs:
            text = div.text.strip()
            class_name = div.get_attribute("class")
            
            # Skip if text is blank or class name is blank
            if not text or not class_name:
                continue
                
            # Track the longest text
            if len(text) > len(longest_text["text"]):
                longest_text = {
                    "text": text,
                    "class": class_name,
                    "element": div
                }
        
        return longest_text
    except Exception as e:
        print(f"Error getting longest text content: {str(e)}")
        return None
    
def save_job_to_database(job_details):
    """Save job details to the database."""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO jobs 
                    (company_name, job_title, job_description, application_url,
                     status, sentiment, notes, date_added)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                 (job_details.get('company_name', ''),
                  job_details.get('job_title', ''),
                  job_details.get('job_description', ''),
                  job_details.get('job_url', ''),
                  job_details.get('application_status', 'Not Applied'),
                  job_details.get('sentiment', 'Neutral'),
                  job_details.get('notes', ''),
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True, "Job details saved successfully!"
    except Exception as e:
        return False, f"Error saving job to database: {str(e)}"
    finally:
        conn.close()

# Test the functions
if __name__ == "__main__":
    # Test with Google
    driver = open_webpage("https://www.google.com")
    if driver:
        # Get div elements with text
        div_elements = get_div_elements_with_text(driver)
        if div_elements:
            # Format for AI parsing
            ai_input = format_for_ai_parsing(div_elements)
            print("\nFormatted text for AI parsing:")
            print(ai_input)
        
        driver.quit() 