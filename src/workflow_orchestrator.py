"""
Batch Processing Workflow Orchestrator

This module provides comprehensive batch processing capabilities that coordinate
all the AI job application preparation steps: filtering, resume customization,
contact finding, email generation, and document creation.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging

from ..ai_processing import (
    AIJobFilter, AIResumeCustomizer, FilterCriteria, CustomizationResult,
    create_customization_request_from_job
)
from ..contact_finder import ContactFinder, ContactSearchResult
from ..email_composer import EmailGenerator, EmailGenerationRequest, GeneratedEmail
from ..document_manager import (
    DocumentManager, DocumentGenerationRequest, DocumentPackage
)
from ..config.database import DatabaseManager
from ..utils import get_logger

logger = get_logger(__name__)

class ProcessingStatus(Enum):
    """Processing status for workflow steps."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowStep:
    """Individual workflow step."""
    name: str
    status: ProcessingStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None

@dataclass
class JobProcessingResult:
    """Complete processing result for a single job."""
    job_id: int
    job_title: str
    company_name: str
    overall_status: ProcessingStatus
    steps: Dict[str, WorkflowStep]
    filter_result: Optional[str] = None
    customization_result: Optional[CustomizationResult] = None
    contact_result: Optional[ContactSearchResult] = None
    email_results: List[GeneratedEmail] = None
    document_package: Optional[DocumentPackage] = None
    total_processing_time: float = 0.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.email_results is None:
            self.email_results = []
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class BatchProcessingRequest:
    """Batch processing request configuration."""
    job_ids: List[int]
    enable_filtering: bool = True
    enable_resume_customization: bool = True
    enable_contact_finding: bool = True
    enable_email_generation: bool = True
    enable_document_generation: bool = True
    filter_criteria: Optional[FilterCriteria] = None
    email_template: str = "professional"
    document_formats: List[str] = None
    max_concurrent_jobs: int = 3
    
    def __post_init__(self):
        if self.document_formats is None:
            self.document_formats = ['html', 'pdf', 'markdown']

@dataclass
class BatchProcessingResult:
    """Complete batch processing result."""
    request_id: str
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    job_results: Dict[int, JobProcessingResult]
    overall_status: ProcessingStatus
    total_processing_time: float
    created_at: datetime
    completed_at: Optional[datetime] = None

class WorkflowOrchestrator:
    """Orchestrates the complete job application preparation workflow."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # Initialize component managers
        self.job_filter = AIJobFilter(db_manager)
        self.resume_customizer = AIResumeCustomizer(db_manager)
        self.contact_finder = ContactFinder(db_manager)
        self.email_generator = EmailGenerator(db_manager)
        self.document_manager = DocumentManager(db_manager)
        
        # Processing state
        self.current_batch_id = None
        self.progress_callbacks: List[Callable] = []
    
    def add_progress_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add a progress callback function."""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, event_type: str, data: Dict[str, Any]):
        """Notify all progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    async def process_jobs_batch(self, request: BatchProcessingRequest) -> BatchProcessingResult:
        """
        Process a batch of jobs through the complete workflow.
        
        Args:
            request: Batch processing configuration
            
        Returns:
            BatchProcessingResult with all job processing results
        """
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_batch_id = batch_id
        start_time = datetime.now()
        
        logger.info(f"Starting batch processing {batch_id} for {len(request.job_ids)} jobs")
        
        self._notify_progress("batch_started", {
            "batch_id": batch_id,
            "total_jobs": len(request.job_ids),
            "request": asdict(request)
        })
        
        # Initialize result tracking
        job_results = {}
        successful_jobs = 0
        failed_jobs = 0
        
        try:
            # Process jobs with concurrency control
            semaphore = asyncio.Semaphore(request.max_concurrent_jobs)
            
            async def process_single_job(job_id: int) -> Tuple[int, JobProcessingResult]:
                async with semaphore:
                    result = await self._process_single_job(job_id, request)
                    return job_id, result
            
            # Execute all jobs concurrently with limits
            tasks = [process_single_job(job_id) for job_id in request.job_ids]
            completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for task_result in completed_tasks:
                if isinstance(task_result, Exception):
                    logger.error(f"Task failed with exception: {task_result}")
                    failed_jobs += 1
                else:
                    job_id, job_result = task_result
                    job_results[job_id] = job_result
                    
                    if job_result.overall_status == ProcessingStatus.COMPLETED:
                        successful_jobs += 1
                    else:
                        failed_jobs += 1
            
            # Calculate final status
            if successful_jobs == len(request.job_ids):
                overall_status = ProcessingStatus.COMPLETED
            elif successful_jobs > 0:
                overall_status = ProcessingStatus.COMPLETED  # Partial success still counts as completed
            else:
                overall_status = ProcessingStatus.FAILED
            
            # Calculate total processing time
            end_time = datetime.now()
            total_processing_time = (end_time - start_time).total_seconds()
            
            # Create final result
            batch_result = BatchProcessingResult(
                request_id=batch_id,
                total_jobs=len(request.job_ids),
                successful_jobs=successful_jobs,
                failed_jobs=failed_jobs,
                job_results=job_results,
                overall_status=overall_status,
                total_processing_time=total_processing_time,
                created_at=start_time,
                completed_at=end_time
            )
            
            # Save batch result
            await self._save_batch_result(batch_result)
            
            self._notify_progress("batch_completed", {
                "batch_id": batch_id,
                "successful_jobs": successful_jobs,
                "failed_jobs": failed_jobs,
                "total_time": total_processing_time
            })
            
            logger.info(f"Batch processing {batch_id} completed: {successful_jobs}/{len(request.job_ids)} successful")
            return batch_result
            
        except Exception as e:
            logger.error(f"Critical error in batch processing: {e}")
            
            end_time = datetime.now()
            total_processing_time = (end_time - start_time).total_seconds()
            
            # Create failed result
            batch_result = BatchProcessingResult(
                request_id=batch_id,
                total_jobs=len(request.job_ids),
                successful_jobs=successful_jobs,
                failed_jobs=len(request.job_ids),
                job_results=job_results,
                overall_status=ProcessingStatus.FAILED,
                total_processing_time=total_processing_time,
                created_at=start_time,
                completed_at=end_time
            )
            
            await self._save_batch_result(batch_result)
            
            self._notify_progress("batch_failed", {
                "batch_id": batch_id,
                "error": str(e)
            })
            
            return batch_result
    
    async def _process_single_job(self, job_id: int, request: BatchProcessingRequest) -> JobProcessingResult:
        """Process a single job through the complete workflow."""
        job_start_time = datetime.now()
        
        # Get job details
        job_data = await self._get_job_data(job_id)
        if not job_data:
            return JobProcessingResult(
                job_id=job_id,
                job_title="Unknown",
                company_name="Unknown",
                overall_status=ProcessingStatus.FAILED,
                steps={"data_loading": WorkflowStep("data_loading", ProcessingStatus.FAILED, error_message="Job not found")}
            )
        
        logger.info(f"Processing job {job_id}: {job_data['title']} at {job_data['company']}")
        
        self._notify_progress("job_started", {
            "job_id": job_id,
            "job_title": job_data['title'],
            "company_name": job_data['company']
        })
        
        # Initialize job result
        job_result = JobProcessingResult(
            job_id=job_id,
            job_title=job_data['title'],
            company_name=job_data['company'],
            overall_status=ProcessingStatus.IN_PROGRESS,
            steps={}
        )
        
        try:
            # Step 1: Job Filtering (if enabled and not already filtered)
            if request.enable_filtering:
                await self._execute_filtering_step(job_result, job_data, request.filter_criteria)
                
                # Skip remaining steps if job was rejected
                if job_result.filter_result == "reject":
                    job_result.overall_status = ProcessingStatus.SKIPPED
                    logger.info(f"Job {job_id} was rejected by filter - skipping remaining steps")
                    return job_result
            
            # Step 2: Resume Customization
            if request.enable_resume_customization:
                await self._execute_resume_customization_step(job_result, job_data)
            
            # Step 3: Contact Finding
            if request.enable_contact_finding:
                await self._execute_contact_finding_step(job_result, job_data)
            
            # Step 4: Email Generation
            if request.enable_email_generation:
                await self._execute_email_generation_step(job_result, job_data, request.email_template)
            
            # Step 5: Document Generation
            if request.enable_document_generation:
                await self._execute_document_generation_step(job_result, job_data, request.document_formats)
            
            # Calculate final status and processing time
            job_end_time = datetime.now()
            job_result.total_processing_time = (job_end_time - job_start_time).total_seconds()
            
            # Determine overall status
            failed_steps = [step for step in job_result.steps.values() if step.status == ProcessingStatus.FAILED]
            if failed_steps:
                job_result.overall_status = ProcessingStatus.FAILED
            else:
                job_result.overall_status = ProcessingStatus.COMPLETED
            
            self._notify_progress("job_completed", {
                "job_id": job_id,
                "status": job_result.overall_status.value,
                "processing_time": job_result.total_processing_time
            })
            
            logger.info(f"Completed processing job {job_id} in {job_result.total_processing_time:.2f}s")
            return job_result
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            job_result.overall_status = ProcessingStatus.FAILED
            
            # Add error to the current step or create a general error step
            if not job_result.steps:
                job_result.steps["general_error"] = WorkflowStep(
                    "general_error", ProcessingStatus.FAILED, error_message=str(e)
                )
            
            self._notify_progress("job_failed", {
                "job_id": job_id,
                "error": str(e)
            })
            
            return job_result
    
    async def _execute_filtering_step(self, job_result: JobProcessingResult, job_data: Dict[str, Any], criteria: Optional[FilterCriteria]):
        """Execute job filtering step."""
        step = WorkflowStep("filtering", ProcessingStatus.IN_PROGRESS, start_time=datetime.now())
        job_result.steps["filtering"] = step
        
        try:
            # Check if job is already filtered
            existing_filter = await self._get_existing_filter_result(job_result.job_id)
            
            if existing_filter:
                job_result.filter_result = existing_filter
                step.status = ProcessingStatus.COMPLETED
                step.result_data = {"decision": existing_filter, "source": "existing"}
            else:
                # Apply filtering
                if not criteria:
                    # Load default criteria
                    criteria = await self._load_default_filter_criteria()
                
                filter_results = await self.job_filter.filter_jobs_batch([job_result.job_id], criteria)
                
                if filter_results and len(filter_results) > 0:
                    filter_result = filter_results[0]
                    job_result.filter_result = filter_result.decision.value
                    step.status = ProcessingStatus.COMPLETED
                    step.result_data = {
                        "decision": filter_result.decision.value,
                        "confidence": filter_result.confidence_score,
                        "reasoning": filter_result.reasoning
                    }
                else:
                    raise Exception("No filter result returned")
            
            step.end_time = datetime.now()
            
        except Exception as e:
            step.status = ProcessingStatus.FAILED
            step.error_message = str(e)
            step.end_time = datetime.now()
            logger.error(f"Filtering step failed for job {job_result.job_id}: {e}")
    
    async def _execute_resume_customization_step(self, job_result: JobProcessingResult, job_data: Dict[str, Any]):
        """Execute resume customization step."""
        step = WorkflowStep("resume_customization", ProcessingStatus.IN_PROGRESS, start_time=datetime.now())
        job_result.steps["resume_customization"] = step
        
        try:
            # Check for existing customization
            existing_customization = await self.resume_customizer.get_customization_for_job(job_result.job_id)
            
            if existing_customization:
                job_result.customization_result = existing_customization
                step.status = ProcessingStatus.COMPLETED
                step.result_data = {"source": "existing", "confidence": existing_customization.confidence_score}
            else:
                # Create customization request
                customization_request = create_customization_request_from_job(job_data)
                
                # Generate customization
                customization_result = await self.resume_customizer.customize_resume_for_job(customization_request)
                
                if customization_result:
                    job_result.customization_result = customization_result
                    step.status = ProcessingStatus.COMPLETED
                    step.result_data = {
                        "confidence": customization_result.confidence_score,
                        "processing_time": customization_result.processing_time
                    }
                else:
                    raise Exception("Resume customization failed")
            
            step.end_time = datetime.now()
            
        except Exception as e:
            step.status = ProcessingStatus.FAILED
            step.error_message = str(e)
            step.end_time = datetime.now()
            logger.error(f"Resume customization step failed for job {job_result.job_id}: {e}")
    
    async def _execute_contact_finding_step(self, job_result: JobProcessingResult, job_data: Dict[str, Any]):
        """Execute contact finding step."""
        step = WorkflowStep("contact_finding", ProcessingStatus.IN_PROGRESS, start_time=datetime.now())
        job_result.steps["contact_finding"] = step
        
        try:
            # Find contacts for the company
            contact_result = await self.contact_finder.find_contacts_for_company(
                company_name=job_data['company'],
                domain=job_data.get('domain')
            )
            
            job_result.contact_result = contact_result
            step.status = ProcessingStatus.COMPLETED
            step.result_data = {
                "contacts_found": contact_result.total_found,
                "success_rate": contact_result.success_rate,
                "methods_used": contact_result.search_methods_used
            }
            step.end_time = datetime.now()
            
        except Exception as e:
            step.status = ProcessingStatus.FAILED
            step.error_message = str(e)
            step.end_time = datetime.now()
            logger.error(f"Contact finding step failed for job {job_result.job_id}: {e}")
    
    async def _execute_email_generation_step(self, job_result: JobProcessingResult, job_data: Dict[str, Any], template_name: str):
        """Execute email generation step."""
        step = WorkflowStep("email_generation", ProcessingStatus.IN_PROGRESS, start_time=datetime.now())
        job_result.steps["email_generation"] = step
        
        try:
            if not job_result.contact_result or not job_result.contact_result.contacts:
                raise Exception("No contacts available for email generation")
            
            # Generate emails for top contacts
            top_contacts = job_result.contact_result.contacts[:3]  # Top 3 contacts
            
            for contact in top_contacts:
                email_request = EmailGenerationRequest(
                    job_id=job_result.job_id,
                    job_title=job_data['title'],
                    company_name=job_data['company'],
                    job_description=job_data.get('description', ''),
                    contact=contact,
                    customization_result=job_result.customization_result,
                    template_name=template_name
                )
                
                generated_email = await self.email_generator.generate_email(email_request)
                if generated_email:
                    job_result.email_results.append(generated_email)
            
            if job_result.email_results:
                step.status = ProcessingStatus.COMPLETED
                step.result_data = {
                    "emails_generated": len(job_result.email_results),
                    "avg_personalization_score": sum(e.personalization_score for e in job_result.email_results) / len(job_result.email_results)
                }
            else:
                raise Exception("No emails were generated")
            
            step.end_time = datetime.now()
            
        except Exception as e:
            step.status = ProcessingStatus.FAILED
            step.error_message = str(e)
            step.end_time = datetime.now()
            logger.error(f"Email generation step failed for job {job_result.job_id}: {e}")
    
    async def _execute_document_generation_step(self, job_result: JobProcessingResult, job_data: Dict[str, Any], formats: List[str]):
        """Execute document generation step."""
        step = WorkflowStep("document_generation", ProcessingStatus.IN_PROGRESS, start_time=datetime.now())
        job_result.steps["document_generation"] = step
        
        try:
            if not job_result.customization_result:
                raise Exception("No customized resume available for document generation")
            
            # Create document generation request
            doc_request = DocumentGenerationRequest(
                job_id=job_result.job_id,
                job_title=job_data['title'],
                company_name=job_data['company'],
                resume_data=job_result.customization_result.customized_resume,
                output_formats=formats
            )
            
            # Generate documents
            document_package = await self.document_manager.generate_documents_for_job(doc_request)
            
            if document_package:
                job_result.document_package = document_package
                step.status = ProcessingStatus.COMPLETED
                step.result_data = {
                    "documents_generated": len(document_package.documents),
                    "total_size": document_package.total_size,
                    "formats": [doc.document_type for doc in document_package.documents]
                }
            else:
                raise Exception("Document generation failed")
            
            step.end_time = datetime.now()
            
        except Exception as e:
            step.status = ProcessingStatus.FAILED
            step.error_message = str(e)
            step.end_time = datetime.now()
            logger.error(f"Document generation step failed for job {job_result.job_id}: {e}")
    
    async def _get_job_data(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get job data from database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT id, title, company, description, url, location, posted_date,
                   salary_range, employment_type, experience_level, requirements
            FROM jobs
            WHERE id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving job data for {job_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def _get_existing_filter_result(self, job_id: int) -> Optional[str]:
        """Get existing filter result for a job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT decision FROM filter_results
            WHERE job_id = ?
            ORDER BY processed_at DESC
            LIMIT 1
            """, (job_id,))
            
            row = cursor.fetchone()
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"Error getting existing filter result: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def _load_default_filter_criteria(self) -> FilterCriteria:
        """Load default filter criteria."""
        # This should load from database or config
        # For now, return a basic criteria
        from ..ai_processing.job_filter import create_default_criteria
        return create_default_criteria()
    
    async def _save_batch_result(self, batch_result: BatchProcessingResult):
        """Save batch processing result to database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_processing_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                total_jobs INTEGER,
                successful_jobs INTEGER,
                failed_jobs INTEGER,
                overall_status TEXT,
                total_processing_time REAL,
                result_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """)
            
            # Convert job results to JSON
            job_results_json = json.dumps({
                str(job_id): {
                    "job_id": result.job_id,
                    "job_title": result.job_title,
                    "company_name": result.company_name,
                    "overall_status": result.overall_status.value,
                    "total_processing_time": result.total_processing_time,
                    "steps": {name: {
                        "name": step.name,
                        "status": step.status.value,
                        "error_message": step.error_message,
                        "result_data": step.result_data
                    } for name, step in result.steps.items()}
                }
                for job_id, result in batch_result.job_results.items()
            })
            
            # Insert batch result
            cursor.execute("""
            INSERT OR REPLACE INTO batch_processing_results (
                request_id, total_jobs, successful_jobs, failed_jobs,
                overall_status, total_processing_time, result_data, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_result.request_id,
                batch_result.total_jobs,
                batch_result.successful_jobs,
                batch_result.failed_jobs,
                batch_result.overall_status.value,
                batch_result.total_processing_time,
                job_results_json,
                batch_result.completed_at.isoformat() if batch_result.completed_at else None
            ))
            
            conn.commit()
            logger.info(f"Saved batch processing result: {batch_result.request_id}")
            
        except Exception as e:
            logger.error(f"Error saving batch result: {e}")
        finally:
            if conn:
                conn.close()
    
    async def get_batch_result(self, request_id: str) -> Optional[BatchProcessingResult]:
        """Get batch processing result by request ID."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT request_id, total_jobs, successful_jobs, failed_jobs,
                   overall_status, total_processing_time, result_data,
                   created_at, completed_at
            FROM batch_processing_results
            WHERE request_id = ?
            """, (request_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Parse job results JSON
            job_results_data = json.loads(row[6]) if row[6] else {}
            job_results = {}
            
            for job_id_str, result_data in job_results_data.items():
                job_id = int(job_id_str)
                # Reconstruct job result (simplified)
                job_results[job_id] = JobProcessingResult(
                    job_id=result_data["job_id"],
                    job_title=result_data["job_title"],
                    company_name=result_data["company_name"],
                    overall_status=ProcessingStatus(result_data["overall_status"]),
                    steps={},  # Steps would need more complex reconstruction
                    total_processing_time=result_data["total_processing_time"]
                )
            
            return BatchProcessingResult(
                request_id=row[0],
                total_jobs=row[1],
                successful_jobs=row[2],
                failed_jobs=row[3],
                job_results=job_results,
                overall_status=ProcessingStatus(row[4]),
                total_processing_time=row[5],
                created_at=datetime.fromisoformat(row[7]),
                completed_at=datetime.fromisoformat(row[8]) if row[8] else None
            )
            
        except Exception as e:
            logger.error(f"Error retrieving batch result: {e}")
            return None
        finally:
            if conn:
                conn.close()

async def process_accepted_jobs(
    db_manager: Optional[DatabaseManager] = None,
    max_concurrent_jobs: int = 3,
    email_template: str = "professional"
) -> BatchProcessingResult:
    """
    Convenience function to process all accepted jobs through the complete workflow.
    
    Args:
        db_manager: Optional database manager instance
        max_concurrent_jobs: Maximum number of jobs to process concurrently
        email_template: Email template to use
        
    Returns:
        BatchProcessingResult
    """
    if not db_manager:
        from ..config.database import get_db_manager
        db_manager = get_db_manager()
    
    # Get accepted job IDs
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT DISTINCT fr.job_id 
        FROM filter_results fr
        JOIN jobs j ON fr.job_id = j.id
        WHERE fr.decision = 'accept'
        ORDER BY j.created_at DESC
        """)
        
        job_ids = [row[0] for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error getting accepted jobs: {e}")
        job_ids = []
    finally:
        if conn:
            conn.close()
    
    if not job_ids:
        logger.warning("No accepted jobs found for processing")
        return BatchProcessingResult(
            request_id="no_jobs",
            total_jobs=0,
            successful_jobs=0,
            failed_jobs=0,
            job_results={},
            overall_status=ProcessingStatus.COMPLETED,
            total_processing_time=0.0,
            created_at=datetime.now()
        )
    
    # Create batch request
    request = BatchProcessingRequest(
        job_ids=job_ids,
        enable_filtering=False,  # Already filtered
        max_concurrent_jobs=max_concurrent_jobs,
        email_template=email_template
    )
    
    # Process batch
    orchestrator = WorkflowOrchestrator(db_manager)
    return await orchestrator.process_jobs_batch(request)