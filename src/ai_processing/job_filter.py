"""
AI Job Filtering System

This module provides AI-powered job filtering capabilities using configurable LLM backends.
It analyzes job postings and determines their relevance based on user preferences and criteria.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .llm_manager import LLMManager, generate_structured_response
from ..config.database import DatabaseManager

logger = logging.getLogger(__name__)


class FilterDecision(Enum):
    """Job filtering decisions."""
    ACCEPT = "accept"
    REJECT = "reject"
    MAYBE = "maybe"


@dataclass
class FilterCriteria:
    """Job filtering criteria configuration."""
    required_skills: List[str]
    preferred_skills: List[str]
    excluded_skills: List[str]
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    preferred_locations: List[str] = None
    excluded_locations: List[str] = None
    experience_levels: List[str] = None
    employment_types: List[str] = None
    company_preferences: List[str] = None
    excluded_companies: List[str] = None
    keywords_include: List[str] = None
    keywords_exclude: List[str] = None
    remote_preference: Optional[str] = None  # "required", "preferred", "no_preference", "not_preferred"


@dataclass
class FilterResult:
    """Result of job filtering analysis."""
    job_id: int
    decision: FilterDecision
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    matched_criteria: List[str]
    concerns: List[str]
    salary_match: Optional[bool] = None
    location_match: Optional[bool] = None
    skills_match_score: Optional[float] = None
    overall_score: Optional[float] = None
    processed_at: datetime = None

    def __post_init__(self):
        if self.processed_at is None:
            self.processed_at = datetime.now(timezone.utc)


class AIJobFilter:
    """
    AI-powered job filtering system using LLM backends.
    
    This system analyzes job postings against user-defined criteria and provides
    intelligent filtering decisions with detailed reasoning.
    """
    
    def __init__(self, db_manager: DatabaseManager, llm_manager: Optional[LLMManager] = None):
        """
        Initialize the AI job filter.
        
        Args:
            db_manager: Database manager instance
            llm_manager: LLM manager instance (optional, will create if not provided)
        """
        self.db_manager = db_manager
        self.llm_manager = llm_manager or LLMManager()
    
    def _build_filter_prompt(self, job_data: Dict[str, Any], criteria: FilterCriteria) -> str:
        """
        Build the prompt for LLM job filtering analysis.
        
        Args:
            job_data: Job posting data
            criteria: Filtering criteria
            
        Returns:
            Formatted prompt for LLM analysis
        """
        prompt = f"""
Analyze the following job posting against the provided criteria and determine if it's a good match.

JOB POSTING:
Title: {job_data.get('title', 'N/A')}
Company: {job_data.get('company', 'N/A')}
Location: {job_data.get('location', 'N/A')}
Employment Type: {job_data.get('employment_type', 'N/A')}
Experience Level: {job_data.get('experience_level', 'N/A')}
Salary Range: {job_data.get('salary_range', 'N/A')}
Description: {job_data.get('description', 'N/A')[:2000]}...

FILTERING CRITERIA:
Required Skills: {', '.join(criteria.required_skills) if criteria.required_skills else 'None'}
Preferred Skills: {', '.join(criteria.preferred_skills) if criteria.preferred_skills else 'None'}
Excluded Skills: {', '.join(criteria.excluded_skills) if criteria.excluded_skills else 'None'}
Salary Range: {f"${criteria.min_salary:,}" if criteria.min_salary else "No min"} - {f"${criteria.max_salary:,}" if criteria.max_salary else "No max"}
Preferred Locations: {', '.join(criteria.preferred_locations) if criteria.preferred_locations else 'Any'}
Excluded Locations: {', '.join(criteria.excluded_locations) if criteria.excluded_locations else 'None'}
Experience Levels: {', '.join(criteria.experience_levels) if criteria.experience_levels else 'Any'}
Employment Types: {', '.join(criteria.employment_types) if criteria.employment_types else 'Any'}
Preferred Companies: {', '.join(criteria.company_preferences) if criteria.company_preferences else 'Any'}
Excluded Companies: {', '.join(criteria.excluded_companies) if criteria.excluded_companies else 'None'}
Include Keywords: {', '.join(criteria.keywords_include) if criteria.keywords_include else 'None'}
Exclude Keywords: {', '.join(criteria.keywords_exclude) if criteria.keywords_exclude else 'None'}
Remote Preference: {criteria.remote_preference or 'No preference'}

Please analyze this job posting and provide a detailed assessment.
"""
        return prompt
    
    def _get_response_format(self) -> Dict[str, Any]:
        """Get the expected JSON response format for LLM analysis."""
        return {
            "decision": "accept|reject|maybe",
            "confidence_score": 0.85,
            "reasoning": "Detailed explanation of the decision",
            "matched_criteria": ["List of criteria that matched"],
            "concerns": ["List of potential concerns or red flags"],
            "salary_match": True,
            "location_match": True,
            "skills_match_score": 0.75,
            "overall_score": 0.80,
            "key_highlights": ["Notable positive aspects"],
            "missing_requirements": ["Important requirements not clearly mentioned"]
        }
    
    async def analyze_job(self, job_data: Dict[str, Any], criteria: FilterCriteria, 
                         provider: Optional[str] = None) -> FilterResult:
        """
        Analyze a single job posting against filtering criteria.
        
        Args:
            job_data: Job posting data dictionary
            criteria: Filtering criteria
            provider: Specific LLM provider to use
            
        Returns:
            FilterResult with analysis details
        """
        try:
            # Build analysis prompt
            prompt = self._build_filter_prompt(job_data, criteria)
            
            # Get structured response from LLM
            system_message = """
You are an expert job matching analyst. Analyze job postings against candidate criteria and provide detailed, objective assessments.

Consider these factors:
1. Skills alignment (required vs preferred vs excluded)
2. Salary compatibility
3. Location preferences
4. Experience level match
5. Company culture fit
6. Growth opportunities
7. Red flags or concerns

Be thorough but concise in your reasoning. Provide actionable insights.
"""
            
            response = await generate_structured_response(
                prompt=prompt,
                response_format=self._get_response_format(),
                system_message=system_message,
                provider=provider,
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=1000
            )
            
            if not response:
                logger.error("Failed to get LLM response for job analysis")
                return FilterResult(
                    job_id=job_data.get('id', 0),
                    decision=FilterDecision.MAYBE,
                    confidence_score=0.0,
                    reasoning="Failed to analyze job posting due to LLM error",
                    matched_criteria=[],
                    concerns=["Analysis failed"]
                )
            
            # Parse LLM response
            decision_str = response.get('decision', 'maybe').lower()
            decision = FilterDecision.ACCEPT if decision_str == 'accept' else \
                      FilterDecision.REJECT if decision_str == 'reject' else \
                      FilterDecision.MAYBE
            
            return FilterResult(
                job_id=job_data.get('id', 0),
                decision=decision,
                confidence_score=min(max(response.get('confidence_score', 0.5), 0.0), 1.0),
                reasoning=response.get('reasoning', 'No reasoning provided'),
                matched_criteria=response.get('matched_criteria', []),
                concerns=response.get('concerns', []),
                salary_match=response.get('salary_match'),
                location_match=response.get('location_match'),
                skills_match_score=response.get('skills_match_score'),
                overall_score=response.get('overall_score')
            )
            
        except Exception as e:
            logger.error(f"Error analyzing job {job_data.get('id', 'unknown')}: {e}")
            return FilterResult(
                job_id=job_data.get('id', 0),
                decision=FilterDecision.MAYBE,
                confidence_score=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                matched_criteria=[],
                concerns=["Technical error during analysis"]
            )
    
    async def filter_jobs_batch(self, job_ids: List[int], criteria: FilterCriteria,
                               provider: Optional[str] = None, 
                               batch_size: int = 5) -> List[FilterResult]:
        """
        Filter multiple jobs in batches to avoid overwhelming the LLM.
        
        Args:
            job_ids: List of job IDs to analyze
            criteria: Filtering criteria
            provider: Specific LLM provider to use
            batch_size: Number of jobs to process concurrently
            
        Returns:
            List of FilterResult objects
        """
        results = []
        
        try:
            # Get job data from database
            jobs_data = self._get_jobs_data(job_ids)
            
            if not jobs_data:
                logger.warning("No job data found for provided IDs")
                return results
            
            # Process jobs in batches
            for i in range(0, len(jobs_data), batch_size):
                batch = jobs_data[i:i + batch_size]
                
                # Create analysis tasks for the batch
                tasks = [
                    self.analyze_job(job_data, criteria, provider)
                    for job_data in batch
                ]
                
                # Execute batch concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch analysis error: {result}")
                        continue
                    results.append(result)
                
                # Small delay between batches to be respectful to LLM APIs
                if i + batch_size < len(jobs_data):
                    await asyncio.sleep(1)
            
            logger.info(f"Completed filtering analysis for {len(results)} jobs")
            
        except Exception as e:
            logger.error(f"Error in batch job filtering: {e}")
        
        return results
    
    def _get_jobs_data(self, job_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Retrieve job data from database for analysis.
        
        Args:
            job_ids: List of job IDs
            
        Returns:
            List of job data dictionaries
        """
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Build query with placeholders
            placeholders = ','.join(['?' for _ in job_ids])
            query = f"""
            SELECT id, title, company, location, description, url, posted_date,
                   source, job_id, salary_range, employment_type, experience_level
            FROM jobs 
            WHERE id IN ({placeholders})
            """
            
            cursor.execute(query, job_ids)
            rows = cursor.fetchall()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            jobs_data = [dict(zip(columns, row)) for row in rows]
            
            return jobs_data
            
        except Exception as e:
            logger.error(f"Error retrieving job data: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def save_filter_results(self, results: List[FilterResult]) -> int:
        """
        Save filtering results to database.
        
        Args:
            results: List of FilterResult objects
            
        Returns:
            Number of results successfully saved
        """
        saved_count = 0
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Create filter_results table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS filter_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                decision TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                reasoning TEXT,
                matched_criteria TEXT,
                concerns TEXT,
                salary_match BOOLEAN,
                location_match BOOLEAN,
                skills_match_score REAL,
                overall_score REAL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
            """)
            
            for result in results:
                try:
                    # Check if result already exists
                    cursor.execute(
                        "SELECT id FROM filter_results WHERE job_id = ?",
                        (result.job_id,)
                    )
                    
                    if cursor.fetchone():
                        # Update existing result
                        cursor.execute("""
                        UPDATE filter_results SET
                            decision = ?, confidence_score = ?, reasoning = ?,
                            matched_criteria = ?, concerns = ?, salary_match = ?,
                            location_match = ?, skills_match_score = ?, overall_score = ?,
                            processed_at = ?
                        WHERE job_id = ?
                        """, (
                            result.decision.value,
                            result.confidence_score,
                            result.reasoning,
                            json.dumps(result.matched_criteria),
                            json.dumps(result.concerns),
                            result.salary_match,
                            result.location_match,
                            result.skills_match_score,
                            result.overall_score,
                            result.processed_at,
                            result.job_id
                        ))
                    else:
                        # Insert new result
                        cursor.execute("""
                        INSERT INTO filter_results (
                            job_id, decision, confidence_score, reasoning,
                            matched_criteria, concerns, salary_match, location_match,
                            skills_match_score, overall_score, processed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            result.job_id,
                            result.decision.value,
                            result.confidence_score,
                            result.reasoning,
                            json.dumps(result.matched_criteria),
                            json.dumps(result.concerns),
                            result.salary_match,
                            result.location_match,
                            result.skills_match_score,
                            result.overall_score,
                            result.processed_at
                        ))
                    
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to save filter result for job {result.job_id}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"Successfully saved {saved_count} filter results")
            
        except Exception as e:
            logger.error(f"Database error while saving filter results: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        return saved_count
    
    def get_filter_results(self, job_ids: Optional[List[int]] = None, 
                          decision: Optional[FilterDecision] = None,
                          min_confidence: Optional[float] = None) -> List[FilterResult]:
        """
        Retrieve filter results from database.
        
        Args:
            job_ids: Specific job IDs to retrieve (optional)
            decision: Filter by decision type (optional)
            min_confidence: Minimum confidence score (optional)
            
        Returns:
            List of FilterResult objects
        """
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM filter_results WHERE 1=1"
            params = []
            
            if job_ids:
                placeholders = ','.join(['?' for _ in job_ids])
                query += f" AND job_id IN ({placeholders})"
                params.extend(job_ids)
            
            if decision:
                query += " AND decision = ?"
                params.append(decision.value)
            
            if min_confidence is not None:
                query += " AND confidence_score >= ?"
                params.append(min_confidence)
            
            query += " ORDER BY processed_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to FilterResult objects
            results = []
            for row in rows:
                results.append(FilterResult(
                    job_id=row[1],
                    decision=FilterDecision(row[2]),
                    confidence_score=row[3],
                    reasoning=row[4],
                    matched_criteria=json.loads(row[5]) if row[5] else [],
                    concerns=json.loads(row[6]) if row[6] else [],
                    salary_match=row[7],
                    location_match=row[8],
                    skills_match_score=row[9],
                    overall_score=row[10],
                    processed_at=datetime.fromisoformat(row[11]) if row[11] else None
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving filter results: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    async def filter_and_save_jobs(self, job_ids: List[int], criteria: FilterCriteria,
                                  provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete workflow: filter jobs and save results.
        
        Args:
            job_ids: List of job IDs to filter
            criteria: Filtering criteria
            provider: Specific LLM provider to use
            
        Returns:
            Summary of filtering results
        """
        start_time = datetime.now()
        
        # Filter jobs
        results = await self.filter_jobs_batch(job_ids, criteria, provider)
        
        # Save results
        saved_count = self.save_filter_results(results)
        
        # Generate summary
        summary = {
            'total_jobs': len(job_ids),
            'analyzed_jobs': len(results),
            'saved_results': saved_count,
            'accepted_jobs': len([r for r in results if r.decision == FilterDecision.ACCEPT]),
            'rejected_jobs': len([r for r in results if r.decision == FilterDecision.REJECT]),
            'maybe_jobs': len([r for r in results if r.decision == FilterDecision.MAYBE]),
            'avg_confidence': sum(r.confidence_score for r in results) / len(results) if results else 0,
            'processing_time': (datetime.now() - start_time).total_seconds(),
            'provider_used': provider or 'default'
        }
        
        logger.info(f"Job filtering completed: {summary}")
        return summary


# Convenience functions
def create_default_criteria() -> FilterCriteria:
    """Create default filtering criteria."""
    return FilterCriteria(
        required_skills=[],
        preferred_skills=[],
        excluded_skills=[],
        preferred_locations=[],
        excluded_locations=[],
        experience_levels=[],
        employment_types=[],
        company_preferences=[],
        excluded_companies=[],
        keywords_include=[],
        keywords_exclude=[]
    )


def create_criteria_from_dict(criteria_dict: Dict[str, Any]) -> FilterCriteria:
    """Create FilterCriteria from dictionary."""
    return FilterCriteria(**criteria_dict)