"""
Clean partially imported data from Supabase before re-running import.
"""

from supabase import create_client, Client

def get_supabase_client():
    """Get Supabase client connection."""
    supabase_url = "https://hnjcdsihsocxlmktjfpl.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhuamNkc2loc29jeGxta3RqZnBsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzODUzNjMsImV4cCI6MjA2Mzk2MTM2M30._BN9eioY59JfVlMhgMSLnm40IwKVkJj5WvnzjMfnJ3c"
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