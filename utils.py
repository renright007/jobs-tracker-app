import sqlite3
from pathlib import Path
import streamlit as st
import openai
from datetime import datetime
import os

# LangChain imports (disabled for OpenAI implementation)
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
    """Get database connection - DEPRECATED: Use database_utils functions instead."""
    # This function is deprecated and maintained only for backwards compatibility
    # New code should use database_utils.py functions which support both SQLite and Supabase
    from database_utils import use_supabase
    
    if use_supabase():
        # For Supabase, this function shouldn't be used - use database_utils functions
        import streamlit as st
        st.warning("⚠️ Using deprecated get_db_connection() with Supabase. Please use database_utils functions.")
        return None
    else:
        # For SQLite compatibility
        return sqlite3.connect('data/jobs.db')

def init_db():
    """Initialize the database with the required tables - DEPRECATED: Use database_utils.init_db() instead."""
    # This function is deprecated - use database_utils.init_db() for unified database support
    from database_utils import init_db as db_utils_init_db
    return db_utils_init_db()

def update_db_schema(query=None):
    """Update the database schema with new fields - DEPRECATED."""
    # This function is deprecated and may not work with Supabase
    from database_utils import use_supabase
    if use_supabase():
        st.warning("⚠️ update_db_schema() is deprecated and doesn't support Supabase. Use Supabase dashboard for schema changes.")
        return
    
    conn = get_db_connection()
    if not conn:  # Supabase case
        return
        
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
    """Save uploaded file and add to database - DEPRECATED: Use user_portal.py functions instead."""
    # This function is deprecated - use database_utils.add_document() for unified database support
    from database_utils import add_document, use_supabase
    
    # Generate file path
    file_path = f"data/documents/{document_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    
    # Save file (Note: This won't work in cloud environments - needs cloud storage)
    if use_supabase():
        st.warning("⚠️ File uploads don't work with cloud storage. This function is deprecated for Supabase.")
        return None
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Add to database using unified function
    document_data = {
        'document_name': document_name,
        'document_type': document_type,
        'file_path': file_path
    }
    success, message = add_document(user_id, document_data)
    
    if not success:
        st.error(f"Error adding document to database: {message}")
        return None
    
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