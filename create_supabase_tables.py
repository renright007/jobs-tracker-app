"""
Script to create tables in Supabase PostgreSQL database.
Run this once to set up the database schema.
"""

import os
from supabase import create_client, Client
import streamlit as st

def get_supabase_client():
    """Get Supabase client connection."""
    try:
        # Try to get from environment variables first
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_API_KEY")
        
        # If not in environment, try Streamlit secrets
        if not supabase_url or not supabase_key:
            try:
                import streamlit as st
                supabase_url = st.secrets["SUPABASE_URL"]
                supabase_key = st.secrets["SUPABASE_API_KEY"]
            except:
                print("❌ Supabase credentials not found in environment variables or Streamlit secrets")
                print("Set SUPABASE_URL and SUPABASE_API_KEY environment variables or run from Streamlit context")
                return None
        
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        return None

def create_tables():
    """Create all necessary tables in Supabase."""
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Could not connect to Supabase")
        return False
    
    # SQL statements to create tables
    tables = {
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
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
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
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
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
                user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                selected_resume TEXT,
                created_date TEXT,
                last_updated_date TEXT
            );
        ''',
        
        'career_goals': '''
            CREATE TABLE IF NOT EXISTS career_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                goals TEXT,
                submission_date TEXT
            );
        '''
    }
    
    print("🏗️  Creating Supabase tables...")
    
    for table_name, sql in tables.items():
        try:
            # Use the SQL editor or direct query execution
            print(f"Creating table: {table_name}")
            
            # Note: Supabase Python client doesn't directly support DDL
            # You'll need to run these SQL statements in the Supabase SQL Editor
            print(f"SQL for {table_name}:")
            print(sql)
            print("---")
            
        except Exception as e:
            print(f"❌ Error creating table {table_name}: {e}")
            return False
    
    print("✅ Table creation SQL generated successfully!")
    print("\n📋 Next Steps:")
    print("1. Copy the SQL statements above")
    print("2. Go to your Supabase dashboard")
    print("3. Navigate to SQL Editor")
    print("4. Paste and run each CREATE TABLE statement")
    print("5. Run the data migration script")
    
    return True

if __name__ == "__main__":
    create_tables()