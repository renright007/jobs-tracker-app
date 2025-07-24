"""
LangChain AI Agent for Job Application Assistant

This module implements a sophisticated AI agent using LangChain that can:
- Analyze job postings
- Optimize resumes
- Generate cover letters
- Research companies
- Provide career guidance
"""

import streamlit as st
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

# LangSmith imports
try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # Create a no-op decorator if LangSmith is not available
    def traceable(func=None, **kwargs):
        if func is None:
            return lambda f: f
        return func

from agent_tools import get_available_tools
from utils import get_db_connection


class JobApplicationAgent:
    """
    Advanced AI agent for job application assistance using LangChain.
    """
    
    def __init__(self, openai_client=None, user_id: Optional[int] = None):
        """Initialize the job application agent."""
        self.user_id = user_id
        self.openai_client = openai_client
        self.agent_executor = None
        self.memory = None
        self._setup_agent()
    
    def _setup_agent(self):
        """Set up the LangChain agent with tools and memory."""
        try:
            # Configure LangSmith tracing if available
            if LANGSMITH_AVAILABLE:
                self._configure_langsmith()
            
            # Initialize the language model
            llm = ChatOpenAI(
                model="gpt-4",
                temperature=0.7,
                openai_api_key=st.secrets.get("OPENAI_API_KEY") if hasattr(st, 'secrets') else None
            )
            
            # Set up memory for conversation history
            self.memory = StreamlitChatMessageHistory(key="chat_messages")
            
            # Create system prompt with job application context
            system_prompt = self._create_system_prompt()
            
            # Create the prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Get user-specific tools
            tools = get_available_tools(user_id=self.user_id)
            
            # Create the agent
            agent = create_tool_calling_agent(
                llm=llm,
                tools=tools,
                prompt=prompt
            )
            
            # Create agent executor
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3
            )
            
        except Exception as e:
            st.error(f"Error setting up AI agent: {str(e)}")
            self.agent_executor = None
    
    def _configure_langsmith(self):
        """Configure LangSmith tracing environment."""
        try:
            # Set LangSmith environment variables
            if hasattr(st, 'secrets') and st.secrets:
                os.environ['LANGSMITH_API_KEY'] = st.secrets.get('LANGSMITH_API_KEY', '')
                os.environ['LANGSMITH_TRACING'] = st.secrets.get('LANGSMITH_TRACING', 'true')
                os.environ['LANGSMITH_PROJECT'] = st.secrets.get('LANGSMITH_PROJECT', 'my_recruiter_agent')
            else:
                # Fallback to existing environment variables
                os.environ['LANGSMITH_TRACING'] = os.getenv('LANGSMITH_TRACING', 'true')
                os.environ['LANGSMITH_PROJECT'] = os.getenv('LANGSMITH_PROJECT', 'my_recruiter_agent')
            
            # Set additional metadata
            if self.user_id:
                os.environ['LANGSMITH_TAGS'] = f"user_id:{self.user_id}"
                
        except Exception as e:
            st.warning(f"LangSmith configuration warning: {str(e)}")
    
    def get_tracing_status(self) -> Dict[str, Any]:
        """Get current LangSmith tracing status."""
        return {
            'langsmith_available': LANGSMITH_AVAILABLE,
            'tracing_enabled': os.getenv('LANGSMITH_TRACING', '').lower() == 'true',
            'project_name': os.getenv('LANGSMITH_PROJECT', ''),
            'api_key_configured': bool(os.getenv('LANGSMITH_API_KEY', ''))
        }
    
    def _create_system_prompt(self) -> str:
        """Create a comprehensive system prompt for the job application agent."""
        
        # Load user preferences
        cover_letter_prefs = self._load_cover_letter_preferences()
        system_instructions = self._load_system_instructions()
        
        system_prompt = f"""
You are an advanced AI job application assistant for Robert Enright. You have access to specialized tools to help with all aspects of job applications.

## Your Role & Capabilities

You are a sophisticated career advisor and job application specialist with these abilities:

1. **Job Analysis**: Analyze job postings to extract key requirements, skills, and insights
2. **Resume Optimization**: Provide specific suggestions to optimize resumes for job matches
3. **Cover Letter Generation**: Create personalized cover letters based on user preferences
4. **Company Research**: Research companies to provide relevant insights for applications
5. **Job Matching**: Analyze how well user qualifications match specific positions
6. **Career Guidance**: Provide strategic advice on job applications and career development

## Available Tools

You have access to these specialized tools:
- `job_analyzer`: Analyze specific jobs from the database
- `resume_optimizer`: Optimize resume content for job descriptions  
- `cover_letter_generator`: Generate personalized cover letters
- `company_researcher`: Research companies using web search
- `job_matcher`: Analyze job-candidate compatibility

## User Preferences

{cover_letter_prefs}

## System Instructions

{system_instructions}

## Interaction Guidelines

1. **Be Proactive**: Suggest using relevant tools to provide comprehensive assistance
2. **Be Specific**: Always reference specific job IDs, company names, and concrete details
3. **Be Personal**: Use Robert's name and tailor advice to his background and preferences
4. **Be Strategic**: Think about the entire job application process, not just individual tasks
5. **Be Efficient**: Use tools in logical sequences to provide complete solutions

## Communication Style

- Professional but conversational
- Direct and actionable advice
- Use bullet points and clear formatting
- Provide step-by-step guidance when appropriate
- Always explain your reasoning

## Common Workflows

**For "Help me apply to this job":**
1. Use job_analyzer to understand the role
2. Use job_matcher to assess compatibility  
3. Use resume_optimizer for tailoring suggestions
4. Use company_researcher for insights
5. Use cover_letter_generator for personalized letter

**For "Research this company":**
1. Use company_researcher for comprehensive research
2. Provide strategic insights for application approach

**For "Optimize my resume":**
1. Use resume_optimizer with specific job descriptions
2. Provide concrete, actionable suggestions

Remember: You're not just answering questions - you're helping Robert succeed in his job search through strategic, comprehensive assistance.
        """
        
        return system_prompt.strip()
    
    def _load_cover_letter_preferences(self) -> str:
        """Load cover letter preferences from file."""
        try:
            with open('robs_cover_letter_preferences.md', 'r') as f:
                return f.read()
        except FileNotFoundError:
            return "Cover letter preferences not found."
    
    def _load_system_instructions(self) -> str:
        """Load system instructions from file."""
        try:
            with open('system_instructions.md', 'r') as f:
                return f.read()
        except FileNotFoundError:
            return "System instructions not found."
    
    @traceable(name="job_agent_chat", metadata={"agent_type": "job_application_assistant"})
    def chat(self, message: str) -> str:
        """Process a chat message and return the agent's response."""
        if not self.agent_executor:
            return "Sorry, the AI agent is not properly initialized. Please check your API keys and try again."
        
        try:
            # Add user context if available
            if self.user_id:
                context = self._get_user_context()
                if context:
                    message = f"{message}\n\nUser Context: {context}"
            
            # Process the message through the agent
            response = self.agent_executor.invoke({
                "input": message,
                "chat_history": self.memory.messages
            })
            
            return response["output"]
            
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try rephrasing your request or check if all required information is available."
    
    @traceable(name="get_user_context")
    def _get_user_context(self) -> str:
        """Get relevant user context from the database."""
        try:
            conn = get_db_connection()
            
            # Get user's recent jobs
            jobs_df = pd.read_sql_query(
                "SELECT id, company_name, job_title, status FROM jobs WHERE user_id = ? ORDER BY date_added DESC LIMIT 5",
                conn, params=(self.user_id,)
            )
            
            # Get user's documents
            docs_df = pd.read_sql_query(
                "SELECT document_name, document_type FROM documents WHERE user_id = ? ORDER BY upload_date DESC LIMIT 3",
                conn, params=(self.user_id,)
            )
            
            conn.close()
            
            context_parts = []
            
            if not jobs_df.empty:
                jobs_list = []
                for _, job in jobs_df.iterrows():
                    jobs_list.append(f"Job ID {job['id']}: {job['company_name']} - {job['job_title']} ({job['status']})")
                context_parts.append(f"Recent Jobs: {'; '.join(jobs_list)}")
            
            if not docs_df.empty:
                docs_list = []
                for _, doc in docs_df.iterrows():
                    docs_list.append(f"{doc['document_name']} ({doc['document_type']})")
                context_parts.append(f"Available Documents: {'; '.join(docs_list)}")
            
            return " | ".join(context_parts) if context_parts else ""
            
        except Exception as e:
            return f"Error getting user context: {str(e)}"
    
    def get_available_jobs(self) -> pd.DataFrame:
        """Get list of available jobs for the user."""
        try:
            conn = get_db_connection()
            jobs_df = pd.read_sql_query(
                "SELECT id, company_name, job_title, status, date_added FROM jobs WHERE user_id = ? ORDER BY date_added DESC",
                conn, params=(self.user_id,)
            )
            conn.close()
            return jobs_df
        except Exception as e:
            st.error(f"Error getting jobs: {str(e)}")
            return pd.DataFrame()
    
    def suggest_next_actions(self) -> List[str]:
        """Suggest next actions based on user's current job search status."""
        suggestions = []
        
        try:
            jobs_df = self.get_available_jobs()
            
            if jobs_df.empty:
                suggestions.extend([
                    "🎯 Add some job postings to get started",
                    "📄 Upload your resume for optimization",
                    "🎯 Set your career goals in the User Portal"
                ])
            else:
                # Analyze job statuses
                not_applied = len(jobs_df[jobs_df['status'] != 'Applied'])
                applied = len(jobs_df[jobs_df['status'] == 'Applied'])
                
                if not_applied > 0:
                    suggestions.append(f"📝 You have {not_applied} jobs you haven't applied to yet")
                    suggestions.append("🔍 Try: 'Help me apply to job ID [X]' for step-by-step guidance")
                
                if applied > 0:
                    suggestions.append(f"✅ You've applied to {applied} jobs - great progress!")
                
                # General suggestions
                suggestions.extend([
                    "🏢 Research companies: 'Research [Company Name]'",
                    "📄 Optimize resume: 'Help me optimize my resume for job ID [X]'",
                    "💼 Get job match analysis: 'How well do I match job ID [X]?'"
                ])
        
        except Exception as e:
            suggestions.append(f"Error getting suggestions: {str(e)}")
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def clear_memory(self):
        """Clear the conversation memory."""
        if self.memory:
            self.memory.clear()


# Helper functions for Streamlit integration
def initialize_agent(user_id: Optional[int] = None) -> JobApplicationAgent:
    """Initialize the job application agent."""
    return JobApplicationAgent(user_id=user_id)


def get_agent_suggestions(agent: JobApplicationAgent) -> List[str]:
    """Get suggested actions from the agent."""
    return agent.suggest_next_actions()


# Predefined prompt templates for common tasks
COMMON_PROMPTS = {
    "analyze_job": "Please analyze job ID {job_id} and tell me what I should know about this position.",
    "help_apply": "Help me apply to job ID {job_id}. I want a complete application strategy including resume optimization, cover letter, and company research.",
    "research_company": "Research {company_name} and provide insights that would help me with my job application.",
    "optimize_resume": "Help me optimize my resume for job ID {job_id}.",
    "job_match": "How well do I match job ID {job_id}? Please provide a detailed compatibility analysis.",
    "cover_letter": "Generate a cover letter for job ID {job_id} following my preferences.",
    "interview_prep": "Help me prepare for an interview at {company_name} for the {job_title} position.",
    "career_advice": "Based on my current job applications, what career advice do you have for me?"
}


def get_prompt_template(template_key: str, **kwargs) -> str:
    """Get a formatted prompt template."""
    if template_key in COMMON_PROMPTS:
        return COMMON_PROMPTS[template_key].format(**kwargs)
    return ""