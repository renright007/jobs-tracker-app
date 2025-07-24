import sqlite3
from pathlib import Path
import streamlit as st
import openai
from datetime import datetime
import os

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

def read_secrets():
    """Read secrets from Streamlit secrets or environment variables."""
    try:
        # Try Streamlit secrets first (for local development and Streamlit Cloud)
        if hasattr(st, 'secrets') and st.secrets:
            return {
                'OPENAI_API_KEY': st.secrets.get('OPENAI_API_KEY', ''),
                'GOOGLE_API_KEY': st.secrets.get('GOOGLE_API_KEY', ''),
                'LANGSMITH_API_KEY': st.secrets.get('LANGSMITH_API_KEY', ''),
                'LANGSMITH_TRACING': st.secrets.get('LANGSMITH_TRACING', ''),
                'LANGSMITH_PROJECT': st.secrets.get('LANGSMITH_PROJECT', ''),
                'SUPABASE_URL': st.secrets.get('SUPABASE_URL', ''),
                'SUPABASE_API_KEY': st.secrets.get('SUPABASE_API_KEY', ''),
                'SUPABASE_DB': st.secrets.get('SUPABASE_DB', ''),
                'SUPABASE_DB_PW': st.secrets.get('SUPABASE_DB_PW', '')
            }
    except Exception:
        pass
    
    # Fallback to environment variables
    return {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
        'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', ''),
        'LANGSMITH_API_KEY': os.getenv('LANGSMITH_API_KEY', ''),
        'LANGSMITH_TRACING': os.getenv('LANGSMITH_TRACING', ''),
        'LANGSMITH_PROJECT': os.getenv('LANGSMITH_PROJECT', ''),
        'SUPABASE_URL': os.getenv('SUPABASE_URL', ''),
        'SUPABASE_API_KEY': os.getenv('SUPABASE_API_KEY', ''),
        'SUPABASE_DB': os.getenv('SUPABASE_DB', ''),
        'SUPABASE_DB_PW': os.getenv('SUPABASE_DB_PW', '')
    }

def init_openai_client():
    """Initialize OpenAI client with API key from secrets or environment variable."""
    secrets = read_secrets()
    api_key = secrets.get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        st.error("OpenAI API key not found. Please set it in secrets.json or as an environment variable.")
        return None
    
    try:
        return openai.OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing OpenAI client: {str(e)}")
        return None

def init_langchain_llm():
    """Initialize LangChain ChatOpenAI instance."""
    if not LANGCHAIN_AVAILABLE:
        st.error("LangChain not available. Please install required packages.")
        return None
    
    secrets = read_secrets()
    api_key = secrets.get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        st.error("OpenAI API key not found for LangChain initialization.")
        return None
    
    try:
        return ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            openai_api_key=api_key
        )
    except Exception as e:
        st.error(f"Error initializing LangChain LLM: {str(e)}")
        return None

def check_langchain_status():
    """Check if LangChain is properly configured."""
    return {
        'available': LANGCHAIN_AVAILABLE,
        'api_key_configured': bool(read_secrets().get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY'))
    }

def get_db_connection():
    """Get SQLite database connection."""
    return sqlite3.connect('data/jobs.db')

def init_db():
    """Initialize the SQLite database with the required tables."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create jobs table
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  company_name TEXT,
                  job_title TEXT,
                  job_description TEXT,
                  application_url TEXT,
                  status TEXT,
                  sentiment TEXT,
                  notes TEXT,
                  date_added TEXT,
                  location TEXT,
                  salary TEXT,
                  applied_date TEXT)''')
    
    # Create documents table
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  document_name TEXT,
                  document_type TEXT,
                  upload_date TEXT,
                  file_path TEXT)''')
    
    # Create user_profile table
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  selected_resume TEXT,
                  created_date TEXT,
                  last_updated_date TEXT)''')
    
    # Create career_goals table
    c.execute('''CREATE TABLE IF NOT EXISTS career_goals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  goals TEXT,
                  submission_date TEXT)''')
    
    conn.commit()
    conn.close()

def update_db_schema(query=None):
    """Update the database schema with new fields.
    
    Args:
        query (str, optional): SQL query to execute. If None, will add default columns.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute(query)
        conn.commit()
    except Exception as e:
        st.error(f"Error executing schema update: {str(e)}")
        conn.rollback()

    conn.close()

# Call update_db_schema when initializing
init_db()

def ensure_directories():
    """Ensure required directories exist."""
    Path("data").mkdir(exist_ok=True)
    Path("data/documents").mkdir(exist_ok=True)
    Path("assets").mkdir(exist_ok=True)

def save_uploaded_file(uploaded_file, document_name, document_type, user_id):
    """Save uploaded file and add to database."""
    # Generate file path
    file_path = f"data/documents/{document_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Add to database with user_id
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO documents 
                (document_name, document_type, upload_date, file_path, user_id)
                VALUES (?, ?, ?, ?, ?)''',
             (document_name, document_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file_path, user_id))
    conn.commit()
    conn.close()
    
    return file_path

def get_custom_css():
    """Return custom CSS for the application."""
    return """
        <style>
        [data-testid="stSidebar"] {
            background-color: #0097b2;
        }
        [data-testid="stSidebar"] .css-1d391kg {
            border-radius: 10px !important;
        }
        hr {
            border-color: white !important;
        }
        .main .block-container {
            max-width: 100%;
            padding-top: 2rem;
            padding-right: 2rem;
            padding-left: 2rem;
            padding-bottom: 2rem;
        }
        .stApp {
            max-width: 100%;
        }
        .stApp > header {
            background-color: transparent;
        }
        /* Center the logo in the sidebar */
        [data-testid="stSidebar"] .stImage {
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
        }
        </style>
    """

def get_menu_style():
    """Return style configuration for the option menu."""
    return {
        "container": {"padding": "5!important", "background-color": "#fafafa"},
        "icon": {"color": "#0097b2", "font-size": "25px"},
        "nav-link": {
            "font-size": "16px",
            "text-align": "left",
            "margin": "0px",
            "--hover-color": "#eee"
        },
        "nav-link-selected": {"background-color": "#0097b2"},
    }