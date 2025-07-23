import streamlit as st
import openai

# Set page config to wide layout - must be first Streamlit command
st.set_page_config(layout="wide")

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
    """Save changes from the DataFrame back to the database."""
    if not st.session_state.get('authenticated', False):
        return False, "User not authenticated"
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        return False, "User ID not found"
    
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
        return True, "Changes saved successfully!"
    except Exception as e:
        return False, f"Error saving changes: {str(e)}"
    finally:
        conn.close()

# Page 1: AI Chat Bot
def show_ai_chatbot():
    st.title("AI Job Assistant")
    
    if client is None:
        st.error("OpenAI API key not configured. Please set up your API key to use the AI Chat Bot.")
        return
    
    # Authentication is now handled at the main app level
    user_id = st.session_state.get('user_id')
    
    # Load jobs for selection (filtered by user)
    conn = get_db_connection()
    jobs_df = pd.read_sql_query("SELECT id, company_name, job_title FROM jobs WHERE user_id = ?", conn, params=(user_id,))
    
    # Load resume from documents database (filtered by user)
    resume_df = pd.read_sql_query("SELECT * FROM documents WHERE document_type = 'Resume' AND user_id = ? ORDER BY upload_date DESC LIMIT 1", conn, params=(user_id,))
    resume_content = ""
    if not resume_df.empty:
        resume_path = resume_df['file_path'].iloc[0]
        try:
            file_extension = resume_path.split('.')[-1].lower()
            if file_extension == 'pdf':
                reader = PdfReader(resume_path)
                resume_content = "\n".join([page.extract_text() for page in reader.pages])
            elif file_extension == 'docx':
                doc = Document(resume_path)
                resume_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            elif file_extension == 'txt':
                with open(resume_path, 'r', encoding='utf-8') as file:
                    resume_content = file.read()
        except Exception as e:
            st.warning(f"Could not load resume content: {str(e)}")
    
    # Load career goals (filtered by user)
    goals_df = pd.read_sql_query("SELECT * FROM career_goals WHERE user_id = ? ORDER BY submission_date DESC LIMIT 1", conn, params=(user_id,))
    career_goals = goals_df['goals'].iloc[0] if not goals_df.empty else "No career goals have been set yet."
    
    # Load cover letter preferences
    try:
        with open('robs_cover_letter_preferences.md', 'r', encoding='utf-8') as file:
            cover_letter_preferences = file.read()
    except Exception as e:
        st.warning(f"Could not load cover letter preferences: {str(e)}")
        cover_letter_preferences = "No cover letter preferences found."
    
    conn.close()
    
    if not jobs_df.empty:
        job_selection = st.selectbox(
            "Select a job to chat about",
            jobs_df.apply(lambda x: f"{x['company_name']} - {x['job_title']}", axis=1)
        )
        
        if 'messages' not in st.session_state:
            st.session_state.messages = []
            
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        if prompt := st.chat_input("What would you like to know about this job?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # Get job details for context
            job_id = jobs_df[jobs_df.apply(lambda x: f"{x['company_name']} - {x['job_title']}", axis=1) == job_selection]['id'].iloc[0]
            conn = get_db_connection()
            job_details = pd.read_sql_query("SELECT * FROM jobs WHERE id = ? AND user_id = ?", conn, params=(job_id, user_id))
            conn.close()
            
            # Prepare system message with job, resume, career goals, and cover letter preferences
            with open('system_instructions.md', 'r', encoding='utf-8') as file:
                system_instructions = file.read()
            
            job_info = f"You are a bubbly helpful hiring assistant discussing the job at {job_details['company_name'].iloc[0]} for the position of {job_details['job_title'].iloc[0]}."
            job_desc = f"Job Description:\n{job_details['job_description'].iloc[0]}"
            notes = f"Notes:\n{job_details['notes'].iloc[0]}"
            resume_info = f"Resume Content:\n{resume_content}" if resume_content else "No resume has been uploaded yet."
            career_goals_info = f"Career Goals:\n{career_goals}"
            
            # Add cover letter preferences if the prompt is about writing a cover letter
            cover_letter_context = ""
            if "cover letter" in prompt.lower():
                cover_letter_context = f"\n\nCover Letter Preferences:\n{cover_letter_preferences}"
                instruction = "Please write a cover letter following the provided preferences, considering the job requirements, resume content, and career goals. The cover letter should reflect the user's voice and style preferences."
            else:
                instruction = "Please provide insights and advice based on the job requirements, resume content, and career goals. Consider how this job aligns with the user's career aspirations."
            
            system_message = f"{system_instructions}\n\n{job_info}\n\n{job_desc}\n\n{resume_info}\n\n{notes}\n\n{career_goals_info}\n\n{cover_letter_context}\n\n{instruction}"
            
            # Generate AI response using OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
            )
            
            assistant_response = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            with st.chat_message("assistant"):
                st.markdown(assistant_response)
    else:
        st.info("No jobs available. Add some jobs in the Job Portal first!")

# Page 2: Dashboard
def show_dashboard():
    """Show the dashboard with job application statistics."""
    st.title("Dashboard")
    
    # Authentication is now handled at the main app level
    user_id = st.session_state.get('user_id')
    
    # Get job data (filtered by user)
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
    st.title("Welcome to Jobs Organiser")
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
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            logo_path = "assets/RLE - Logo 2.0 White.png"
            if os.path.exists(logo_path):
                st.image(logo_path, width=200, use_column_width="auto")
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