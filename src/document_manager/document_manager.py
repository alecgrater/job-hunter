"""
Document Manager Module

This module provides comprehensive document management functionality including
PDF generation, HTML formatting, and resume document handling for the AI Job
Application Preparation Tool.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

if TYPE_CHECKING:
    from ..ai_processing.resume_customizer import CustomizationResult

try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("pdfkit not available - PDF generation will be disabled")

from .resume_handler import ResumeTemplateHandler, ResumeData
# Remove circular import - will use TYPE_CHECKING for type hints
from ..config import get_config
from ..config.database import DatabaseManager
from ..utils import get_logger

logger = get_logger(__name__)

@dataclass
class DocumentGenerationRequest:
    """Request for document generation."""
    job_id: int
    job_title: str
    company_name: str
    resume_data: ResumeData
    output_formats: List[str]  # ['html', 'pdf', 'markdown']
    filename_prefix: Optional[str] = None

@dataclass
class GeneratedDocument:
    """Generated document information."""
    job_id: int
    document_type: str  # 'html', 'pdf', 'markdown'
    file_path: str
    filename: str
    file_size: int
    created_at: datetime

@dataclass
class DocumentPackage:
    """Complete document package for a job application."""
    job_id: int
    job_title: str
    company_name: str
    documents: List[GeneratedDocument]
    total_size: int
    created_at: datetime

class PDFGenerator:
    """PDF document generation utilities."""
    
    def __init__(self):
        self.config = get_config()
        self.wkhtmltopdf_path = self._find_wkhtmltopdf()
        
        # PDF options
        self.pdf_options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
    
    def _find_wkhtmltopdf(self) -> Optional[str]:
        """Find wkhtmltopdf executable path."""
        if not PDFKIT_AVAILABLE:
            return None
        
        # Common paths for wkhtmltopdf
        common_paths = [
            '/usr/local/bin/wkhtmltopdf',
            '/usr/bin/wkhtmltopdf',
            '/opt/homebrew/bin/wkhtmltopdf',
            'wkhtmltopdf'  # System PATH
        ]
        
        for path in common_paths:
            if os.path.exists(path) or os.system(f"which {path}") == 0:
                return path
        
        return None
    
    def generate_pdf_from_html(self, html_content: str, output_path: str) -> bool:
        """
        Generate PDF from HTML content.
        
        Args:
            html_content: HTML content to convert
            output_path: Output PDF file path
            
        Returns:
            True if successful, False otherwise
        """
        if not PDFKIT_AVAILABLE:
            logger.error("pdfkit not available - cannot generate PDF")
            return False
        
        if not self.wkhtmltopdf_path:
            logger.error("wkhtmltopdf not found - cannot generate PDF")
            return False
        
        try:
            # Configure pdfkit with wkhtmltopdf path
            config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)
            
            # Generate PDF
            pdfkit.from_string(
                html_content,
                output_path,
                options=self.pdf_options,
                configuration=config
            )
            
            logger.info(f"PDF generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if PDF generation is available."""
        return PDFKIT_AVAILABLE and self.wkhtmltopdf_path is not None

class HTMLFormatter:
    """HTML formatting utilities for resumes."""
    
    @staticmethod
    def create_professional_html(resume_data: ResumeData, job_title: str = "", company_name: str = "") -> str:
        """Create professionally formatted HTML resume."""
        
        # Enhanced CSS styles
        css_styles = """
        <style>
            body {
                font-family: 'Arial', 'Helvetica', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px 20px;
                background-color: #fff;
            }
            
            .header {
                text-align: center;
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }
            
            .header h1 {
                color: #2c3e50;
                font-size: 2.5em;
                margin: 0 0 10px 0;
                font-weight: 300;
            }
            
            .header .title {
                color: #7f8c8d;
                font-size: 1.2em;
                font-weight: 500;
                margin-bottom: 15px;
            }
            
            .contact-info {
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 20px;
                font-size: 0.9em;
                color: #555;
            }
            
            .contact-info .contact-item {
                display: flex;
                align-items: center;
                gap: 5px;
            }
            
            .section {
                margin-bottom: 35px;
            }
            
            .section h2 {
                color: #2c3e50;
                font-size: 1.4em;
                border-bottom: 2px solid #3498db;
                padding-bottom: 8px;
                margin-bottom: 20px;
                font-weight: 600;
            }
            
            .job {
                margin-bottom: 25px;
                padding-left: 0;
            }
            
            .job-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 8px;
            }
            
            .job-title {
                font-weight: 600;
                color: #2c3e50;
                font-size: 1.1em;
            }
            
            .job-company {
                font-weight: 500;
                color: #3498db;
            }
            
            .job-meta {
                color: #7f8c8d;
                font-style: italic;
                font-size: 0.9em;
                margin-bottom: 10px;
            }
            
            .job-description ul {
                margin: 0;
                padding-left: 20px;
            }
            
            .job-description li {
                margin-bottom: 6px;
                line-height: 1.5;
            }
            
            .skills-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
            }
            
            .skill-category {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #3498db;
            }
            
            .skill-category h3 {
                margin: 0 0 10px 0;
                color: #2c3e50;
                font-size: 1em;
                font-weight: 600;
            }
            
            .skill-list {
                color: #555;
                font-size: 0.9em;
                line-height: 1.4;
            }
            
            .education {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 15px;
            }
            
            .education-degree {
                font-weight: 600;
                color: #2c3e50;
                font-size: 1.1em;
            }
            
            .education-school {
                color: #3498db;
                font-weight: 500;
            }
            
            .education-year {
                color: #7f8c8d;
                font-size: 0.9em;
            }
            
            .summary {
                background-color: #ecf0f1;
                padding: 20px;
                border-radius: 5px;
                font-size: 1.05em;
                line-height: 1.7;
                color: #2c3e50;
                text-align: justify;
            }
            
            .customization-note {
                background-color: #e8f6f3;
                border-left: 4px solid #1abc9c;
                padding: 15px;
                margin-bottom: 20px;
                font-size: 0.9em;
                color: #16a085;
            }
            
            @media print {
                body { padding: 20px; }
                .section { page-break-inside: avoid; }
                .job { page-break-inside: avoid; }
            }
        </style>
        """
        
        # Build HTML content
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            f"<title>{resume_data.contact_info.name} - Resume</title>",
            css_styles,
            "</head>",
            "<body>"
        ]
        
        # Customization note if job-specific
        if job_title and company_name:
            html_parts.extend([
                "<div class='customization-note'>",
                f"<strong>Customized for:</strong> {job_title} at {company_name}",
                "</div>"
            ])
        
        # Header section
        html_parts.extend([
            "<div class='header'>",
            f"<h1>{resume_data.contact_info.name}</h1>",
            "<div class='title'>Software Engineer & Problem Solver</div>",
            "<div class='contact-info'>"
        ])
        
        # Contact information
        contact_items = []
        if resume_data.contact_info.email:
            contact_items.append(f"<div class='contact-item'>📧 {resume_data.contact_info.email}</div>")
        if resume_data.contact_info.phone:
            contact_items.append(f"<div class='contact-item'>📱 {resume_data.contact_info.phone}</div>")
        if resume_data.contact_info.linkedin:
            contact_items.append(f"<div class='contact-item'>🔗 <a href='{resume_data.contact_info.linkedin}'>LinkedIn</a></div>")
        if resume_data.contact_info.location:
            contact_items.append(f"<div class='contact-item'>📍 {resume_data.contact_info.location}</div>")
        
        html_parts.extend(contact_items)
        html_parts.extend(["</div>", "</div>"])
        
        # Professional Summary
        if resume_data.professional_summary:
            html_parts.extend([
                "<div class='section'>",
                "<h2>Professional Summary</h2>",
                f"<div class='summary'>{resume_data.professional_summary}</div>",
                "</div>"
            ])
        
        # Work Experience
        if resume_data.work_experience:
            html_parts.extend([
                "<div class='section'>",
                "<h2>Work Experience</h2>"
            ])
            
            for exp in resume_data.work_experience:
                html_parts.extend([
                    "<div class='job'>",
                    "<div class='job-header'>",
                    "<div>",
                    f"<div class='job-title'>{exp.title}</div>",
                    f"<div class='job-company'>{exp.company}</div>",
                    "</div>",
                    "</div>"
                ])
                
                # Job meta information
                meta_parts = []
                if exp.start_date:
                    date_range = exp.start_date
                    if exp.end_date:
                        date_range += f" – {exp.end_date}"
                    meta_parts.append(date_range)
                if exp.location:
                    meta_parts.append(exp.location)
                
                if meta_parts:
                    html_parts.append(f"<div class='job-meta'>{' | '.join(meta_parts)}</div>")
                
                # Job description
                if exp.description:
                    html_parts.extend([
                        "<div class='job-description'>",
                        "<ul>"
                    ])
                    for desc in exp.description:
                        html_parts.append(f"<li>{desc}</li>")
                    html_parts.extend(["</ul>", "</div>"])
                
                html_parts.append("</div>")
            
            html_parts.append("</div>")
        
        # Technical Skills
        if resume_data.technical_skills:
            html_parts.extend([
                "<div class='section'>",
                "<h2>Technical Skills</h2>",
                "<div class='skills-grid'>"
            ])
            
            for skill in resume_data.technical_skills:
                skills_text = ", ".join(skill.skills)
                html_parts.extend([
                    "<div class='skill-category'>",
                    f"<h3>{skill.category}</h3>",
                    f"<div class='skill-list'>{skills_text}</div>",
                    "</div>"
                ])
            
            html_parts.extend(["</div>", "</div>"])
        
        # Education
        if resume_data.education:
            html_parts.extend([
                "<div class='section'>",
                "<h2>Education</h2>"
            ])
            
            for edu in resume_data.education:
                html_parts.extend([
                    "<div class='education'>",
                    f"<div class='education-degree'>{edu.degree}</div>",
                    f"<div class='education-school'>{edu.institution}</div>"
                ])
                
                if edu.year:
                    html_parts.append(f"<div class='education-year'>{edu.year}</div>")
                
                if edu.details:
                    html_parts.append("<ul>")
                    for detail in edu.details:
                        html_parts.append(f"<li>{detail}</li>")
                    html_parts.append("</ul>")
                
                html_parts.append("</div>")
            
            html_parts.append("</div>")
        
        # Additional sections
        for section_name, content in resume_data.additional_sections.items():
            section_title = section_name.replace('_', ' ').title()
            html_parts.extend([
                "<div class='section'>",
                f"<h2>{section_title}</h2>",
                f"<div>{content}</div>",
                "</div>"
            ])
        
        html_parts.extend(["</body>", "</html>"])
        
        return "\n".join(html_parts)

class DocumentManager:
    """Comprehensive document management for resumes and job applications."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.config = get_config()
        self.pdf_generator = PDFGenerator()
        self.resume_handler = ResumeTemplateHandler()
        
        # Ensure export directory exists
        self.export_dir = Path(self.config.export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_documents_for_job(self, request: DocumentGenerationRequest) -> Optional[DocumentPackage]:
        """
        Generate all requested document formats for a job application.
        
        Args:
            request: Document generation request
            
        Returns:
            DocumentPackage with all generated documents
        """
        try:
            generated_documents = []
            
            # Create job-specific directory
            job_dir = self.export_dir / f"job_{request.job_id}_{self._sanitize_filename(request.company_name)}"
            job_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename prefix
            if request.filename_prefix:
                filename_base = request.filename_prefix
            else:
                filename_base = f"{self._sanitize_filename(request.company_name)}_{self._sanitize_filename(request.job_title)}_resume"
            
            # Generate each requested format
            for format_type in request.output_formats:
                document = await self._generate_single_document(
                    request, format_type, job_dir, filename_base
                )
                if document:
                    generated_documents.append(document)
            
            # Calculate total package size
            total_size = sum(doc.file_size for doc in generated_documents)
            
            # Create document package
            package = DocumentPackage(
                job_id=request.job_id,
                job_title=request.job_title,
                company_name=request.company_name,
                documents=generated_documents,
                total_size=total_size,
                created_at=datetime.now()
            )
            
            # Save package info to database
            await self._save_document_package(package)
            
            logger.info(f"Generated {len(generated_documents)} documents for job {request.job_id}")
            return package
            
        except Exception as e:
            logger.error(f"Error generating documents for job {request.job_id}: {e}")
            return None
    
    async def _generate_single_document(
        self, 
        request: DocumentGenerationRequest, 
        format_type: str, 
        output_dir: Path, 
        filename_base: str
    ) -> Optional[GeneratedDocument]:
        """Generate a single document in the specified format."""
        
        try:
            if format_type == 'markdown':
                return await self._generate_markdown_document(request, output_dir, filename_base)
            elif format_type == 'html':
                return await self._generate_html_document(request, output_dir, filename_base)
            elif format_type == 'pdf':
                return await self._generate_pdf_document(request, output_dir, filename_base)
            else:
                logger.warning(f"Unsupported document format: {format_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating {format_type} document: {e}")
            return None
    
    async def _generate_markdown_document(
        self, 
        request: DocumentGenerationRequest, 
        output_dir: Path, 
        filename_base: str
    ) -> Optional[GeneratedDocument]:
        """Generate markdown resume document."""
        
        filename = f"{filename_base}.md"
        file_path = output_dir / filename
        
        # Convert resume data to markdown
        markdown_content = self.resume_handler.to_markdown(request.resume_data)
        
        # Add job-specific header if applicable
        if request.job_title and request.company_name:
            header = f"<!-- Customized for {request.job_title} at {request.company_name} -->\n\n"
            markdown_content = header + markdown_content
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        file_size = file_path.stat().st_size
        
        return GeneratedDocument(
            job_id=request.job_id,
            document_type='markdown',
            file_path=str(file_path),
            filename=filename,
            file_size=file_size,
            created_at=datetime.now()
        )
    
    async def _generate_html_document(
        self, 
        request: DocumentGenerationRequest, 
        output_dir: Path, 
        filename_base: str
    ) -> Optional[GeneratedDocument]:
        """Generate HTML resume document."""
        
        filename = f"{filename_base}.html"
        file_path = output_dir / filename
        
        # Generate professional HTML
        html_content = HTMLFormatter.create_professional_html(
            request.resume_data,
            request.job_title,
            request.company_name
        )
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        file_size = file_path.stat().st_size
        
        return GeneratedDocument(
            job_id=request.job_id,
            document_type='html',
            file_path=str(file_path),
            filename=filename,
            file_size=file_size,
            created_at=datetime.now()
        )
    
    async def _generate_pdf_document(
        self, 
        request: DocumentGenerationRequest, 
        output_dir: Path, 
        filename_base: str
    ) -> Optional[GeneratedDocument]:
        """Generate PDF resume document."""
        
        if not self.pdf_generator.is_available():
            logger.warning("PDF generation not available - skipping PDF document")
            return None
        
        filename = f"{filename_base}.pdf"
        file_path = output_dir / filename
        
        # Generate HTML first
        html_content = HTMLFormatter.create_professional_html(
            request.resume_data,
            request.job_title,
            request.company_name
        )
        
        # Convert to PDF
        success = self.pdf_generator.generate_pdf_from_html(html_content, str(file_path))
        
        if not success:
            logger.error("Failed to generate PDF document")
            return None
        
        file_size = file_path.stat().st_size
        
        return GeneratedDocument(
            job_id=request.job_id,
            document_type='pdf',
            file_path=str(file_path),
            filename=filename,
            file_size=file_size,
            created_at=datetime.now()
        )
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filenames."""
        import re
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', text)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized.lower()
    
    async def _save_document_package(self, package: DocumentPackage) -> None:
        """Save document package information to database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                job_title TEXT,
                company_name TEXT,
                total_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                document_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
            """)
            
            # Insert package
            cursor.execute("""
            INSERT INTO document_packages (job_id, job_title, company_name, total_size)
            VALUES (?, ?, ?, ?)
            """, (package.job_id, package.job_title, package.company_name, package.total_size))
            
            # Insert documents
            for doc in package.documents:
                cursor.execute("""
                INSERT INTO generated_documents (
                    job_id, document_type, file_path, filename, file_size
                ) VALUES (?, ?, ?, ?, ?)
                """, (doc.job_id, doc.document_type, doc.file_path, doc.filename, doc.file_size))
            
            conn.commit()
            logger.info(f"Saved document package for job {package.job_id}")
            
        except Exception as e:
            logger.error(f"Error saving document package: {e}")
        finally:
            if conn:
                conn.close()
    
    async def get_documents_for_job(self, job_id: int) -> Optional[DocumentPackage]:
        """Get generated documents for a specific job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get package info
            cursor.execute("""
            SELECT job_title, company_name, total_size, created_at
            FROM document_packages
            WHERE job_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """, (job_id,))
            
            package_row = cursor.fetchone()
            if not package_row:
                return None
            
            # Get documents
            cursor.execute("""
            SELECT document_type, file_path, filename, file_size, created_at
            FROM generated_documents
            WHERE job_id = ?
            ORDER BY created_at DESC
            """, (job_id,))
            
            doc_rows = cursor.fetchall()
            documents = []
            
            for row in doc_rows:
                doc = GeneratedDocument(
                    job_id=job_id,
                    document_type=row[0],
                    file_path=row[1],
                    filename=row[2],
                    file_size=row[3] or 0,
                    created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now()
                )
                documents.append(doc)
            
            return DocumentPackage(
                job_id=job_id,
                job_title=package_row[0],
                company_name=package_row[1],
                documents=documents,
                total_size=package_row[2] or 0,
                created_at=datetime.fromisoformat(package_row[3]) if package_row[3] else datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error retrieving documents for job {job_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def batch_generate_documents(self, requests: List[DocumentGenerationRequest]) -> Dict[int, Optional[DocumentPackage]]:
        """Generate documents for multiple jobs in batch."""
        results = {}
        
        try:
            for request in requests:
                try:
                    package = await self.generate_documents_for_job(request)
                    results[request.job_id] = package
                    
                    # Small delay to avoid overwhelming the system
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error generating documents for job {request.job_id}: {e}")
                    results[request.job_id] = None
            
            logger.info(f"Completed batch document generation for {len(requests)} jobs")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch document generation: {e}")
            return {req.job_id: None for req in requests}

async def generate_documents_for_customization(
    customization_result: "CustomizationResult",
    output_formats: List[str] = None,
    db_manager: Optional[DatabaseManager] = None
) -> Optional[DocumentPackage]:
    """
    Convenience function to generate documents from a customization result.
    
    Args:
        customization_result: Resume customization result
        output_formats: List of formats to generate ['html', 'pdf', 'markdown']
        db_manager: Optional database manager instance
        
    Returns:
        DocumentPackage or None if generation failed
    """
    if not db_manager:
        from ..config.database import get_db_manager
        db_manager = get_db_manager()
    
    if output_formats is None:
        output_formats = ['html', 'pdf', 'markdown']
    
    # Get job details for the request (you'd need to implement this)
    # For now, we'll use placeholder values
    request = DocumentGenerationRequest(
        job_id=customization_result.job_id,
        job_title="Software Engineer",  # This should come from job data
        company_name="Target Company",  # This should come from job data
        resume_data=customization_result.customized_resume,
        output_formats=output_formats
    )
    
    manager = DocumentManager(db_manager)
    return await manager.generate_documents_for_job(request)