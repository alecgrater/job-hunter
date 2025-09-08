"""
LinkedIn RSS Feed Scraper

This module provides functionality to scrape job postings from LinkedIn RSS feeds.
It extracts job data and stores it in the database for further processing.
"""

import feedparser
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, parse_qs
import re
import time
import logging
from dataclasses import dataclass

from ..config.database import DatabaseManager
from ..utils.rate_limiter import RateLimitConfig, RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class JobPosting:
    """Data class for job posting information."""
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_date: datetime
    source: str = "linkedin"
    job_id: Optional[str] = None
    salary_range: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    skills: Optional[List[str]] = None


class LinkedInRSScraper:
    """
    LinkedIn RSS Feed Scraper for job postings.
    
    This scraper fetches job postings from LinkedIn RSS feeds and extracts
    relevant job information for storage and processing.
    """
    
    def __init__(self, db_manager: DatabaseManager, rate_limit_calls: int = 10, rate_limit_period: int = 60):
        """
        Initialize the LinkedIn RSS scraper.
        
        Args:
            db_manager: Database manager instance
            rate_limit_calls: Number of calls allowed per period
            rate_limit_period: Time period in seconds for rate limiting
        """
        self.db_manager = db_manager
        
        # Create rate limit config
        rate_config = RateLimitConfig(
            requests_per_minute=rate_limit_calls,
            requests_per_hour=rate_limit_calls * 6,  # Conservative hourly limit
            cooldown_seconds=rate_limit_period / rate_limit_calls
        )
        self.rate_limiter = RateLimiter(rate_config)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def build_linkedin_rss_url(self, keywords: str, location: str = "", 
                              experience_level: str = "", job_type: str = "") -> str:
        """
        Build LinkedIn RSS feed URL with search parameters.
        
        Args:
            keywords: Job search keywords
            location: Job location
            experience_level: Experience level filter
            job_type: Job type filter
            
        Returns:
            LinkedIn RSS feed URL
        """
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        
        params = {
            'keywords': keywords,
            'location': location,
            'f_E': experience_level,  # Experience level
            'f_JT': job_type,  # Job type
            'start': '0',
            'count': '25'
        }
        
        # Remove empty parameters
        params = {k: v for k, v in params.items() if v}
        
        # Build URL manually to ensure proper formatting
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"
    
    def extract_job_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract job ID from LinkedIn job URL.
        
        Args:
            url: LinkedIn job URL
            
        Returns:
            Job ID if found, None otherwise
        """
        try:
            # LinkedIn job URLs typically contain the job ID
            match = re.search(r'/jobs/view/(\d+)', url)
            if match:
                return match.group(1)
            
            # Alternative pattern for different URL formats
            match = re.search(r'currentJobId=(\d+)', url)
            if match:
                return match.group(1)
                
            return None
        except Exception as e:
            logger.warning(f"Failed to extract job ID from URL {url}: {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove extra whitespace
        text = text.strip()
        
        return text
    
    def extract_job_details(self, entry: Dict[str, Any]) -> Optional[JobPosting]:
        """
        Extract job details from RSS feed entry.
        
        Args:
            entry: RSS feed entry
            
        Returns:
            JobPosting object if extraction successful, None otherwise
        """
        try:
            # Extract basic information
            title = self.clean_text(entry.get('title', ''))
            link = entry.get('link', '')
            description = self.clean_text(entry.get('summary', ''))
            
            if not title or not link:
                logger.warning("Missing required fields (title or link) in RSS entry")
                return None
            
            # Extract job ID
            job_id = self.extract_job_id_from_url(link)
            
            # Parse published date
            published_date = datetime.now(timezone.utc)
            if 'published_parsed' in entry and entry['published_parsed']:
                try:
                    published_date = datetime(*entry['published_parsed'][:6], tzinfo=timezone.utc)
                except Exception as e:
                    logger.warning(f"Failed to parse published date: {e}")
            
            # Extract company and location from title or description
            company = "Unknown"
            location = "Unknown"
            
            # Try to extract company from title (common format: "Job Title at Company Name")
            title_match = re.search(r'\s+at\s+(.+?)(?:\s+in\s+(.+))?$', title, re.IGNORECASE)
            if title_match:
                company = title_match.group(1).strip()
                if title_match.group(2):
                    location = title_match.group(2).strip()
                # Clean title by removing the "at Company" part
                title = re.sub(r'\s+at\s+.+$', '', title, flags=re.IGNORECASE).strip()
            
            # Try to extract location from description if not found in title
            if location == "Unknown":
                location_match = re.search(r'Location[:\s]+([^,\n]+)', description, re.IGNORECASE)
                if location_match:
                    location = location_match.group(1).strip()
            
            # Extract employment type
            employment_type = None
            type_patterns = [
                r'Full[- ]?time',
                r'Part[- ]?time',
                r'Contract',
                r'Temporary',
                r'Internship',
                r'Freelance'
            ]
            
            for pattern in type_patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    employment_type = re.search(pattern, description, re.IGNORECASE).group(0)
                    break
            
            # Extract experience level
            experience_level = None
            exp_patterns = [
                r'Entry[- ]?level',
                r'Junior',
                r'Senior',
                r'Lead',
                r'Principal',
                r'Manager',
                r'Director'
            ]
            
            for pattern in exp_patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    experience_level = re.search(pattern, description, re.IGNORECASE).group(0)
                    break
            
            # Extract salary information
            salary_range = None
            salary_patterns = [
                r'\$[\d,]+(?:\s*-\s*\$?[\d,]+)?(?:\s*(?:per\s+)?(?:year|annually|yr))?',
                r'[\d,]+k?(?:\s*-\s*[\d,]+k?)?\s*(?:per\s+)?(?:year|annually|yr)',
            ]
            
            for pattern in salary_patterns:
                salary_match = re.search(pattern, description, re.IGNORECASE)
                if salary_match:
                    salary_range = salary_match.group(0)
                    break
            
            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=description,
                url=link,
                posted_date=published_date,
                job_id=job_id,
                salary_range=salary_range,
                employment_type=employment_type,
                experience_level=experience_level,
                skills=[]  # Skills extraction can be enhanced later
            )
            
        except Exception as e:
            logger.error(f"Failed to extract job details from RSS entry: {e}")
            return None
    
    def fetch_rss_feed(self, rss_url: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch and parse RSS feed from URL.
        
        Args:
            rss_url: RSS feed URL
            
        Returns:
            List of RSS entries if successful, None otherwise
        """
        try:
            # Simple time-based rate limiting for synchronous usage
            import time
            current_time = time.time()
            if hasattr(self, '_last_request_time'):
                time_since_last = current_time - self._last_request_time
                min_interval = 60.0 / self.rate_limiter.config.requests_per_minute
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
            
            self._last_request_time = time.time()
            
            logger.info(f"Fetching RSS feed from: {rss_url}")
            
            response = self.session.get(rss_url, timeout=30)
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"RSS feed parsing warning: {feed.bozo_exception}")
            
            if not feed.entries:
                logger.warning("No entries found in RSS feed")
                return []
            
            logger.info(f"Successfully fetched {len(feed.entries)} entries from RSS feed")
            return feed.entries
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch RSS feed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching RSS feed: {e}")
            return None
    
    def scrape_jobs(self, keywords: str, location: str = "", 
                   experience_level: str = "", job_type: str = "",
                   max_jobs: int = 100) -> List[JobPosting]:
        """
        Scrape jobs from LinkedIn RSS feed.
        
        Args:
            keywords: Job search keywords
            location: Job location filter
            experience_level: Experience level filter
            job_type: Job type filter
            max_jobs: Maximum number of jobs to scrape
            
        Returns:
            List of JobPosting objects
        """
        jobs = []
        
        try:
            # Build RSS URL
            rss_url = self.build_linkedin_rss_url(keywords, location, experience_level, job_type)
            
            # Fetch RSS feed entries
            entries = self.fetch_rss_feed(rss_url)
            if not entries:
                return jobs
            
            # Process entries
            for entry in entries[:max_jobs]:
                job_posting = self.extract_job_details(entry)
                if job_posting:
                    jobs.append(job_posting)
                
                # Add small delay between processing entries
                time.sleep(0.1)
            
            logger.info(f"Successfully scraped {len(jobs)} jobs for keywords: {keywords}")
            
        except Exception as e:
            logger.error(f"Failed to scrape jobs: {e}")
        
        return jobs
    
    def save_jobs_to_database(self, jobs: List[JobPosting]) -> int:
        """
        Save job postings to database.
        
        Args:
            jobs: List of JobPosting objects
            
        Returns:
            Number of jobs successfully saved
        """
        saved_count = 0
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            for job in jobs:
                try:
                    # Check if job already exists (by URL or job_id)
                    existing_query = """
                    SELECT id FROM jobs 
                    WHERE url = ? OR (job_id IS NOT NULL AND job_id = ?)
                    """
                    cursor.execute(existing_query, (job.url, job.job_id))
                    
                    if cursor.fetchone():
                        logger.debug(f"Job already exists, skipping: {job.title}")
                        continue
                    
                    # Insert new job
                    insert_query = """
                    INSERT INTO jobs (
                        title, company, location, description, url, posted_date,
                        source, job_id, salary_range, employment_type, 
                        experience_level, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    cursor.execute(insert_query, (
                        job.title,
                        job.company,
                        job.location,
                        job.description,
                        job.url,
                        job.posted_date,
                        job.source,
                        job.job_id,
                        job.salary_range,
                        job.employment_type,
                        job.experience_level,
                        datetime.now(timezone.utc)
                    ))
                    
                    saved_count += 1
                    logger.debug(f"Saved job: {job.title} at {job.company}")
                    
                except Exception as e:
                    logger.error(f"Failed to save job {job.title}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"Successfully saved {saved_count} jobs to database")
            
        except Exception as e:
            logger.error(f"Database error while saving jobs: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        return saved_count
    
    def scrape_and_save_jobs(self, keywords: str, location: str = "",
                           experience_level: str = "", job_type: str = "",
                           max_jobs: int = 100) -> Dict[str, int]:
        """
        Scrape jobs and save them to database in one operation.
        
        Args:
            keywords: Job search keywords
            location: Job location filter
            experience_level: Experience level filter
            job_type: Job type filter
            max_jobs: Maximum number of jobs to scrape
            
        Returns:
            Dictionary with scraping results
        """
        start_time = time.time()
        
        # Scrape jobs
        jobs = self.scrape_jobs(keywords, location, experience_level, job_type, max_jobs)
        
        # Save to database
        saved_count = self.save_jobs_to_database(jobs)
        
        end_time = time.time()
        duration = end_time - start_time
        
        results = {
            'scraped_count': len(jobs),
            'saved_count': saved_count,
            'duration_seconds': round(duration, 2),
            'keywords': keywords,
            'location': location
        }
        
        logger.info(f"Scraping completed: {results}")
        return results