"""
Script to create tables in Supabase PostgreSQL database.
Run this once to set up the database schema.
"""

import os
from supabase import create_client, Client
import streamlit as st

def get_supabase_client():
    """Get Supabase client connection."""
    # Load from secrets file for local development
    try:
        supabase_url = "https://hnjcdsihsocxlmktjfpl.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhuamNkc2loc29jeGxta3RqZnBsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzODUzNjMsImV4cCI6MjA2Mzk2MTM2M30._BN9eioY59JfVlMhgMSLnm40IwKVkJj5WvnzjMfnJ3c"
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