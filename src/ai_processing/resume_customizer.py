"""
AI Resume Customization Engine

This module provides AI-powered resume customization functionality that tailors
resumes for specific job postings using LLM analysis and structured prompting.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

from .llm_manager import get_llm_manager, LLMResponse
from ..document_manager.resume_handler import ResumeTemplateHandler, ResumeData
from ..config.database import DatabaseManager
from ..utils import get_logger

logger = get_logger(__name__)

@dataclass
class CustomizationRequest:
    """Request for resume customization."""
    job_id: int
    job_title: str
    company_name: str
    job_description: str
    job_requirements: Optional[str] = None
    company_info: Optional[str] = None
    salary_range: Optional[str] = None
    experience_level: Optional[str] = None

@dataclass
class CustomizationResult:
    """Result of resume customization."""
    job_id: int
    customized_resume: ResumeData
    customization_notes: str
    skills_emphasized: List[str]
    experience_highlights: List[str]
    summary_changes: str
    confidence_score: float
    processing_time: float

class AIResumeCustomizer:
    """AI-powered resume customization engine."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the resume customizer."""
        self.db_manager = db_manager
        self.llm_manager = get_llm_manager()
        self.base_resume_handler = ResumeTemplateHandler()
        
        # Load base resume template
        if not self.base_resume_handler.load_template():
            logger.warning("Could not load base resume template")
    
    async def customize_resume_for_job(self, request: CustomizationRequest) -> Optional[CustomizationResult]:
        """
        Customize resume for a specific job posting.
        
        Args:
            request: Customization request with job details
            
        Returns:
            CustomizationResult or None if failed
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get base resume data
            base_resume = self.base_resume_handler.get_resume_data()
            if not base_resume:
                logger.error("No base resume data available")
                return None
            
            # Analyze job posting for customization insights
            job_analysis = await self._analyze_job_posting(request)
            if not job_analysis:
                logger.error("Failed to analyze job posting")
                return None
            
            # Customize each section of the resume
            customized_resume = await self._customize_resume_sections(
                base_resume, request, job_analysis
            )
            
            # Calculate processing time
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Create result
            result = CustomizationResult(
                job_id=request.job_id,
                customized_resume=customized_resume,
                customization_notes=job_analysis.get('customization_strategy', ''),
                skills_emphasized=job_analysis.get('key_skills_to_emphasize', []),
                experience_highlights=job_analysis.get('experience_to_highlight', []),
                summary_changes=job_analysis.get('summary_customization', ''),
                confidence_score=job_analysis.get('customization_confidence', 0.8),
                processing_time=processing_time
            )
            
            # Save to database
            await self._save_customization_result(result)
            
            logger.info(f"Successfully customized resume for job {request.job_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error customizing resume for job {request.job_id}: {e}")
            return None
    
    async def _analyze_job_posting(self, request: CustomizationRequest) -> Optional[Dict[str, Any]]:
        """Analyze job posting to determine customization strategy."""
        base_resume = self.base_resume_handler.get_resume_data()
        
        # Create analysis prompt
        analysis_prompt = self._create_job_analysis_prompt(request, base_resume)
        
        try:
            response = await self.llm_manager.generate_structured_response(
                prompt=analysis_prompt,
                system_prompt="You are an expert resume customization analyst. Analyze job postings and provide strategic customization recommendations.",
                response_format={
                    "key_requirements": "List of 5-7 most important job requirements",
                    "key_skills_to_emphasize": "List of skills from candidate's background that match job requirements",
                    "experience_to_highlight": "List of specific experiences/achievements to emphasize",
                    "summary_customization": "How to adjust the professional summary for this role",
                    "customization_strategy": "Overall strategy for tailoring this resume",
                    "missing_requirements": "Job requirements the candidate doesn't clearly meet",
                    "customization_confidence": "Float 0-1 indicating how well candidate matches role",
                    "tone_recommendations": "Recommended tone/language adjustments"
                },
                max_tokens=2000
            )
            
            if response.success:
                return response.data
            else:
                logger.error(f"Job analysis failed: {response.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing job posting: {e}")
            return None
    
    def _create_job_analysis_prompt(self, request: CustomizationRequest, base_resume: ResumeData) -> str:
        """Create prompt for job analysis."""
        resume_summary = self._create_resume_summary(base_resume)
        
        return f"""
Analyze this job posting and candidate background to determine the best resume customization strategy.

JOB DETAILS:
Title: {request.job_title}
Company: {request.company_name}
Experience Level: {request.experience_level or 'Not specified'}
Salary Range: {request.salary_range or 'Not specified'}

JOB DESCRIPTION:
{request.job_description}

{f"ADDITIONAL REQUIREMENTS: {request.job_requirements}" if request.job_requirements else ""}

CANDIDATE BACKGROUND SUMMARY:
{resume_summary}

Please analyze the match between this candidate and job posting, then provide strategic recommendations for customizing the resume to maximize the candidate's appeal for this specific role.

Focus on:
1. Which of the candidate's skills and experiences most directly match the job requirements
2. How to reframe experiences to better align with the job description language
3. Which achievements should be emphasized or de-emphasized
4. How to adjust the professional summary to speak directly to this role
5. Any gaps that should be addressed or downplayed

Provide specific, actionable recommendations that will help this resume stand out for this particular position.
"""
    
    def _create_resume_summary(self, resume_data: ResumeData) -> str:
        """Create a concise summary of the resume for analysis."""
        summary_parts = []
        
        # Professional summary
        if resume_data.professional_summary:
            summary_parts.append(f"SUMMARY: {resume_data.professional_summary}")
        
        # Technical skills
        if resume_data.technical_skills:
            all_skills = []
            for skill_category in resume_data.technical_skills:
                all_skills.extend(skill_category.skills)
            summary_parts.append(f"TECHNICAL SKILLS: {', '.join(all_skills)}")
        
        # Work experience highlights
        if resume_data.work_experience:
            exp_summary = []
            for exp in resume_data.work_experience[:3]:  # Top 3 experiences
                exp_summary.append(f"{exp.title} at {exp.company} ({exp.start_date} - {exp.end_date})")
            summary_parts.append(f"RECENT EXPERIENCE: {'; '.join(exp_summary)}")
        
        # Education
        if resume_data.education:
            edu = resume_data.education[0]  # Most recent/relevant
            summary_parts.append(f"EDUCATION: {edu.degree} from {edu.institution}")
        
        return "\n\n".join(summary_parts)
    
    async def _customize_resume_sections(
        self, 
        base_resume: ResumeData, 
        request: CustomizationRequest, 
        job_analysis: Dict[str, Any]
    ) -> ResumeData:
        """Customize each section of the resume based on job analysis."""
        
        # Create a copy of the base resume
        import copy
        customized_resume = copy.deepcopy(base_resume)
        
        # Customize professional summary
        customized_summary = await self._customize_professional_summary(
            base_resume.professional_summary, request, job_analysis
        )
        if customized_summary:
            customized_resume.professional_summary = customized_summary
        
        # Customize work experience descriptions
        for i, experience in enumerate(customized_resume.work_experience):
            customized_descriptions = await self._customize_experience_descriptions(
                experience, request, job_analysis
            )
            if customized_descriptions:
                customized_resume.work_experience[i].description = customized_descriptions
        
        # Reorder/emphasize technical skills
        customized_resume.technical_skills = self._reorder_technical_skills(
            base_resume.technical_skills, job_analysis
        )
        
        return customized_resume
    
    async def _customize_professional_summary(
        self, 
        base_summary: str, 
        request: CustomizationRequest, 
        job_analysis: Dict[str, Any]
    ) -> Optional[str]:
        """Customize the professional summary for the specific job."""
        
        customization_prompt = f"""
Based on the job analysis, customize this professional summary for the specific role:

ORIGINAL SUMMARY:
{base_summary}

JOB TITLE: {request.job_title}
COMPANY: {request.company_name}

KEY REQUIREMENTS TO ADDRESS:
{chr(10).join(f"- {req}" for req in job_analysis.get('key_requirements', []))}

CUSTOMIZATION STRATEGY:
{job_analysis.get('summary_customization', '')}

SKILLS TO EMPHASIZE:
{', '.join(job_analysis.get('key_skills_to_emphasize', []))}

Rewrite the professional summary to:
1. Directly address the key job requirements
2. Emphasize the most relevant skills and experiences
3. Use language that aligns with the job description
4. Maintain the candidate's authentic voice and achievements
5. Keep it concise (2-3 sentences maximum)

Return only the customized professional summary, no explanation.
"""
        
        try:
            response = await self.llm_manager.generate_text(
                prompt=customization_prompt,
                system_prompt="You are an expert resume writer. Customize professional summaries to maximize job relevance while maintaining authenticity.",
                max_tokens=300
            )
            
            if response.success:
                return response.content.strip()
            else:
                logger.warning(f"Failed to customize professional summary: {response.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error customizing professional summary: {e}")
            return None
    
    async def _customize_experience_descriptions(
        self, 
        experience, 
        request: CustomizationRequest, 
        job_analysis: Dict[str, Any]
    ) -> Optional[List[str]]:
        """Customize work experience bullet points for the specific job."""
        
        if not experience.description:
            return None
        
        customization_prompt = f"""
Customize these work experience bullet points for a {request.job_title} role at {request.company_name}:

ROLE: {experience.title} at {experience.company}
ORIGINAL BULLET POINTS:
{chr(10).join(f"- {desc}" for desc in experience.description)}

JOB REQUIREMENTS TO ADDRESS:
{chr(10).join(f"- {req}" for req in job_analysis.get('key_requirements', []))}

EXPERIENCES TO HIGHLIGHT:
{chr(10).join(f"- {exp}" for exp in job_analysis.get('experience_to_highlight', []))}

Rewrite the bullet points to:
1. Use keywords and phrases from the target job description
2. Quantify achievements where possible
3. Emphasize skills and experiences most relevant to the target role
4. Maintain factual accuracy - don't fabricate achievements
5. Use strong action verbs
6. Keep 3-5 of the most impactful bullet points

Return only the customized bullet points (one per line, starting with "-"), no explanation.
"""
        
        try:
            response = await self.llm_manager.generate_text(
                prompt=customization_prompt,
                system_prompt="You are an expert resume writer. Customize work experience descriptions to maximize relevance for specific job applications.",
                max_tokens=500
            )
            
            if response.success:
                # Parse bullet points from response
                lines = response.content.strip().split('\n')
                bullet_points = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('- '):
                        bullet_points.append(line[2:])
                    elif line.startswith('•'):
                        bullet_points.append(line[1:].strip())
                    elif line and not line.startswith('#'):
                        bullet_points.append(line)
                
                return bullet_points if bullet_points else None
            else:
                logger.warning(f"Failed to customize experience descriptions: {response.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error customizing experience descriptions: {e}")
            return None
    
    def _reorder_technical_skills(
        self, 
        base_skills: List, 
        job_analysis: Dict[str, Any]
    ) -> List:
        """Reorder technical skills to emphasize job-relevant skills first."""
        
        emphasized_skills = set(job_analysis.get('key_skills_to_emphasize', []))
        reordered_skills = []
        
        for skill_category in base_skills:
            # Separate emphasized and regular skills
            emphasized = []
            regular = []
            
            for skill in skill_category.skills:
                if any(emp_skill.lower() in skill.lower() for emp_skill in emphasized_skills):
                    emphasized.append(skill)
                else:
                    regular.append(skill)
            
            # Create new skill category with emphasized skills first
            new_category = type(skill_category)(
                category=skill_category.category,
                skills=emphasized + regular
            )
            reordered_skills.append(new_category)
        
        return reordered_skills
    
    async def _save_customization_result(self, result: CustomizationResult) -> None:
        """Save customization result to database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume_customizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                customized_resume_json TEXT NOT NULL,
                customization_notes TEXT,
                skills_emphasized TEXT,
                experience_highlights TEXT,
                summary_changes TEXT,
                confidence_score REAL,
                processing_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
            """)
            
            # Convert resume data to JSON
            resume_json = json.dumps(asdict(result.customized_resume))
            
            # Insert customization result
            cursor.execute("""
            INSERT INTO resume_customizations (
                job_id, customized_resume_json, customization_notes,
                skills_emphasized, experience_highlights, summary_changes,
                confidence_score, processing_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.job_id,
                resume_json,
                result.customization_notes,
                json.dumps(result.skills_emphasized),
                json.dumps(result.experience_highlights),
                result.summary_changes,
                result.confidence_score,
                result.processing_time
            ))
            
            conn.commit()
            logger.info(f"Saved customization result for job {result.job_id}")
            
        except Exception as e:
            logger.error(f"Error saving customization result: {e}")
        finally:
            if conn:
                conn.close()
    
    async def get_customization_for_job(self, job_id: int) -> Optional[CustomizationResult]:
        """Get existing customization result for a job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT customized_resume_json, customization_notes, skills_emphasized,
                   experience_highlights, summary_changes, confidence_score, processing_time
            FROM resume_customizations
            WHERE job_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """, (job_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Parse JSON data
            resume_data_dict = json.loads(row[0])
            skills_emphasized = json.loads(row[2]) if row[2] else []
            experience_highlights = json.loads(row[3]) if row[3] else []
            
            # Reconstruct ResumeData object
            from ..document_manager.resume_handler import ResumeData, ContactInfo, WorkExperience, Education, Skill
            
            resume_data = ResumeData(**resume_data_dict)
            
            return CustomizationResult(
                job_id=job_id,
                customized_resume=resume_data,
                customization_notes=row[1] or "",
                skills_emphasized=skills_emphasized,
                experience_highlights=experience_highlights,
                summary_changes=row[4] or "",
                confidence_score=row[5] or 0.0,
                processing_time=row[6] or 0.0
            )
            
        except Exception as e:
            logger.error(f"Error retrieving customization for job {job_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def batch_customize_resumes(self, job_ids: List[int]) -> Dict[int, Optional[CustomizationResult]]:
        """Customize resumes for multiple jobs in batch."""
        results = {}
        
        try:
            # Get job details for all jobs
            job_details = await self._get_job_details_batch(job_ids)
            
            # Process each job
            tasks = []
            for job_id, job_data in job_details.items():
                if job_data:
                    request = CustomizationRequest(
                        job_id=job_id,
                        job_title=job_data['title'],
                        company_name=job_data['company'],
                        job_description=job_data['description'],
                        job_requirements=job_data.get('requirements'),
                        salary_range=job_data.get('salary_range'),
                        experience_level=job_data.get('experience_level')
                    )
                    tasks.append(self.customize_resume_for_job(request))
                else:
                    tasks.append(asyncio.sleep(0, result=None))
            
            # Execute all customizations concurrently
            customization_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Map results back to job IDs
            for i, job_id in enumerate(job_ids):
                result = customization_results[i]
                if isinstance(result, Exception):
                    logger.error(f"Error customizing resume for job {job_id}: {result}")
                    results[job_id] = None
                else:
                    results[job_id] = result
            
            logger.info(f"Completed batch customization for {len(job_ids)} jobs")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch resume customization: {e}")
            return {job_id: None for job_id in job_ids}
    
    async def _get_job_details_batch(self, job_ids: List[int]) -> Dict[int, Optional[Dict[str, Any]]]:
        """Get job details for multiple jobs."""
        job_details = {}
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Create placeholder string for IN clause
            placeholders = ','.join('?' * len(job_ids))
            
            cursor.execute(f"""
            SELECT id, title, company, description, requirements, salary_range, experience_level
            FROM jobs
            WHERE id IN ({placeholders})
            """, job_ids)
            
            rows = cursor.fetchall()
            
            for row in rows:
                job_details[row[0]] = {
                    'title': row[1],
                    'company': row[2],
                    'description': row[3],
                    'requirements': row[4],
                    'salary_range': row[5],
                    'experience_level': row[6]
                }
            
            # Add None for missing jobs
            for job_id in job_ids:
                if job_id not in job_details:
                    job_details[job_id] = None
            
            return job_details
            
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            return {job_id: None for job_id in job_ids}
        finally:
            if conn:
                conn.close()

def create_customization_request_from_job(job_data: Dict[str, Any]) -> CustomizationRequest:
    """Create a customization request from job data dictionary."""
    return CustomizationRequest(
        job_id=job_data['id'],
        job_title=job_data['title'],
        company_name=job_data['company'],
        job_description=job_data['description'],
        job_requirements=job_data.get('requirements'),
        company_info=job_data.get('company_info'),
        salary_range=job_data.get('salary_range'),
        experience_level=job_data.get('experience_level')
    )