import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_db_connection, init_db, ensure_directories
from streamlit_shadcn_ui import tabs
# from selenium_scraper import open_webpage, get_longest_text_content, scraper_openai_agent, save_job_to_database
# ⚠️  Selenium temporarily disabled for cloud deployment

import json
import time

# Initialize database and ensure directories exist
init_db()
ensure_directories()

# Initialize session state
if 'jobs_data' not in st.session_state:
    st.session_state.jobs_data = pd.DataFrame(columns=[
        'company_name', 'job_title', 'job_description', 'application_url',
        'status', 'sentiment', 'notes', 'date_added', 'location', 'salary', 'applied_date'
    ])

# Add custom CSS for the container
st.markdown("""
    <style>
    .job-submission-container {
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1.5rem;
        background-color: white;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
    }
    </style>
""", unsafe_allow_html=True)

def save_jobs_to_database(jobs_df, user_id):
    """Save changes from the DataFrame back to the database."""
    conn = get_db_connection()
    try:
        # First, get the current data to compare (filtered by user)
        current_data = pd.read_sql_query("SELECT id FROM jobs WHERE user_id = ?", conn, params=(user_id,))
        current_ids = set(current_data['id'])
        
        # Get the IDs in the edited DataFrame
        edited_ids = set(jobs_df['id'].dropna())
        
        # Find IDs to delete (in current but not in edited)
        ids_to_delete = current_ids - edited_ids
        
        # Delete removed rows (only for current user)
        if ids_to_delete:
            placeholders = ','.join('?' * len(ids_to_delete))
            params = tuple(ids_to_delete) + (user_id,)
            conn.execute(f'DELETE FROM jobs WHERE id IN ({placeholders}) AND user_id = ?', params)
        
        # Update or insert remaining rows
        for _, row in jobs_df.iterrows():
            if pd.notna(row['id']):
                # Update existing row (only for current user)
                conn.execute('''UPDATE jobs 
                              SET company_name = ?, 
                                  job_title = ?, 
                                  job_description = ?, 
                                  application_url = ?, 
                                  status = ?, 
                                  sentiment = ?, 
                                  notes = ?,
                                  location = ?,
                                  salary = ?,
                                  applied_date = ?
                              WHERE id = ? AND user_id = ?''',
                           (row['company_name'], row['job_title'], 
                            row['job_description'], row['application_url'],
                            row['status'], row['sentiment'], row['notes'],
                            row['location'], row['salary'], row['applied_date'],
                            row['id'], user_id))
            else:
                # Insert new row with user_id
                conn.execute('''INSERT INTO jobs 
                              (company_name, job_title, job_description, 
                               application_url, status, sentiment, notes, date_added,
                               location, salary, applied_date, user_id)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (row['company_name'], row['job_title'], 
                            row['job_description'], row['application_url'],
                            row['status'], row['sentiment'], row['notes'],
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            row['location'], row['salary'], row['applied_date'], user_id))
        
        conn.commit()
        return True, "Changes saved successfully!"
    except Exception as e:
        conn.rollback()
        return False, f"Error saving changes: {str(e)}"
    finally:
        conn.close()

def show_jobs_portal():
    """Show the Jobs Portal with shadcn tabs."""
    # Authentication is now handled at the main app level
    user_id = st.session_state.get('user_id')
    
    # Get database connection
    conn = get_db_connection()
    
    # Create shadcn tabs with default tab (URL Job Loader temporarily disabled for cloud deployment)
    selected_tab = tabs(["Jobs Database", "Jobs Submissions"], default_value="Jobs Database")
    
    if selected_tab == "Jobs Database":
        try:
            jobs_df = pd.read_sql_query("SELECT * FROM jobs WHERE user_id = ?", conn, params=(user_id,))
            st.session_state.df = jobs_df
            if not jobs_df.empty:
                # Create a form for the data editor
                with st.form("jobs_database_form"):
                    edited_df = st.data_editor(
                        jobs_df,
                        hide_index=True,
                        num_rows="dynamic"
                    )
                    
                    # Add save button
                    if st.form_submit_button("Save Changes"):
                        success, message = save_jobs_to_database(edited_df, user_id)
                        if success:
                            st.success(message)
                            st.rerun()  # Refresh to show updated data
                        else:
                            st.error(message)
            else:
                st.info("No jobs added yet. Add your first job in the Job Portal!")
        except Exception as e:
            st.error(f"Error loading jobs: {str(e)}")
    
    elif selected_tab == "Jobs Submissions":
        with st.form("job_submission_form"):
            st.subheader("Submit New Job")
            
            company_name = st.text_input("Company Name")
            job_title = st.text_input("Job Title")
            job_description = st.text_area("Job Description")
            application_url = st.text_input("Application URL")
            location = st.text_input("Location")
            salary = st.text_input("Salary")
            job_listing_type = st.selectbox(
                "Job Listing Type",
                ["Company Listing", "Indeed", "LinkedIn", "Recruiter"]
            )
            status = st.selectbox("Application Status", 
                                ["Not Applied", "Applied", "Interviewing", "Offered", "Rejected"])
            sentiment = st.select_slider("Your Sentiment", 
                                       ["Very Negative", "Negative", "Neutral", "Positive", "Very Positive"],
                                       value="Neutral")
            applied_date = st.date_input("Date Applied", value=None)
            notes = st.text_area("Notes")
            
            submitted = st.form_submit_button("Submit")
            
            if submitted:
                # Add to database
                conn = get_db_connection()
                c = conn.cursor()
                c.execute('''INSERT INTO jobs 
                            (company_name, job_title, job_description, application_url,
                             status, sentiment, notes, date_added, location, salary, applied_date, user_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (company_name, job_title, job_description, application_url,
                          status, sentiment, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          location, salary, applied_date.strftime("%Y-%m-%d") if applied_date else None, user_id))
                conn.commit()
                conn.close()
                st.success("Job added successfully!")
    
    # elif selected_tab == "URL Job Loader":
    #     ⚠️ URL Job Loader temporarily disabled for cloud deployment
    #     This feature uses Selenium which requires browser automation not available in cloud hosting
    #     To re-enable: uncomment this section and add selenium back to requirements.txt
    #     
    #     st.info("🚧 URL Job Loader feature temporarily unavailable in cloud deployment")
    #     st.markdown("""
    #     **This feature will be re-enabled in a future update with cloud-compatible web scraping.**
    #     
    #     For now, please use the **Jobs Submissions** tab to manually add job details.
    #     """)
    
    # Close database connection
    conn.close()
