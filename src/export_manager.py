"""
Export Manager Module

This module provides comprehensive export functionality for job application packages,
including emails, resumes, contact lists, and application tracking data.
"""

import os
import json
import csv
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from ..email_composer import GeneratedEmail
from ..contact_finder import Contact, ContactSearchResult
from ..document_manager import DocumentPackage, GeneratedDocument
from ..ai_processing.resume_customizer import CustomizationResult
from ..config import get_config
from ..config.database import DatabaseManager
from ..utils import get_logger

logger = get_logger(__name__)

@dataclass
class ExportPackage:
    """Complete export package for job applications."""
    job_id: int
    job_title: str
    company_name: str
    export_type: str
    files: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    export_path: str

@dataclass
class ExportRequest:
    """Export request configuration."""
    job_ids: List[int]
    export_formats: List[str]  # ['individual', 'bulk_csv', 'email_client', 'application_package']
    include_emails: bool = True
    include_resumes: bool = True
    include_contacts: bool = True
    include_metadata: bool = True
    output_directory: Optional[str] = None

class ApplicationExporter:
    """Handles exporting of job application packages."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.config = get_config()
        
        # Setup export directory
        self.export_base_dir = Path(self.config.export_dir)
        self.export_base_dir.mkdir(parents=True, exist_ok=True)
    
    async def export_job_applications(self, request: ExportRequest) -> Dict[str, Any]:
        """
        Export job applications in the requested formats.
        
        Args:
            request: Export request configuration
            
        Returns:
            Export result summary
        """
        export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_session_dir = self.export_base_dir / f"export_{export_timestamp}"
        export_session_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting export for {len(request.job_ids)} jobs")
        
        results = {
            "export_id": export_timestamp,
            "export_path": str(export_session_dir),
            "total_jobs": len(request.job_ids),
            "successful_exports": 0,
            "failed_exports": 0,
            "exported_packages": [],
            "summary_files": [],
            "errors": []
        }
        
        try:
            # Get job application data
            job_data = await self._get_job_application_data(request.job_ids)
            
            # Export in each requested format
            for export_format in request.export_formats:
                try:
                    format_result = await self._export_in_format(
                        job_data, export_format, export_session_dir, request
                    )
                    results["summary_files"].extend(format_result.get("files", []))
                    results["successful_exports"] += format_result.get("count", 0)
                    
                except Exception as e:
                    logger.error(f"Error exporting in format {export_format}: {e}")
                    results["errors"].append(f"Format {export_format}: {str(e)}")
                    results["failed_exports"] += 1
            
            # Create master summary
            await self._create_export_summary(results, export_session_dir)
            
            logger.info(f"Export completed: {results['successful_exports']} successful, {results['failed_exports']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Critical error during export: {e}")
            results["errors"].append(f"Critical error: {str(e)}")
            return results
    
    async def _get_job_application_data(self, job_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get comprehensive job application data for export."""
        job_data = {}
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get basic job information
            placeholders = ','.join('?' * len(job_ids))
            cursor.execute(f"""
            SELECT id, title, company, description, url, location, posted_date,
                   salary_range, employment_type, experience_level, requirements, created_at
            FROM jobs
            WHERE id IN ({placeholders})
            """, job_ids)
            
            jobs = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            for job_row in jobs:
                job_dict = dict(zip(columns, job_row))
                job_id = job_dict['id']
                
                # Get additional data for each job
                job_data[job_id] = {
                    'job_info': job_dict,
                    'emails': await self._get_emails_for_job(job_id),
                    'contacts': await self._get_contacts_for_job(job_id),
                    'documents': await self._get_documents_for_job(job_id),
                    'customization': await self._get_customization_for_job(job_id),
                    'filter_result': await self._get_filter_result_for_job(job_id)
                }
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error getting job application data: {e}")
            return {}
        finally:
            if conn:
                conn.close()
    
    async def _export_in_format(
        self, 
        job_data: Dict[int, Dict[str, Any]], 
        export_format: str, 
        export_dir: Path,
        request: ExportRequest
    ) -> Dict[str, Any]:
        """Export data in a specific format."""
        
        if export_format == "individual":
            return await self._export_individual_packages(job_data, export_dir, request)
        elif export_format == "bulk_csv":
            return await self._export_bulk_csv(job_data, export_dir, request)
        elif export_format == "email_client":
            return await self._export_email_client_format(job_data, export_dir, request)
        elif export_format == "application_package":
            return await self._export_application_packages(job_data, export_dir, request)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    async def _export_individual_packages(
        self, 
        job_data: Dict[int, Dict[str, Any]], 
        export_dir: Path,
        request: ExportRequest
    ) -> Dict[str, Any]:
        """Export individual application packages for each job."""
        
        individual_dir = export_dir / "individual_applications"
        individual_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        successful_count = 0
        
        for job_id, data in job_data.items():
            try:
                job_info = data['job_info']
                company_name = self._sanitize_filename(job_info['company'])
                job_title = self._sanitize_filename(job_info['title'])
                
                # Create job-specific directory
                job_dir = individual_dir / f"{company_name}_{job_title}_{job_id}"
                job_dir.mkdir(parents=True, exist_ok=True)
                
                # Export emails
                if request.include_emails and data['emails']:
                    emails_file = await self._export_job_emails(data['emails'], job_dir)
                    if emails_file:
                        exported_files.append(str(emails_file))
                
                # Export contacts
                if request.include_contacts and data['contacts']:
                    contacts_file = await self._export_job_contacts(data['contacts'], job_dir)
                    if contacts_file:
                        exported_files.append(str(contacts_file))
                
                # Copy resume documents
                if request.include_resumes and data['documents']:
                    doc_files = await self._copy_job_documents(data['documents'], job_dir)
                    exported_files.extend(doc_files)
                
                # Create job summary
                if request.include_metadata:
                    summary_file = await self._create_job_summary(data, job_dir)
                    if summary_file:
                        exported_files.append(str(summary_file))
                
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Error exporting individual package for job {job_id}: {e}")
        
        return {
            "files": exported_files,
            "count": successful_count,
            "type": "individual_packages"
        }
    
    async def _export_bulk_csv(
        self, 
        job_data: Dict[int, Dict[str, Any]], 
        export_dir: Path,
        request: ExportRequest
    ) -> Dict[str, Any]:
        """Export all data in CSV format."""
        
        csv_dir = export_dir / "csv_exports"
        csv_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        
        # Export jobs CSV
        jobs_file = csv_dir / "jobs.csv"
        with open(jobs_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Job ID', 'Title', 'Company', 'Location', 'Posted Date',
                'Salary Range', 'Employment Type', 'Experience Level',
                'URL', 'Filter Decision', 'Customization Score'
            ])
            
            # Data rows
            for job_id, data in job_data.items():
                job_info = data['job_info']
                filter_result = data.get('filter_result', {})
                customization = data.get('customization', {})
                
                writer.writerow([
                    job_id,
                    job_info.get('title', ''),
                    job_info.get('company', ''),
                    job_info.get('location', ''),
                    job_info.get('posted_date', ''),
                    job_info.get('salary_range', ''),
                    job_info.get('employment_type', ''),
                    job_info.get('experience_level', ''),
                    job_info.get('url', ''),
                    filter_result.get('decision', ''),
                    customization.get('confidence_score', '')
                ])
        
        exported_files.append(str(jobs_file))
        
        # Export emails CSV
        if request.include_emails:
            emails_file = csv_dir / "emails.csv"
            await self._export_all_emails_csv(job_data, emails_file)
            exported_files.append(str(emails_file))
        
        # Export contacts CSV
        if request.include_contacts:
            contacts_file = csv_dir / "contacts.csv"
            await self._export_all_contacts_csv(job_data, contacts_file)
            exported_files.append(str(contacts_file))
        
        return {
            "files": exported_files,
            "count": len(job_data),
            "type": "bulk_csv"
        }
    
    async def _export_email_client_format(
        self, 
        job_data: Dict[int, Dict[str, Any]], 
        export_dir: Path,
        request: ExportRequest
    ) -> Dict[str, Any]:
        """Export emails in email client compatible format."""
        
        email_dir = export_dir / "email_client_ready"
        email_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        email_count = 0
        
        for job_id, data in job_data.items():
            if not data['emails']:
                continue
            
            job_info = data['job_info']
            company_name = self._sanitize_filename(job_info['company'])
            
            # Create individual email files
            for i, email in enumerate(data['emails']):
                filename = f"{company_name}_{job_info['title']}_{i+1}.txt"
                email_file = email_dir / filename
                
                # Format email for copying to email client
                email_content = self._format_email_for_client(email, job_info)
                
                with open(email_file, 'w', encoding='utf-8') as f:
                    f.write(email_content)
                
                exported_files.append(str(email_file))
                email_count += 1
        
        # Create email summary with instructions
        instructions_file = email_dir / "EMAIL_INSTRUCTIONS.txt"
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(self._create_email_client_instructions())
        
        exported_files.append(str(instructions_file))
        
        return {
            "files": exported_files,
            "count": email_count,
            "type": "email_client"
        }
    
    async def _export_application_packages(
        self, 
        job_data: Dict[int, Dict[str, Any]], 
        export_dir: Path,
        request: ExportRequest
    ) -> Dict[str, Any]:
        """Export complete application packages as ZIP files."""
        
        packages_dir = export_dir / "application_packages"
        packages_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        successful_count = 0
        
        for job_id, data in job_data.items():
            try:
                job_info = data['job_info']
                company_name = self._sanitize_filename(job_info['company'])
                job_title = self._sanitize_filename(job_info['title'])
                
                # Create ZIP package
                zip_filename = f"{company_name}_{job_title}_application_package.zip"
                zip_path = packages_dir / zip_filename
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add emails
                    if request.include_emails and data['emails']:
                        for i, email in enumerate(data['emails']):
                            email_content = self._format_email_for_client(email, job_info)
                            zipf.writestr(f"emails/email_{i+1}_{email['contact_name']}.txt", email_content)
                    
                    # Add resume documents
                    if request.include_resumes and data['documents']:
                        for doc in data['documents']['documents']:
                            if os.path.exists(doc['file_path']):
                                zipf.write(doc['file_path'], f"resumes/{doc['filename']}")
                    
                    # Add contacts
                    if request.include_contacts and data['contacts']:
                        contacts_content = self._format_contacts_for_export(data['contacts'])
                        zipf.writestr("contacts/contacts.txt", contacts_content)
                    
                    # Add application summary
                    if request.include_metadata:
                        summary_content = self._create_application_summary(data)
                        zipf.writestr("APPLICATION_SUMMARY.txt", summary_content)
                
                exported_files.append(str(zip_path))
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Error creating application package for job {job_id}: {e}")
        
        return {
            "files": exported_files,
            "count": successful_count,
            "type": "application_packages"
        }
    
    async def _get_emails_for_job(self, job_id: int) -> List[Dict[str, Any]]:
        """Get emails for a specific job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM generated_emails
            WHERE job_id = ?
            ORDER BY created_at DESC
            """, (job_id,))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting emails for job {job_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    async def _get_contacts_for_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get contacts for a specific job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM contact_cache cc
            JOIN jobs j ON cc.company_name = j.company
            WHERE j.id = ?
            ORDER BY cc.created_at DESC
            LIMIT 1
            """, (job_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                contact_data = dict(zip(columns, row))
                contact_data['contacts'] = json.loads(contact_data['contacts_json'])
                return contact_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting contacts for job {job_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def _get_documents_for_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get documents for a specific job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get document package
            cursor.execute("""
            SELECT * FROM document_packages
            WHERE job_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """, (job_id,))
            
            package_row = cursor.fetchone()
            if not package_row:
                return None
            
            # Get individual documents
            cursor.execute("""
            SELECT * FROM generated_documents
            WHERE job_id = ?
            ORDER BY created_at DESC
            """, (job_id,))
            
            doc_rows = cursor.fetchall()
            doc_columns = [desc[0] for desc in cursor.description]
            documents = [dict(zip(doc_columns, row)) for row in doc_rows]
            
            package_columns = [desc[0] for desc in cursor.description]
            package_data = dict(zip(package_columns, package_row))
            package_data['documents'] = documents
            
            return package_data
            
        except Exception as e:
            logger.error(f"Error getting documents for job {job_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def _get_customization_for_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get customization result for a specific job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM resume_customizations
            WHERE job_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """, (job_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting customization for job {job_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def _get_filter_result_for_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get filter result for a specific job."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM filter_results
            WHERE job_id = ?
            ORDER BY processed_at DESC
            LIMIT 1
            """, (job_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting filter result for job {job_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filenames."""
        import re
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', text)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized.lower()
    
    def _format_email_for_client(self, email: Dict[str, Any], job_info: Dict[str, Any]) -> str:
        """Format email for copying to email client."""
        return f"""To: {email['contact_name']} <{email['contact_email']}>
Subject: {email['subject']}

{email['body']}

---
Generated by AI Job Application Automation System
Job: {job_info['title']} at {job_info['company']}
Date: {email.get('created_at', 'Unknown')}
Personalization Score: {email.get('personalization_score', 0):.1%}
"""
    
    def _format_contacts_for_export(self, contacts_data: Dict[str, Any]) -> str:
        """Format contacts for export."""
        if not contacts_data or 'contacts' not in contacts_data:
            return "No contacts found."
        
        contacts = contacts_data['contacts']
        output = [f"Contacts for {contacts_data.get('company_name', 'Unknown Company')}"]
        output.append("=" * 50)
        
        for i, contact in enumerate(contacts, 1):
            output.append(f"\n{i}. {contact.get('name', 'Unknown')}")
            output.append(f"   Email: {contact.get('email', 'N/A')}")
            output.append(f"   Title: {contact.get('title', 'N/A')}")
            output.append(f"   Confidence: {contact.get('confidence', 0):.1%}")
            output.append(f"   Source: {contact.get('source', 'N/A')}")
        
        return "\n".join(output)
    
    def _create_application_summary(self, data: Dict[str, Any]) -> str:
        """Create application summary."""
        job_info = data['job_info']
        output = [
            f"APPLICATION SUMMARY",
            "=" * 50,
            f"Job Title: {job_info.get('title', 'N/A')}",
            f"Company: {job_info.get('company', 'N/A')}",
            f"Location: {job_info.get('location', 'N/A')}",
            f"Posted Date: {job_info.get('posted_date', 'N/A')}",
            f"Job URL: {job_info.get('url', 'N/A')}",
            "",
            "PROCESSING RESULTS:",
        ]
        
        # Filter result
        if data.get('filter_result'):
            filter_result = data['filter_result']
            output.append(f"AI Filter Decision: {filter_result.get('decision', 'N/A')}")
            output.append(f"Filter Confidence: {filter_result.get('confidence_score', 0):.1%}")
        
        # Customization result
        if data.get('customization'):
            customization = data['customization']
            output.append(f"Resume Customization: Completed")
            output.append(f"Customization Confidence: {customization.get('confidence_score', 0):.1%}")
        
        # Contacts found
        if data.get('contacts'):
            contacts_count = len(data['contacts'].get('contacts', []))
            output.append(f"Contacts Found: {contacts_count}")
        
        # Emails generated
        if data.get('emails'):
            emails_count = len(data['emails'])
            output.append(f"Emails Generated: {emails_count}")
        
        # Documents generated
        if data.get('documents'):
            docs_count = len(data['documents'].get('documents', []))
            output.append(f"Documents Generated: {docs_count}")
        
        output.extend([
            "",
            "NEXT STEPS:",
            "1. Review and customize emails as needed",
            "2. Send emails to contacts",
            "3. Follow up as appropriate",
            "4. Track application status",
            "",
            f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        return "\n".join(output)
    
    def _create_email_client_instructions(self) -> str:
        """Create instructions for using exported emails."""
        return """EMAIL CLIENT INSTRUCTIONS
========================

This folder contains ready-to-send emails for your job applications.

USAGE:
1. Open each email file in a text editor
2. Copy the content (Ctrl+A, Ctrl+C)
3. Open your email client (Gmail, Outlook, etc.)
4. Create a new email
5. Paste the content
6. The To: field and Subject: line are already formatted
7. Review and customize as needed
8. Send!

TIPS:
- Always review emails before sending
- Personalize further if needed
- Check that contact information is current
- Follow up appropriately

FILES:
Each file is named: CompanyName_JobTitle_EmailNumber.txt

Generated by AI Job Application Automation System
"""
    
    async def _export_all_emails_csv(self, job_data: Dict[int, Dict[str, Any]], output_file: Path):
        """Export all emails to CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Job ID', 'Company', 'Job Title', 'Contact Name', 'Contact Email',
                'Subject', 'Body Preview', 'Template', 'Personalization Score', 'Created'
            ])
            
            # Data rows
            for job_id, data in job_data.items():
                if not data['emails']:
                    continue
                
                job_info = data['job_info']
                for email in data['emails']:
                    writer.writerow([
                        job_id,
                        job_info.get('company', ''),
                        job_info.get('title', ''),
                        email.get('contact_name', ''),
                        email.get('contact_email', ''),
                        email.get('subject', ''),
                        email.get('body', '')[:100] + "...",  # Preview
                        email.get('template_used', ''),
                        email.get('personalization_score', ''),
                        email.get('created_at', '')
                    ])
    
    async def _export_all_contacts_csv(self, job_data: Dict[int, Dict[str, Any]], output_file: Path):
        """Export all contacts to CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Job ID', 'Company', 'Contact Name', 'Contact Email', 'Title',
                'Confidence', 'Source', 'Verified'
            ])
            
            # Data rows
            for job_id, data in job_data.items():
                if not data['contacts'] or not data['contacts'].get('contacts'):
                    continue
                
                job_info = data['job_info']
                for contact in data['contacts']['contacts']:
                    writer.writerow([
                        job_id,
                        job_info.get('company', ''),
                        contact.get('name', ''),
                        contact.get('email', ''),
                        contact.get('title', ''),
                        contact.get('confidence', ''),
                        contact.get('source', ''),
                        contact.get('verified', False)
                    ])
    
    async def _create_export_summary(self, results: Dict[str, Any], export_dir: Path):
        """Create master export summary."""
        summary_file = export_dir / "EXPORT_SUMMARY.txt"
        
        summary_content = [
            "EXPORT SUMMARY",
            "=" * 50,
            f"Export ID: {results['export_id']}",
            f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Jobs: {results['total_jobs']}",
            f"Successful Exports: {results['successful_exports']}",
            f"Failed Exports: {results['failed_exports']}",
            "",
            "FILES GENERATED:",
        ]
        
        for file_path in results['summary_files']:
            relative_path = Path(file_path).relative_to(export_dir)
            summary_content.append(f"  - {relative_path}")
        
        if results['errors']:
            summary_content.extend(["", "ERRORS:"])
            for error in results['errors']:
                summary_content.append(f"  - {error}")
        
        summary_content.extend([
            "",
            "USAGE:",
            "- Review individual application packages",
            "- Use email client ready files for quick sending",
            "- Import CSV files for tracking and analysis",
            "",
            "Generated by AI Job Application Automation System"
        ])
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary_content))
        
        results['summary_files'].append(str(summary_file))

async def export_approved_applications(
    job_ids: Optional[List[int]] = None,
    export_formats: List[str] = None,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Convenience function to export approved job applications.
    
    Args:
        job_ids: Optional list of specific job IDs to export
        export_formats: Export formats to use
        db_manager: Optional database manager instance
        
    Returns:
        Export results summary
    """
    if not db_manager:
        from ..config.database import get_db_manager
        db_manager = get_db_manager()
    
    if export_formats is None:
        export_formats = ["individual", "bulk_csv", "email_client", "application_package"]
    
    # Get approved job IDs if not provided
    if job_ids is None:
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT DISTINCT fr.job_id 
            FROM filter_results fr
            WHERE fr.decision = 'accept'
            ORDER BY fr.processed_at DESC
            """)
            
            job_ids = [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting approved jobs: {e}")
            job_ids = []
        finally:
            if conn:
                conn.close()
    
    if not job_ids:
        return {
            "export_id": "no_jobs",
            "total_jobs": 0,
            "successful_exports": 0,
            "failed_exports": 0,
            "exported_packages": [],
            "summary_files": [],
            "errors": ["No approved jobs found for export"]
        }
    
    # Create export request
    request = ExportRequest(
        job_ids=job_ids,
        export_formats=export_formats
    )
    
    # Export applications
    exporter = ApplicationExporter(db_manager)
    return await exporter.export_job_applications(request)