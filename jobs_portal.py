import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_db_connection, init_db, ensure_directories
from streamlit_shadcn_ui import tabs
from selenium_scraper import open_webpage, get_longest_text_content, scraper_openai_agent, save_job_to_database

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

def save_jobs_to_database(jobs_df):
    """Save changes from the DataFrame back to the database."""
    conn = get_db_connection()
    try:
        # First, get the current data to compare
        current_data = pd.read_sql_query("SELECT id FROM jobs", conn)
        current_ids = set(current_data['id'])
        
        # Get the IDs in the edited DataFrame
        edited_ids = set(jobs_df['id'].dropna())
        
        # Find IDs to delete (in current but not in edited)
        ids_to_delete = current_ids - edited_ids
        
        # Delete removed rows
        if ids_to_delete:
            placeholders = ','.join('?' * len(ids_to_delete))
            conn.execute(f'DELETE FROM jobs WHERE id IN ({placeholders})', tuple(ids_to_delete))
        
        # Update or insert remaining rows
        for _, row in jobs_df.iterrows():
            if pd.notna(row['id']):
                # Update existing row
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
                              WHERE id = ?''',
                           (row['company_name'], row['job_title'], 
                            row['job_description'], row['application_url'],
                            row['status'], row['sentiment'], row['notes'],
                            row['location'], row['salary'], row['applied_date'],
                            row['id']))
            else:
                # Insert new row
                conn.execute('''INSERT INTO jobs 
                              (company_name, job_title, job_description, 
                               application_url, status, sentiment, notes, date_added,
                               location, salary, applied_date)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (row['company_name'], row['job_title'], 
                            row['job_description'], row['application_url'],
                            row['status'], row['sentiment'], row['notes'],
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            row['location'], row['salary'], row['applied_date']))
        
        conn.commit()
        return True, "Changes saved successfully!"
    except Exception as e:
        conn.rollback()
        return False, f"Error saving changes: {str(e)}"
    finally:
        conn.close()

def show_jobs_portal():
    """Show the Jobs Portal with shadcn tabs."""
    # Get database connection
    conn = get_db_connection()
    
    # Create shadcn tabs with default tab
    selected_tab = tabs(["Jobs Database", "Jobs Submissions", "URL Job Loader"], default_value="Jobs Database")
    
    if selected_tab == "Jobs Database":
        try:
            jobs_df = pd.read_sql_query("SELECT * FROM jobs", conn)
            st.session_state.df = jobs_df
            if not jobs_df.empty:
                # Create a form for the data editor
                with st.form("jobs_database_form"):
                    edited_df = st.data_editor(
                        jobs_df,
                        hide_index=True,
                        num_rows="dynamic",
                        height=600
                    )
                    
                    # Add save button
                    if st.form_submit_button("Save Changes"):
                        success, message = save_jobs_to_database(edited_df)
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
                user_id = st.session_state.get('user_id')
                # Add to database
                conn = get_db_connection()
                c = conn.cursor()
                c.execute('''INSERT INTO jobs 
                            (user_id, company_name, job_title, job_description, application_url,
                             status, sentiment, notes, date_added, location, salary, applied_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (user_id, company_name, job_title, job_description, application_url,
                          status, sentiment, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          location, salary, applied_date.strftime("%Y-%m-%d") if applied_date else None))
                conn.commit()
                conn.close()
                st.success("Job added successfully!")
    
    elif selected_tab == "URL Job Loader":
        # Initialize session state for job description and metadata
        if 'job_description' not in st.session_state:
            st.session_state.job_description = None
        if 'job_metadata' not in st.session_state:
            st.session_state.job_metadata = {}
        if 'ai_analysis' not in st.session_state:
            st.session_state.ai_analysis = None
        
        # Create a form for job details
        with st.form("job_form"):
            st.subheader("Enter Job Details")
            
            # Input fields
            job_url = st.text_input("Job URL")
            listing_type = st.selectbox(
                "Listing Type",
                ["Company Listing", "Indeed", "LinkedIn", "Recruiter"]
            )
            application_status = st.selectbox(
                "Application Status",
                ["Not Applied", "Applied", "Interviewing", "Offered", "Rejected"]
            )
            
            # Submit button
            get_details = st.form_submit_button("Get Job Details")
            
            if get_details and job_url:
                with st.spinner("Scraping job details..."):
                    # Store metadata
                    st.session_state.job_metadata = {
                        "job_url": job_url,
                        "listing_type": listing_type,
                        "application_status": application_status
                    }
                    
                    # Open the webpage
                    driver = open_webpage(job_url)
                    if driver:
                        try:
                            # Get the longest text content (likely job description)
                            longest_text = get_longest_text_content(driver)
                            
                            if longest_text and longest_text["text"]:
                                # Store in session state for AI parsing
                                st.session_state.job_description = longest_text["text"]
                                
                                # Display the scraped content
                                st.subheader("Scraped Content")
                                st.text_area("Job Description", value=longest_text["text"], height=300)
                            else:
                                st.error("Could not find job description. Please check the URL and try again.")
                        finally:
                            driver.quit()
                    else:
                        st.error("Failed to open the webpage. Please check the URL and try again.")
        
        # Show Parse with AI button if we have content
        if st.session_state.job_description:
            if st.button("Parse with AI"):
                with st.spinner("Analyzing content..."):
                    # Get AI analysis
                    ai_analysis = scraper_openai_agent(st.session_state.job_description)
                    
                    # Display AI analysis
                    st.subheader("AI Analysis")
                    
                    # Ensure we have a dictionary and format it properly
                    if isinstance(ai_analysis, str):
                        try:
                            # Try to parse string as JSON
                            analysis_dict = json.loads(ai_analysis)
                        except:
                            # If parsing fails, create a dictionary with the text
                            analysis_dict = {"Analysis": ai_analysis}
                    else:
                        analysis_dict = ai_analysis
                    
                    # Map the AI analysis fields to our required fields
                    job_details = {
                        'company_name': analysis_dict.get('Company Name', ''),
                        'job_title': analysis_dict.get('Job Title', ''),
                        'job_description': analysis_dict.get('Job Description', ''),
                        'application_url': st.session_state.job_metadata['job_url'],
                        'status': 'Not Applied',
                        'sentiment': 'Neutral',
                        'location': analysis_dict.get('Job Location', 'Not Listed'),
                        'salary': analysis_dict.get('Job Salary', 'Not Listed'),
                        'applied_date': '',
                        'notes': ''  # Store full analysis as notes
                    }
                    
                    # Store in session state
                    st.session_state.ai_analysis = job_details
                    
                    # Display the standardized format
                    st.json(job_details)
        
        # Show save form if we have AI analysis
        if st.session_state.ai_analysis:
            with st.form("save_job_form"):
                st.subheader("Save Job Details")
                
                # Only show Notes and Applied Date fields
                notes = st.text_area("Notes")
                applied_date = st.date_input("Date Applied", value=None)
                
                if st.form_submit_button("Save to Database"):
                    try:
                        user_id = st.session_state.get('user_id')
                        # Add to database
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute('''INSERT INTO jobs 
                                    (user_id, company_name, job_title, job_description, application_url,
                                     status, sentiment, notes, date_added, location, salary, applied_date)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                 (user_id,
                                  st.session_state.ai_analysis['company_name'],
                                  st.session_state.ai_analysis['job_title'],
                                  st.session_state.ai_analysis['job_description'],
                                  st.session_state.ai_analysis['application_url'],
                                  st.session_state.ai_analysis['status'],
                                  st.session_state.ai_analysis['sentiment'],
                                  notes,
                                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  st.session_state.ai_analysis['location'],
                                  st.session_state.ai_analysis['salary'],
                                  applied_date.strftime("%Y-%m-%d") if applied_date else None))
                        conn.commit()
                        conn.close()
                        
                        # Show success message in a prominent way
                        st.success("✅ Job details saved successfully!")
                        
                        # Clear session state after successful save
                        st.session_state.job_description = None
                        st.session_state.job_metadata = {}
                        st.session_state.ai_analysis = None
                        
                        # Add a small delay to ensure the message is seen
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error saving job to database: {str(e)}")
                        conn.rollback()
                        conn.close()
    
    # Close database connection
    conn.close()