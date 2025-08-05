"""
Export all data from SQLite database to JSON files for Supabase migration.
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime

def export_sqlite_data():
    """Export all SQLite data to JSON files."""
    conn = sqlite3.connect('data/jobs.db')
    
    export_data = {
        'export_timestamp': datetime.now().isoformat(),
        'tables': {}
    }
    
    tables = ['users', 'jobs', 'documents', 'user_profile', 'career_goals']
    
    print("📤 Exporting SQLite data...")
    
    for table in tables:
        try:
            # Get data from table
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            
            # Convert to records (list of dicts) 
            records = df.to_dict('records')
            
            # Handle NaN values by converting to None
            for record in records:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
            
            export_data['tables'][table] = {
                'count': len(records),
                'data': records
            }
            
            print(f"✅ Exported {len(records)} records from {table}")
            
        except Exception as e:
            print(f"❌ Error exporting {table}: {e}")
            export_data['tables'][table] = {
                'count': 0,
                'data': [],
                'error': str(e)
            }
    
    conn.close()
    
    # Save to JSON file
    export_file = f"sqlite_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(export_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    print(f"\n📁 Data exported to: {export_file}")
    
    # Print summary
    print("\n📊 Export Summary:")
    for table, info in export_data['tables'].items():
        if 'error' in info:
            print(f"  ❌ {table}: {info['error']}")
        else:
            print(f"  ✅ {table}: {info['count']} records")
    
    return export_file, export_data

def preview_data():
    """Preview the current database contents."""
    conn = sqlite3.connect('data/jobs.db')
    
    print("🔍 Current Database Contents:")
    print("-" * 50)
    
    tables = ['users', 'jobs', 'documents', 'user_profile', 'career_goals']
    
    for table in tables:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count} records")
            
            # Show sample data
            if count > 0:
                df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 2", conn)
                print(f"  Sample columns: {list(df.columns)}")
                if len(df) > 0:
                    print(f"  Sample record: {dict(df.iloc[0])}")
                print()
        except Exception as e:
            print(f"❌ Error reading {table}: {e}")
    
    conn.close()

if __name__ == "__main__":
    # Preview current data
    preview_data()
    
    # Export data
    export_file, data = export_sqlite_data()
    
    print(f"\n🎯 Next step: Import this data to Supabase using import_to_supabase.py")