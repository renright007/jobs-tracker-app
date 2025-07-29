"""
Dataset-Aware Tools for LangChain Agent

These tools allow your AI agent to interact with your jobs database
using the loaded LangChain documents for better insights and recommendations.
"""

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json

# LangSmith imports
try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def traceable(func=None, **kwargs):
        if func is None:
            return lambda f: f
        return func

from job_dataset_loader import JobsDatasetLoader, load_user_jobs_dataset, search_jobs_dataset


class JobSearchInput(BaseModel):
    """Input for job search tool."""
    company: Optional[str] = Field(None, description="Company name to search for")
    status: Optional[str] = Field(None, description="Application status (Not Applied, Applied, Interviewing, Offered, Rejected)")
    keyword: Optional[str] = Field(None, description="Keyword to search in job descriptions, titles, or notes")


class JobAnalysisInput(BaseModel):
    """Input for job analysis tool."""
    analysis_type: str = Field(description="Type of analysis: 'overview', 'patterns', 'companies', 'status'")


class DatasetSearchTool(BaseTool):
    """Tool to search through the user's job applications dataset."""
    
    name: str = "search_jobs_dataset"
    description: str = "Search through the user's job applications using company name, status, or keywords"
    args_schema: type[BaseModel] = JobSearchInput
    user_id: Optional[int] = None
    
    def __init__(self, user_id: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
    
    @traceable(name="search_jobs_dataset", metadata={"tool": "dataset_search"})
    def _run(self, company: Optional[str] = None, status: Optional[str] = None, keyword: Optional[str] = None) -> str:
        """Search the jobs dataset with filters."""
        try:
            # Search the dataset
            documents = search_jobs_dataset(
                user_id=self.user_id,
                company=company,
                status=status,
                keyword=keyword
            )
            
            if not documents:
                return "No jobs found matching your search criteria."
            
            # Format results
            results = []
            for doc in documents[:10]:  # Limit to top 10 results
                metadata = doc.metadata
                result = {
                    "job_id": metadata.get("job_id"),
                    "company": metadata.get("company_name"),
                    "position": metadata.get("job_title"),
                    "status": metadata.get("status"),
                    "location": metadata.get("location"),
                    "date_added": metadata.get("date_added")
                }
                results.append(result)
            
            response = f"Found {len(documents)} jobs matching your criteria:\n\n"
            for i, result in enumerate(results, 1):
                response += f"{i}. **{result['company']} - {result['position']}**\n"
                response += f"   Status: {result['status']}\n"
                if result['location']:
                    response += f"   Location: {result['location']}\n"
                response += f"   Added: {result['date_added']}\n"
                response += f"   Job ID: {result['job_id']}\n\n"
            
            if len(documents) > 10:
                response += f"... and {len(documents) - 10} more results.\n"
            
            return response
            
        except Exception as e:
            return f"Error searching jobs dataset: {str(e)}"


class DatasetAnalysisTool(BaseTool):
    """Tool to analyze patterns and trends in the user's job applications."""
    
    name: str = "analyze_jobs_dataset"
    description: str = "Analyze patterns, trends, and statistics in the user's job applications dataset"
    args_schema: type[BaseModel] = JobAnalysisInput
    user_id: Optional[int] = None
    
    def __init__(self, user_id: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
    
    @traceable(name="analyze_jobs_dataset", metadata={"tool": "dataset_analysis"})
    def _run(self, analysis_type: str) -> str:
        """Analyze the jobs dataset based on the requested type."""
        try:
            loader = JobsDatasetLoader(user_id=self.user_id)
            
            if analysis_type == "overview":
                return self._get_overview_analysis(loader)
            elif analysis_type == "patterns":
                return self._get_patterns_analysis(loader)
            elif analysis_type == "companies":
                return self._get_companies_analysis(loader)
            elif analysis_type == "status":
                return self._get_status_analysis(loader)
            else:
                return "Invalid analysis type. Use: 'overview', 'patterns', 'companies', or 'status'"
                
        except Exception as e:
            return f"Error analyzing jobs dataset: {str(e)}"
    
    def _get_overview_analysis(self, loader: JobsDatasetLoader) -> str:
        """Get an overview of the jobs dataset."""
        stats = loader.get_dataset_stats()
        documents = loader.load()
        
        response = f"**Job Applications Overview**\n\n"
        response += f"📊 **Statistics:**\n"
        response += f"• Total Applications: {stats.get('total_jobs', 0)}\n"
        response += f"• Companies Applied To: {stats.get('companies', 0)}\n"
        
        if stats.get('date_range'):
            response += f"• Date Range: {stats['date_range'].get('earliest')} to {stats['date_range'].get('latest')}\n"
        
        # Application status breakdown
        if stats.get('status_breakdown'):
            response += f"\n📈 **Application Status:**\n"
            for status, count in stats['status_breakdown'].items():
                response += f"• {status}: {count}\n"
        
        # Sentiment breakdown
        if stats.get('sentiment_breakdown'):
            response += f"\n😊 **Sentiment:**\n"
            for sentiment, count in stats['sentiment_breakdown'].items():
                response += f"• {sentiment}: {count}\n"
        
        return response
    
    def _get_patterns_analysis(self, loader: JobsDatasetLoader) -> str:
        """Analyze patterns in job applications."""
        documents = loader.load()
        
        if not documents:
            return "No job applications found to analyze patterns."
        
        # Analyze common keywords in job titles
        job_titles = [doc.metadata.get('job_title', '').lower() for doc in documents if doc.metadata.get('job_title')]
        title_words = []
        for title in job_titles:
            title_words.extend(title.split())
        
        # Count word frequency
        word_freq = {}
        for word in title_words:
            if len(word) > 3:  # Filter short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        response = f"**Job Application Patterns**\n\n"
        response += f"🔍 **Most Common Keywords in Job Titles:**\n"
        for word, count in top_keywords:
            response += f"• {word.title()}: {count} times\n"
        
        # Analyze application timing
        dates = [doc.metadata.get('date_added') for doc in documents if doc.metadata.get('date_added')]
        if dates:
            response += f"\n📅 **Application Timeline:**\n"
            response += f"• Total Applications: {len(documents)}\n"
            response += f"• Most Recent: {max(dates)}\n"
            response += f"• Oldest: {min(dates)}\n"
        
        return response
    
    def _get_companies_analysis(self, loader: JobsDatasetLoader) -> str:
        """Analyze companies in the dataset."""
        documents = loader.load()
        
        if not documents:
            return "No job applications found to analyze companies."
        
        # Count applications per company
        company_counts = {}
        for doc in documents:
            company = doc.metadata.get('company_name', 'Unknown')
            company_counts[company] = company_counts.get(company, 0) + 1
        
        # Sort companies by application count
        sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
        
        response = f"**Company Analysis**\n\n"
        response += f"🏢 **Companies Applied To:**\n"
        
        for i, (company, count) in enumerate(sorted_companies[:15], 1):  # Top 15 companies
            response += f"{i}. {company}: {count} application{'s' if count > 1 else ''}\n"
        
        if len(sorted_companies) > 15:
            response += f"... and {len(sorted_companies) - 15} more companies.\n"
        
        return response
    
    def _get_status_analysis(self, loader: JobsDatasetLoader) -> str:
        """Analyze application statuses and success rates."""
        documents = loader.load()
        
        if not documents:
            return "No job applications found to analyze status."
        
        # Count statuses
        status_counts = {}
        for doc in documents:
            status = doc.metadata.get('status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_apps = len(documents)
        
        response = f"**Application Status Analysis**\n\n"
        response += f"📊 **Status Breakdown:**\n"
        
        for status, count in status_counts.items():
            percentage = (count / total_apps) * 100
            response += f"• {status}: {count} ({percentage:.1f}%)\n"
        
        # Calculate success metrics
        interview_count = status_counts.get('Interviewing', 0)
        offered_count = status_counts.get('Offered', 0)
        applied_count = status_counts.get('Applied', 0)
        
        if applied_count > 0:
            interview_rate = ((interview_count + offered_count) / applied_count) * 100
            response += f"\n🎯 **Success Metrics:**\n"
            response += f"• Interview Rate: {interview_rate:.1f}%\n"
        
        if interview_count > 0:
            offer_rate = (offered_count / interview_count) * 100
            response += f"• Offer Rate: {offer_rate:.1f}%\n"
        
        return response


class JobContentTool(BaseTool):
    """Tool to get detailed content of a specific job application."""
    
    name: str = "get_job_content"
    description: str = "Get detailed content and information about a specific job application by ID"
    args_schema: type[BaseModel] = BaseModel
    user_id: Optional[int] = None
    
    def __init__(self, user_id: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
    
    @traceable(name="get_job_content", metadata={"tool": "job_content"})
    def _run(self, job_id: str) -> str:
        """Get detailed content of a specific job."""
        try:
            job_id_int = int(job_id)
            loader = JobsDatasetLoader(user_id=self.user_id)
            document = loader.load_job_by_id(job_id_int)
            
            if not document:
                return f"Job with ID {job_id} not found."
            
            # Return the full content
            response = f"**Job Details (ID: {job_id})**\n\n"
            response += document.page_content
            
            # Add metadata if useful
            metadata = document.metadata
            if metadata.get('application_url'):
                response += f"\n\n**Application URL:** {metadata['application_url']}"
            
            return response
            
        except ValueError:
            return f"Invalid job ID: {job_id}. Please provide a numeric job ID."
        except Exception as e:
            return f"Error getting job content: {str(e)}"


# Helper function to get all dataset tools
def get_dataset_tools(user_id: Optional[int] = None) -> List[BaseTool]:
    """Get all dataset-aware tools for the AI agent."""
    return [
        DatasetSearchTool(user_id=user_id),
        DatasetAnalysisTool(user_id=user_id),
        JobContentTool(user_id=user_id)
    ]