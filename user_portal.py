import streamlit as st
import pandas as pd
from datetime import datetime
from PyPDF2 import PdfReader
from docx import Document
from utils import get_db_connection, save_uploaded_file, init_db, ensure_directories
from streamlit_shadcn_ui import tabs

# Initialize database and ensure directories exist
init_db()
ensure_directories()

# Initialize session state
if 'documents' not in st.session_state:
    st.session_state.documents = pd.DataFrame(columns=[
        'document_name', 'document_type', 'upload_date', 'file_path'
    ])

if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        'selected_resume': None,
        'career_goals': "",
        'created_date': None,
        'last_updated_date': None
    }

if 'career_goals' not in st.session_state:
    st.session_state.career_goals = pd.DataFrame(columns=[
        'goals', 'submission_date'
    ])

# Add custom CSS for the container
st.markdown("""
    <style>
    .document-container {
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1.5rem;
        background-color: white;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
    }
    </style>
""", unsafe_allow_html=True)

def show_user_portal():
    """Show the User Portal with shadcn tabs."""
    # Authentication is now handled at the main app level
    user_id = st.session_state.get('user_id')
    
    # Create shadcn tabs with default tab
    selected_tab = tabs(["User Profile", "Document Portal"], default_value="User Profile")
    
    if selected_tab == "User Profile":
        # Load documents from database (filtered by user)
        conn = get_db_connection()
        documents_df = pd.read_sql_query("SELECT * FROM documents WHERE document_type = 'Resume' AND user_id = ?", conn, params=(user_id,))
        
        # Load user profile if it exists (filtered by user)
        profile_df = pd.read_sql_query("SELECT * FROM user_profile WHERE user_id = ? ORDER BY id DESC LIMIT 1", conn, params=(user_id,))
        conn.close()
        
        # Initialize variables with default values
        selected_resume = None
        
        # Load existing profile data if it exists
        if not profile_df.empty:
            selected_resume = profile_df['selected_resume'].iloc[0]
        
        # Resume Selection
        if not documents_df.empty:
            resume_options = documents_df['document_name'].tolist()
            default_index = resume_options.index(selected_resume) if selected_resume in resume_options else 0
            selected_resume = st.selectbox(
                "Select Your Resume",
                resume_options,
                index=default_index
            )
            
            # Get the selected resume's file path
            selected_resume_path = documents_df[documents_df['document_name'] == selected_resume]['file_path'].iloc[0]
            
            # Display resume content in expandable section
            with st.expander("View Resume Content"):
                file_extension = selected_resume_path.split('.')[-1].lower()
                
                try:
                    if file_extension == 'pdf':
                        # Extract text from PDF
                        reader = PdfReader(selected_resume_path)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                    elif file_extension == 'docx':
                        # Extract text from DOCX
                        doc = Document(selected_resume_path)
                        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                    elif file_extension == 'txt':
                        # Read text file
                        with open(selected_resume_path, 'r', encoding='utf-8') as file:
                            text = file.read()
                    else:
                        st.error(f"Unsupported file type: {file_extension}")
                        return
                    
                    # Display the extracted text
                    st.text_area("Resume Content", text, height=300)
                    
                    # Add download button
                    st.download_button(
                        label="Download Original File",
                        data=open(selected_resume_path, 'rb').read(),
                        file_name=selected_resume_path.split('/')[-1],
                        mime=f"application/{file_extension}"
                    )
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
        else:
            st.warning("No resumes found. Please upload a resume in the Document Portal.")
        
        # Save button
        if st.button("Save Profile"):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            conn = get_db_connection()
            c = conn.cursor()
            
            if not profile_df.empty:
                # Update existing profile (only for current user)
                c.execute('''UPDATE user_profile 
                            SET selected_resume = ?, 
                                last_updated_date = ?
                            WHERE id = ? AND user_id = ?''',
                         (selected_resume, current_time, profile_df['id'].iloc[0], user_id))
            else:
                # Create new profile
                c.execute('''INSERT INTO user_profile 
                            (selected_resume, created_date, last_updated_date, user_id)
                            VALUES (?, ?, ?, ?)''',
                         (selected_resume, current_time, current_time, user_id))
            
            conn.commit()
            conn.close()
            
            st.success("Profile saved successfully!")
            st.rerun()
        
        # Career Goals Section
        st.markdown("---")
        st.subheader("What are you looking for?")
        
        # Load career goals from database (filtered by user)
        conn = get_db_connection()
        goals_df = pd.read_sql_query("SELECT * FROM career_goals WHERE user_id = ? ORDER BY submission_date DESC LIMIT 1", conn, params=(user_id,))
        conn.close()
        
        # Initialize career goals
        career_goals = ""
        if not goals_df.empty:
            career_goals = goals_df['goals'].iloc[0]
        
        # Career Goals input
        career_goals = st.text_area(
            "Describe your career goals, preferred roles, industries, and what you're looking for in your next position...",
            value=career_goals,
            height=300
        )
        
        # Save Career Goals button
        if st.button("Save Career Goals"):
            if career_goals.strip():
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                conn = get_db_connection()
                c = conn.cursor()
                
                # Insert new career goals
                c.execute('''INSERT INTO career_goals 
                            (goals, submission_date, user_id)
                            VALUES (?, ?, ?)''',
                         (career_goals, current_time, user_id))
                
                conn.commit()
                conn.close()
                
                st.success("Career goals saved successfully!")
                st.rerun()
            else:
                st.warning("Please enter your career goals before saving.")
        
        # Display previous career goals submissions (filtered by user)
        conn = get_db_connection()
        all_goals_df = pd.read_sql_query("SELECT * FROM career_goals WHERE user_id = ? ORDER BY submission_date DESC LIMIT 2", conn, params=(user_id,))
        conn.close()
        
        if not all_goals_df.empty and len(all_goals_df) > 1:
            st.subheader("Previous Submission")
            with st.expander(f"Submission from {all_goals_df.iloc[1]['submission_date']}"):
                st.write(all_goals_df.iloc[1]['goals'])
    
    elif selected_tab == "Document Portal":
        # Upload new document
        st.subheader("Upload New Document")
        uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'docx', 'txt'])
        if uploaded_file is not None:
            document_name = st.text_input("Document Name")
            document_type = st.selectbox("Document Type", ["Resume", "Cover Letter", "Other"])
            
            if st.button("Save Document"):
                file_path = save_uploaded_file(uploaded_file, document_name, document_type, user_id)
                st.success("Document uploaded successfully!")
        
        # Display existing documents (filtered by user)
        st.subheader("Your Documents")
        conn = get_db_connection()
        documents_df = pd.read_sql_query("SELECT * FROM documents WHERE user_id = ?", conn, params=(user_id,))
        conn.close()
        
        if not documents_df.empty:
            st.dataframe(documents_df)
        else:
            st.info("No documents uploaded yet.")