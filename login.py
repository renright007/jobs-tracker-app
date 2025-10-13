import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import os
from streamlit_option_menu import option_menu
from utils import get_menu_style, get_db_connection
from user_portal import show_user_portal
from jobs_portal import show_jobs_portal
from dashboard_utils import show_dashboard
import pandas as pd
from streamlit_shadcn_ui import tabs
import time

def init_auth_db():
    """Initialize the authentication database."""
    # Use the unified database initialization
    from database_utils import init_db
    return init_db()

def save_users_to_database(users_df):
    """Save changes from the DataFrame back to the database."""
    conn = get_db_connection()
    try:
        # First, get the current data to compare
        current_data = pd.read_sql_query("SELECT id FROM users", conn)
        current_ids = set(current_data['id'])
        
        # Get the IDs in the edited DataFrame
        edited_ids = set(users_df['id'].dropna())
        
        # Find IDs to delete (in current but not in edited)
        ids_to_delete = current_ids - edited_ids
        
        # Delete removed rows
        if ids_to_delete:
            placeholders = ','.join('?' * len(ids_to_delete))
            conn.execute(f'DELETE FROM users WHERE id IN ({placeholders})', tuple(ids_to_delete))
        
        # Update or insert remaining rows
        for _, row in users_df.iterrows():
            if pd.notna(row['id']):
                # Update existing row
                conn.execute('''UPDATE users 
                              SET username = ?, 
                                  password_hash = ?, 
                                  email = ?, 
                                  created_at = ?
                              WHERE id = ?''',
                           (row['username'], row['password_hash'], 
                            row['email'], row['created_at'],
                            row['id']))
            else:
                # Insert new row
                conn.execute('''INSERT INTO users 
                              (username, password_hash, email, created_at)
                              VALUES (?, ?, ?, ?)''',
                           (row['username'], row['password_hash'], 
                            row['email'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        return True, "Changes saved successfully!"
    except Exception as e:
        conn.rollback()
        return False, f"Error saving changes: {str(e)}"
    finally:
        conn.close()

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_email_exists(email):
    """Check if an email exists in the database."""
    from database_utils import use_supabase
    
    if use_supabase():
        from supabase_utils import get_supabase_client
        try:
            supabase = get_supabase_client()
            result = supabase.table('users').select('id').eq('email', email).execute()
            return len(result.data) > 0
        except Exception as e:
            st.error(f"Error checking email: {str(e)}")
            return False
    else:
        # SQLite fallback
        conn = get_db_connection()
        if not conn:
            return False
        c = conn.cursor()
        try:
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            result = c.fetchone()
            return result is not None
        finally:
            conn.close()

def register_user(username, password, email=None):
    """Register a new user using unified database system."""
    from database_utils import use_supabase
    
    # Validate input
    if not username or not password:
        st.error("Username and password are required.")
        return False, "Username and password are required."
    
    # Hash the password
    password_hash = hash_password(password)
    
    if use_supabase():
        from supabase_utils import get_supabase_client
        try:
            supabase = get_supabase_client()
            
            # Check if username already exists
            username_check = supabase.table('users').select('id').eq('username', username).execute()
            if username_check.data:
                st.error("Username already exists.")
                return False, "Username already exists. Please choose a different username."
            
            # Check if email already exists (if provided)
            if email:
                email_check = supabase.table('users').select('id').eq('email', email).execute()
                if email_check.data:
                    st.error("Email already registered.")
                    return False, "Email already registered. Please use a different email."
            
            # Insert the new user
            user_data = {
                'username': username,
                'password_hash': password_hash,
                'email': email,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            result = supabase.table('users').insert(user_data).execute()
            st.success("User registered successfully!")
            return True, "Registration successful! You can now login."
            
        except Exception as e:
            st.error(f"Error during registration: {str(e)}")
            return False, f"Error during registration: {str(e)}"
    else:
        # SQLite fallback
        os.makedirs('data', exist_ok=True)
        conn = get_db_connection()
        if not conn:
            return False, "Database connection failed"
        c = conn.cursor()
        
        try:
            # Check if username already exists
            c.execute('SELECT id FROM users WHERE username = ?', (username,))
            if c.fetchone():
                st.error("Username already exists.")
                return False, "Username already exists. Please choose a different username."
            
            # Check if email already exists (if provided)
            if email:
                c.execute('SELECT id FROM users WHERE email = ?', (email,))
                if c.fetchone():
                    st.error("Email already registered.")
                    return False, "Email already registered. Please use a different email."
            
            # Insert the new user
            c.execute('''INSERT INTO users (username, password_hash, email, created_at)
                         VALUES (?, ?, ?, ?)''', 
                         (username, password_hash, email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            st.success("User registered successfully!")
            return True, "Registration successful! You can now login."
        except sqlite3.IntegrityError as e:
            st.error(f"Database error: {str(e)}")
            return False, f"Database error: {str(e)}"
        except Exception as e:
            st.error(f"Error during registration: {str(e)}")
            return False, f"Error during registration: {str(e)}"
        finally:
            conn.close()

def verify_user(username, password):
    """Verify user credentials and return detailed status using unified database system."""
    from database_utils import use_supabase
    
    if use_supabase():
        from supabase_utils import get_supabase_client
        try:
            supabase = get_supabase_client()
            
            # First check if username exists
            result = supabase.table('users').select('id, password_hash, email').eq('username', username).execute()
            
            if not result.data:
                return False, "username_not_found", None
            
            user_data = result.data[0]
            user_id = user_data['id']
            stored_hash = user_data['password_hash']
            email = user_data['email']
            
            password_hash = hash_password(password)
            
            if password_hash == stored_hash:
                return True, "success", user_id
            else:
                return False, "wrong_password", None
                
        except Exception as e:
            st.error(f"Error during verification: {str(e)}")
            return False, "error", None
    else:
        # SQLite fallback
        conn = get_db_connection()
        if not conn:
            return False, "error", None
        c = conn.cursor()
        
        try:
            # First check if username exists
            c.execute('SELECT id, password_hash, email FROM users WHERE username = ?', (username,))
            result = c.fetchone()
            
            if result is None:
                return False, "username_not_found", None
            
            user_id, stored_hash, email = result
            password_hash = hash_password(password)
            
            if password_hash == stored_hash:
                return True, "success", user_id
            else:
                return False, "wrong_password", None
                
        except Exception as e:
            st.error(f"Error during verification: {str(e)}")
            return False, "error", None
        finally:
            conn.close()

def show_main_menu():
    """Display the main menu after successful login."""
    # Define menu options
    menu_options = {
        "User Portal": show_user_portal,
        "Jobs Portal": show_jobs_portal,
        "Dashboard": show_dashboard
    }
    
    # Create menu with icons
    with st.sidebar:
        selected_page = option_menu(
            menu_title=None,
            options=list(menu_options.keys()),
            icons=['person', 'database', 'bar-chart'],
            default_index=0,
            styles=get_menu_style()
        )
    
    # Show selected page
    menu_options[selected_page]()

def get_existing_users():
    """Get list of existing users from the database using unified database system."""
    from database_utils import use_supabase
    
    if use_supabase():
        from supabase_utils import get_supabase_client
        try:
            supabase = get_supabase_client()
            result = supabase.table('users').select('id, username, email, created_at').order('created_at', desc=True).execute()
            
            if result.data:
                # Convert to DataFrame
                df = pd.DataFrame(result.data)
                df.columns = ['id', 'Username', 'Email', 'Registration Date']
                df['Registration Date'] = pd.to_datetime(df['Registration Date']).dt.strftime('%Y-%m-%d %H:%M:%S')
                return df
            else:
                return pd.DataFrame(columns=['id', 'Username', 'Email', 'Registration Date'])
        except Exception as e:
            st.error(f"Error getting users: {str(e)}")
            return pd.DataFrame(columns=['id', 'Username', 'Email', 'Registration Date'])
    else:
        # SQLite fallback
        conn = get_db_connection()
        if not conn:
            return pd.DataFrame(columns=['id', 'Username', 'Email', 'Registration Date'])
        c = conn.cursor()
        
        try:
            c.execute('SELECT id, username, email, created_at FROM users ORDER BY created_at DESC')
            users = c.fetchall()
            # Convert to DataFrame
            df = pd.DataFrame(users, columns=['id', 'Username', 'Email', 'Registration Date'])
            df['Registration Date'] = pd.to_datetime(df['Registration Date']).dt.strftime('%Y-%m-%d %H:%M:%S')
            return df
        finally:
            conn.close()

def show_login_page():
    """Display the login page."""
    st.title("Welcome to JobHopper")
    
    # Initialize session state for authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    # Create tabs using streamlit_shadcn_ui
    tab_options = ["Login", "Register"]
    selected_tab = tabs(options=tab_options, default_value="Login")
    
    if selected_tab == "Login":
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                success, status, user_id = verify_user(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_id = user_id
                    st.success("Login successful!")
                    st.rerun()
                else:
                    if status == "wrong_password":
                        st.error("Incorrect password. Please try again.")
                    elif status == "username_not_found":
                        st.error("Username not found. Please register first.")
                    else:
                        st.error("An error occurred during login. Please try again.")
    
    elif selected_tab == "Register":
        st.subheader("Register")
        with st.form("register_form"):
            new_username = st.text_input("Choose a username")
            new_password = st.text_input("Choose a password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            email = st.text_input("Email (optional)")
            register = st.form_submit_button("Register", use_container_width=True)
            
            if register:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    success, message = register_user(new_username, new_password, email)
                    if success:
                        st.success("🎉 Registration Successful! You can now login with your new account.🎉")
                        #time.sleep(2)
                        #st.rerun()  # Refresh the page after successful registration
                    else:
                        st.error(message)

def logout():
    """Logout the current user."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.rerun()

def show_logout_button():
    """Display the logout button in the sidebar."""
    if st.session_state.authenticated:
        with st.sidebar:
            st.write(f"Logged in as: {st.session_state.username}")
            if st.button("Logout"):
                logout() 