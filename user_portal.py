import streamlit as st
import pandas as pd
from datetime import datetime
import os
from PyPDF2 import PdfReader
from docx import Document
from utils import get_db_connection, save_uploaded_file, init_db, ensure_directories
from database_utils import delete_document, save_documents_to_database, migrate_existing_data
from streamlit_shadcn_ui import tabs

# Initialize database and ensure directories exist
init_db()
ensure_directories()

# Run migration to ensure preferred_resume column exists
migrate_existing_data()

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
        
        # Simplified Preferred Resume Display
        st.markdown("### 🎯 Current Preferred Resume")
        
        # Get current preferred resume from database
        conn = get_db_connection()
        preferred_df = pd.read_sql_query(
            "SELECT document_name, upload_date FROM documents WHERE user_id = ? AND preferred_resume = 1 AND document_type = 'Resume'", 
            conn, params=(user_id,)
        )
        conn.close()
        
        if not preferred_df.empty:
            preferred_name = preferred_df['document_name'].iloc[0]
            preferred_date = preferred_df['upload_date'].iloc[0]
            st.success(f"✅ **{preferred_name}** (uploaded: {preferred_date})")
            st.info("💡 This resume will be used by default for all AI-powered features like cover letter generation and job matching.")
            
            # Get the full document data including file path
            conn = get_db_connection()
            full_doc_df = pd.read_sql_query(
                "SELECT file_path FROM documents WHERE user_id = ? AND preferred_resume = 1 AND document_type = 'Resume'", 
                conn, params=(user_id,)
            )
            conn.close()
            
            if not full_doc_df.empty and full_doc_df['file_path'].iloc[0]:
                selected_resume_path = full_doc_df['file_path'].iloc[0]
                
                # Display resume content in expandable section
                with st.expander("👁️ View Resume Content"):
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
                            text = None
                        
                        if text:
                            # Display the extracted text
                            st.text_area("Resume Content", text, height=300)
                            
                            # Add download button
                            if os.path.exists(selected_resume_path):
                                st.download_button(
                                    label="📥 Download Original File",
                                    data=open(selected_resume_path, 'rb').read(),
                                    file_name=selected_resume_path.split('/')[-1],
                                    mime=f"application/{file_extension}"
                                )
                            
                    except Exception as e:
                        st.error(f"Error processing file: {str(e)}")
            else:
                st.warning("File path not found for preferred resume")
        else:
            st.warning("⚠️ No preferred resume selected")
            st.info("📋 Go to the **Document Portal** tab to select your preferred resume by checking the box next to it.")
        
        st.markdown("---")
        st.caption("💡 **Tip:** To change your preferred resume, go to Document Portal → Manage Your Documents → Check the 'Preferred Resume' box")
        
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
        # Upload new document section
        st.subheader("📄 Upload New Document")
        uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'docx', 'txt'])
        if uploaded_file is not None:
            document_name = st.text_input("Document Name")
            document_type = st.selectbox("Document Type", ["Resume", "Cover Letter", "Other"])
            
            if st.button("Save Document"):
                file_path = save_uploaded_file(uploaded_file, document_name, document_type, user_id)
                st.success("Document uploaded successfully!")
                st.rerun()
        
        st.markdown("---")
        
        # Document management section
        st.subheader("📋 Manage Your Documents")
        st.info("💡 Check the 'Preferred Resume' box for the resume you want AI features to use by default. Only one can be selected.")
        
        # Load documents from database
        conn = get_db_connection()
        documents_df = pd.read_sql_query(
            "SELECT id, document_name, document_type, upload_date, preferred_resume FROM documents WHERE user_id = ? ORDER BY upload_date DESC", 
            conn, params=(user_id,)
        )
        conn.close()
        
        if not documents_df.empty:
            # Convert preferred_resume to boolean for display
            documents_df['preferred_resume'] = documents_df['preferred_resume'].astype(bool)
            
            # Create editable data editor like jobs table
            with st.form("documents_form"):
                st.write("**Edit your documents:**")
                
                # Configure column settings
                column_config = {
                    "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "document_name": st.column_config.TextColumn("Document Name", disabled=True, width="medium"),
                    "document_type": st.column_config.TextColumn("Type", disabled=True, width="small"),
                    "upload_date": st.column_config.TextColumn("Upload Date", disabled=True, width="medium"),
                    "preferred_resume": st.column_config.CheckboxColumn(
                        "Preferred Resume",
                        help="Check to use this resume for AI features",
                        width="small"
                    )
                }
                
                edited_documents_df = st.data_editor(
                    documents_df,
                    column_config=column_config,
                    hide_index=True,
                    use_container_width=True,
                    height=400,
                    key="documents_editor"
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.form_submit_button("💾 Save Changes", use_container_width=True):
                        success, message = save_documents_to_database(user_id, edited_documents_df)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                
                with col2:
                    if st.form_submit_button("🗑️ Delete Selected", use_container_width=True):
                        # Get selected rows for deletion (this would need additional logic)
                        st.info("Select documents and use individual delete buttons for now")
            
            # Download section
            st.markdown("---")
            st.subheader("📥 Download Documents")
            for _, row in documents_df.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    status_icon = "⭐" if row['preferred_resume'] else ""
                    st.write(f"{status_icon} **{row['document_name']}**")
                
                with col2:
                    st.write(row['document_type'])
                
                with col3:
                    # Get file path for download
                    conn = get_db_connection()
                    file_path_df = pd.read_sql_query(
                        "SELECT file_path FROM documents WHERE id = ?", 
                        conn, params=(row['id'],)
                    )
                    conn.close()
                    
                    if not file_path_df.empty and file_path_df['file_path'].iloc[0]:
                        file_path = file_path_df['file_path'].iloc[0]
                        if os.path.exists(file_path):
                            with open(file_path, 'rb') as file:
                                st.download_button(
                                    label="📥 Download",
                                    data=file.read(),
                                    file_name=file_path.split('/')[-1],
                                    key=f"download_{row['id']}"
                                )
                        else:
                            st.write("File not found")
                    else:
                        st.write("No file")
                
                with col4:
                    if st.button("🗑️ Delete", key=f"delete_{row['id']}", help="Delete this document"):
                        success, message = delete_document(user_id, row['id'])
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            st.info("📝 No documents uploaded yet. Upload your first document above!")