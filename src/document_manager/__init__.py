"""
Document management module for the AI Job Application Preparation Tool.

This module handles resume templates, document generation, and file management.
"""

from .resume_handler import (
    ResumeTemplateHandler,
    ResumeData,
    ContactInfo,
    WorkExperience,
    Education,
    Skill,
    load_resume_template
)

from .document_manager import (
    DocumentManager,
    DocumentGenerationRequest,
    GeneratedDocument,
    DocumentPackage,
    PDFGenerator,
    HTMLFormatter,
    generate_documents_for_customization
)

__all__ = [
    'ResumeTemplateHandler',
    'ResumeData',
    'ContactInfo',
    'WorkExperience',
    'Education',
    'Skill',
    'load_resume_template',
    'DocumentManager',
    'DocumentGenerationRequest',
    'GeneratedDocument',
    'DocumentPackage',
    'PDFGenerator',
    'HTMLFormatter',
    'generate_documents_for_customization'
]