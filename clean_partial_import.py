"""
Clean partially imported data from Supabase before re-running import.
"""

import os
from supabase import create_client, Client

def get_supabase_client():
    """Get Supabase client connection."""
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
            raise ValueError("❌ Supabase credentials not found. Set SUPABASE_URL and SUPABASE_API_KEY environment variables or run from Streamlit context")
    
    return create_client(supabase_url, supabase_key)

def clean_partial_import():
    """Clean any partially imported data."""
    supabase = get_supabase_client()
    
    print("🧹 Cleaning partially imported data...")
    
    # Delete in reverse order due to foreign key constraints
    tables = ['career_goals', 'user_profile', 'documents', 'jobs', 'users']
    
    for table in tables:
        try:
            # Check if table has data
            result = supabase.table(table).select('id', count='exact').execute()
            count = result.count
            
            if count > 0:
                print(f"  🗑️ Cleaning {count} records from {table}")
                # Delete all records
                delete_result = supabase.table(table).delete().neq('id', 0).execute()
                print(f"  ✅ Cleaned {table}")
            else:
                print(f"  ✅ {table} already empty")
                
        except Exception as e:
            print(f"  ❌ Error cleaning {table}: {str(e)}")
    
    print("\n✅ Cleanup completed!")

if __name__ == "__main__":
    clean_partial_import()