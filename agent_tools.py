"""
Custom LangChain Tools for Job Application Assistant

This module contains specialized tools for job-related tasks including:
- Resume analysis and optimization
- Job description parsing
- Cover letter generation
- Company research
- Document processing
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import re

from langchain.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from PyPDF2 import PdfReader
from docx import Document

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

from utils import get_db_connection


class JobAnalysisInput(BaseModel):
    """Input for job analysis tool."""
    job_id: int = Field(description="ID of the job to analyze from the database")


class ResumeOptimizerInput(BaseModel):
    """Input for resume optimizer tool."""
    job_description: str = Field(description="The job description to optimize the resume for")
    current_resume_text: str = Field(description="Current resume content as text")


class CoverLetterInput(BaseModel):
    """Input for cover letter generation tool."""
    job_id: int = Field(description="ID of the job from the database")
    company_name: str = Field(description="Name of the company")
    job_title: str = Field(description="Title of the job position")
    job_description: str = Field(description="Full job description text")


class CompanyResearchInput(BaseModel):
    """Input for company research tool."""
    company_name: str = Field(description="Name of the company to research")


class JobAnalysisTool(BaseTool):
    """Tool to analyze job postings from the database."""
    
    name = "job_analyzer"
    description = "Analyze a specific job posting from the database to extract key requirements, skills, and insights"
    args_schema = JobAnalysisInput
    
    def __init__(self, user_id: Optional[int] = None):
        super().__init__()
        self.user_id = user_id
    
    @traceable(name="analyze_job", metadata={"tool": "job_analyzer"})
    def _run(self, job_id: int) -> str:
        """Analyze a job posting and return key insights."""
        try:
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
                return f"No job found with ID {job_id}"
            
            job = job_df.iloc[0]
            
            # Extract key information
            analysis = {
                "company": job['company_name'],
                "title": job['job_title'],
                "description_length": len(job['job_description']),
                "key_requirements": self._extract_requirements(job['job_description']),
                "skills_mentioned": self._extract_skills(job['job_description']),
                "experience_level": self._determine_experience_level(job['job_description']),
                "salary_info": job.get('salary', 'Not specified'),
                "location": job.get('location', 'Not specified'),
                "application_status": job.get('status', 'Not applied')
            }
            
            # Format the analysis
            result = f"""
**Job Analysis for {analysis['company']} - {analysis['title']}**

**Key Requirements:**
{chr(10).join([f"• {req}" for req in analysis['key_requirements']])}

**Technical Skills Mentioned:**
{', '.join(analysis['skills_mentioned']) if analysis['skills_mentioned'] else 'None specifically mentioned'}

**Experience Level:** {analysis['experience_level']}
**Location:** {analysis['location']}
**Salary:** {analysis['salary_info']}
**Current Status:** {analysis['application_status']}

**Job Description Length:** {analysis['description_length']} characters
            """
            
            return result.strip()
            
        except Exception as e:
            return f"Error analyzing job: {str(e)}"
    
    def _extract_requirements(self, job_description: str) -> List[str]:
        """Extract key requirements from job description."""
        requirements = []
        text = job_description.lower()
        
        # Common requirement patterns
        requirement_patterns = [
            r"(\d+\+?\s*years?\s*(?:of\s*)?experience)",
            r"(bachelor'?s?\s*degree)",
            r"(master'?s?\s*degree)",
            r"(phd|doctorate)",
            r"(experience\s*(?:with|in)\s*[\w\s]+)",
            r"(knowledge\s*(?:of|in)\s*[\w\s]+)",
            r"(proficiency\s*(?:with|in)\s*[\w\s]+)"
        ]
        
        for pattern in requirement_patterns:
            matches = re.findall(pattern, text)
            requirements.extend([match.strip() for match in matches[:3]])  # Limit to 3 per pattern
        
        return requirements[:10]  # Limit total requirements
    
    def _extract_skills(self, job_description: str) -> List[str]:
        """Extract technical skills from job description."""
        text = job_description.lower()
        
        # Common technical skills (expand this list as needed)
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'postgresql', 
            'mysql', 'mongodb', 'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'git', 'agile', 'scrum', 'jira', 'confluence', 'slack', 'teams',
            'excel', 'tableau', 'power bi', 'salesforce', 'hubspot', 'google analytics'
        ]
        
        found_skills = []
        for skill in skill_keywords:
            if skill in text:
                found_skills.append(skill.title())
        
        return found_skills[:8]  # Limit to top 8 skills
    
    def _determine_experience_level(self, job_description: str) -> str:
        """Determine the experience level required."""
        text = job_description.lower()
        
        if any(term in text for term in ['senior', '5+ years', '7+ years', 'lead', 'principal']):
            return "Senior Level (5+ years)"
        elif any(term in text for term in ['3+ years', '4+ years', 'mid-level', 'intermediate']):
            return "Mid Level (3-5 years)"
        elif any(term in text for term in ['entry level', 'junior', '0-2 years', 'new grad']):
            return "Entry Level (0-2 years)"
        else:
            return "Experience level not clearly specified"


class ResumeOptimizerTool(BaseTool):
    """Tool to optimize resume content for specific job descriptions."""
    
    name = "resume_optimizer"
    description = "Optimize resume content to better match a specific job description"
    args_schema = ResumeOptimizerInput
    
    @traceable(name="optimize_resume", metadata={"tool": "resume_optimizer"})
    def _run(self, job_description: str, current_resume_text: str) -> str:
        """Optimize resume for the given job description."""
        try:
            # Analyze job requirements
            job_skills = self._extract_job_skills(job_description)
            job_keywords = self._extract_keywords(job_description)
            
            # Analyze current resume
            resume_skills = self._extract_resume_skills(current_resume_text)
            
            # Generate optimization suggestions
            suggestions = []
            
            # Skills gap analysis
            missing_skills = set(job_skills) - set(resume_skills)
            if missing_skills:
                suggestions.append(f"**Skills to highlight or add:** {', '.join(list(missing_skills)[:5])}")
            
            # Keyword optimization
            missing_keywords = [kw for kw in job_keywords if kw.lower() not in current_resume_text.lower()]
            if missing_keywords:
                suggestions.append(f"**Keywords to incorporate:** {', '.join(missing_keywords[:5])}")
            
            # Format suggestions
            if suggestions:
                result = "**Resume Optimization Suggestions:**\n\n" + "\n\n".join(suggestions)
                result += "\n\n**Matching Skills Found:** " + ", ".join(list(set(job_skills) & set(resume_skills)))
            else:
                result = "Your resume appears well-aligned with this job description. Consider emphasizing relevant experience and quantifiable achievements."
            
            return result
            
        except Exception as e:
            return f"Error optimizing resume: {str(e)}"
    
    def _extract_job_skills(self, job_description: str) -> List[str]:
        """Extract required skills from job description."""
        text = job_description.lower()
        
        # Technical skills pattern matching
        skill_patterns = [
            r'\b(python|java|javascript|react|angular|vue|node\.?js)\b',
            r'\b(sql|postgresql|mysql|mongodb|redis|elasticsearch)\b',
            r'\b(aws|azure|gcp|google cloud|cloud)\b',
            r'\b(docker|kubernetes|jenkins|gitlab|github)\b',
            r'\b(agile|scrum|kanban|jira|confluence)\b',
            r'\b(excel|tableau|power\s*bi|looker|qlik)\b'
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text)
            skills.extend([match.title() for match in matches])
        
        return list(set(skills))
    
    def _extract_keywords(self, job_description: str) -> List[str]:
        """Extract important keywords from job description."""
        # Simple keyword extraction - can be enhanced with NLP
        words = re.findall(r'\b[a-zA-Z]{4,}\b', job_description)
        word_freq = {}
        
        # Count word frequency
        for word in words:
            word_lower = word.lower()
            if word_lower not in ['that', 'with', 'will', 'have', 'this', 'they', 'from', 'your', 'their']:
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
        
        # Return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word[0].title() for word in sorted_words[:10]]
    
    def _extract_resume_skills(self, resume_text: str) -> List[str]:
        """Extract skills mentioned in resume."""
        return self._extract_job_skills(resume_text)  # Reuse the same logic


class CoverLetterGeneratorTool(BaseTool):
    """Tool to generate personalized cover letters."""
    
    name = "cover_letter_generator"
    description = "Generate a personalized cover letter based on job details and user preferences"
    args_schema = CoverLetterInput
    
    @traceable(name="generate_cover_letter", metadata={"tool": "cover_letter_generator"})
    def _run(self, job_id: int, company_name: str, job_title: str, job_description: str) -> str:
        """Generate a cover letter for the specified job."""
        try:
            # Load user preferences from file
            preferences = self._load_cover_letter_preferences()
            system_instructions = self._load_system_instructions()
            
            # Analyze the job for key points
            key_requirements = self._extract_key_points(job_description)
            
            # Generate cover letter structure
            cover_letter = self._generate_letter_content(
                company_name, job_title, job_description, key_requirements, preferences
            )
            
            return cover_letter
            
        except Exception as e:
            return f"Error generating cover letter: {str(e)}"
    
    def _load_cover_letter_preferences(self) -> str:
        """Load cover letter preferences from file."""
        try:
            with open('robs_cover_letter_preferences.md', 'r') as f:
                return f.read()
        except FileNotFoundError:
            return "No cover letter preferences found."
    
    def _load_system_instructions(self) -> str:
        """Load system instructions from file."""
        try:
            with open('system_instructions.md', 'r') as f:
                return f.read()
        except FileNotFoundError:
            return "No system instructions found."
    
    def _extract_key_points(self, job_description: str) -> List[str]:
        """Extract key points from job description for cover letter focus."""
        # Simple extraction - can be enhanced with more sophisticated NLP
        sentences = job_description.split('.')
        key_points = []
        
        for sentence in sentences[:5]:  # Look at first 5 sentences
            if any(keyword in sentence.lower() for keyword in ['responsible', 'experience', 'skills', 'qualifications']):
                key_points.append(sentence.strip())
        
        return key_points[:3]  # Return top 3 key points
    
    def _generate_letter_content(self, company_name: str, job_title: str, 
                                job_description: str, key_requirements: List[str], 
                                preferences: str) -> str:
        """Generate the actual cover letter content."""
        
        # This is a template-based approach - in the full implementation,
        # this would use the LangChain agent with OpenAI to generate personalized content
        
        template = f"""
**COVER LETTER GENERATED FOR: {company_name} - {job_title}**

Based on your preferences and the job requirements, here's a draft cover letter:

---

Dear Hiring Manager,

I'm excited to apply for the {job_title} position at {company_name}. Your focus on [SPECIFIC COMPANY VALUE/MISSION] resonates with my approach to [RELEVANT EXPERIENCE AREA].

In my previous roles, I've [RELEVANT EXPERIENCE HIGHLIGHT] which directly aligns with your requirements for [KEY REQUIREMENT FROM JOB]. My experience with [TECHNICAL SKILLS] and [SOFT SKILLS] positions me well to contribute to your team's success.

What particularly excites me about this role is [SPECIFIC ASPECT OF THE JOB]. I'm confident that my [RELEVANT STRENGTH] and collaborative approach would add value to [COMPANY NAME]'s continued growth.

I'd welcome the opportunity to discuss how my background in [RELEVANT AREA] can contribute to [SPECIFIC TEAM/DEPARTMENT].

Best regards,
Robert Enright

---

**KEY REQUIREMENTS IDENTIFIED:**
{chr(10).join([f"• {req}" for req in key_requirements])}

**NOTES:**
- This is a template structure. The final version should be customized with specific details.
- Consider researching {company_name}'s recent news or initiatives to personalize the opening.
- Replace bracketed placeholders with specific examples from your experience.
        """
        
        return template.strip()


class CompanyResearchTool(BaseTool):
    """Tool to research companies using web search."""
    
    name = "company_researcher"
    description = "Research a company using web search to gather relevant information for job applications"
    args_schema = CompanyResearchInput
    
    def __init__(self):
        super().__init__()
        self.search = DuckDuckGoSearchAPIWrapper()
    
    @traceable(name="research_company", metadata={"tool": "company_researcher"})
    def _run(self, company_name: str) -> str:
        """Research the company and return relevant information."""
        try:
            # Search for company information
            search_queries = [
                f"{company_name} company recent news",
                f"{company_name} company culture values",
                f"{company_name} company size revenue"
            ]
            
            research_results = []
            
            for query in search_queries:
                try:
                    results = self.search.run(query)
                    research_results.append(f"**Search: {query}**\n{results}\n")
                except Exception as e:
                    research_results.append(f"**Search: {query}**\nError: {str(e)}\n")
            
            # Compile research report
            report = f"""
**COMPANY RESEARCH REPORT: {company_name}**

{chr(10).join(research_results)}

**RESEARCH SUMMARY:**
Based on the search results above, consider highlighting these points in your application:
- Company's recent achievements or news
- Alignment with company values and culture
- Understanding of company's market position
- Specific projects or initiatives you find interesting

**NEXT STEPS:**
1. Review the search results for specific details to mention
2. Check the company's official website and LinkedIn page
3. Look for mutual connections or employees you could reach out to
4. Tailor your application materials based on the insights gathered
            """
            
            return report.strip()
            
        except Exception as e:
            return f"Error researching company: {str(e)}"


class JobMatchingTool(BaseTool):
    """Tool to analyze how well a user matches a job posting."""
    
    name = "job_matcher"
    description = "Analyze how well user qualifications match a specific job posting"
    args_schema = JobAnalysisInput
    
    def __init__(self, user_id: Optional[int] = None):
        super().__init__()
        self.user_id = user_id
    
    @traceable(name="analyze_job_match", metadata={"tool": "job_matcher"})
    def _run(self, job_id: int) -> str:
        """Analyze job match and provide compatibility score."""
        try:
            # Get job details
            conn = get_db_connection()
            if self.user_id:
                job_df = pd.read_sql_query(
                    "SELECT * FROM jobs WHERE id = ? AND user_id = ?", 
                    conn, 
                    params=(job_id, self.user_id)
                )
                
                # Get user's latest resume
                resume_df = pd.read_sql_query(
                    "SELECT * FROM documents WHERE document_type = 'Resume' AND user_id = ? ORDER BY upload_date DESC LIMIT 1", 
                    conn,
                    params=(self.user_id,)
                )
            else:
                job_df = pd.read_sql_query(
                    "SELECT * FROM jobs WHERE id = ?", 
                    conn, 
                    params=(job_id,)
                )
                
                # Get user's latest resume
                resume_df = pd.read_sql_query(
                    "SELECT * FROM documents WHERE document_type = 'Resume' ORDER BY upload_date DESC LIMIT 1", 
                    conn
                )
            conn.close()
            
            if job_df.empty:
                return f"No job found with ID {job_id}"
            
            job = job_df.iloc[0]
            resume_content = ""
            
            if not resume_df.empty:
                resume_path = resume_df['file_path'].iloc[0]
                resume_content = self._extract_resume_text(resume_path)
            
            # Perform matching analysis
            match_analysis = self._analyze_match(job['job_description'], resume_content)
            
            result = f"""
**JOB MATCH ANALYSIS**

**Position:** {job['company_name']} - {job['job_title']}

**Match Score:** {match_analysis['score']}/10

**Strengths:**
{chr(10).join([f"✅ {strength}" for strength in match_analysis['strengths']])}

**Areas to Address:**
{chr(10).join([f"⚠️ {gap}" for gap in match_analysis['gaps']])}

**Recommendations:**
{chr(10).join([f"💡 {rec}" for rec in match_analysis['recommendations']])}
            """
            
            return result.strip()
            
        except Exception as e:
            return f"Error analyzing job match: {str(e)}"
    
    def _extract_resume_text(self, file_path: str) -> str:
        """Extract text from resume file."""
        try:
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
            return f"Error reading resume: {str(e)}"
    
    def _analyze_match(self, job_description: str, resume_content: str) -> Dict[str, Any]:
        """Analyze how well the resume matches the job description."""
        # Simple matching algorithm - can be enhanced with more sophisticated NLP
        
        job_skills = set(re.findall(r'\b(?:python|java|javascript|sql|aws|azure|agile|scrum)\b', 
                                   job_description.lower()))
        resume_skills = set(re.findall(r'\b(?:python|java|javascript|sql|aws|azure|agile|scrum)\b', 
                                      resume_content.lower()))
        
        matching_skills = job_skills & resume_skills
        missing_skills = job_skills - resume_skills
        
        # Calculate basic score
        if len(job_skills) > 0:
            score = min(10, (len(matching_skills) / len(job_skills)) * 10)
        else:
            score = 7  # Default score if no skills detected
        
        return {
            'score': round(score, 1),
            'strengths': [f"Experience with {skill}" for skill in list(matching_skills)[:5]],
            'gaps': [f"May need to highlight {skill} experience" for skill in list(missing_skills)[:3]],
            'recommendations': [
                "Tailor resume to emphasize relevant experience",
                "Research the company culture and values",
                "Prepare specific examples of relevant projects"
            ]
        }


# Tool registry for easy access
def get_available_tools(user_id: Optional[int] = None) -> List[BaseTool]:
    """Get all available tools with user context."""
    return [
        JobAnalysisTool(user_id=user_id),
        ResumeOptimizerTool(),
        CoverLetterGeneratorTool(),
        CompanyResearchTool(),
        JobMatchingTool(user_id=user_id)
    ]

# Default tools for backwards compatibility
AVAILABLE_TOOLS = get_available_tools()