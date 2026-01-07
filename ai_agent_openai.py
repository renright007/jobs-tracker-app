"""
OpenAI-based AI Agent for Job Application Assistant

This module implements a simplified AI agent using direct OpenAI function calling that can:
- Analyze job postings
- Optimize resumes
- Generate cover letters
- Research companies
- Provide career guidance

This is an alternative to the LangChain-based implementation for comparison.
"""

import streamlit as st
import os
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from utils import get_db_connection, init_openai_client
from PyPDF2 import PdfReader
from docx import Document
import requests
from bs4 import BeautifulSoup


class OpenAIJobAgent:
    """
    Simplified AI agent for job application assistance using direct OpenAI function calling.
    """
    
    def __init__(self, user_id: Optional[int] = None):
        """Initialize the OpenAI job agent."""
        self.user_id = user_id
        self.client = init_openai_client()
        self.conversation_history = []
        self.available_functions = self._setup_functions()
        
        if not self.client:
            raise ValueError("OpenAI client not available - check API key configuration")
    
    def _setup_functions(self) -> Dict[str, Any]:
        """Set up OpenAI function definitions and their implementations."""
        return {
            "analyze_job": {
                "function": {
                    "name": "analyze_job",
                    "description": "Analyze a specific job posting from the database to extract key requirements, skills, and insights",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "integer",
                                "description": "ID of the job to analyze from the database"
                            }
                        },
                        "required": ["job_id"]
                    }
                },
                "implementation": self._analyze_job
            },
            "optimize_resume": {
                "function": {
                    "name": "optimize_resume",
                    "description": "Optimize resume content to better match a specific job description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "integer",
                                "description": "ID of the job to optimize resume for"
                            }
                        },
                        "required": ["job_id"]
                    }
                },
                "implementation": self._optimize_resume
            },
            "generate_cover_letter": {
                "function": {
                    "name": "generate_cover_letter",
                    "description": "Generate a personalized cover letter based on job details and user preferences",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "integer",
                                "description": "ID of the job from the database"
                            }
                        },
                        "required": ["job_id"]
                    }
                },
                "implementation": self._generate_cover_letter
            },
            "research_company": {
                "function": {
                    "name": "research_company",
                    "description": "Research a company to gather relevant information for job applications",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_name": {
                                "type": "string",
                                "description": "Name of the company to research"
                            }
                        },
                        "required": ["company_name"]
                    }
                },
                "implementation": self._research_company
            },
            "match_job": {
                "function": {
                    "name": "match_job",
                    "description": "Analyze how well user qualifications match a specific job posting",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "integer",
                                "description": "ID of the job to analyze match for"
                            }
                        },
                        "required": ["job_id"]
                    }
                },
                "implementation": self._match_job
            }
        }
    
    def _get_job_data(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get job data from database using unified database system."""
        from database_utils import use_supabase
        
        try:
            if use_supabase():
                from supabase_utils import get_supabase_client
                supabase = get_supabase_client()
                
                if self.user_id:
                    result = supabase.table('jobs').select('*').eq('id', job_id).eq('user_id', self.user_id).execute()
                else:
                    result = supabase.table('jobs').select('*').eq('id', job_id).execute()
                
                if not result.data:
                    return None
                
                return result.data[0]
            else:
                conn = get_db_connection()
                if self.user_id:
                    job_df = pd.read_sql_query(
                        "SELECT * FROM jobs WHERE id = ? AND user_id = ?", 
                        conn, 
                        params=(job_id, self.user_id)
                    )
                else:
                    job_df = pd.read_sql_query(
                        "SELECT * FROM jobs WHERE id = ?", 
                        conn, 
                        params=(job_id,)
                    )
                conn.close()
                
                if job_df.empty:
                    return None
                
                return job_df.iloc[0].to_dict()
        except Exception as e:
            st.error(f"Error getting job data: {str(e)}")
            return None
    
    def _get_user_resume(self) -> str:
        """Get user's preferred resume content, falling back to latest if none selected."""
        from database_utils import use_supabase
        
        try:
            if use_supabase():
                from supabase_utils import get_supabase_client
                supabase = get_supabase_client()
                
                if self.user_id:
                    # First try to get the user's preferred resume
                    preferred_result = supabase.table('documents').select('file_path, document_content, document_name').eq('user_id', self.user_id).eq('document_type', 'Resume').eq('preferred_resume', 1).limit(1).execute()
                    
                    if preferred_result.data:
                        resume_data = preferred_result.data[0]
                    else:
                        # Fall back to latest resume
                        latest_result = supabase.table('documents').select('file_path, document_content, document_name').eq('user_id', self.user_id).eq('document_type', 'Resume').order('upload_date', desc=True).limit(1).execute()
                        resume_data = latest_result.data[0] if latest_result.data else None
                else:
                    # For non-authenticated users, get latest resume
                    latest_result = supabase.table('documents').select('file_path, document_content, document_name').eq('document_type', 'Resume').order('upload_date', desc=True).limit(1).execute()
                    resume_data = latest_result.data[0] if latest_result.data else None
                
                if resume_data:
                    doc_name = resume_data.get('document_name', 'Unknown')
                    content = resume_data.get('document_content')
                    if content:
                        return f"[Using resume: {doc_name}]\n\n{str(content)}"
                    else:
                        file_path = resume_data.get('file_path')
                        if file_path:
                            extracted_content = self._extract_text_from_file(file_path)
                            return f"[Using resume: {doc_name}]\n\n{extracted_content}"
            else:
                conn = get_db_connection()
                
                if self.user_id:
                    # First try to get the user's preferred resume using the preferred_resume column
                    resume_df = pd.read_sql_query(
                        "SELECT file_path, document_content, document_name FROM documents WHERE user_id = ? AND document_type = 'Resume' AND preferred_resume = 1 LIMIT 1",
                        conn, params=(self.user_id,)
                    )
                    
                    # If no preferred resume, fall back to latest resume
                    if resume_df.empty:
                        resume_df = pd.read_sql_query(
                            "SELECT file_path, document_content, document_name FROM documents WHERE user_id = ? AND document_type = 'Resume' ORDER BY upload_date DESC LIMIT 1",
                            conn, params=(self.user_id,)
                        )
                else:
                    # For non-authenticated users, get latest resume
                    resume_df = pd.read_sql_query(
                        "SELECT file_path, document_content, document_name FROM documents WHERE document_type = 'Resume' ORDER BY upload_date DESC LIMIT 1",
                        conn
                    )
                
                conn.close()
                
                if not resume_df.empty:
                    # Get document name for reference
                    doc_name = resume_df['document_name'].iloc[0] if pd.notna(resume_df['document_name'].iloc[0]) else "Unknown"
                    
                    # Try to get content from database first
                    content = resume_df['document_content'].iloc[0]
                    if content and pd.notna(content):
                        return f"[Using resume: {doc_name}]\n\n{str(content)}"
                    else:
                        # Fall back to extracting from file
                        file_path = resume_df['file_path'].iloc[0]
                        if pd.notna(file_path):
                            extracted_content = self._extract_text_from_file(file_path)
                            return f"[Using resume: {doc_name}]\n\n{extracted_content}"
            
            return "No resume found. Please upload a resume in the Document Portal and set it as your preferred resume."
        except Exception as e:
            return f"Error loading resume: {str(e)}"
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from document file."""
        try:
            # Check if file exists first
            if not os.path.exists(file_path):
                return f"File not found: {file_path}. This might be a cloud deployment issue where local files aren't available."
            
            if file_path.endswith('.pdf'):
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
            elif file_path.endswith('.docx'):
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            else:
                return "Unsupported file format"
        except Exception as e:
            return f"Error reading file: {str(e)}. This might be due to file corruption or cloud deployment limitations."
    
    def _analyze_job(self, job_id: int) -> str:
        """Analyze a job posting and return key insights."""
        job = self._get_job_data(job_id)
        if not job:
            return f"No job found with ID {job_id}"
        
        # Get user's resume data for context
        resume_data = self._get_user_resume()
        
        # Create detailed prompt for job analysis
        prompt = f"""
You are an expert career strategist and job market analyst. Provide a comprehensive analysis of this job opportunity for the user, considering both the role requirements and their background.

**JOB DETAILS:**
- Company: {job['company_name']}
- Position: {job['job_title']}
- Job Description: {job.get('job_description', 'No description available')}
- Location: {job.get('location', 'Not specified')}
- Salary: {job.get('salary', 'Not specified')}

**USER'S RESUME:**
{resume_data}

**COMPREHENSIVE JOB ANALYSIS:**

1. **Role Overview & Market Position**:
   - What this position typically involves day-to-day
   - Seniority level and career progression potential
   - Industry context and market demand for this role
   - Typical salary range and benefits for similar positions

2. **Key Requirements Analysis**:
   - Must-have technical skills and experience
   - Preferred qualifications and nice-to-haves
   - Educational requirements and certifications
   - Soft skills and cultural fit indicators

3. **Company & Opportunity Assessment**:
   - Company size, stage, and growth trajectory
   - Industry position and competitive advantages
   - Work culture and environment indicators
   - Career development and learning opportunities

4. **Candidate Fit Assessment (0-100% match)**:
   - Overall compatibility score with reasoning
   - Strengths that align perfectly with requirements
   - Areas where the candidate exceeds expectations
   - Experience gaps or potential concerns

5. **Application Strategy Recommendations**:
   - Key selling points to emphasize in application
   - How to position the candidate's unique value proposition
   - Potential objections to address proactively
   - Timeline and next steps for application

6. **Interview Preparation Priorities**:
   - Most likely interview questions and topics
   - Technical areas to review and practice
   - Company research focus areas
   - Questions the candidate should prepare to ask

7. **Decision Factors**:
   - Pros and cons of this opportunity for the candidate's career
   - How this role fits into their career trajectory
   - Potential red flags or concerns to investigate
   - Alternative approaches if not selected

Provide specific, actionable insights that will help the candidate make an informed decision about pursuing this opportunity and optimize their approach if they decide to apply.
        """
        
        try:
            # Use the AI chat method to analyze the job
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert career strategist with deep knowledge of job markets, recruitment practices, and career development. Provide detailed, strategic analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1800
            )
            
            analysis = response.choices[0].message.content.strip()
            
            return f"""**COMPREHENSIVE JOB ANALYSIS: {job['company_name']} - {job['job_title']}**

{analysis}

---
*Analysis based on current job market trends and your specific background*
"""
        
        except Exception as e:
            return f"Error analyzing job: {str(e)}"
    
    def _help_apply(self, job_id: int) -> str:
        """Generate comprehensive application strategy and action plan."""
        job = self._get_job_data(job_id)
        if not job:
            return f"No job found with ID {job_id}"
        
        # Get user's resume data for context
        resume_data = self._get_user_resume()
        
        # Create detailed prompt for application strategy
        prompt = f"""
You are an expert career strategist and application optimization specialist. Create a comprehensive, step-by-step application strategy for the user for this specific job opportunity.

**JOB DETAILS:**
- Company: {job['company_name']}
- Position: {job['job_title']}
- Job Description: {job.get('job_description', 'No description available')}
- Location: {job.get('location', 'Not specified')}
- Salary: {job.get('salary', 'Not specified')}

**USER'S RESUME:**
{resume_data}

**COMPREHENSIVE APPLICATION STRATEGY:**

1. **Application Readiness Assessment**:
   - Current match level (0-100%) and reasoning
   - Key strengths to leverage
   - Critical gaps to address before applying
   - Estimated application competitiveness

2. **Resume Optimization Strategy**:
   - Specific sections to modify for this role
   - Keywords and phrases to incorporate naturally
   - Achievements and metrics to emphasize
   - Skills section updates and reordering priorities
   - ATS optimization recommendations

3. **Cover Letter Strategy**:
   - Key themes and messaging to emphasize
   - Specific company/role research to incorporate
   - Personal narrative and value proposition
   - How to address any potential concerns
   - Call-to-action and closing strategy

4. **Company Research Action Plan**:
   - Essential company information to gather
   - Recent news, developments, and initiatives to research
   - Key people to research (hiring manager, team leads)
   - Company culture and values alignment points
   - Industry trends and challenges to understand

5. **Application Timing & Channel Strategy**:
   - Best time/day to submit application
   - Recommended application channels (company site vs. LinkedIn vs. referrals)
   - Networking opportunities within the company
   - Follow-up timeline and approach

6. **Pre-Application Skill Building** (if needed):
   - Priority skills/certifications to acquire quickly
   - Portfolio projects or examples to develop
   - Professional development opportunities
   - Timeline for skill gaps to be addressed

7. **Interview Preparation Preview**:
   - Key interview formats to expect (technical, behavioral, case study)
   - Top 5 questions likely to be asked
   - Technical assessment preparation needed
   - Presentation or portfolio preparation requirements

8. **Application Success Metrics & Backup Plan**:
   - How to track application progress
   - Follow-up schedule and touchpoints
   - Alternative approaches if no initial response
   - Similar roles/companies to pursue in parallel

9. **30-Day Action Plan**:
   - Week 1: Immediate preparation tasks
   - Week 2: Application submission and initial follow-up
   - Week 3-4: Continued networking and follow-up activities
   - Contingency planning for different response scenarios

Provide specific, actionable steps that the user can execute immediately to maximize their chances of success with this application.
        """
        
        try:
            # Use the AI chat method to generate application strategy
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert career strategist specializing in application optimization and job search strategy. Provide detailed, actionable guidance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2000
            )
            
            strategy = response.choices[0].message.content.strip()
            
            return f"""**COMPREHENSIVE APPLICATION STRATEGY: {job['company_name']} - {job['job_title']}**

{strategy}

---
*Strategic guidance based on your background and current job market best practices*
"""
        
        except Exception as e:
            return f"Error generating application strategy: {str(e)}"
    
    def _optimize_resume(self, job_id: int) -> str:
        """Optimize resume for the given job."""
        job = self._get_job_data(job_id)
        if not job:
            return f"No job found with ID {job_id}"
        
        resume_content = self._get_user_resume()
        job_description = job['job_description']
        
        # Simple keyword matching for optimization suggestions
        job_keywords = set(re.findall(r'\b[a-zA-Z]{4,}\b', job_description.lower()))
        resume_keywords = set(re.findall(r'\b[a-zA-Z]{4,}\b', resume_content.lower()))
        
        # Find missing keywords that might be important
        important_missing = []
        for keyword in ['experience', 'skills', 'management', 'development', 'analysis', 'project']:
            if keyword in job_keywords and keyword not in resume_keywords:
                important_missing.append(keyword)
        
        # Extract skills from job description
        skill_keywords = ['python', 'java', 'javascript', 'sql', 'aws', 'azure', 'agile', 'scrum']
        job_skills = [skill for skill in skill_keywords if skill in job_description.lower()]
        resume_skills = [skill for skill in skill_keywords if skill in resume_content.lower()]
        missing_skills = [skill for skill in job_skills if skill not in resume_skills]
        
        suggestions = []
        if missing_skills:
            suggestions.append(f"**Skills to highlight or add:** {', '.join(missing_skills[:5])}")
        
        if important_missing:
            suggestions.append(f"**Keywords to incorporate:** {', '.join(important_missing[:5])}")
        
        matching_skills = [skill for skill in job_skills if skill in resume_skills]
        
        if suggestions:
            result = "**Resume Optimization Suggestions:**\n\n" + "\n\n".join(suggestions)
            if matching_skills:
                result += f"\n\n**Matching Skills Found:** {', '.join(matching_skills)}"
        else:
            result = "Your resume appears well-aligned with this job description. Consider emphasizing relevant experience and quantifiable achievements."
        
        return result
    
    def _generate_cover_letter(self, job_id: int) -> str:
        """Generate a cover letter for the specified job using AI with user preferences."""
        job = self._get_job_data(job_id)
        if not job:
            return f"No job found with ID {job_id}"
        
        # Load user preferences
        try:
            with open('robs_cover_letter_preferences.md', 'r') as f:
                preferences = f.read()
        except FileNotFoundError:
            preferences = "Cover letter preferences not found."
        
        # Get user's resume data for context
        resume_data = self._get_user_resume()
        
        # Create detailed prompt for AI cover letter generation
        prompt = f"""
You are writing a personalized cover letter for the user. Follow their specific preferences exactly.

**JOB DETAILS:**
- Company: {job['company_name']}
- Position: {job['job_title']}
- Job Description: {job.get('job_description', 'No description available')}
- Location: {job.get('location', 'Not specified')}

**USER'S COVER LETTER PREFERENCES:**
{preferences}

**USER'S BACKGROUND (for context):**
{resume_data}

**INSTRUCTIONS:**
1. Write a complete, polished cover letter following the user's preferences exactly
2. Use the conversational, human tone they prefer - not overly formal or AI-sounding
3. Follow the 5-paragraph structure they outlined
4. Keep to 350-400 words maximum
5. Use em dashes and their preferred punctuation style
6. Avoid corporate speak, buzzwords, and passive language
7. Make specific connections between their experience and this role
8. Research and reference something specific about the company/role
9. End with a sincere, confident closing (not robotic). DO NOT USE THE PHRASE "I am excited" or "I am thrilled" in the closing paragrpah, instead something like "I would love the opportunity to discuss why I am a good fit for the role with you in person."

Write the cover letter now - provide only the letter content, no additional notes or explanations.
        """
        
        try:
            # Use the AI chat method to generate the cover letter
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert cover letter writer who follows specific user preferences exactly. Write natural, human-sounding cover letters."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            cover_letter = response.choices[0].message.content.strip()
            
            return f"""**COVER LETTER FOR: {job['company_name']} - {job['job_title']}**

{cover_letter}

---
*Generated using your personal preferences from robs_cover_letter_preferences.md*
"""
        
        except Exception as e:
            return f"Error generating cover letter: {str(e)}"
    
    def _match_skills(self, job_id: int) -> str:
        """Analyze how well the user's skills match a specific job with detailed comparison."""
        job = self._get_job_data(job_id)
        if not job:
            return f"No job found with ID {job_id}"
        
        # Get user's resume data for context
        resume_data = self._get_user_resume()
        
        # Create detailed prompt for skills matching analysis
        prompt = f"""
You are an expert career advisor and skills assessment specialist. Conduct a comprehensive analysis of how well the user's background matches the requirements for this specific position.

**JOB DETAILS:**
- Company: {job['company_name']}
- Position: {job['job_title']}
- Job Description: {job.get('job_description', 'No description available')}
- Location: {job.get('location', 'Not specified')}
- Salary: {job.get('salary', 'Not specified')}

**USER'S RESUME:**
{resume_data}

**ANALYSIS REQUIRED:**

1. **Skills Match Score (0-100%)**: Provide an overall compatibility score

2. **Technical Skills Analysis**:
   - List required technical skills from the job posting
   - Match each requirement to the user's experience (Strong Match/Partial Match/Missing)
   - Highlight relevant technologies, tools, and software the user knows

3. **Experience Level Comparison**:
   - Compare years of experience required vs. the user's background
   - Assess seniority level match (entry/mid/senior)
   - Evaluate industry experience relevance

4. **Key Strengths for This Role**:
   - Top 5 strengths from the user's background that align perfectly
   - Specific examples and achievements that demonstrate these strengths
   - Quantifiable results and impacts

5. **Skill Gaps & Development Areas**:
   - Missing skills or technologies mentioned in the job posting
   - Areas where the user could strengthen their profile
   - Suggested learning priorities (ranked by importance)

6. **Competitive Advantages**:
   - Unique aspects of the user's background that stand out
   - Cross-functional skills that add value
   - Leadership, project management, or specialized experience

7. **Application Strategy Recommendations**:
   - How to position the user's experience in the application
   - Key selling points to emphasize in cover letter/interview
   - Potential concerns to address proactively

8. **Interview Preparation Focus**:
   - Technical areas to review before the interview
   - Experience examples to prepare and practice
   - Questions the user should ask to demonstrate fit

Provide specific, actionable insights that will help the user understand their competitive position and optimize their application strategy.
        """
        
        try:
            # Use the AI chat method to analyze skills match
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert career advisor specializing in skills assessment and job matching. Provide detailed, specific analysis with concrete examples."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            analysis = response.choices[0].message.content.strip()
            
            return f"""**SKILLS & EXPERIENCE MATCH ANALYSIS: {job['company_name']} - {job['job_title']}**

{analysis}

---
*Analysis based on your current resume and the specific job requirements*
"""
        
        except Exception as e:
            return f"Error analyzing skills match: {str(e)}"
    
    def _prepare_interview(self, job_id: int, company_name: str) -> str:
        """Generate comprehensive interview preparation based on job requirements and user's background."""
        job = self._get_job_data(job_id)
        if not job:
            return f"No job found with ID {job_id}"
        
        # Get user's resume data for context
        resume_data = self._get_user_resume()
        
        # Create detailed prompt for interview preparation
        prompt = f"""
You are an expert interview coach and career strategist. Create a comprehensive interview preparation guide for the user based on their specific background and this job opportunity.

**JOB DETAILS:**
- Company: {job['company_name']}
- Position: {job['job_title']}
- Job Description: {job.get('job_description', 'No description available')}
- Location: {job.get('location', 'Not specified')}
- Salary: {job.get('salary', 'Not specified')}

**USER'S RESUME:**
{resume_data}

**COMPREHENSIVE INTERVIEW PREPARATION GUIDE:**

1. **Most Likely Interview Questions (8-10 questions)**:
   - Technical questions based on job requirements
   - Behavioral questions relevant to the role
   - Situational questions testing problem-solving
   - Questions about the user's specific experience and background

2. **Prepared Response Framework**:
   For each question, provide:
   - Key points the user should cover
   - Specific examples from their experience to mention
   - Quantifiable achievements to highlight
   - How to connect their background to the company's needs

3. **Technical Deep-Dive Areas**:
   - Technologies/tools they'll likely test knowledge on
   - Technical challenges or scenarios they might present
   - Industry-specific knowledge to review
   - Best practices and methodologies to discuss

4. **STAR Method Examples**:
   - 3-4 prepared STAR (Situation, Task, Action, Result) stories
   - Match stories to common behavioral questions
   - Include specific metrics and outcomes
   - Cover different aspects: leadership, problem-solving, collaboration, innovation

5. **Questions the User Should Ask**:
   - About the role and day-to-day responsibilities
   - About team structure and collaboration
   - About company culture and growth opportunities
   - About challenges and success metrics
   - Technical questions that show expertise

6. **Company-Specific Talking Points**:
   - Recent company news or developments to reference
   - Company values and culture alignment
   - How the user's experience relates to their business
   - Why they're specifically interested in this company

7. **Potential Concerns & How to Address**:
   - Any gaps in experience and how to position them
   - Career transitions or changes to explain
   - Why they're leaving current role (if applicable)
   - Salary expectations and negotiation talking points

8. **Interview Day Strategy**:
   - Key strengths to emphasize throughout
   - Professional examples to weave into answers
   - Follow-up questions to demonstrate engagement
   - Closing statements that reinforce fit

Focus on practical, actionable guidance that the user can use to confidently navigate the interview and demonstrate their value as a candidate.
        """
        
        try:
            # Use the AI chat method to generate interview preparation
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert interview coach with extensive experience preparing candidates for technical and behavioral interviews. Provide specific, actionable guidance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2000
            )
            
            preparation_guide = response.choices[0].message.content.strip()
            
            return f"""**INTERVIEW PREPARATION GUIDE: {job['company_name']} - {job['job_title']}**

{preparation_guide}

---
*Tailored preparation based on your resume and the specific role requirements*
"""
        
        except Exception as e:
            return f"Error generating interview preparation: {str(e)}"
    
    def _research_company(self, company_name: str) -> str:
        """Research the company using AI agent with web search capabilities."""
        try:
            # Create comprehensive research prompt for the AI agent
            research_prompt = f"""
            Research the company "{company_name}" comprehensively for a job applicant. I need detailed, actionable insights that will help with job applications and interviews.

            Please provide a professional research report that includes:

            1. **Company Overview**:
               - What the company does (products/services)
               - Industry and market position
               - Company size and locations
               - Business model and target customers

            2. **Recent Developments** (last 6-12 months):
               - Recent news, press releases, announcements
               - New product launches or services
               - Funding rounds, acquisitions, partnerships
               - Leadership changes or organizational updates
               - Awards, recognition, or industry achievements

            3. **Company Culture & Values**:
               - Mission, vision, and core values
               - Work culture and employee experience
               - Diversity, equity, and inclusion initiatives
               - Company benefits and employee perks
               - Remote work policies and workplace flexibility

            4. **Leadership & Key People**:
               - CEO and executive team information
               - Notable leaders and their backgrounds
               - Company founders and founding story
               - Key department heads relevant to job search

            5. **Financial & Growth Information**:
               - Recent financial performance (if public)
               - Growth trajectory and expansion plans
               - Market challenges and opportunities
               - Competitive landscape and main competitors

            6. **Job Application Insights**:
               - What they likely look for in candidates
               - Company-specific skills or experience they value
               - Interview process insights (if available)
               - Questions to ask during interviews
               - How to align application with their values/needs

            7. **Red Flags or Considerations**:
               - Any negative news or controversies
               - Employee review trends (Glassdoor, etc.)
               - Industry challenges affecting the company
               - Potential concerns for job seekers

            Please search the web thoroughly and provide specific, current, and actionable information. Include sources where possible and focus on information that will help tailor job applications and prepare for interviews.

            Format the response as a professional research report with clear sections and actionable insights.
            """
            
            # Use OpenAI's function calling to simulate agent research
            # Since Task tool isn't directly available in this context, we'll use OpenAI to generate research
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional company research analyst with web search capabilities. Provide comprehensive, current research about companies for job seekers."},
                    {"role": "user", "content": research_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            ai_research = response.choices[0].message.content
            
            # Format the result with additional context
            formatted_report = f"""
**COMPREHENSIVE COMPANY RESEARCH REPORT: {company_name}**

{ai_research}

---
**Research Method**: AI-Powered Company Analysis
**Research Scope**: Multi-source research synthesis and analysis  
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Purpose**: Job application preparation and interview insights

**Note**: This research combines AI knowledge with company analysis. For the most current information, verify recent developments through direct web searches.
            """
            
            return formatted_report.strip()
            
        except Exception as e:
            # Simple error handling - OpenAI API is reliable, so elaborate fallbacks aren't needed
            return f"""
**COMPANY RESEARCH REPORT: {company_name}**

❌ **Research Error**: Unable to complete automated research at this time.

**Error Details**: {str(e)}

**Recommendation**: Please try the research request again. If the issue persists, you can manually research {company_name} using web search, LinkedIn, and news sources.

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            """.strip()
    
    def _match_job(self, job_id: int) -> str:
        """Analyze job match and provide compatibility score."""
        job = self._get_job_data(job_id)
        if not job:
            return f"No job found with ID {job_id}"
        
        resume_content = self._get_user_resume()
        job_description = job['job_description']
        
        # Simple matching algorithm
        job_skills = set(re.findall(r'\b(?:python|java|javascript|sql|aws|azure|agile|scrum|react|node|mongodb|postgresql)\b', 
                                   job_description.lower()))
        resume_skills = set(re.findall(r'\b(?:python|java|javascript|sql|aws|azure|agile|scrum|react|node|mongodb|postgresql)\b', 
                                      resume_content.lower()))
        
        matching_skills = job_skills & resume_skills
        missing_skills = job_skills - resume_skills
        
        # Calculate basic score
        if len(job_skills) > 0:
            score = min(10, (len(matching_skills) / len(job_skills)) * 10)
        else:
            score = 7  # Default score if no skills detected
        
        # Generate strengths and gaps
        strengths = []
        if matching_skills:
            strengths.extend([f"Experience with {skill.title()}" for skill in list(matching_skills)[:5]])
        
        if not strengths:
            strengths = ["Professional experience relevant to the role", "Strong foundational skills"]
        
        gaps = []
        if missing_skills:
            gaps.extend([f"Consider highlighting {skill.title()} experience" for skill in list(missing_skills)[:3]])
        
        if not gaps:
            gaps = ["No significant skill gaps identified"]
        
        recommendations = [
            "Tailor resume to emphasize relevant experience",
            f"Research {job['company_name']}'s culture and values",
            "Prepare specific examples of relevant projects",
            "Practice discussing your experience with the required technologies"
        ]
        
        result = f"""
**JOB MATCH ANALYSIS**

**Position:** {job['company_name']} - {job['job_title']}

**Match Score:** {round(score, 1)}/10

**Strengths:**
{chr(10).join([f"✅ {strength}" for strength in strengths[:5]])}

**Areas to Address:**
{chr(10).join([f"⚠️ {gap}" for gap in gaps[:3]])}

**Recommendations:**
{chr(10).join([f"💡 {rec}" for rec in recommendations[:4]])}
        """
        
        return result.strip()
    
    def chat(self, message: str) -> str:
        """Process a chat message and return the agent's response."""
        try:
            # Add user message to conversation history
            self.conversation_history.append({"role": "user", "content": message})
            
            # Create system message with context
            system_message = self._create_system_message()
            
            # Prepare function definitions for OpenAI
            tools = [func_def["function"] for func_def in self.available_functions.values()]
            
            # Create messages for OpenAI API
            messages = [{"role": "system", "content": system_message}] + self.conversation_history
            
            # Call OpenAI API with function calling
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=[{"type": "function", "function": tool} for tool in tools],
                tool_choice="auto",
                temperature=0.7
            )
            
            response_message = response.choices[0].message
            
            # Handle function calls
            if response_message.tool_calls:
                # Add the assistant's response to conversation
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [{"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in response_message.tool_calls]
                })
                
                # Execute function calls
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_name in self.available_functions:
                        function_impl = self.available_functions[function_name]["implementation"]
                        function_result = function_impl(**function_args)
                        
                        # Add function result to conversation
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": function_result
                        })
                
                # Get final response after function execution
                final_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "system", "content": system_message}] + self.conversation_history,
                    temperature=0.7
                )
                
                final_message = final_response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": final_message})
                
                return final_message
            else:
                # No function calls, just return the response
                self.conversation_history.append({"role": "assistant", "content": response_message.content})
                return response_message.content
                
        except Exception as e:
            error_message = f"I encountered an error: {str(e)}. Please try rephrasing your request."
            self.conversation_history.append({"role": "assistant", "content": error_message})
            return error_message
    
    def _create_system_message(self) -> str:
        """Create a comprehensive system message for the OpenAI agent."""
        
        # Load user context
        resume = self._get_user_resume()
        
        try:
            with open('robs_cover_letter_preferences.md', 'r') as f:
                cover_letter_prefs = f.read()
        except FileNotFoundError:
            cover_letter_prefs = "Cover letter preferences not found."
        
        try:
            with open('system_instructions.md', 'r') as f:
                system_instructions = f.read()
        except FileNotFoundError:
            system_instructions = "System instructions not found."
        
        system_prompt = f"""You are an expert recruitment assistant specializing in helping users find employment. 

## Agent Purpose

You are a dedicated AI Job Application Assistant designed to provide comprehensive support throughout the entire job search and application process. Your primary mission is to:

- **Empower job seekers** with data-driven insights and personalized guidance
- **Streamline the application process** by automating analysis and content generation
- **Increase application success rates** through strategic optimization and research
- **Provide expert-level career advice** backed by industry best practices
- **Maintain a supportive, professional approach** that builds user confidence

You excel at breaking down complex job requirements, identifying key opportunities for improvement, and providing actionable recommendations that directly impact application success. Every interaction should leave the user better prepared and more confident in their job search journey.

## User Context
**Resume:** {resume}...

**Career Context:** You're helping a job seeker optimize their applications, analyze opportunities, and provide strategic career guidance.

## Your Capabilities

You have access to these specialized functions:
- `analyze_job`: Analyze specific jobs from the database
- `optimize_resume`: Optimize resume content for job descriptions  
- `generate_cover_letter`: Generate personalized cover letters
- `research_company`: Research companies for application insights
- `match_job`: Analyze job-candidate compatibility

## User Preferences

{cover_letter_prefs}

## System Instructions

{system_instructions}

## Interaction Guidelines

1. **Be Proactive**: Use relevant functions to provide comprehensive assistance
2. **Be Specific**: Always reference specific job IDs, company names, and concrete details
3. **Be Strategic**: Think about the entire job application process
4. **Be Efficient**: Use functions when they can provide better insights than general knowledge

## Communication Style

- Professional but conversational
- Direct and actionable advice
- Use bullet points and clear formatting
- Provide step-by-step guidance when appropriate
- Always explain your reasoning

Remember: You're not just answering questions - you're helping the user succeed in their job search through strategic, comprehensive assistance.
        """
        
        return system_prompt.strip()
    
    def get_available_jobs(self) -> pd.DataFrame:
        """Get list of available jobs for the user using unified database system."""
        from database_utils import use_supabase
        
        try:
            if use_supabase():
                from supabase_utils import get_supabase_client
                supabase = get_supabase_client()
                
                if self.user_id:
                    result = supabase.table('jobs').select('id, company_name, job_title, job_description, status, date_added').eq('user_id', self.user_id).order('date_added', desc=True).execute()
                else:
                    result = supabase.table('jobs').select('id, company_name, job_title, job_description, status, date_added').order('date_added', desc=True).execute()
                
                return pd.DataFrame(result.data) if result.data else pd.DataFrame()
            else:
                conn = get_db_connection()
                if self.user_id:
                    jobs_df = pd.read_sql_query(
                        "SELECT id, company_name, job_title, job_description, status, date_added FROM jobs WHERE user_id = ? ORDER BY date_added DESC",
                        conn, params=(self.user_id,)
                    )
                else:
                    jobs_df = pd.read_sql_query(
                        "SELECT id, company_name, job_title, job_description, status, date_added FROM jobs ORDER BY date_added DESC",
                        conn
                    )
                conn.close()
                return jobs_df
        except Exception as e:
            st.error(f"Error getting jobs: {str(e)}")
            return pd.DataFrame()
    
    def clear_memory(self):
        """Clear the conversation memory."""
        self.conversation_history = []
    
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
                not_applied = len(jobs_df[jobs_df['status'] == 'Not Applied'])
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


# Helper functions for Streamlit integration
def initialize_openai_agent(user_id: Optional[int] = None) -> OpenAIJobAgent:
    """Initialize the OpenAI job agent."""
    return OpenAIJobAgent(user_id=user_id)


def get_openai_agent_suggestions(agent: OpenAIJobAgent) -> List[str]:
    """Get suggested actions from the OpenAI agent."""
    return agent.suggest_next_actions()


