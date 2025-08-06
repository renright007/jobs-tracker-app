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

def import_data_to_supabase(export_file):
    """Import data from SQLite export to Supabase with foreign key mapping."""
    
    if not os.path.exists(export_file):
        print(f"❌ Export file not found: {export_file}")
        return False
    
    # Load export data
    with open(export_file, 'r') as f:
        export_data = json.load(f)
    
    supabase = get_supabase_client()
    print("🚀 Importing data to Supabase...")
    
    # Track ID mappings for foreign keys
    id_mappings = {}
    
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
                
                # Clean records for PostgreSQL and handle foreign keys
                cleaned_batch = []
                for record in batch:
                    cleaned_record = {}
                    old_id = record.get('id')  # Store original ID for mapping
                    
                    for key, value in record.items():
                        # Skip SQLite auto-increment IDs - let PostgreSQL generate new ones
                        if key == 'id':
                            continue
                        
                        # Handle foreign key references
                        if key == 'user_id' and table_name != 'users':
                            # Map old user_id to new user_id
                            if value in id_mappings.get('users', {}):
                                cleaned_record[key] = id_mappings['users'][value]
                            else:
                                print(f"⚠️ Warning: user_id {value} not found in mapping")
                                cleaned_record[key] = value  # Keep original, might fail
                        else:
                            cleaned_record[key] = value
                    
                    cleaned_batch.append(cleaned_record)
                
                # Insert batch and track new IDs for users table
                if cleaned_batch:
                    result = supabase.table(table_name).insert(cleaned_batch).execute()
                    inserted_records = result.data
                    
                    # For users table, create ID mapping
                    if table_name == 'users':
                        if table_name not in id_mappings:
                            id_mappings[table_name] = {}
                        
                        # Map old SQLite IDs to new PostgreSQL IDs
                        for j, new_record in enumerate(inserted_records):
                            original_record = batch[i + j]
                            old_id = original_record['id']
                            new_id = new_record['id']
                            id_mappings[table_name][old_id] = new_id
                            print(f"    📝 ID mapping: {old_id} → {new_id}")
                    
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

def check_existing_data():
    """Check if tables already contain data before import."""
    supabase = get_supabase_client()
    
    print("🔍 Checking existing data in Supabase...")
    
    tables = ['users', 'jobs', 'documents', 'user_profile', 'career_goals']
    has_data = False
    
    for table in tables:
        try:
            result = supabase.table(table).select('id', count='exact').execute()
            count = result.count
            if count > 0:
                print(f"  ⚠️ {table}: {count} existing records")
                has_data = True
            else:
                print(f"  ✅ {table}: empty")
        except Exception as e:
            print(f"  ❓ {table}: {str(e)}")
    
    if has_data:
        print("\n⚠️ WARNING: Existing data found in Supabase tables!")
        print("   Import will ADD to existing data, not replace it.")
        print("   Consider cleaning tables first if you want fresh import.")
        
        response = input("\n❓ Continue with import anyway? (y/N): ").lower().strip()
        return response in ['y', 'yes']
    
    return True

def main():
    # Find the most recent export file
    export_files = [f for f in os.listdir('.') if f.startswith('sqlite_export_') and f.endswith('.json')]
    
    if not export_files:
        print("❌ No export files found. Run export_sqlite_data.py first.")
        return
    
    # Use the most recent export
    export_file = sorted(export_files)[-1]
    print(f"📁 Using export file: {export_file}")
    
    # Check for existing data
    if not check_existing_data():
        print("❌ Import cancelled by user.")
        return
    
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