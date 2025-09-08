"""
Email Composer Module

This module provides AI-powered email generation functionality for personalized
outreach to hiring managers and decision makers. It creates customized emails
based on job postings, company information, and contact details.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from ..ai_processing.llm_manager import get_llm_manager
from ..contact_finder import Contact, ContactSearchResult
from ..ai_processing.resume_customizer import CustomizationResult
from ..config.database import DatabaseManager
from ..config import get_user_config
from ..utils import get_logger

logger = get_logger(__name__)

@dataclass
class EmailTemplate:
    """Email template structure."""
    name: str
    subject_template: str
    body_template: str
    tone: str
    style: str
    purpose: str

@dataclass
class EmailGenerationRequest:
    """Request for email generation."""
    job_id: int
    job_title: str
    company_name: str
    job_description: str
    contact: Contact
    customization_result: Optional[CustomizationResult] = None
    template_name: str = "professional"
    additional_context: Optional[str] = None

@dataclass
class GeneratedEmail:
    """Generated email result."""
    job_id: int
    contact_email: str
    contact_name: str
    subject: str
    body: str
    template_used: str
    personalization_score: float
    generation_notes: str
    created_at: datetime

class EmailTemplateManager:
    """Manages email templates for different scenarios."""
    
    DEFAULT_TEMPLATES = {
        "professional": EmailTemplate(
            name="professional",
            subject_template="Application for {job_title} at {company_name}",
            body_template="""Dear {contact_name},

I hope this email finds you well. I am writing to express my strong interest in the {job_title} position at {company_name}.

{personalized_introduction}

{experience_highlight}

{skills_alignment}

I have attached my resume for your review and would welcome the opportunity to discuss how my background and enthusiasm can contribute to {company_name}'s continued success.

Thank you for your time and consideration. I look forward to hearing from you.

Best regards,
{sender_name}
{sender_contact}""",
            tone="professional",
            style="formal",
            purpose="job_application"
        ),
        
        "conversational": EmailTemplate(
            name="conversational",
            subject_template="Excited about the {job_title} role at {company_name}",
            body_template="""Hi {contact_name},

I came across the {job_title} opening at {company_name} and couldn't help but get excited about the opportunity.

{personalized_introduction}

{experience_highlight}

{skills_alignment}

I'd love to chat more about how I can contribute to the team. I've attached my resume and would be happy to discuss further at your convenience.

Thanks for your time!

Best,
{sender_name}
{sender_contact}""",
            tone="conversational",
            style="informal",
            purpose="job_application"
        ),
        
        "technical": EmailTemplate(
            name="technical",
            subject_template="Software Engineer Application - {job_title} at {company_name}",
            body_template="""Dear {contact_name},

I am writing to apply for the {job_title} position at {company_name}. As a software engineer with expertise in {key_technologies}, I am particularly drawn to this opportunity.

{technical_experience_highlight}

{problem_solving_example}

{technical_skills_alignment}

I have attached my resume detailing my technical background and would appreciate the opportunity to discuss how my skills align with your team's needs.

Thank you for your consideration.

Best regards,
{sender_name}
{sender_contact}""",
            tone="professional",
            style="technical",
            purpose="technical_application"
        )
    }
    
    def get_template(self, template_name: str) -> Optional[EmailTemplate]:
        """Get an email template by name."""
        return self.DEFAULT_TEMPLATES.get(template_name)
    
    def list_templates(self) -> List[str]:
        """List available template names."""
        return list(self.DEFAULT_TEMPLATES.keys())

class EmailGenerator:
    """AI-powered email generation engine."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.llm_manager = get_llm_manager()
        self.template_manager = EmailTemplateManager()
        self.user_config = get_user_config()
    
    async def generate_email(self, request: EmailGenerationRequest) -> Optional[GeneratedEmail]:
        """
        Generate a personalized email for a job application.
        
        Args:
            request: Email generation request with job and contact details
            
        Returns:
            GeneratedEmail or None if generation failed
        """
        try:
            # Get template
            template = self.template_manager.get_template(request.template_name)
            if not template:
                logger.error(f"Template not found: {request.template_name}")
                return None
            
            # Generate personalized content
            personalized_content = await self._generate_personalized_content(request, template)
            if not personalized_content:
                logger.error("Failed to generate personalized content")
                return None
            
            # Generate subject line
            subject = await self._generate_subject_line(request, template, personalized_content)
            
            # Generate email body
            body = await self._generate_email_body(request, template, personalized_content)
            
            # Calculate personalization score
            personalization_score = self._calculate_personalization_score(personalized_content)
            
            # Create generated email
            generated_email = GeneratedEmail(
                job_id=request.job_id,
                contact_email=request.contact.email,
                contact_name=request.contact.name or "Hiring Manager",
                subject=subject,
                body=body,
                template_used=request.template_name,
                personalization_score=personalization_score,
                generation_notes=personalized_content.get('generation_notes', ''),
                created_at=datetime.now()
            )
            
            # Save to database
            await self._save_generated_email(generated_email)
            
            logger.info(f"Generated email for job {request.job_id} to {request.contact.email}")
            return generated_email
            
        except Exception as e:
            logger.error(f"Error generating email for job {request.job_id}: {e}")
            return None
    
    async def _generate_personalized_content(self, request: EmailGenerationRequest, template: EmailTemplate) -> Optional[Dict[str, Any]]:
        """Generate personalized content components for the email."""
        
        # Build context for LLM
        context = self._build_email_context(request)
        
        # Create personalization prompt
        personalization_prompt = self._create_personalization_prompt(request, template, context)
        
        try:
            response = await self.llm_manager.generate_structured_response(
                prompt=personalization_prompt,
                system_prompt="You are an expert email writer specializing in professional job application emails. Create personalized, engaging content that feels authentic and relevant.",
                response_format={
                    "personalized_introduction": "A personalized opening that connects with the company/role",
                    "experience_highlight": "1-2 sentences highlighting most relevant experience",
                    "skills_alignment": "How candidate's skills align with the job requirements",
                    "company_connection": "Specific connection or interest in this company",
                    "technical_skills_match": "Technical skills that directly match job requirements",
                    "key_achievements": "1-2 quantified achievements relevant to the role",
                    "call_to_action": "Natural, confident call to action",
                    "personalization_score": "Float 0-1 indicating how personalized this content is",
                    "generation_notes": "Notes about the personalization strategy used"
                },
                max_tokens=1500
            )
            
            if response.success:
                return response.data
            else:
                logger.error(f"Content personalization failed: {response.error}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating personalized content: {e}")
            return None
    
    def _create_personalization_prompt(self, request: EmailGenerationRequest, template: EmailTemplate, context: Dict[str, Any]) -> str:
        """Create prompt for email personalization."""
        
        return f"""
Create personalized email content for this job application:

JOB DETAILS:
Title: {request.job_title}
Company: {request.company_name}
Description: {request.job_description[:1000]}...

RECIPIENT:
Name: {request.contact.name or 'Hiring Manager'}
Title: {request.contact.title}
Email: {request.contact.email}

CANDIDATE PROFILE:
Name: {self.user_config.name}
Location: {self.user_config.location}
Background: {context.get('candidate_summary', '')}

CUSTOMIZATION INSIGHTS:
{context.get('customization_notes', 'No specific customization insights available')}

EMAIL TEMPLATE STYLE: {template.tone} - {template.style}

Generate personalized content that:
1. Addresses the recipient by name when available
2. Shows specific knowledge about the company and role
3. Highlights the most relevant experiences and skills
4. Demonstrates genuine interest in the position
5. Uses appropriate tone for the template style
6. Includes specific examples and quantified achievements where possible
7. Avoids generic phrases and templates

Make the content feel authentic and tailored specifically to this opportunity.
"""
    
    def _build_email_context(self, request: EmailGenerationRequest) -> Dict[str, Any]:
        """Build context information for email generation."""
        context = {
            "sender_name": self.user_config.name,
            "sender_email": self.user_config.email,
            "sender_phone": self.user_config.phone,
            "sender_location": self.user_config.location,
        }
        
        # Add customization insights if available
        if request.customization_result:
            context.update({
                "customization_notes": request.customization_result.customization_notes,
                "skills_emphasized": request.customization_result.skills_emphasized,
                "experience_highlights": request.customization_result.experience_highlights,
                "candidate_summary": self._create_candidate_summary(request.customization_result)
            })
        
        # Add contact information
        context.update({
            "contact_name": request.contact.name or "Hiring Manager",
            "contact_title": request.contact.title,
            "company_name": request.company_name,
            "job_title": request.job_title
        })
        
        return context
    
    def _create_candidate_summary(self, customization_result: CustomizationResult) -> str:
        """Create a brief candidate summary from customization result."""
        resume_data = customization_result.customized_resume
        
        summary_parts = []
        
        # Professional summary
        if resume_data.professional_summary:
            summary_parts.append(resume_data.professional_summary)
        
        # Key skills
        if customization_result.skills_emphasized:
            skills_text = ", ".join(customization_result.skills_emphasized[:5])
            summary_parts.append(f"Key skills: {skills_text}")
        
        # Recent experience
        if resume_data.work_experience:
            recent_exp = resume_data.work_experience[0]
            summary_parts.append(f"Currently: {recent_exp.title} at {recent_exp.company}")
        
        return ". ".join(summary_parts)
    
    async def _generate_subject_line(self, request: EmailGenerationRequest, template: EmailTemplate, content: Dict[str, Any]) -> str:
        """Generate a personalized subject line."""
        
        subject_prompt = f"""
Create a compelling email subject line for this job application:

Job: {request.job_title} at {request.company_name}
Template Style: {template.tone}
Recipient: {request.contact.name or 'Hiring Manager'}

The subject line should:
1. Be clear and professional
2. Include the job title and company name
3. Stand out in a crowded inbox
4. Match the {template.tone} tone
5. Be 50 characters or less

Generate 3 subject line options and return the best one.
Return only the subject line, no explanation.
"""
        
        try:
            response = await self.llm_manager.generate_text(
                prompt=subject_prompt,
                system_prompt="You are an expert at writing compelling email subject lines for job applications.",
                max_tokens=100
            )
            
            if response.success:
                # Extract the first line as the subject
                subject = response.content.strip().split('\n')[0]
                return subject.replace('"', '').strip()
            else:
                # Fallback to template
                return template.subject_template.format(
                    job_title=request.job_title,
                    company_name=request.company_name
                )
                
        except Exception as e:
            logger.error(f"Error generating subject line: {e}")
            return template.subject_template.format(
                job_title=request.job_title,
                company_name=request.company_name
            )
    
    async def _generate_email_body(self, request: EmailGenerationRequest, template: EmailTemplate, content: Dict[str, Any]) -> str:
        """Generate the email body using template and personalized content."""
        
        try:
            # Prepare template variables
            template_vars = {
                "contact_name": request.contact.name or "Hiring Manager",
                "job_title": request.job_title,
                "company_name": request.company_name,
                "sender_name": self.user_config.name,
                "sender_contact": f"{self.user_config.email} | {self.user_config.phone}",
                "personalized_introduction": content.get("personalized_introduction", ""),
                "experience_highlight": content.get("experience_highlight", ""),
                "skills_alignment": content.get("skills_alignment", ""),
                "company_connection": content.get("company_connection", ""),
                "technical_experience_highlight": content.get("experience_highlight", ""),
                "problem_solving_example": content.get("key_achievements", ""),
                "technical_skills_alignment": content.get("technical_skills_match", ""),
                "key_technologies": ", ".join(content.get("technical_skills_match", "").split(", ")[:3])
            }
            
            # Format template
            email_body = template.body_template.format(**template_vars)
            
            # Clean up any empty sections
            lines = email_body.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Remove lines that are just whitespace or empty placeholders
                if line.strip() and not line.strip() == "":
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            logger.error(f"Error generating email body: {e}")
            return template.body_template  # Return basic template as fallback
    
    def _calculate_personalization_score(self, content: Dict[str, Any]) -> float:
        """Calculate a personalization score based on generated content."""
        score = content.get("personalization_score", 0.5)
        
        # Adjust score based on content quality
        if content.get("company_connection"):
            score += 0.1
        if content.get("key_achievements"):
            score += 0.1
        if content.get("technical_skills_match"):
            score += 0.1
        
        return min(score, 1.0)
    
    async def _save_generated_email(self, email: GeneratedEmail) -> None:
        """Save generated email to database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                contact_email TEXT NOT NULL,
                contact_name TEXT,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                template_used TEXT,
                personalization_score REAL,
                generation_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
            """)
            
            # Insert generated email
            cursor.execute("""
            INSERT INTO generated_emails (
                job_id, contact_email, contact_name, subject, body,
                template_used, personalization_score, generation_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email.job_id,
                email.contact_email,
                email.contact_name,
                email.subject,
                email.body,
                email.template_used,
                email.personalization_score,
                email.generation_notes
            ))
            
            conn.commit()
            logger.info(f"Saved generated email for job {email.job_id}")
            
        except Exception as e:
            logger.error(f"Error saving generated email: {e}")
        finally:
            if conn:
                conn.close()
    
    async def batch_generate_emails(self, requests: List[EmailGenerationRequest]) -> Dict[int, Optional[GeneratedEmail]]:
        """Generate emails for multiple job applications in batch."""
        results = {}
        
        try:
            # Process requests with some delay to respect rate limits
            for i, request in enumerate(requests):
                if i > 0:
                    await asyncio.sleep(1)  # Rate limiting delay
                
                try:
                    result = await self.generate_email(request)
                    results[request.job_id] = result
                except Exception as e:
                    logger.error(f"Error generating email for job {request.job_id}: {e}")
                    results[request.job_id] = None
            
            logger.info(f"Completed batch email generation for {len(requests)} jobs")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch email generation: {e}")
            return {req.job_id: None for req in requests}
    
    async def get_generated_emails_for_job(self, job_id: int) -> List[GeneratedEmail]:
        """Get all generated emails for a specific job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT job_id, contact_email, contact_name, subject, body,
                   template_used, personalization_score, generation_notes, created_at
            FROM generated_emails
            WHERE job_id = ?
            ORDER BY created_at DESC
            """, (job_id,))
            
            rows = cursor.fetchall()
            emails = []
            
            for row in rows:
                email = GeneratedEmail(
                    job_id=row[0],
                    contact_email=row[1],
                    contact_name=row[2],
                    subject=row[3],
                    body=row[4],
                    template_used=row[5],
                    personalization_score=row[6] or 0.0,
                    generation_notes=row[7] or "",
                    created_at=datetime.fromisoformat(row[8]) if row[8] else datetime.now()
                )
                emails.append(email)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error retrieving generated emails for job {job_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

async def generate_email_for_job(
    job_id: int,
    job_title: str,
    company_name: str,
    job_description: str,
    contact: Contact,
    customization_result: Optional[CustomizationResult] = None,
    template_name: str = "professional",
    db_manager: Optional[DatabaseManager] = None
) -> Optional[GeneratedEmail]:
    """
    Convenience function to generate an email for a job application.
    
    Args:
        job_id: Job ID
        job_title: Job title
        company_name: Company name
        job_description: Job description
        contact: Contact information
        customization_result: Optional resume customization result
        template_name: Email template to use
        db_manager: Optional database manager instance
        
    Returns:
        GeneratedEmail or None if generation failed
    """
    if not db_manager:
        from ..config.database import get_db_manager
        db_manager = get_db_manager()
    
    generator = EmailGenerator(db_manager)
    request = EmailGenerationRequest(
        job_id=job_id,
        job_title=job_title,
        company_name=company_name,
        job_description=job_description,
        contact=contact,
        customization_result=customization_result,
        template_name=template_name
    )
    
    return await generator.generate_email(request)