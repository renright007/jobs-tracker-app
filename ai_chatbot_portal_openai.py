import streamlit as st
from streamlit_shadcn_ui import tabs
from utils import init_openai_client

# OpenAI agent imports
try:
    from ai_agent_openai import OpenAIJobAgent, get_openai_prompt_template, OPENAI_COMMON_PROMPTS
    OPENAI_AGENT_AVAILABLE = True
except ImportError as e:
    st.error(f"OpenAI agent not available: {str(e)}")
    OPENAI_AGENT_AVAILABLE = False

def show_openai_chatbot():
    """Show the OpenAI-based AI Chat Bot with tabbed interface for Chat and Quick Actions."""
    st.title("🤖 AI Job Assistant (OpenAI)")
    
    # Check if OpenAI agent is available
    if not OPENAI_AGENT_AVAILABLE:
        st.error("OpenAI AI Agent is not available. Please check your installation and API keys.")
        st.info("Falling back to basic chat mode...")
        _show_basic_openai_chatbot()
        return
    
    # Check API key configuration
    client = init_openai_client()
    if not client:
        st.error("OpenAI API key not configured. Please set up your API key to use the AI Assistant.")
        return
    
    user_id = st.session_state.get('user_id')
    
    # Initialize the OpenAI agent
    if 'openai_job_agent' not in st.session_state:
        with st.spinner("Initializing OpenAI AI Assistant..."):
            try:
                st.session_state.openai_job_agent = OpenAIJobAgent(user_id=user_id)
                st.success("OpenAI Assistant initialized successfully!")
            except Exception as e:
                st.error(f"Failed to initialize OpenAI Assistant: {str(e)}")
                return
    
    agent = st.session_state.openai_job_agent
    
    # Display agent status
    st.success("🚀 **OpenAI Direct Integration Active** - Using function calling for enhanced capabilities")
    
    # Create tabs
    selected_tab = tabs(["Chat", "Quick Actions"], default_value="Chat")
    
    if selected_tab == "Chat":
        # Get available jobs for selection
        jobs_df = agent.get_available_jobs()
        
        if not jobs_df.empty:
            # Job selection dropdown
            job_options = jobs_df.apply(lambda x: f"{x['company_name']} - {x['job_title']} (ID: {x['id']})", axis=1).tolist()
            selected_job = st.selectbox("Select a job to discuss:", job_options, key="openai_chat_job_select")
            
            # Extract job ID from selection
            selected_job_id = int(selected_job.split("ID: ")[1].replace(")", ""))
            selected_job_data = jobs_df[jobs_df['id'] == selected_job_id].iloc[0]
            
            # Show selected job info
            with st.expander("📋 Selected Job Details", expanded=False):
                st.write(f"**Company:** {selected_job_data['company_name']}")
                st.write(f"**Position:** {selected_job_data['job_title']}")
                st.write(f"**Status:** {selected_job_data['status']}")
                if selected_job_data.get('location'):
                    st.write(f"**Location:** {selected_job_data['location']}")
                if selected_job_data.get('salary'):
                    st.write(f"**Salary:** {selected_job_data['salary']}")
            
            st.subheader("💬 Chat with Your OpenAI Assistant")
            
            # Display conversation history
            if agent.conversation_history:
                for message in agent.conversation_history:
                    if message["role"] == "user":
                        with st.chat_message("user"):
                            st.markdown(message["content"])
                    elif message["role"] == "assistant" and message.get("content"):
                        with st.chat_message("assistant"):
                            st.markdown(message["content"])
            
            # Chat input with job context
            if prompt := st.chat_input(f"Ask me about {selected_job_data['company_name']} - {selected_job_data['job_title']}!"):
                # Add job context to the prompt
                contextual_prompt = f"Regarding job ID {selected_job_id} ({selected_job_data['company_name']} - {selected_job_data['job_title']}): {prompt}"
                
                # Display user message
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Get agent response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = agent.chat(contextual_prompt)
                        st.markdown(response)
        else:
            st.info("No jobs found. Add some jobs in the Job Portal to get started!")
    
    elif selected_tab == "Quick Actions":
        # Get available jobs for selection
        jobs_df = agent.get_available_jobs()
        
        if not jobs_df.empty:
            # Job selection dropdown
            job_options = jobs_df.apply(lambda x: f"{x['company_name']} - {x['job_title']} (ID: {x['id']})", axis=1).tolist()
            selected_job = st.selectbox("Select a job for quick actions:", job_options, key="openai_actions_job_select")
            
            # Extract job ID from selection
            selected_job_id = int(selected_job.split("ID: ")[1].replace(")", ""))
            selected_job_data = jobs_df[jobs_df['id'] == selected_job_id].iloc[0]
            
            # Show selected job info
            st.info(f"**Selected:** {selected_job_data['company_name']} - {selected_job_data['job_title']}")
            
            st.subheader("🎯 Quick Actions")
            
            # Create columns for better layout
            input_text = ""
            response_text = ""
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 Analyze this job", key="openai_analyze_selected_btn"):
                    prompt = get_openai_prompt_template('analyze_job', job_id=selected_job_id)
                    with st.spinner("Analyzing job..."):
                        input_text = "Job Analysis:"
                        response_text = agent.chat(prompt)
                
                if st.button("🎯 Help me apply to this job", key="openai_apply_selected_btn"):
                    prompt = get_openai_prompt_template('help_apply', job_id=selected_job_id)
                    with st.spinner("Creating application strategy..."):
                        input_text = "Application Strategy:"
                        response_text = agent.chat(prompt)
                
                if st.button("📄 Tailor Resume", key="openai_tailor_resume_btn"):
                    with st.spinner("Tailoring your resume..."):
                        input_text, response_text = _tailor_resume_for_job(agent, selected_job_id, selected_job_data)
                
                if st.button("💡 Match my skills to this job", key="openai_skills_match_btn"):
                    prompt = f"Analyze how well my skills match job ID {selected_job_id} and suggest areas for improvement."
                    with st.spinner("Analyzing skill match..."):
                        input_text = "Skill Analysis:"
                        response_text = agent.chat(prompt)
            
            with col2:
                if st.button("🏢 Research this company", key="openai_research_selected_btn"):
                    company = selected_job_data['company_name']
                    prompt = get_openai_prompt_template('research_company', company_name=company)
                    with st.spinner("Researching company..."):
                        input_text = "Company Research:"
                        response_text = agent.chat(prompt)
                
                if st.button("📝 Generate cover letter", key="openai_cover_letter_btn"):
                    prompt = f"Generate a personalized cover letter for job ID {selected_job_id} at {selected_job_data['company_name']}."
                    with st.spinner("Writing cover letter..."):
                        input_text = "Cover Letter:"
                        response_text = agent.chat(prompt)
                
                if st.button("🔍 Suggest interview questions", key="openai_interview_questions_btn"):
                    prompt = f"What interview questions should I prepare for job ID {selected_job_id} at {selected_job_data['company_name']}?"
                    with st.spinner("Preparing questions..."):
                        input_text = "Interview Questions:"
                        response_text = agent.chat(prompt)

            # Show the response in a text area if an action was taken
            if input_text and response_text:
                st.text_area(input_text, response_text, height=500)
                
                # Add download button if this is a tailored resume
                if input_text == "Tailored Resume:" and 'tailored_resume' in st.session_state:
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        job_name = st.session_state.get('tailored_resume_job', 'Unknown_Job')
                        # Clean job name for filename
                        safe_job_name = "".join(c for c in job_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_job_name = safe_job_name.replace(' ', '_')
                        filename = f"Tailored_Resume_{safe_job_name}.txt"
                        
                        st.download_button(
                            label="📥 Download Tailored Resume",
                            data=st.session_state['tailored_resume'],
                            file_name=filename,
                            mime="text/plain",
                            key="download_tailored_resume"
                        )
                    
                    with col2:
                        if st.button("🗑️ Clear Resume", key="clear_tailored_resume"):
                            if 'tailored_resume' in st.session_state:
                                del st.session_state['tailored_resume']
                            if 'tailored_resume_job' in st.session_state:
                                del st.session_state['tailored_resume_job']
                            st.rerun()
        
        else:
            st.info("No jobs found. Add some jobs in the Job Portal to get started!")
    
    # Add a section for suggested next actions
    with st.sidebar:
        st.subheader("💡 Suggested Actions")
        suggestions = agent.suggest_next_actions()
        for suggestion in suggestions:
            st.write(f"• {suggestion}")
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation", key="openai_clear_conv"):
            agent.clear_memory()
            st.success("Conversation cleared!")
            st.rerun()


def _show_basic_openai_chatbot():
    """Fallback basic OpenAI chatbot when the agent is not available."""
    import pandas as pd
    from utils import get_db_connection, init_openai_client
    
    client = init_openai_client()
    
    if client is None:
        st.error("OpenAI client not available.")
        return
    
    user_id = st.session_state.get('user_id')
    
    # Load jobs for selection
    try:
        conn = get_db_connection()
        if user_id:
            jobs_df = pd.read_sql_query("SELECT id, company_name, job_title FROM jobs WHERE user_id = ?", conn, params=(user_id,))
        else:
            jobs_df = pd.read_sql_query("SELECT id, company_name, job_title FROM jobs", conn)
        conn.close()
    except Exception as e:
        st.error(f"Error loading jobs: {str(e)}")
        return
    
    if not jobs_df.empty:
        job_selection = st.selectbox(
            "Select a job to chat about",
            jobs_df.apply(lambda x: f"{x['company_name']} - {x['job_title']}", axis=1)
        )
        
        if 'openai_basic_messages' not in st.session_state:
            st.session_state.openai_basic_messages = []
            
        for message in st.session_state.openai_basic_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.openai_basic_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # Get job details for context
            try:
                selected_row = jobs_df[jobs_df.apply(lambda x: f"{x['company_name']} - {x['job_title']}", axis=1) == job_selection]
                if not selected_row.empty:
                    job_id = selected_row['id'].iloc[0]
                    conn = get_db_connection()
                    if user_id:
                        job_details = pd.read_sql_query("SELECT * FROM jobs WHERE id = ? AND user_id = ?", conn, params=(job_id, user_id))
                    else:
                        job_details = pd.read_sql_query("SELECT * FROM jobs WHERE id = ?", conn, params=(job_id,))
                    conn.close()
                    
                    if not job_details.empty:
                        # Simple system message
                        job_desc = job_details['job_description'].iloc[0][:500] if pd.notna(job_details['job_description'].iloc[0]) else "No description available"
                        system_message = f"You are a helpful job application assistant. Job: {job_details['company_name'].iloc[0]} - {job_details['job_title'].iloc[0]}. Description: {job_desc}..."
                        
                        # Generate response
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        
                        assistant_response = response.choices[0].message.content
                        st.session_state.openai_basic_messages.append({"role": "assistant", "content": assistant_response})
                        with st.chat_message("assistant"):
                            st.markdown(assistant_response)
                    else:
                        st.error("Job details not found.")
                else:
                    st.error("Selected job not found.")
            except Exception as e:
                st.error(f"Error processing request: {str(e)}")
    else:
        st.info("No jobs available. Add some jobs in the Job Portal first!")


# Alternative show function that can be called to test the OpenAI implementation
def show_ai_chatbot_openai():
    """Alternative entry point for the OpenAI chatbot implementation."""
    return show_openai_chatbot()


def _tailor_resume_for_job(agent, selected_job_id, selected_job_data):
    """
    Tailor a user's resume for a specific job using AI.
    
    Args:
        agent: The OpenAIJobAgent instance
        selected_job_id: ID of the selected job
        selected_job_data: Job data dictionary
    
    Returns:
        tuple: (input_text, response_text) for display
    """
    from database_utils import get_preferred_resume
    
    try:
        user_id = st.session_state.get('user_id')
        
        # Validate user is authenticated
        if not user_id:
            return ("Error:", "❌ User not authenticated. Please log in first.")
        
        # Get user's preferred resume
        resume_data = get_preferred_resume(user_id)
        
        if resume_data is None or resume_data.empty:
            return ("Error:", "❌ No preferred resume found. Please upload and set a preferred resume in the User Portal first.\n\nℹ️ To set a preferred resume:\n1. Go to User Portal\n2. Upload a resume\n3. Mark it as preferred (⭐)")
        
        resume_content = resume_data.iloc[0]['document_content'] if not resume_data.empty else ''
        if not resume_content or len(resume_content.strip()) < 50:
            return ("Error:", "❌ Resume content is too short or empty. Please re-upload your resume with proper content.")
        
        # Get job description and validate
        job_description = selected_job_data['job_description'] if 'job_description' in selected_job_data else ''
        if not job_description or len(job_description.strip()) < 100:
            return ("Error:", "❌ Job description is missing or too short. Please ensure the job has a complete, detailed description.\n\nℹ️ Try using the job scraper to get a full description.")
        
        # Validate resume and job description lengths for API limits
        total_length = len(resume_content) + len(job_description)
        if total_length > 50000:  # Conservative limit for API
            return ("Error:", "❌ Resume and job description are too long for processing. Please use a shorter resume or job description.")
        
        # Create the tailoring prompt
        tailor_prompt = _create_resume_tailor_prompt(resume_content, job_description)
        
        # Get AI response with error handling
        try:
            response = agent.chat(tailor_prompt)
        except Exception as api_error:
            if "rate limit" in str(api_error).lower():
                return ("Error:", "❌ API rate limit exceeded. Please wait a moment and try again.")
            elif "token" in str(api_error).lower():
                return ("Error:", "❌ Content too long for processing. Please use a shorter resume or job description.")
            else:
                return ("Error:", f"❌ AI processing failed: {str(api_error)}")
        
        # Validate response
        if not response or len(response.strip()) < 100:
            return ("Error:", "❌ AI generated an incomplete response. Please try again.")
        
        # Store the tailored resume in session state for download
        st.session_state['tailored_resume'] = response
        st.session_state['tailored_resume_job'] = f"{selected_job_data['company_name']} - {selected_job_data['job_title']}"
        
        return ("Tailored Resume:", response)
        
    except Exception as e:
        # Log the error for debugging (you can add logging here if needed)
        return ("Error:", f"❌ Unexpected error occurred: {str(e)}\n\nPlease try again or contact support if the problem persists.")


def _create_resume_tailor_prompt(resume, job_description):
    """
    Create the resume tailoring prompt with the user's specifications.
    
    Args:
        resume: The user's resume content
        job_description: The job description to tailor for
    
    Returns:
        str: The complete prompt for AI processing
    """
    return f"""You are a professional resume writer. I need you to tailor my resume for a specific job posting.

TASK: Rewrite my resume to be optimized for the job description below and make it ATS friendly.

REQUIREMENTS:
1. Incorporate relevant keywords and skills from the job description naturally
2. Highlight my most relevant achievements and experiences for this role
3. Maintain accuracy and honesty in all details
4. Use a clear, ATS-friendly format with no graphics, tables, or unusual formatting
5. Keep professional language and 1-2 pages in length

MY CURRENT RESUME:
{resume}

JOB DESCRIPTION TO TAILOR FOR:
{job_description}

OUTPUT: Please provide the complete tailored resume, formatted professionally and ready to use. Start immediately with the tailored resume content."""