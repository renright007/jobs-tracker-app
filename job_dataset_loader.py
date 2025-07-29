"""
LangChain Dataset Loader for Jobs Database

This module creates a custom LangChain document loader that reads from your SQLite 
jobs database and converts job records into LangChain Document objects for use 
with your AI agent.
"""

import sqlite3
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime

from langchain_core.documents import Document
from langchain.docstore.document import Document as LangChainDocument
from utils import get_db_connection

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


class JobsDatasetLoader:
    """
    Custom LangChain document loader for the jobs database.
    
    Converts job application records into LangChain Document objects
    with rich metadata for use with AI agents.
    """
    
    def __init__(self, user_id: Optional[int] = None):
        """Initialize the jobs dataset loader."""
        self.user_id = user_id
    
    @traceable(name="load_jobs_dataset", metadata={"loader": "jobs_database"})
    def load(self) -> List[Document]:
        """
        Load all job records from the database as LangChain Documents.
        
        Returns:
            List[Document]: List of LangChain Document objects
        """
        try:
            conn = get_db_connection()
            
            # Query based on user_id if provided
            if self.user_id:
                query = "SELECT * FROM jobs WHERE user_id = ? ORDER BY date_added DESC"
                params = (self.user_id,)
            else:
                query = "SELECT * FROM jobs ORDER BY date_added DESC"
                params = ()
            
            jobs_df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if jobs_df.empty:
                return []
            
            documents = []
            for _, job in jobs_df.iterrows():
                doc = self._create_document_from_job(job)
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"Error loading jobs dataset: {str(e)}")
            return []
    
    def _create_document_from_job(self, job: pd.Series) -> Document:
        """
        Convert a job record into a LangChain Document.
        
        Args:
            job (pd.Series): Job record from database
            
        Returns:
            Document: LangChain Document object
        """
        # Create the main content - combine key information
        content_parts = []
        
        # Add company and job title
        if job.get('company_name'):
            content_parts.append(f"Company: {job['company_name']}")
        if job.get('job_title'):
            content_parts.append(f"Position: {job['job_title']}")
        
        # Add location and salary if available
        if job.get('location'):
            content_parts.append(f"Location: {job['location']}")
        if job.get('salary'):
            content_parts.append(f"Salary: {job['salary']}")
        
        # Add job description (main content)
        if job.get('job_description'):
            content_parts.append(f"Description: {job['job_description']}")
        
        # Add application details
        if job.get('status'):
            content_parts.append(f"Application Status: {job['status']}")
        if job.get('notes'):
            content_parts.append(f"Notes: {job['notes']}")
        
        # Combine all content
        page_content = "\n\n".join(content_parts)
        
        # Create metadata dictionary
        metadata = {
            "job_id": int(job['id']) if job.get('id') else None,
            "company_name": job.get('company_name', ''),
            "job_title": job.get('job_title', ''),
            "status": job.get('status', ''),
            "sentiment": job.get('sentiment', ''),
            "location": job.get('location', ''),
            "salary": job.get('salary', ''),
            "application_url": job.get('application_url', ''),
            "date_added": job.get('date_added', ''),
            "applied_date": job.get('applied_date', ''),
            "user_id": job.get('user_id', None),
            "document_type": "job_application",
            "source": "jobs_database"
        }
        
        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        return Document(
            page_content=page_content,
            metadata=metadata
        )
    
    @traceable(name="load_job_by_id", metadata={"loader": "jobs_database"})
    def load_job_by_id(self, job_id: int) -> Optional[Document]:
        """
        Load a specific job by ID as a LangChain Document.
        
        Args:
            job_id (int): Job ID to load
            
        Returns:
            Optional[Document]: LangChain Document object or None if not found
        """
        try:
            conn = get_db_connection()
            
            if self.user_id:
                query = "SELECT * FROM jobs WHERE id = ? AND user_id = ?"
                params = (job_id, self.user_id)
            else:
                query = "SELECT * FROM jobs WHERE id = ?"
                params = (job_id,)
            
            jobs_df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if jobs_df.empty:
                return None
            
            job = jobs_df.iloc[0]
            return self._create_document_from_job(job)
            
        except Exception as e:
            print(f"Error loading job {job_id}: {str(e)}")
            return None
    
    @traceable(name="search_jobs", metadata={"loader": "jobs_database"})
    def search_jobs(self, 
                   company: Optional[str] = None,
                   status: Optional[str] = None,
                   keyword: Optional[str] = None) -> List[Document]:
        """
        Search for jobs with specific criteria.
        
        Args:
            company (Optional[str]): Company name to filter by
            status (Optional[str]): Application status to filter by
            keyword (Optional[str]): Keyword to search in descriptions
            
        Returns:
            List[Document]: List of matching LangChain Document objects
        """
        try:
            conn = get_db_connection()
            
            # Build query based on filters
            where_conditions = []
            params = []
            
            if self.user_id:
                where_conditions.append("user_id = ?")
                params.append(self.user_id)
            
            if company:
                where_conditions.append("company_name LIKE ?")
                params.append(f"%{company}%")
            
            if status:
                where_conditions.append("status = ?")
                params.append(status)
            
            if keyword:
                where_conditions.append("(job_description LIKE ? OR job_title LIKE ? OR notes LIKE ?)")
                params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
            
            # Construct final query
            query = "SELECT * FROM jobs"
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
            query += " ORDER BY date_added DESC"
            
            jobs_df = pd.read_sql_query(query, conn, params=tuple(params))
            conn.close()
            
            if jobs_df.empty:
                return []
            
            documents = []
            for _, job in jobs_df.iterrows():
                doc = self._create_document_from_job(job)
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"Error searching jobs: {str(e)}")
            return []
    
    def get_dataset_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the jobs dataset.
        
        Returns:
            Dict[str, Any]: Dataset statistics
        """
        try:
            conn = get_db_connection()
            
            if self.user_id:
                query = "SELECT * FROM jobs WHERE user_id = ?"
                params = (self.user_id,)
            else:
                query = "SELECT * FROM jobs"
                params = ()
            
            jobs_df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if jobs_df.empty:
                return {"total_jobs": 0}
            
            stats = {
                "total_jobs": len(jobs_df),
                "companies": jobs_df['company_name'].nunique() if 'company_name' in jobs_df.columns else 0,
                "status_breakdown": jobs_df['status'].value_counts().to_dict() if 'status' in jobs_df.columns else {},
                "sentiment_breakdown": jobs_df['sentiment'].value_counts().to_dict() if 'sentiment' in jobs_df.columns else {},
                "date_range": {
                    "earliest": jobs_df['date_added'].min() if 'date_added' in jobs_df.columns else None,
                    "latest": jobs_df['date_added'].max() if 'date_added' in jobs_df.columns else None
                }
            }
            
            return stats
            
        except Exception as e:
            print(f"Error getting dataset stats: {str(e)}")
            return {"error": str(e)}


# Helper functions for easy access
def load_user_jobs_dataset(user_id: Optional[int] = None) -> List[Document]:
    """
    Load all jobs for a user as LangChain Documents.
    
    Args:
        user_id (Optional[int]): User ID to filter by
        
    Returns:
        List[Document]: List of job documents
    """
    loader = JobsDatasetLoader(user_id=user_id)
    return loader.load()


def load_job_document(job_id: int, user_id: Optional[int] = None) -> Optional[Document]:
    """
    Load a specific job as a LangChain Document.
    
    Args:
        job_id (int): Job ID to load
        user_id (Optional[int]): User ID for security
        
    Returns:
        Optional[Document]: Job document or None if not found
    """
    loader = JobsDatasetLoader(user_id=user_id)
    return loader.load_job_by_id(job_id)


def search_jobs_dataset(user_id: Optional[int] = None, **kwargs) -> List[Document]:
    """
    Search jobs dataset with filters.
    
    Args:
        user_id (Optional[int]): User ID to filter by
        **kwargs: Search filters (company, status, keyword)
        
    Returns:
        List[Document]: List of matching job documents
    """
    loader = JobsDatasetLoader(user_id=user_id)
    return loader.search_jobs(**kwargs)


# Test function
if __name__ == "__main__":
    # Test the loader
    loader = JobsDatasetLoader()
    documents = loader.load()
    
    print(f"Loaded {len(documents)} job documents")
    
    if documents:
        print("\nFirst document:")
        print(f"Content preview: {documents[0].page_content[:200]}...")
        print(f"Metadata: {documents[0].metadata}")
        
        # Test statistics
        stats = loader.get_dataset_stats()
        print(f"\nDataset stats: {stats}")