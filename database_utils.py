import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
import os

# Import Supabase utilities
try:
    from supabase_utils import (
        supabase_get_user_jobs, supabase_get_user_documents, supabase_get_user_profile,
        supabase_get_user_career_goals, supabase_add_job, supabase_add_document,
        supabase_add_career_goals, supabase_save_documents_to_database,
        supabase_update_user_profile, supabase_delete_document,
        supabase_get_preferred_resume, supabase_get_user_stats
    )
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

def is_cloud_environment():
    """Detect if running in Streamlit Cloud environment."""
    # Check for Streamlit Cloud specific indicators
    if hasattr(st, 'secrets') and 'SUPABASE_URL' in st.secrets:
        return True
    # Check if we're in a cloud environment (no local file system access)
    return not os.path.exists('data/jobs.db')

def use_supabase():
    """Determine whether to use Supabase or SQLite."""
    return SUPABASE_AVAILABLE and is_cloud_environment()

def get_database_status():
    """Get current database backend status."""
    if use_supabase():
        return "🌐 Supabase (PostgreSQL) - Cloud Database"
    else:
        return "💾 SQLite - Local Database"

def get_db_connection():
    """Get SQLite database connection."""
    return sqlite3.connect('data/jobs.db')

def init_db():
    """Initialize the database with updated schema including user relationships."""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Create users table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL,
                      password_hash TEXT NOT NULL,
                      email TEXT UNIQUE,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Create jobs table with user relationship
        c.execute('''CREATE TABLE IF NOT EXISTS jobs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
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
                      applied_date TEXT,
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        # Create documents table with user relationship
        c.execute('''CREATE TABLE IF NOT EXISTS documents
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      document_name TEXT,
                      document_type TEXT,
                      upload_date TEXT,
                      file_path TEXT,
                      preferred_resume INTEGER DEFAULT 0,
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        # Create user_profile table with user relationship
        c.execute('''CREATE TABLE IF NOT EXISTS user_profile
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER UNIQUE,
                      selected_resume TEXT,
                      created_date TEXT,
                      last_updated_date TEXT,
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        # Create career_goals table with user relationship
        c.execute('''CREATE TABLE IF NOT EXISTS career_goals
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      goals TEXT,
                      submission_date TEXT,
                      FOREIGN KEY (user_id) REFERENCES users(id))''')
        
        conn.commit()
        # Database initialized silently - no need for user notification
    except Exception as e:
        st.error(f"Error initializing database: {str(e)}")
    finally:
        conn.close()

def get_user_jobs(user_id):
    """Get all jobs for a specific user."""
    if use_supabase():
        return supabase_get_user_jobs(user_id)
    else:
        conn = get_db_connection()
        try:
            query = '''SELECT * FROM jobs WHERE user_id = ? ORDER BY date_added DESC'''
            return pd.read_sql_query(query, conn, params=(user_id,))
        finally:
            conn.close()

def get_user_documents(user_id):
    """Get all documents for a specific user."""
    if use_supabase():
        return supabase_get_user_documents(user_id)
    else:
        conn = get_db_connection()
        try:
            query = '''SELECT * FROM documents WHERE user_id = ? ORDER BY upload_date DESC'''
            return pd.read_sql_query(query, conn, params=(user_id,))
        finally:
            conn.close()

def get_user_profile(user_id):
    """Get user profile for a specific user."""
    if use_supabase():
        return supabase_get_user_profile(user_id)
    else:
        conn = get_db_connection()
        try:
            query = '''SELECT * FROM user_profile WHERE user_id = ?'''
            return pd.read_sql_query(query, conn, params=(user_id,))
        finally:
            conn.close()

def get_user_career_goals(user_id):
    """Get career goals for a specific user."""
    if use_supabase():
        return supabase_get_user_career_goals(user_id)
    else:
        conn = get_db_connection()
        try:
            query = '''SELECT * FROM career_goals WHERE user_id = ? ORDER BY submission_date DESC'''
            return pd.read_sql_query(query, conn, params=(user_id,))
        finally:
            conn.close()

def add_job(user_id, job_data):
    """Add a new job for a user."""
    if use_supabase():
        return supabase_add_job(user_id, job_data)
    else:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            query = '''INSERT INTO jobs 
                      (user_id, company_name, job_title, job_description, application_url,
                       status, sentiment, notes, date_added, location, salary, applied_date)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            c.execute(query, (
                user_id,
                job_data.get('company_name'),
                job_data.get('job_title'),
                job_data.get('job_description'),
                job_data.get('application_url'),
                job_data.get('status'),
                job_data.get('sentiment'),
                job_data.get('notes'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                job_data.get('location'),
                job_data.get('salary'),
                job_data.get('applied_date')
            ))
            conn.commit()
            return True, "Job added successfully!"
        except Exception as e:
            conn.rollback()
            return False, f"Error adding job: {str(e)}"
        finally:
            conn.close()

def add_document(user_id, document_data):
    """Add a new document for a user."""
    if use_supabase():
        return supabase_add_document(user_id, document_data)
    else:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            query = '''INSERT INTO documents 
                      (user_id, document_name, document_type, upload_date, file_path)
                      VALUES (?, ?, ?, ?, ?)'''
            c.execute(query, (
                user_id,
                document_data.get('document_name'),
                document_data.get('document_type'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                document_data.get('file_path')
            ))
            conn.commit()
            return True, "Document added successfully!"
        except Exception as e:
            conn.rollback()
            return False, f"Error adding document: {str(e)}"
        finally:
            conn.close()

def update_user_profile(user_id, profile_data):
    """Update or create user profile."""
    if use_supabase():
        return supabase_update_user_profile(user_id, profile_data)
    else:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            # Check if profile exists
            c.execute('SELECT id FROM user_profile WHERE user_id = ?', (user_id,))
            profile = c.fetchone()
            
            if profile:
                # Update existing profile
                query = '''UPDATE user_profile 
                          SET selected_resume = ?, last_updated_date = ?
                          WHERE user_id = ?'''
                c.execute(query, (
                    profile_data.get('selected_resume'),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    user_id
                ))
            else:
                # Create new profile
                query = '''INSERT INTO user_profile 
                          (user_id, selected_resume, created_date, last_updated_date)
                          VALUES (?, ?, ?, ?)'''
                c.execute(query, (
                    user_id,
                    profile_data.get('selected_resume'),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
            
            conn.commit()
            return True, "Profile updated successfully!"
        except Exception as e:
            conn.rollback()
            return False, f"Error updating profile: {str(e)}"
        finally:
            conn.close()

def add_career_goals(user_id, goals):
    """Add new career goals for a user."""
    if use_supabase():
        return supabase_add_career_goals(user_id, goals)
    else:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            query = '''INSERT INTO career_goals 
                      (user_id, goals, submission_date)
                      VALUES (?, ?, ?)'''
            c.execute(query, (
                user_id,
                goals,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            return True, "Career goals added successfully!"
        except Exception as e:
            conn.rollback()
            return False, f"Error adding career goals: {str(e)}"
        finally:
            conn.close()

def save_documents_to_database(user_id, documents_df):
    """Save changes from the documents DataFrame back to the database with preferred resume validation."""
    if use_supabase():
        return supabase_save_documents_to_database(user_id, documents_df)
    else:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            
            # Business rule: Only one preferred resume per user
            preferred_count = len(documents_df[documents_df['preferred_resume'] == True])
            if preferred_count > 1:
                return False, "Only one document can be set as preferred resume per user"
            
            # Update each document
            for _, row in documents_df.iterrows():
                # Ensure the document belongs to the current user
                c.execute('SELECT user_id FROM documents WHERE id = ?', (row['id'],))
                result = c.fetchone()
                if not result or result[0] != user_id:
                    continue  # Skip documents that don't belong to this user
                
                # Convert boolean to integer for SQLite
                preferred_value = 1 if row['preferred_resume'] else 0
                
                # Update the document
                c.execute('''UPDATE documents 
                            SET preferred_resume = ?
                            WHERE id = ? AND user_id = ?''',
                         (preferred_value, row['id'], user_id))
            
            conn.commit()
            return True, "Documents updated successfully!"
        except Exception as e:
            conn.rollback()
            return False, f"Error saving documents: {str(e)}"
        finally:
            conn.close()

def get_preferred_resume(user_id):
    """Get the user's preferred resume document."""
    if use_supabase():
        return supabase_get_preferred_resume(user_id)
    else:
        conn = get_db_connection()
        try:
            query = '''SELECT * FROM documents 
                      WHERE user_id = ? AND preferred_resume = 1 AND document_type = 'Resume'
                      LIMIT 1'''
            result = pd.read_sql_query(query, conn, params=(user_id,))
            return result if not result.empty else None
        finally:
            conn.close()

def delete_document(user_id, document_id):
    """Delete a document for a user (both from database and file system)."""
    if use_supabase():
        return supabase_delete_document(user_id, document_id)
    else:
        import os
        conn = get_db_connection()
        try:
            c = conn.cursor()
            
            # First get the document info to ensure it belongs to the user and get file path
            c.execute('SELECT file_path FROM documents WHERE id = ? AND user_id = ?', (document_id, user_id))
            document = c.fetchone()
            
            if not document:
                return False, "Document not found or access denied"
            
            file_path = document[0]
            
            # Delete from database
            c.execute('DELETE FROM documents WHERE id = ? AND user_id = ?', (document_id, user_id))
            
            # Delete physical file if it exists
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    # Log the error but don't fail the database operation
                    print(f"Warning: Could not delete file {file_path}: {e}")
            
            conn.commit()
            return True, "Document deleted successfully!"
        except Exception as e:
            conn.rollback()
            return False, f"Error deleting document: {str(e)}"
        finally:
            conn.close()

def get_user_stats(user_id):
    """Get statistics for a user's job applications."""
    if use_supabase():
        return supabase_get_user_stats(user_id)
    else:
        conn = get_db_connection()
        try:
            # Get total applications
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM jobs WHERE user_id = ?', (user_id,))
            total_applications = c.fetchone()[0]
            
            # Get applications by status
            c.execute('''SELECT status, COUNT(*) as count 
                        FROM jobs 
                        WHERE user_id = ? 
                        GROUP BY status''', (user_id,))
            status_counts = dict(c.fetchall())
            
            # Get recent applications (last 7 days)
            c.execute('''SELECT COUNT(*) 
                        FROM jobs 
                        WHERE user_id = ? 
                        AND date_added >= date('now', '-7 days')''', (user_id,))
            recent_applications = c.fetchone()[0]
            
            return {
                'total_applications': total_applications,
                'status_counts': status_counts,
                'recent_applications': recent_applications
            }
        finally:
            conn.close()

def migrate_existing_data():
    """Migrate existing data to include user relationships and preferred_resume column."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        
        # Add user_id column to jobs if it doesn't exist
        try:
            c.execute('ALTER TABLE jobs ADD COLUMN user_id INTEGER REFERENCES users(id)')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add user_id column to documents if it doesn't exist
        try:
            c.execute('ALTER TABLE documents ADD COLUMN user_id INTEGER REFERENCES users(id)')
        except sqlite3.OperationalError:
            pass
        
        # Add preferred_resume column to documents if it doesn't exist
        try:
            c.execute('ALTER TABLE documents ADD COLUMN preferred_resume INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add user_id column to user_profile if it doesn't exist
        try:
            c.execute('ALTER TABLE user_profile ADD COLUMN user_id INTEGER REFERENCES users(id)')
        except sqlite3.OperationalError:
            pass
        
        # Add user_id column to career_goals if it doesn't exist
        try:
            c.execute('ALTER TABLE career_goals ADD COLUMN user_id INTEGER REFERENCES users(id)')
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        return True, "Migration completed successfully!"
    except Exception as e:
        conn.rollback()
        return False, f"Error during migration: {str(e)}"
    finally:
        conn.close() 