"""
Import SQLite data to Supabase PostgreSQL database.
Run this after creating tables in Supabase dashboard.
"""

import json
import os
from supabase import create_client, Client
from datetime import datetime

def get_supabase_client():
    """Get Supabase client connection."""
    supabase_url = "https://hnjcdsihsocxlmktjfpl.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhuamNkc2loc29jeGxta3RqZnBsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzODUzNjMsImV4cCI6MjA2Mzk2MTM2M30._BN9eioY59JfVlMhgMSLnm40IwKVkJj5WvnzjMfnJ3c"
    return create_client(supabase_url, supabase_key)

def import_data_to_supabase(export_file):
    """Import data from SQLite export to Supabase."""
    
    if not os.path.exists(export_file):
        print(f"❌ Export file not found: {export_file}")
        return False
    
    # Load export data
    with open(export_file, 'r') as f:
        export_data = json.load(f)
    
    supabase = get_supabase_client()
    print("🚀 Importing data to Supabase...")
    
    # Import order matters due to foreign key constraints
    import_order = ['users', 'jobs', 'documents', 'user_profile', 'career_goals']
    
    for table_name in import_order:
        if table_name not in export_data['tables']:
            print(f"⚠️ No data found for table: {table_name}")
            continue
            
        table_data = export_data['tables'][table_name]
        if 'error' in table_data:
            print(f"❌ Skipping {table_name} due to export error: {table_data['error']}")
            continue
            
        records = table_data['data']
        if not records:
            print(f"ℹ️ No records to import for {table_name}")
            continue
        
        print(f"📤 Importing {len(records)} records to {table_name}...")
        
        try:
            # Process records in batches
            batch_size = 100
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                # Clean records for PostgreSQL
                cleaned_batch = []
                for record in batch:
                    cleaned_record = {}
                    for key, value in record.items():
                        # Skip SQLite auto-increment IDs - let PostgreSQL generate new ones
                        if key == 'id':
                            continue
                        # Handle None values
                        cleaned_record[key] = value
                    cleaned_batch.append(cleaned_record)
                
                # Insert batch
                if cleaned_batch:
                    result = supabase.table(table_name).insert(cleaned_batch).execute()
                    print(f"  ✅ Batch {i//batch_size + 1}: {len(cleaned_batch)} records inserted")
            
            print(f"✅ Successfully imported {len(records)} records to {table_name}")
            
        except Exception as e:
            print(f"❌ Error importing to {table_name}: {str(e)}")
            return False
    
    print("\n🎉 Data import completed successfully!")
    return True

def verify_import():
    """Verify that data was imported correctly."""
    supabase = get_supabase_client()
    
    print("\n🔍 Verifying import...")
    
    tables = ['users', 'jobs', 'documents', 'user_profile', 'career_goals']
    
    for table in tables:
        try:
            result = supabase.table(table).select('id', count='exact').execute()
            count = result.count
            print(f"  ✅ {table}: {count} records")
        except Exception as e:
            print(f"  ❌ {table}: Error - {str(e)}")

def main():
    # Find the most recent export file
    export_files = [f for f in os.listdir('.') if f.startswith('sqlite_export_') and f.endswith('.json')]
    
    if not export_files:
        print("❌ No export files found. Run export_sqlite_data.py first.")
        return
    
    # Use the most recent export
    export_file = sorted(export_files)[-1]
    print(f"📁 Using export file: {export_file}")
    
    # Import data
    success = import_data_to_supabase(export_file)
    
    if success:
        # Verify import
        verify_import()
        print("\n✅ Migration completed successfully!")
        print("🌐 Your app can now use Supabase in cloud deployment")
    else:
        print("\n❌ Migration failed. Check the errors above.")

if __name__ == "__main__":
    main()