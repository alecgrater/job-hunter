"""
Database models and schema for the AI Job Application Preparation Tool.

This module defines the SQLite database structure for storing jobs, applications,
contacts, and tracking information.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations for the job application system."""
    
    def __init__(self, db_path: str = "data/job_applications.db"):
        """Initialize database manager with path to SQLite database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self) -> None:
        """Initialize database with all required tables."""
        with self.get_connection() as conn:
            # Jobs table - stores scraped job postings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    description TEXT,
                    url TEXT,
                    source_url TEXT,
                    salary_range TEXT,
                    job_type TEXT,
                    posted_date TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    ai_score REAL,
                    ai_reasoning TEXT,
                    tags TEXT,
                    source TEXT,
                    job_id TEXT,
                    employment_type TEXT,
                    experience_level TEXT,
                    created_at TIMESTAMP,
                    UNIQUE(url)
                )
            """)
            
            # Applications table - tracks application preparation status
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resume_path TEXT,
                    cover_letter_path TEXT,
                    email_draft TEXT,
                    notes TEXT,
                    submitted_at TIMESTAMP,
                    response_received BOOLEAN DEFAULT FALSE,
                    response_date TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            """)
            
            # Contacts table - stores hiring manager and company contact info
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    company TEXT NOT NULL,
                    name TEXT,
                    email TEXT,
                    title TEXT,
                    linkedin_url TEXT,
                    phone TEXT,
                    source TEXT,
                    confidence_score REAL,
                    verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            """)
            
            # Batch runs table - tracks processing batches
            conn.execute("""
                CREATE TABLE IF NOT EXISTS batch_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    source_urls TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT DEFAULT 'running',
                    jobs_scraped INTEGER DEFAULT 0,
                    jobs_filtered INTEGER DEFAULT 0,
                    jobs_approved INTEGER DEFAULT 0,
                    error_log TEXT
                )
            """)
            
            # Settings table - stores user preferences and configuration
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company)")
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    # Job operations
    def insert_job(self, job_data: Dict[str, Any]) -> int:
        """Insert a new job posting into the database."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO jobs 
                (title, company, location, description, url, source_url, 
                 salary_range, job_type, posted_date, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data.get('title'),
                job_data.get('company'),
                job_data.get('location'),
                job_data.get('description'),
                job_data.get('url'),
                job_data.get('source_url'),
                job_data.get('salary_range'),
                job_data.get('job_type'),
                job_data.get('posted_date'),
                json.dumps(job_data.get('tags', []))
            ))
            return cursor.lastrowid
    
    def get_jobs(self, status: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve jobs from database with optional filtering."""
        query = "SELECT * FROM jobs"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY scraped_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            jobs = []
            for row in cursor.fetchall():
                job = dict(row)
                job['tags'] = json.loads(job['tags']) if job['tags'] else []
                jobs.append(job)
            return jobs
    
    def update_job_status(self, job_id: int, status: str, ai_score: Optional[float] = None, 
                         ai_reasoning: Optional[str] = None) -> None:
        """Update job status and AI filtering results."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE jobs 
                SET status = ?, ai_score = ?, ai_reasoning = ?
                WHERE id = ?
            """, (status, ai_score, ai_reasoning, job_id))
    
    # Application operations
    def create_application(self, job_id: int) -> int:
        """Create a new application for a job."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO applications (job_id)
                VALUES (?)
            """, (job_id,))
            return cursor.lastrowid
    
    def update_application(self, app_id: int, **kwargs) -> None:
        """Update application with provided fields."""
        if not kwargs:
            return
        
        # Always update the updated_at timestamp
        kwargs['updated_at'] = datetime.now().isoformat()
        
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [app_id]
        
        with self.get_connection() as conn:
            conn.execute(f"""
                UPDATE applications 
                SET {fields}
                WHERE id = ?
            """, values)
    
    def get_applications(self, status: Optional[str] = None) -> List[Dict]:
        """Get applications with job details."""
        query = """
            SELECT a.*, j.title, j.company, j.location, j.url
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
        """
        params = []
        
        if status:
            query += " WHERE a.status = ?"
            params.append(status)
        
        query += " ORDER BY a.updated_at DESC"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # Contact operations
    def insert_contact(self, contact_data: Dict[str, Any]) -> int:
        """Insert contact information."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO contacts 
                (job_id, company, name, email, title, linkedin_url, phone, 
                 source, confidence_score, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact_data.get('job_id'),
                contact_data.get('company'),
                contact_data.get('name'),
                contact_data.get('email'),
                contact_data.get('title'),
                contact_data.get('linkedin_url'),
                contact_data.get('phone'),
                contact_data.get('source'),
                contact_data.get('confidence_score'),
                contact_data.get('verified', False)
            ))
            return cursor.lastrowid
    
    def get_contacts_for_job(self, job_id: int) -> List[Dict]:
        """Get all contacts for a specific job."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM contacts 
                WHERE job_id = ? 
                ORDER BY confidence_score DESC
            """, (job_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Batch run operations
    def create_batch_run(self, name: str, source_urls: List[str]) -> int:
        """Create a new batch processing run."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO batch_runs (name, source_urls)
                VALUES (?, ?)
            """, (name, json.dumps(source_urls)))
            return cursor.lastrowid
    
    def update_batch_run(self, batch_id: int, **kwargs) -> None:
        """Update batch run with provided fields."""
        if not kwargs:
            return
        
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [batch_id]
        
        with self.get_connection() as conn:
            conn.execute(f"""
                UPDATE batch_runs 
                SET {fields}
                WHERE id = ?
            """, values)
    
    def get_batch_runs(self, limit: int = 10) -> List[Dict]:
        """Get recent batch runs."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM batch_runs 
                ORDER BY started_at DESC 
                LIMIT ?
            """, (limit,))
            runs = []
            for row in cursor.fetchall():
                run = dict(row)
                run['source_urls'] = json.loads(run['source_urls']) if run['source_urls'] else []
                runs.append(run)
            return runs
    
    # Settings operations
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            return default
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value."""
        with self.get_connection() as conn:
            json_value = json.dumps(value) if not isinstance(value, str) else value
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, json_value))
    
    # Analytics and reporting
    def get_stats(self) -> Dict[str, Any]:
        """Get application statistics."""
        with self.get_connection() as conn:
            stats = {}
            
            # Job stats
            cursor = conn.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status")
            stats['jobs_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Application stats
            cursor = conn.execute("SELECT status, COUNT(*) as count FROM applications GROUP BY status")
            stats['applications_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM jobs 
                WHERE scraped_at > datetime('now', '-7 days')
            """)
            stats['jobs_last_week'] = cursor.fetchone()['count']
            
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM applications 
                WHERE created_at > datetime('now', '-7 days')
            """)
            stats['applications_last_week'] = cursor.fetchone()['count']
            
            return stats
    
    def get_recent_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs for dashboard activity feed."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, title, company, location, status, scraped_at, ai_score
                    FROM jobs 
                    ORDER BY scraped_at DESC 
                    LIMIT ?
                """, (limit,))
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting recent jobs: {e}")
            return []
    
    def get_jobs_filtered(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get jobs with applied filters."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM jobs WHERE 1=1"
                params = []
                
                # Apply filters
                if filters.get('status'):
                    query += " AND status = ?"
                    params.append(filters['status'])
                
                if filters.get('company'):
                    query += " AND company LIKE ?"
                    params.append(f"%{filters['company']}%")
                
                if filters.get('location'):
                    query += " AND location LIKE ?"
                    params.append(f"%{filters['location']}%")
                
                if filters.get('min_score'):
                    query += " AND ai_score >= ?"
                    params.append(filters['min_score'])
                
                query += " ORDER BY scraped_at DESC"
                
                if filters.get('limit'):
                    query += " LIMIT ?"
                    params.append(filters['limit'])
                
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting filtered jobs: {e}")
            return []