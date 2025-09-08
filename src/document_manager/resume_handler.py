"""
Resume template handler for parsing, storing, and managing resume content.

This module provides functionality to load resume templates from markdown,
parse them into structured data, and prepare them for AI customization.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import markdown
from markdown.extensions import codehilite, tables, toc
import logging

from ..config import get_config
from ..utils import get_logger

logger = get_logger(__name__)

@dataclass
class ContactInfo:
    """Contact information structure."""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""

@dataclass
class WorkExperience:
    """Work experience entry."""
    title: str = ""
    company: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    description: List[str] = None
    
    def __post_init__(self):
        if self.description is None:
            self.description = []

@dataclass
class Education:
    """Education entry."""
    degree: str = ""
    institution: str = ""
    year: str = ""
    location: str = ""
    details: List[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = []

@dataclass
class Skill:
    """Skill entry with category."""
    category: str = ""
    skills: List[str] = None
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []

@dataclass
class ResumeData:
    """Structured resume data."""
    contact_info: ContactInfo = None
    professional_summary: str = ""
    work_experience: List[WorkExperience] = None
    education: List[Education] = None
    technical_skills: List[Skill] = None
    additional_sections: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.contact_info is None:
            self.contact_info = ContactInfo()
        if self.work_experience is None:
            self.work_experience = []
        if self.education is None:
            self.education = []
        if self.technical_skills is None:
            self.technical_skills = []
        if self.additional_sections is None:
            self.additional_sections = {}

class ResumeTemplateHandler:
    """Handles loading, parsing, and managing resume templates."""
    
    def __init__(self, template_path: Optional[str] = None):
        """Initialize with template path."""
        self.config = get_config()
        self.template_path = template_path or Path(self.config.template_dir) / "resume_template.md"
        self.resume_data: Optional[ResumeData] = None
        self.raw_markdown: str = ""
    
    def load_template(self, template_path: Optional[str] = None) -> bool:
        """
        Load resume template from markdown file.
        
        Args:
            template_path: Optional path to template file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        path = Path(template_path) if template_path else self.template_path
        
        try:
            if not path.exists():
                logger.error(f"Resume template not found: {path}")
                return False
            
            with open(path, 'r', encoding='utf-8') as f:
                self.raw_markdown = f.read()
            
            logger.info(f"Loaded resume template from {path}")
            return self.parse_template()
            
        except Exception as e:
            logger.error(f"Failed to load resume template: {e}")
            return False
    
    def parse_template(self) -> bool:
        """
        Parse the loaded markdown template into structured data.
        
        Returns:
            True if parsed successfully, False otherwise
        """
        try:
            self.resume_data = ResumeData()
            lines = self.raw_markdown.split('\n')
            
            current_section = None
            current_subsection = None
            buffer = []
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines in most contexts
                if not line and current_section != "professional_summary":
                    continue
                
                # Main sections (# headers)
                if line.startswith('# '):
                    # Process previous section
                    if current_section and buffer:
                        self._process_section(current_section, buffer, current_subsection)
                    
                    # Extract name from title
                    name_match = re.match(r'# (.+)', line)
                    if name_match:
                        self.resume_data.contact_info.name = name_match.group(1).strip()
                    
                    current_section = "header"
                    current_subsection = None
                    buffer = []
                
                # Subsections (## headers)
                elif line.startswith('## '):
                    # Process previous section
                    if current_section and buffer:
                        self._process_section(current_section, buffer, current_subsection)
                    
                    section_name = line[3:].strip().lower().replace(' ', '_')
                    current_section = section_name
                    current_subsection = None
                    buffer = []
                
                # Work experience entries (### headers)
                elif line.startswith('### '):
                    # Process previous subsection
                    if current_subsection and buffer:
                        self._process_subsection(current_section, current_subsection, buffer)
                    
                    current_subsection = line[4:].strip()
                    buffer = []
                
                else:
                    buffer.append(line)
            
            # Process final section
            if current_section and buffer:
                self._process_section(current_section, buffer, current_subsection)
            
            logger.info("Resume template parsed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to parse resume template: {e}")
            return False
    
    def _process_section(self, section: str, lines: List[str], subsection: Optional[str] = None) -> None:
        """Process a section of the resume."""
        if section == "header":
            self._parse_header(lines)
        elif section == "professional_summary":
            self._parse_professional_summary(lines)
        elif section == "work_experience":
            if subsection:
                self._process_subsection(section, subsection, lines)
        elif section == "technical_skills":
            self._parse_technical_skills(lines)
        elif section == "education":
            self._parse_education(lines)
        else:
            # Additional sections
            content = '\n'.join(lines).strip()
            if content:
                self.resume_data.additional_sections[section] = content
    
    def _process_subsection(self, section: str, subsection: str, lines: List[str]) -> None:
        """Process a subsection (like individual work experiences)."""
        if section == "work_experience":
            self._parse_work_experience(subsection, lines)
    
    def _parse_header(self, lines: List[str]) -> None:
        """Parse header section with contact information."""
        for line in lines:
            # Look for contact info patterns
            if '📧' in line or '@' in line:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
                if email_match:
                    self.resume_data.contact_info.email = email_match.group()
            
            elif '📱' in line or re.search(r'\(\d{3}\)', line):
                phone_match = re.search(r'[\+\d\(\)\-\s]+', line)
                if phone_match:
                    self.resume_data.contact_info.phone = phone_match.group().strip()
            
            elif '🔗' in line or 'linkedin.com' in line:
                linkedin_match = re.search(r'linkedin\.com/in/[\w\-]+', line)
                if linkedin_match:
                    self.resume_data.contact_info.linkedin = f"https://{linkedin_match.group()}"
            
            elif '📍' in line:
                # Extract location (everything after the emoji)
                location_match = re.search(r'📍\s*(.+)', line)
                if location_match:
                    self.resume_data.contact_info.location = location_match.group(1).strip()
    
    def _parse_professional_summary(self, lines: List[str]) -> None:
        """Parse professional summary section."""
        summary_lines = [line for line in lines if line and not line.startswith('**')]
        self.resume_data.professional_summary = ' '.join(summary_lines).strip()
    
    def _parse_work_experience(self, title_line: str, lines: List[str]) -> None:
        """Parse individual work experience entry."""
        experience = WorkExperience()
        
        # Parse title line: "Title — Company"
        if '—' in title_line:
            parts = title_line.split('—')
            experience.title = parts[0].strip()
            experience.company = parts[1].strip()
        else:
            experience.title = title_line.strip()
        
        # Parse details from lines
        for line in lines:
            if line.startswith('*') and '|' in line:
                # Date and location line: "*Jan 2020 – Present | Location*"
                date_location = line.strip('*').strip()
                if '|' in date_location:
                    date_part, location_part = date_location.split('|', 1)
                    
                    # Parse dates
                    date_range = date_part.strip()
                    if '–' in date_range:
                        start, end = date_range.split('–', 1)
                        experience.start_date = start.strip()
                        experience.end_date = end.strip()
                    else:
                        experience.start_date = date_range
                    
                    experience.location = location_part.strip()
            
            elif line.startswith('- '):
                # Bullet point
                bullet = line[2:].strip()
                if bullet:
                    experience.description.append(bullet)
        
        self.resume_data.work_experience.append(experience)
    
    def _parse_technical_skills(self, lines: List[str]) -> None:
        """Parse technical skills section."""
        for line in lines:
            if line.startswith('- **') and ':**' in line:
                # Category line: "- **Languages & Tools:** Python, SQL, ..."
                category_match = re.match(r'- \*\*(.+?):\*\*\s*(.+)', line)
                if category_match:
                    category = category_match.group(1).strip()
                    skills_text = category_match.group(2).strip()
                    skills = [skill.strip() for skill in skills_text.split(',') if skill.strip()]
                    
                    skill_entry = Skill(category=category, skills=skills)
                    self.resume_data.technical_skills.append(skill_entry)
    
    def _parse_education(self, lines: List[str]) -> None:
        """Parse education section."""
        education = Education()
        
        for line in lines:
            if line.startswith('**') and '**' in line[2:]:
                # Degree line: "**Bachelor of Economics** — University of Massachusetts Amherst, 2016"
                degree_match = re.match(r'\*\*(.+?)\*\*\s*—\s*(.+?)(?:,\s*(\d{4}))?$', line)
                if degree_match:
                    education.degree = degree_match.group(1).strip()
                    institution_part = degree_match.group(2).strip()
                    year_part = degree_match.group(3)
                    
                    # Handle case where year might be part of institution
                    if year_part:
                        education.institution = institution_part
                        education.year = year_part
                    else:
                        # Try to extract year from institution part
                        year_match = re.search(r'(.+?),?\s*(\d{4})$', institution_part)
                        if year_match:
                            education.institution = year_match.group(1).strip()
                            education.year = year_match.group(2)
                        else:
                            education.institution = institution_part
            
            elif line.startswith('- '):
                # Detail line
                detail = line[2:].strip()
                if detail:
                    education.details.append(detail)
        
        if education.degree or education.institution:
            self.resume_data.education.append(education)
    
    def get_resume_data(self) -> Optional[ResumeData]:
        """Get parsed resume data."""
        return self.resume_data
    
    def get_raw_markdown(self) -> str:
        """Get raw markdown content."""
        return self.raw_markdown
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resume data to dictionary."""
        if not self.resume_data:
            return {}
        return asdict(self.resume_data)
    
    def to_markdown(self, resume_data: Optional[ResumeData] = None) -> str:
        """
        Convert resume data back to markdown format.
        
        Args:
            resume_data: Optional resume data to convert, uses loaded data if None
            
        Returns:
            Markdown formatted resume
        """
        data = resume_data or self.resume_data
        if not data:
            return ""
        
        lines = []
        
        # Header
        lines.append(f"# {data.contact_info.name}")
        lines.append("**Software Engineer & Problem Solver**")
        lines.append("")
        
        # Contact info
        contact_parts = []
        if data.contact_info.email:
            contact_parts.append(f"📧 {data.contact_info.email}")
        if data.contact_info.phone:
            contact_parts.append(f"📱 {data.contact_info.phone}")
        if data.contact_info.linkedin:
            contact_parts.append(f"🔗 [{data.contact_info.linkedin}]({data.contact_info.linkedin})")
        if data.contact_info.location:
            contact_parts.append(f"📍 {data.contact_info.location}")
        
        if contact_parts:
            lines.append(" | ".join(contact_parts))
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Professional Summary
        if data.professional_summary:
            lines.append("## Professional Summary")
            lines.append(data.professional_summary)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Work Experience
        if data.work_experience:
            lines.append("## Work Experience")
            lines.append("")
            
            for exp in data.work_experience:
                lines.append(f"### {exp.title} — {exp.company}")
                
                date_location = []
                if exp.start_date:
                    date_range = exp.start_date
                    if exp.end_date:
                        date_range += f" – {exp.end_date}"
                    date_location.append(date_range)
                if exp.location:
                    date_location.append(exp.location)
                
                if date_location:
                    lines.append(f"*{' | '.join(date_location)}*")
                
                for desc in exp.description:
                    lines.append(f"- {desc}")
                
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # Technical Skills
        if data.technical_skills:
            lines.append("## Technical Skills")
            for skill in data.technical_skills:
                skills_text = ", ".join(skill.skills)
                lines.append(f"- **{skill.category}:** {skills_text}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Education
        if data.education:
            lines.append("## Education")
            for edu in data.education:
                edu_line = f"**{edu.degree}**"
                if edu.institution:
                    edu_line += f" — {edu.institution}"
                if edu.year:
                    edu_line += f", {edu.year}"
                lines.append(edu_line)
                
                for detail in edu.details:
                    lines.append(f"- {detail}")
                
                lines.append("")
        
        # Additional sections
        for section_name, content in data.additional_sections.items():
            section_title = section_name.replace('_', ' ').title()
            lines.append(f"## {section_title}")
            lines.append(content)
            lines.append("")
        
        return "\n".join(lines)
    
    def to_html(self, resume_data: Optional[ResumeData] = None) -> str:
        """
        Convert resume data to HTML format.
        
        Args:
            resume_data: Optional resume data to convert
            
        Returns:
            HTML formatted resume
        """
        markdown_content = self.to_markdown(resume_data)
        
        # Configure markdown with extensions
        md = markdown.Markdown(
            extensions=['codehilite', 'tables', 'toc'],
            extension_configs={
                'codehilite': {'css_class': 'highlight'},
                'toc': {'permalink': True}
            }
        )
        
        html_content = md.convert(markdown_content)
        
        # Wrap in basic HTML structure
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.resume_data.contact_info.name if self.resume_data else 'Resume'}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
        h2 {{ color: #34495e; border-bottom: 1px solid #bdc3c7; }}
        h3 {{ color: #2c3e50; }}
        .highlight {{ background-color: #f8f9fa; padding: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""
        return html_template
    
    def save_template(self, path: str, resume_data: Optional[ResumeData] = None) -> bool:
        """
        Save resume data as markdown template.
        
        Args:
            path: Path to save the template
            resume_data: Optional resume data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            markdown_content = self.to_markdown(resume_data)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Resume template saved to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save resume template: {e}")
            return False
    
    def validate_template(self) -> Dict[str, List[str]]:
        """
        Validate the loaded resume template.
        
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        issues = {"errors": [], "warnings": []}
        
        if not self.resume_data:
            issues["errors"].append("No resume data loaded")
            return issues
        
        # Check required fields
        if not self.resume_data.contact_info.name:
            issues["errors"].append("Name is required")
        
        if not self.resume_data.contact_info.email:
            issues["warnings"].append("Email address not found")
        
        if not self.resume_data.professional_summary:
            issues["warnings"].append("Professional summary is empty")
        
        if not self.resume_data.work_experience:
            issues["warnings"].append("No work experience found")
        
        if not self.resume_data.technical_skills:
            issues["warnings"].append("No technical skills found")
        
        # Validate work experience entries
        for i, exp in enumerate(self.resume_data.work_experience):
            if not exp.title:
                issues["warnings"].append(f"Work experience {i+1} missing title")
            if not exp.company:
                issues["warnings"].append(f"Work experience {i+1} missing company")
            if not exp.description:
                issues["warnings"].append(f"Work experience {i+1} missing description")
        
        return issues
    
    def debug_parsing(self) -> Dict[str, Any]:
        """
        Debug method to show what was parsed from the template.
        
        Returns:
            Dictionary with parsing debug information
        """
        if not self.resume_data:
            return {"error": "No resume data loaded"}
        
        debug_info = {
            "contact_info": asdict(self.resume_data.contact_info),
            "professional_summary_length": len(self.resume_data.professional_summary),
            "work_experience_count": len(self.resume_data.work_experience),
            "technical_skills_count": len(self.resume_data.technical_skills),
            "education_count": len(self.resume_data.education),
            "technical_skills_details": [
                {"category": skill.category, "skills_count": len(skill.skills), "skills": skill.skills}
                for skill in self.resume_data.technical_skills
            ],
            "education_details": [
                {"degree": edu.degree, "institution": edu.institution, "year": edu.year}
                for edu in self.resume_data.education
            ]
        }
        
        return debug_info

def load_resume_template(template_path: Optional[str] = None) -> Optional[ResumeTemplateHandler]:
    """
    Convenience function to load and parse a resume template.
    
    Args:
        template_path: Optional path to template file
        
    Returns:
        ResumeTemplateHandler instance or None if failed
    """
    handler = ResumeTemplateHandler(template_path)
    if handler.load_template():
        return handler
    return None