"""
Supabase database utilities for cloud deployment.
Provides PostgreSQL database operations for Streamlit Cloud.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import os

def get_supabase_client() -> Client:
    """Get Supabase client connection."""
    try:
        # Try to get from Streamlit secrets first (cloud deployment)
        supabase_url = st.secrets.get("SUPABASE_URL")
        supabase_key = st.secrets.get("SUPABASE_API_KEY")
    except:
        # Fallback to environment variables (local development)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_API_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase credentials not found in secrets or environment variables")
    
    return create_client(supabase_url, supabase_key)

def init_supabase_tables():
    """Initialize Supabase tables with the same schema as SQLite."""
    supabase = get_supabase_client()
    
    # Note: Tables should be created through Supabase dashboard or migrations
    # This function verifies tables exist and creates them if needed via SQL
    
    tables_sql = {
        'users': '''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''',
        'jobs': '''
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
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
                applied_date TEXT
            );
        ''',
        'documents': '''
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                document_name TEXT,
                document_type TEXT,
                upload_date TEXT,
                file_path TEXT,
                document_content TEXT,
                preferred_resume INTEGER DEFAULT 0
            );
        ''',
        'user_profile': '''
            CREATE TABLE IF NOT EXISTS user_profile (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE REFERENCES users(id),
                selected_resume TEXT,
                created_date TEXT,
                last_updated_date TEXT
            );
        ''',
        'career_goals': '''
            CREATE TABLE IF NOT EXISTS career_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                goals TEXT,
                submission_date TEXT
            );
        '''
    }
    
    try:
        for table_name, sql in tables_sql.items():
            # Execute raw SQL to create tables
            result = supabase.rpc('exec_sql', {'sql': sql})
            st.write(f"✅ Table {table_name} verified/created")
        return True, "Supabase tables initialized successfully!"
    except Exception as e:
        return False, f"Error initializing Supabase tables: {str(e)}"

# User operations
def supabase_get_user_jobs(user_id):
    """Get all jobs for a specific user from Supabase."""
    supabase = get_supabase_client()
    try:
        result = supabase.table('jobs').select('*').eq('user_id', user_id).order('date_added', desc=True).execute()
        return pd.DataFrame(result.data)
    except Exception as e:
        st.error(f"Error getting user jobs: {str(e)}")
        return pd.DataFrame()

def supabase_get_user_documents(user_id):
    """Get all documents for a specific user from Supabase."""
    supabase = get_supabase_client()
    try:
        result = supabase.table('documents').select('*').eq('user_id', user_id).order('upload_date', desc=True).execute()
        return pd.DataFrame(result.data)
    except Exception as e:
        st.error(f"Error getting user documents: {str(e)}")
        return pd.DataFrame()

def supabase_get_user_profile(user_id):
    """Get user profile from Supabase."""
    supabase = get_supabase_client()
    try:
        result = supabase.table('user_profile').select('*').eq('user_id', user_id).execute()
        return pd.DataFrame(result.data)
    except Exception as e:
        st.error(f"Error getting user profile: {str(e)}")
        return pd.DataFrame()

def supabase_get_user_career_goals(user_id):
    """Get career goals for a specific user from Supabase."""
    supabase = get_supabase_client()
    try:
        result = supabase.table('career_goals').select('*').eq('user_id', user_id).order('submission_date', desc=True).execute()
        return pd.DataFrame(result.data)
    except Exception as e:
        st.error(f"Error getting career goals: {str(e)}")
        return pd.DataFrame()

# Create operations
def supabase_add_job(user_id, job_data):
    """Add a new job for a user to Supabase."""
    supabase = get_supabase_client()
    try:
        job_record = {
            'user_id': user_id,
            'company_name': job_data.get('company_name'),
            'job_title': job_data.get('job_title'),
            'job_description': job_data.get('job_description'),
            'application_url': job_data.get('application_url'),
            'status': job_data.get('status'),
            'sentiment': job_data.get('sentiment'),
            'notes': job_data.get('notes'),
            'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'location': job_data.get('location'),
            'salary': job_data.get('salary'),
            'applied_date': job_data.get('applied_date')
        }
        
        result = supabase.table('jobs').insert(job_record).execute()
        return True, "Job added successfully!"
    except Exception as e:
        return False, f"Error adding job: {str(e)}"

def supabase_add_document(user_id, document_data):
    """Add a new document for a user to Supabase."""
    supabase = get_supabase_client()
    try:
        doc_record = {
            'user_id': user_id,
            'document_name': document_data.get('document_name'),
            'document_type': document_data.get('document_type'),
            'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'file_path': document_data.get('file_path'),
            'document_content': document_data.get('document_content'),
            'preferred_resume': 0  # Default to not preferred
        }
        
        result = supabase.table('documents').insert(doc_record).execute()
        return True, "Document added successfully!"
    except Exception as e:
        return False, f"Error adding document: {str(e)}"

def supabase_add_career_goals(user_id, goals):
    """Add new career goals for a user to Supabase."""
    supabase = get_supabase_client()
    try:
        goals_record = {
            'user_id': user_id,
            'goals': goals,
            'submission_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        result = supabase.table('career_goals').insert(goals_record).execute()
        return True, "Career goals added successfully!"
    except Exception as e:
        return False, f"Error adding career goals: {str(e)}"

# Update operations
def supabase_save_documents_to_database(user_id, documents_df):
    """Save changes from the documents DataFrame back to Supabase with preferred resume validation."""
    supabase = get_supabase_client()
    try:
        # Business rule: Only one preferred resume per user
        preferred_count = len(documents_df[documents_df['preferred_resume'] == True])
        if preferred_count > 1:
            return False, "Only one document can be set as preferred resume per user"
        
        # Update each document
        for _, row in documents_df.iterrows():
            # Verify document belongs to user
            doc_check = supabase.table('documents').select('user_id').eq('id', row['id']).execute()
            if not doc_check.data or doc_check.data[0]['user_id'] != user_id:
                continue  # Skip documents that don't belong to this user
            
            # Convert boolean to integer
            preferred_value = 1 if row['preferred_resume'] else 0
            
            # Update the document
            update_data = {'preferred_resume': preferred_value}
            result = supabase.table('documents').update(update_data).eq('id', row['id']).eq('user_id', user_id).execute()
        
        return True, "Documents updated successfully!"
    except Exception as e:
        return False, f"Error saving documents: {str(e)}"

def supabase_update_user_profile(user_id, profile_data):
    """Update or create user profile in Supabase."""
    supabase = get_supabase_client()
    try:
        # Check if profile exists
        existing = supabase.table('user_profile').select('id').eq('user_id', user_id).execute()
        
        profile_record = {
            'user_id': user_id,
            'selected_resume': profile_data.get('selected_resume'),
            'last_updated_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if existing.data:
            # Update existing profile
            result = supabase.table('user_profile').update(profile_record).eq('user_id', user_id).execute()
        else:
            # Create new profile
            profile_record['created_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = supabase.table('user_profile').insert(profile_record).execute()
        
        return True, "Profile updated successfully!"
    except Exception as e:
        return False, f"Error updating profile: {str(e)}"

# Delete operations  
def supabase_delete_document(user_id, document_id):
    """Delete a document for a user from Supabase (database only - files handled separately)."""
    supabase = get_supabase_client()
    try:
        # Verify document belongs to user before deletion
        doc_check = supabase.table('documents').select('user_id').eq('id', document_id).execute()
        if not doc_check.data or doc_check.data[0]['user_id'] != user_id:
            return False, "Document not found or access denied"
        
        # Delete from database
        result = supabase.table('documents').delete().eq('id', document_id).eq('user_id', user_id).execute()
        return True, "Document deleted successfully!"
    except Exception as e:
        return False, f"Error deleting document: {str(e)}"

# Utility functions
def supabase_get_preferred_resume(user_id):
    """Get the user's preferred resume document from Supabase."""
    supabase = get_supabase_client()
    try:
        result = supabase.table('documents').select('*').eq('user_id', user_id).eq('preferred_resume', 1).eq('document_type', 'Resume').limit(1).execute()
        return pd.DataFrame(result.data) if result.data else None
    except Exception as e:
        st.error(f"Error getting preferred resume: {str(e)}")
        return None

def supabase_get_user_stats(user_id):
    """Get statistics for a user's job applications from Supabase."""
    supabase = get_supabase_client()
    try:
        # Get all jobs for user
        jobs_result = supabase.table('jobs').select('status, date_added').eq('user_id', user_id).execute()
        jobs_df = pd.DataFrame(jobs_result.data)
        
        if jobs_df.empty:
            return {
                'total_applications': 0,
                'status_counts': {},
                'recent_applications': 0
            }
        
        # Calculate stats
        total_applications = len(jobs_df)
        status_counts = jobs_df['status'].value_counts().to_dict()
        
        # Recent applications (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        recent_jobs = jobs_df[jobs_df['date_added'] >= seven_days_ago]
        recent_applications = len(recent_jobs)
        
        return {
            'total_applications': total_applications,
            'status_counts': status_counts,
            'recent_applications': recent_applications
        }
    except Exception as e:
        st.error(f"Error getting user stats: {str(e)}")
        return {
            'total_applications': 0,
            'status_counts': {},
            'recent_applications': 0
        }