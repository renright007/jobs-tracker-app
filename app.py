import streamlit as st
import openai

# Set page config to wide layout - must be first Streamlit command
st.set_page_config(
    layout="wide",
    page_title="Jobs Organiser",
    page_icon="./assets/job_hopper_logo.png",
    initial_sidebar_state="expanded"
)

# Now import other modules
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
from utils import (
    init_openai_client,
    get_db_connection,
    init_db,
    ensure_directories,
    get_custom_css,
    get_menu_style
)
from streamlit_echarts import st_echarts
from dashboard_utils import prepare_dashboard_data, show_metrics
from user_portal import show_user_portal
from jobs_portal import show_jobs_portal
from ai_chatbot_portal_openai import show_openai_chatbot as show_ai_chatbot
from login import show_login_page, init_auth_db


# Load environment variables
load_dotenv()

# Initialize authentication database
init_auth_db()

# Initialize OpenAI client
client = init_openai_client()
if client is None:
    st.error("OpenAI client initialization failed. The AI Chat Bot feature will be disabled.")

# Ensure required directories exist
ensure_directories()

# Initialize database
init_db()

# Initialize session state
if 'jobs_data' not in st.session_state:
    st.session_state.jobs_data = pd.DataFrame(columns=[
        'company_name', 'job_title', 'job_description', 'application_url',
        'status', 'sentiment', 'notes', 'date_added'
    ])

if 'documents' not in st.session_state:
    st.session_state.documents = pd.DataFrame(columns=[
        'document_name', 'document_type', 'upload_date', 'file_path'
    ])

if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        'selected_resume': None,
        'career_goals': "",
        'created_date': None,
        'last_updated_date': None
    }

if 'career_goals' not in st.session_state:
    st.session_state.career_goals = pd.DataFrame(columns=[
        'goals', 'submission_date'
    ])

def save_jobs_to_database(jobs_df):
    """Save changes from the DataFrame back to the database using unified database system."""
    from database_utils import use_supabase
    
    if not st.session_state.get('authenticated', False):
        return False, "User not authenticated"
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        return False, "User ID not found"
    
    try:
        if use_supabase():
            from supabase_utils import get_supabase_client
            supabase = get_supabase_client()
            
            # For each row in the DataFrame
            for _, row in jobs_df.iterrows():
                job_data = {
                    'company_name': row['company_name'],
                    'job_title': row['job_title'],
                    'job_description': row['job_description'],
                    'application_url': row['application_url'],
                    'status': row['status'],
                    'sentiment': row['sentiment'],
                    'notes': row['notes']
                }
                
                # Check if this is an existing row (has an id)
                if 'id' in row and pd.notna(row['id']):
                    # Update existing row (only if it belongs to current user)
                    supabase.table('jobs').update(job_data).eq('id', row['id']).eq('user_id', user_id).execute()
                else:
                    # Insert new row with user_id
                    job_data['user_id'] = user_id
                    job_data['date_added'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    supabase.table('jobs').insert(job_data).execute()
        else:
            conn = get_db_connection()
            try:
                # First, get the current data to compare (filtered by user)
                current_data = pd.read_sql_query("SELECT * FROM jobs WHERE user_id = ?", conn, params=(user_id,))
                
                # For each row in the DataFrame
                for _, row in jobs_df.iterrows():
                    # Check if this is an existing row (has an id)
                    if 'id' in row and pd.notna(row['id']):
                        # Update existing row (only if it belongs to current user)
                        conn.execute('''UPDATE jobs 
                                      SET company_name = ?, 
                                          job_title = ?, 
                                          job_description = ?, 
                                          application_url = ?, 
                                          status = ?, 
                                          sentiment = ?, 
                                          notes = ?
                                      WHERE id = ? AND user_id = ?''',
                                   (row['company_name'], row['job_title'], 
                                    row['job_description'], row['application_url'],
                                    row['status'], row['sentiment'], row['notes'],
                                    row['id'], user_id))
                    else:
                        # Insert new row with user_id
                        conn.execute('''INSERT INTO jobs 
                                      (company_name, job_title, job_description, 
                                       application_url, status, sentiment, notes, date_added, user_id)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                   (row['company_name'], row['job_title'], 
                                    row['job_description'], row['application_url'],
                                    row['status'], row['sentiment'], row['notes'],
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
                
                conn.commit()
            finally:
                conn.close()
        
        return True, "Changes saved successfully!"
    except Exception as e:
        return False, f"Error saving changes: {str(e)}"


# Page 2: Dashboard
def show_dashboard():
    """Show the dashboard with job application statistics using unified database system."""
    from database_utils import use_supabase
    
    st.title("Dashboard")
    
    # Authentication is now handled at the main app level
    user_id = st.session_state.get('user_id')
    
    # Get job data (filtered by user)
    if use_supabase():
        from supabase_utils import get_supabase_client
        supabase = get_supabase_client()
        result = supabase.table('jobs').select('*').eq('user_id', user_id).execute()
        jobs_df = pd.DataFrame(result.data) if result.data else pd.DataFrame()
    else:
        conn = get_db_connection()
        jobs_df = pd.read_sql_query("SELECT * FROM jobs WHERE user_id = ?", conn, params=(user_id,))
        conn.close()
    
    if jobs_df.empty:
        st.warning("No job applications found. Add some jobs to see statistics.")
        return
    
    # Prepare dashboard data
    dashboard_data = prepare_dashboard_data(jobs_df)
    if not dashboard_data:
        return
    
    # Display key metrics at the top
    show_metrics(dashboard_data["metrics"])
    
    # Create two columns for the charts
    col1, col2 = st.columns(2)
    
    with st.container():
        with col1:
            st_echarts(options=dashboard_data["status_chart"], height="400px")
    
    with col2:
        st_echarts(options=dashboard_data["sentiment_chart"], height="400px")
    
    # Applications Over Time Line Chart
    st_echarts(options=dashboard_data["timeline_chart"], height="400px")
    
    # Job Titles Bar Chart
    st_echarts(options=dashboard_data["job_titles_chart"], height="400px")
    
    # Company Distribution Bar Chart
    st_echarts(options=dashboard_data["company_chart"], height="400px")

# Main app
def main():
    # Add custom CSS
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # Initialize session state for authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    # Always show the main app layout (regardless of authentication)
    show_main_app()

def show_login_prompt():
    """Show login prompt for unauthenticated users."""
    st.info("👋 Please log in to access this feature")
    
    # Import the login functionality
    from login import show_login_page
    
    # Show the login interface
    show_login_page()

def show_main_app():
    """Show the main application layout for all users."""
    # Create logo section first
    create_logo_section()
    
    # Define menu options (same for everyone)
    menu_options = ["User Portal", "Jobs Portal", "AI Chat Bot", "Dashboard"]
    
    # Create menu with icons
    with st.sidebar:
        selected_page = option_menu(
            menu_title=None,
            options=menu_options,
            icons=['person', 'database', 'robot', 'bar-chart'],
            default_index=0,
            styles=get_menu_style()
        )
    
    # Create authentication section after menu
    create_auth_section()
    
    # Handle menu selection based on authentication status
    handle_menu_selection(selected_page)

def create_logo_section():
    """Create the logo section at the top of the sidebar."""
    with st.sidebar:
        # Add logo
        logo_path = "assets/job_hopper_logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            st.error(f"Logo file not found at {logo_path}")
        st.markdown("---")  # Add a horizontal line after the logo

def create_auth_section():
    """Create the authentication section at the bottom of the sidebar."""
    with st.sidebar:
        st.markdown("---")  # Add separator before auth section
        
        # Show authentication status
        if st.session_state.get('authenticated', False):
            # Show current user and logout button for authenticated users
            st.markdown(f"**Logged in as:** {st.session_state.username}")
            if st.button("Logout", key="logout_btn"):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.user_id = None
                st.rerun()
        else:
            # Show login status for unauthenticated users
            st.markdown("**Status:** Not logged in")
            st.markdown("🔒 Click menu items to login")

def handle_menu_selection(selected_page):
    """Handle menu selection based on authentication status."""
    # Check if user is authenticated
    if not st.session_state.get('authenticated', False):
        # User is not authenticated - show login prompt
        show_login_prompt()
        return
    
    # User is authenticated - show the actual functionality
    menu_functions = {
        "User Portal": show_user_portal,
        "Jobs Portal": show_jobs_portal,
        "AI Chat Bot": show_ai_chatbot,
        "Dashboard": show_dashboard
    }
    
    # Call the appropriate function
    if selected_page in menu_functions:
        menu_functions[selected_page]()

if __name__ == "__main__":
    main() 