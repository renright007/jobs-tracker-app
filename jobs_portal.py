import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_db_connection, init_db, ensure_directories
from streamlit_shadcn_ui import tabs
from selenium_scraper import open_webpage, get_longest_text_content, scraper_openai_agent, save_job_to_database
from firecrawl_scraper import scrape_job_with_firecrawl, is_firecrawl_available

import json
import time

# Note: Database initialization is handled by main app.py to prevent cloud filesystem issues
# ensure_directories() also moved to main app initialization

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
    """Save changes from the DataFrame back to the database using unified database system."""
    from database_utils import use_supabase
    
    if use_supabase():
        from supabase_utils import get_supabase_client
        try:
            supabase = get_supabase_client()
            
            # Get current job IDs
            current_result = supabase.table('jobs').select('id').execute()
            current_ids = set(row['id'] for row in current_result.data)
            
            # Get edited job IDs
            edited_ids = set(jobs_df['id'].dropna())
            
            # Delete removed jobs
            ids_to_delete = current_ids - edited_ids
            if ids_to_delete:
                for job_id in ids_to_delete:
                    supabase.table('jobs').delete().eq('id', job_id).execute()
            
            # Update or insert jobs
            for _, row in jobs_df.iterrows():
                job_data = {
                    'company_name': row['company_name'],
                    'job_title': row['job_title'],
                    'job_description': row['job_description'],
                    'application_url': row['application_url'],
                    'status': row['status'],
                    'sentiment': row['sentiment'],
                    'notes': row['notes'],
                    'location': row['location'],
                    'salary': row['salary'],
                    'applied_date': row['applied_date']
                }
                
                if pd.notna(row['id']):
                    # Update existing job
                    supabase.table('jobs').update(job_data).eq('id', row['id']).execute()
                else:
                    # Insert new job
                    job_data['date_added'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    supabase.table('jobs').insert(job_data).execute()
            
            return True, "Changes saved successfully!"
        except Exception as e:
            return False, f"Error saving changes: {str(e)}"
    else:
        # SQLite fallback
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
    """Show the Jobs Portal with shadcn tabs using unified database system."""
    from database_utils import use_supabase
    
    # Create shadcn tabs with default tab
    selected_tab = tabs(["Jobs Database", "Jobs Submissions", "Firecrawl Job Scraper"], default_value="Jobs Database")
    
    if selected_tab == "Jobs Database":
        try:
            if use_supabase():
                from supabase_utils import get_supabase_client
                supabase = get_supabase_client()
                result = supabase.table('jobs').select('*').order('date_added', desc=True).execute()
                jobs_df = pd.DataFrame(result.data) if result.data else pd.DataFrame()
            else:
                conn = get_db_connection()
                jobs_df = pd.read_sql_query("SELECT * FROM jobs ORDER BY date_added DESC", conn)
                conn.close()
                
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
                ["Company Listing", "Indeed", "LinkedIn", "Recruiter", "Upwork"]
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
                from database_utils import use_supabase
                user_id = st.session_state.get('user_id')
                
                if use_supabase():
                    from supabase_utils import get_supabase_client
                    try:
                        supabase = get_supabase_client()
                        job_data = {
                            'user_id': user_id,
                            'company_name': company_name,
                            'job_title': job_title,
                            'job_description': job_description,
                            'application_url': application_url,
                            'status': status,
                            'sentiment': sentiment,
                            'notes': notes,
                            'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'location': location,
                            'salary': salary,
                            'applied_date': applied_date.strftime("%Y-%m-%d") if applied_date else None
                        }
                        supabase.table('jobs').insert(job_data).execute()
                        st.success("Job added successfully!")
                    except Exception as e:
                        st.error(f"Error adding job: {str(e)}")
                else:
                    # SQLite fallback
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
    
    elif selected_tab == "Firecrawl Job Scraper":
        st.info("🔥 **Firecrawl-Only Scraper** - Test the cloud-compatible Firecrawl API directly")
        
        # Initialize session state for Firecrawl scraper (separate from URL Job Loader)
        if 'firecrawl_job_description' not in st.session_state:
            st.session_state.firecrawl_job_description = None
        if 'firecrawl_job_metadata' not in st.session_state:
            st.session_state.firecrawl_job_metadata = {}
        if 'firecrawl_ai_analysis' not in st.session_state:
            st.session_state.firecrawl_ai_analysis = None
        if 'firecrawl_scrape_time' not in st.session_state:
            st.session_state.firecrawl_scrape_time = None
        
        # Check if Firecrawl is available
        if not is_firecrawl_available():
            st.error("🚫 Firecrawl API not available. Please check your API key configuration.")
            st.info("💡 See FIRECRAWL_SETUP.md for setup instructions.")
            return
        
        st.success("✅ Firecrawl API is ready for testing!")
        
        # Create a form for job details
        with st.form("firecrawl_job_form"):
            st.subheader("Enter Job Details")
            
            # Input fields (same as URL Job Loader)
            job_url = st.text_input("Job URL", help="Enter the job posting URL to scrape with Firecrawl")
            listing_type = st.selectbox(
                "Listing Type",
                ["Company Listing", "Indeed", "LinkedIn", "Recruiter", "Upwork"]
            )
            application_status = st.selectbox(
                "Application Status", 
                ["Not Applied", "Applied", "Interviewing", "Offered", "Rejected"]
            )
            
            # Submit button
            get_details = st.form_submit_button("🔥 Scrape with Firecrawl")
            
            if get_details and job_url:
                # Store metadata
                st.session_state.firecrawl_job_metadata = {
                    "job_url": job_url,
                    "listing_type": listing_type,
                    "application_status": application_status
                }
                
                # Show scraping method
                st.info("🔥 Using Firecrawl API for scraping")
                
                with st.spinner("Scraping job details with Firecrawl..."):
                    import time as time_module
                    start_time = time_module.time()
                    
                    # Use Firecrawl exclusively (no fallbacks)
                    result = scrape_job_with_firecrawl(job_url)
                    
                    end_time = time_module.time()
                    scrape_time = end_time - start_time
                    st.session_state.firecrawl_scrape_time = scrape_time
                    
                    if result.get("success"):
                        # Extract content from simplified response
                        data = result.get("data", {})
                        scraped_content = data.get("scraped_content", "")
                        
                        if scraped_content and scraped_content.strip():
                            # Store in session state for AI parsing
                            st.session_state.firecrawl_job_description = scraped_content
                            
                            # Show performance metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("⏱️ Scrape Time", f"{scrape_time:.2f}s")
                            with col2:
                                st.metric("📄 Content Length", f"{len(scraped_content):,} chars")
                            with col3:
                                word_count = len(scraped_content.split())
                                st.metric("📝 Word Count", f"{word_count:,} words")
                            
                            # Display the scraped content
                            st.subheader("📄 Scraped Content")
                            st.text_area("Job Description (Firecrawl)", value=scraped_content, height=300, key="firecrawl_content_display")
                            
                            # Always require manual AI parsing for consistency
                            st.info("💡 Click 'Parse with AI' below to extract job information")
                        else:
                            st.error("❌ Could not extract content from the webpage using Firecrawl")
                            st.info("The page may have restrictions or the content may be behind authentication")
                            
                            # Show debug information
                            if data:
                                st.write("**Debug - Raw Response Data:**")
                                st.json(data)
                    else:
                        error = result.get("error", "Unknown error")
                        st.error(f"❌ Firecrawl scraping failed: {error}")
                        st.info("💡 This could be due to:")
                        st.write("- Site blocking automated access")
                        st.write("- Invalid URL")
                        st.write("- API rate limits or quota exceeded")
                        st.write("- Page requiring authentication")
                        st.write("- Firecrawl API key issues")
                        
                        # Show debug information
                        st.write("**Debug - Full Response:**")
                        st.json(result)
        
        # Show Parse with AI button if we have content (but no AI analysis yet)
        if st.session_state.firecrawl_job_description and not st.session_state.firecrawl_ai_analysis:
            if st.button("🤖 Parse with AI", key="firecrawl_parse_ai"):
                with st.spinner("Analyzing content with AI..."):
                    # Get AI analysis using the existing function
                    ai_analysis = scraper_openai_agent(st.session_state.firecrawl_job_description)
                    
                    # Display AI analysis
                    st.subheader("🤖 AI Analysis")
                    
                    # Parse AI response
                    if isinstance(ai_analysis, str):
                        try:
                            analysis_dict = json.loads(ai_analysis)
                        except:
                            analysis_dict = {"Analysis": ai_analysis}
                    else:
                        analysis_dict = ai_analysis
                    
                    # Map to our standard format
                    job_details = {
                        'company_name': analysis_dict.get('Company Name', ''),
                        'job_title': analysis_dict.get('Job Title', ''),
                        'job_description': analysis_dict.get('Job Description', ''),
                        'application_url': st.session_state.firecrawl_job_metadata['job_url'],
                        'status': 'Not Applied',
                        'sentiment': 'Neutral',
                        'location': analysis_dict.get('Job Location', 'Not Listed'),
                        'salary': analysis_dict.get('Job Salary', 'Not Listed'),
                        'applied_date': '',
                        'notes': f'Scraped with Firecrawl API in {st.session_state.firecrawl_scrape_time:.2f}s'
                    }
                    
                    # Store in session state
                    st.session_state.firecrawl_ai_analysis = job_details
                    
                    # Display the standardized format
                    st.json(job_details)
        
        # Show save form if we have AI analysis
        if st.session_state.firecrawl_ai_analysis:
            with st.form("save_firecrawl_job_form"):
                st.subheader("💾 Save Job Details")
                
                # Show a summary of what will be saved
                job_data = st.session_state.firecrawl_ai_analysis
                st.write(f"**Company:** {job_data['company_name']}")
                st.write(f"**Position:** {job_data['job_title']}")
                st.write(f"**Location:** {job_data['location']}")
                st.write(f"**Salary:** {job_data['salary']}")
                
                # Only show editable fields
                notes = st.text_area("Notes", help="Add any additional notes about this job")
                applied_date = st.date_input("Date Applied", value=None)
                
                if st.form_submit_button("💾 Save to Database", use_container_width=True):
                    from database_utils import use_supabase
                    try:
                        user_id = st.session_state.get('user_id')
                        
                        # Update notes before saving
                        st.session_state.firecrawl_ai_analysis['notes'] = notes
                        
                        if use_supabase():
                            from supabase_utils import get_supabase_client
                            supabase = get_supabase_client()
                            job_data = {
                                'user_id': user_id,
                                'company_name': st.session_state.firecrawl_ai_analysis['company_name'],
                                'job_title': st.session_state.firecrawl_ai_analysis['job_title'],
                                'job_description': st.session_state.firecrawl_ai_analysis['job_description'],
                                'application_url': st.session_state.firecrawl_ai_analysis['application_url'],
                                'status': st.session_state.firecrawl_ai_analysis['status'],
                                'sentiment': st.session_state.firecrawl_ai_analysis['sentiment'],
                                'notes': notes,
                                'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'location': st.session_state.firecrawl_ai_analysis['location'],
                                'salary': st.session_state.firecrawl_ai_analysis['salary'],
                                'applied_date': applied_date.strftime("%Y-%m-%d") if applied_date else None
                            }
                            supabase.table('jobs').insert(job_data).execute()
                        else:
                            # SQLite fallback
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute('''INSERT INTO jobs 
                                        (user_id, company_name, job_title, job_description, application_url,
                                         status, sentiment, notes, date_added, location, salary, applied_date)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                     (user_id,
                                      st.session_state.firecrawl_ai_analysis['company_name'],
                                      st.session_state.firecrawl_ai_analysis['job_title'],
                                      st.session_state.firecrawl_ai_analysis['job_description'],
                                      st.session_state.firecrawl_ai_analysis['application_url'],
                                      st.session_state.firecrawl_ai_analysis['status'],
                                      st.session_state.firecrawl_ai_analysis['sentiment'],
                                      notes,
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                      st.session_state.firecrawl_ai_analysis['location'],
                                      st.session_state.firecrawl_ai_analysis['salary'],
                                      applied_date.strftime("%Y-%m-%d") if applied_date else None))
                            conn.commit()
                            conn.close()
                        
                        # Show success message
                        st.success("🎉 Job details saved successfully via Firecrawl!")
                        
                        # Show performance summary
                        st.info(f"📊 **Scraping Summary:** {st.session_state.firecrawl_scrape_time:.2f}s scrape time, {len(st.session_state.firecrawl_job_description):,} characters extracted")
                        
                        # Clear session state after successful save
                        st.session_state.firecrawl_job_description = None
                        st.session_state.firecrawl_job_metadata = {}
                        st.session_state.firecrawl_ai_analysis = None
                        st.session_state.firecrawl_scrape_time = None
                        
                        # Add a small delay to ensure the message is seen
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error saving job to database: {str(e)}")


# =============================================================================
# ARCHIVED CODE - URL Job Loader (Selenium-based)
# =============================================================================
# This code is preserved but not active in the current application
# Uncomment and add "URL Job Loader" back to tabs list if you want to re-enable it
"""
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
                ["Company Listing", "Indeed", "LinkedIn", "Recruiter", "Upwork"]
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
                    
                    # Try Firecrawl first (cloud-compatible)
                    if is_firecrawl_available():
                        st.info("🔥 Using Firecrawl API for scraping (cloud-compatible)")
                        result = scrape_job_with_firecrawl(job_url)
                        
                        if result.get("success"):
                            # Extract content and AI analysis
                            data = result.get("data", {})
                            scraped_content = data.get("scraped_content", "")
                            
                            if scraped_content:
                                # Store in session state for AI parsing
                                st.session_state.job_description = scraped_content
                                
                                # Display the scraped content
                                st.subheader("Scraped Content")
                                st.text_area("Job Description", value=scraped_content, height=300)
                                
                                # If AI extraction was already done, show it
                                if "company_name" in data:
                                    st.session_state.ai_analysis = {
                                        'company_name': data.get('company_name', ''),
                                        'job_title': data.get('job_title', ''),
                                        'job_description': data.get('job_description', scraped_content),
                                        'application_url': job_url,
                                        'status': 'Not Applied',
                                        'sentiment': 'Neutral',
                                        'location': data.get('job_location', 'Not Listed'),
                                        'salary': data.get('job_salary', 'Not Listed'),
                                        'applied_date': '',
                                        'notes': ''
                                    }
                                    st.success("🤖 AI extraction completed automatically!")
                            else:
                                st.error("Could not extract content from the webpage. Please check the URL and try again.")
                        else:
                            error = result.get("error", "Unknown error")
                            st.error(f"❌ Firecrawl scraping failed: {error}")
                            st.info("💡 Trying backup Selenium scraper...")
                            
                            # Fallback to Selenium
                            driver = open_webpage(job_url)
                            if driver:
                                try:
                                    # Get the longest text content (likely job description)
                                    longest_text = get_longest_text_content(driver)
                                    
                                    if longest_text and longest_text["text"]:
                                        # Store in session state for AI parsing
                                        st.session_state.job_description = longest_text["text"]
                                        
                                        # Display the scraped content
                                        st.subheader("Scraped Content (Selenium Fallback)")
                                        st.text_area("Job Description", value=longest_text["text"], height=300)
                                    else:
                                        st.error("Could not find job description with fallback method either.")
                                finally:
                                    driver.quit()
                            else:
                                st.error("Both Firecrawl and Selenium scraping failed. Please check the URL.")
                    else:
                        # Firecrawl not available, use Selenium
                        st.info("🔧 Using Selenium for scraping (local only)")
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
                    from database_utils import use_supabase
                    try:
                        user_id = st.session_state.get('user_id')
                        
                        if use_supabase():
                            from supabase_utils import get_supabase_client
                            supabase = get_supabase_client()
                            job_data = {
                                'user_id': user_id,
                                'company_name': st.session_state.ai_analysis['company_name'],
                                'job_title': st.session_state.ai_analysis['job_title'],
                                'job_description': st.session_state.ai_analysis['job_description'],
                                'application_url': st.session_state.ai_analysis['application_url'],
                                'status': st.session_state.ai_analysis['status'],
                                'sentiment': st.session_state.ai_analysis['sentiment'],
                                'notes': notes,
                                'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'location': st.session_state.ai_analysis['location'],
                                'salary': st.session_state.ai_analysis['salary'],
                                'applied_date': applied_date.strftime("%Y-%m-%d") if applied_date else None
                            }
                            supabase.table('jobs').insert(job_data).execute()
                        else:
                            # SQLite fallback
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
"""
