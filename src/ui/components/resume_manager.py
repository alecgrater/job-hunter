"""
Resume Manager Tab Component for AI Job Application Automation System.

This module provides comprehensive resume management including editing, preview,
customization, and template management capabilities.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.utils.styling import create_info_card, create_status_badge

class ResumeManagerTab:
    """Resume manager tab component for managing resume templates and customization."""
    
    def __init__(self):
        """Initialize the resume manager tab."""
        self.resume_handler = st.session_state.get('resume_handler')
        self.config = st.session_state.get('config')
        
    def render(self):
        """Render the resume manager tab content."""
        st.markdown("### 📄 Resume Manager")
        
        if not self.resume_handler:
            self._render_no_resume_state()
            return
        
        # Resume status and validation
        self._render_resume_status()
        
        # Main resume management interface
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Edit Template", 
            "👀 Preview", 
            "🎯 Customize", 
            "📊 Analytics"
        ])
        
        with tab1:
            self._render_template_editor()
        
        with tab2:
            self._render_resume_preview()
        
        with tab3:
            self._render_customization_tools()
        
        with tab4:
            self._render_resume_analytics()
    
    def _render_no_resume_state(self):
        """Render interface when no resume is loaded."""
        st.warning("⚠️ No resume template found!")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("""
            **To get started with resume management:**
            
            1. Create a resume template file at `data/templates/resume_template.md`
            2. Use markdown format for your resume content
            3. Include sections like: Contact Info, Summary, Experience, Education, Skills
            4. Reload the application to load your template
            """)
        
        with col2:
            if st.button("📁 Create Sample Template", width="stretch"):
                self._create_sample_template()
            
            if st.button("🔄 Reload Resume", width="stretch"):
                self._reload_resume_handler()
    
    def _render_resume_status(self):
        """Render resume status and validation information."""
        st.markdown("#### 📋 Resume Status")
        
        try:
            resume_data = self.resume_handler.get_resume_data()
            validation_issues = self.resume_handler.validate_template()
            
            col1, col2, col3, col4 = st.columns(4)
            
            # Template status
            with col1:
                if resume_data:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-healthy">✅</div>
                        <div class="metric-label">Template Loaded</div>
                    </div>
                    """
                else:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-error">❌</div>
                        <div class="metric-label">Template Error</div>
                    </div>
                    """
                st.markdown(status_html, unsafe_allow_html=True)
            
            # Validation status
            with col2:
                if not validation_issues["errors"]:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-healthy">✅</div>
                        <div class="metric-label">Valid</div>
                    </div>
                    """
                else:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-error">{len(validation_issues["errors"])}</div>
                        <div class="metric-label">Errors</div>
                    </div>
                    """
                st.markdown(status_html, unsafe_allow_html=True)
            
            # Sections count
            with col3:
                if resume_data:
                    section_count = (
                        len(resume_data.work_experience) + 
                        len(resume_data.education) + 
                        len(resume_data.technical_skills) + 
                        len(resume_data.additional_sections)
                    )
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value">{section_count}</div>
                        <div class="metric-label">Sections</div>
                    </div>
                    """
                else:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value">0</div>
                        <div class="metric-label">Sections</div>
                    </div>
                    """
                st.markdown(status_html, unsafe_allow_html=True)
            
            # Last modified
            with col4:
                try:
                    template_path = Path(self.config.template_dir) / "resume_template.md"
                    if template_path.exists():
                        mod_time = datetime.fromtimestamp(template_path.stat().st_mtime)
                        days_ago = (datetime.now() - mod_time).days
                        status_html = f"""
                        <div class="metric-card">
                            <div class="metric-value">{days_ago}</div>
                            <div class="metric-label">Days Ago</div>
                        </div>
                        """
                    else:
                        status_html = f"""
                        <div class="metric-card">
                            <div class="metric-value">❓</div>
                            <div class="metric-label">Unknown</div>
                        </div>
                        """
                except:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value">❓</div>
                        <div class="metric-label">Unknown</div>
                    </div>
                    """
                st.markdown(status_html, unsafe_allow_html=True)
            
            # Display validation issues
            if validation_issues["errors"]:
                st.error("**Resume Validation Errors:**")
                for error in validation_issues["errors"]:
                    st.error(f"• {error}")
            
            if validation_issues["warnings"]:
                st.warning("**Resume Validation Warnings:**")
                for warning in validation_issues["warnings"]:
                    st.warning(f"• {warning}")
            
            if not validation_issues["errors"] and not validation_issues["warnings"]:
                st.success("✅ Resume template is valid and ready to use!")
                
        except Exception as e:
            st.error(f"Error checking resume status: {str(e)}")
    
    def _render_template_editor(self):
        """Render the resume template editor."""
        st.markdown("#### 📝 Resume Template Editor")
        
        try:
            # Load current template content
            template_path = Path(self.config.template_dir) / "resume_template.md"
            
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()
            else:
                current_content = ""
            
            # Editor interface
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Template editor
                edited_content = st.text_area(
                    "Resume Template (Markdown)",
                    value=current_content,
                    height=500,
                    help="Edit your resume template in Markdown format"
                )
                
                # Save button
                col_save, col_preview = st.columns(2)
                
                with col_save:
                    if st.button("💾 Save Template", width="stretch"):
                        self._save_template(edited_content)
                
                with col_preview:
                    if st.button("👀 Preview Changes", width="stretch"):
                        st.session_state.preview_content = edited_content
            
            with col2:
                # Template help and shortcuts
                st.markdown("**Template Help:**")
                
                with st.expander("📖 Markdown Guide"):
                    st.markdown("""
                    **Basic Formatting:**
                    - `# Header 1`
                    - `## Header 2`
                    - `**Bold text**`
                    - `*Italic text*`
                    - `- Bullet point`
                    - `[Link](url)`
                    
                    **Resume Sections:**
                    - Contact Information
                    - Professional Summary
                    - Work Experience
                    - Education
                    - Technical Skills
                    - Additional Sections
                    """)
                
                with st.expander("🎯 Template Variables"):
                    st.markdown("""
                    **Available Variables:**
                    - `{name}` - Your name
                    - `{email}` - Email address
                    - `{phone}` - Phone number
                    - `{location}` - Location
                    - `{linkedin_url}` - LinkedIn URL
                    - `{github_url}` - GitHub URL
                    
                    These will be replaced with your
                    configured user information.
                    """)
                
                # Quick actions
                st.markdown("**Quick Actions:**")
                
                if st.button("📋 Insert Template", width="stretch"):
                    st.session_state.insert_template = True
                
                if st.button("🔄 Reset to Default", width="stretch"):
                    st.session_state.reset_template = True
                
                if st.button("📥 Import Template", width="stretch"):
                    st.session_state.show_import = True
        
        except Exception as e:
            st.error(f"Error in template editor: {str(e)}")
    
    def _render_resume_preview(self):
        """Render resume preview in different formats."""
        st.markdown("#### 👀 Resume Preview")
        
        if not self.resume_handler:
            st.warning("Resume handler not available for preview.")
            return
        
        # Preview options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            preview_format = st.selectbox(
                "Preview Format",
                ["Markdown", "HTML", "JSON Data"],
                key="preview_format"
            )
        
        with col2:
            if st.button("🔄 Refresh Preview", width="stretch"):
                # Reload resume handler to get latest changes
                self._reload_resume_handler()
        
        with col3:
            if st.button("📄 Generate PDF", width="stretch"):
                st.info("🚧 PDF generation coming soon!")
        
        # Preview content
        try:
            if preview_format == "Markdown":
                markdown_content = self.resume_handler.to_markdown()
                st.markdown("**Markdown Preview:**")
                st.code(markdown_content, language="markdown")
                
                st.markdown("**Rendered Preview:**")
                st.markdown(markdown_content)
            
            elif preview_format == "HTML":
                html_content = self.resume_handler.to_html()
                st.markdown("**HTML Preview:**")
                st.code(html_content, language="html")
                
                st.markdown("**Rendered Preview:**")
                st.components.v1.html(html_content, height=600, scrolling=True)
            
            elif preview_format == "JSON Data":
                resume_dict = self.resume_handler.to_dict()
                st.markdown("**JSON Data Structure:**")
                st.json(resume_dict)
        
        except Exception as e:
            st.error(f"Error generating preview: {str(e)}")
    
    def _render_customization_tools(self):
        """Render resume customization tools."""
        st.markdown("#### 🎯 Resume Customization Tools")
        
        # Job-specific customization
        st.markdown("**Job-Specific Customization:**")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Job description input
            job_description = st.text_area(
                "Job Description",
                placeholder="Paste the job description here to customize your resume...",
                height=200,
                help="Paste a job description to get AI-powered resume customization suggestions"
            )
            
            # Customization options
            col_opt1, col_opt2 = st.columns(2)
            
            with col_opt1:
                focus_skills = st.multiselect(
                    "Skills to Emphasize",
                    ["Python", "JavaScript", "React", "Node.js", "SQL", "AWS", "Docker", "Kubernetes"],
                    help="Select skills to highlight in the customized resume"
                )
            
            with col_opt2:
                customization_level = st.selectbox(
                    "Customization Level",
                    ["Light", "Moderate", "Aggressive"],
                    help="How much to modify the original resume"
                )
        
        with col2:
            st.markdown("**Customization Actions:**")
            
            if st.button("🤖 AI Customize", width="stretch"):
                if job_description:
                    self._ai_customize_resume(job_description, focus_skills, customization_level)
                else:
                    st.warning("Please provide a job description for customization.")
            
            if st.button("💡 Get Suggestions", width="stretch"):
                if job_description:
                    self._get_customization_suggestions(job_description)
                else:
                    st.warning("Please provide a job description for suggestions.")
            
            if st.button("📋 Save Custom Version", width="stretch"):
                st.info("🚧 Custom version saving coming soon!")
        
        # Template management
        st.markdown("---")
        st.markdown("**Template Management:**")
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            if st.button("📁 Load Template", width="stretch"):
                self._show_template_loader()
        
        with col4:
            if st.button("💾 Save as Template", width="stretch"):
                self._show_template_saver()
        
        with col5:
            if st.button("🗂️ Manage Templates", width="stretch"):
                self._show_template_manager()
    
    def _render_resume_analytics(self):
        """Render resume analytics and insights."""
        st.markdown("#### 📊 Resume Analytics & Insights")
        
        if not self.resume_handler:
            st.warning("Resume handler not available for analytics.")
            return
        
        try:
            resume_data = self.resume_handler.get_resume_data()
            
            if not resume_data:
                st.warning("No resume data available for analysis.")
                return
            
            # Resume statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                word_count = len(self.resume_handler.to_markdown().split())
                metric_html = f"""
                <div class="metric-card">
                    <div class="metric-value">{word_count}</div>
                    <div class="metric-label">Total Words</div>
                </div>
                """
                st.markdown(metric_html, unsafe_allow_html=True)
            
            with col2:
                exp_count = len(resume_data.work_experience)
                metric_html = f"""
                <div class="metric-card">
                    <div class="metric-value">{exp_count}</div>
                    <div class="metric-label">Work Experiences</div>
                </div>
                """
                st.markdown(metric_html, unsafe_allow_html=True)
            
            with col3:
                skill_count = len(resume_data.technical_skills)
                metric_html = f"""
                <div class="metric-card">
                    <div class="metric-value">{skill_count}</div>
                    <div class="metric-label">Skill Categories</div>
                </div>
                """
                st.markdown(metric_html, unsafe_allow_html=True)
            
            with col4:
                edu_count = len(resume_data.education)
                metric_html = f"""
                <div class="metric-card">
                    <div class="metric-value">{edu_count}</div>
                    <div class="metric-label">Education Entries</div>
                </div>
                """
                st.markdown(metric_html, unsafe_allow_html=True)
            
            # Detailed analysis
            col_left, col_right = st.columns(2)
            
            with col_left:
                # Skills analysis
                st.markdown("**Skills Analysis:**")
                
                all_skills = []
                for skill_category in resume_data.technical_skills:
                    if hasattr(skill_category, 'skills'):
                        all_skills.extend(skill_category.skills)
                
                if all_skills:
                    skills_df = pd.DataFrame({'Skill': all_skills})
                    st.dataframe(skills_df, width="stretch", hide_index=True)
                else:
                    st.info("No skills data available for analysis.")
            
            with col_right:
                # Experience timeline
                st.markdown("**Experience Timeline:**")
                
                if resume_data.work_experience:
                    exp_data = []
                    for exp in resume_data.work_experience:
                        exp_data.append({
                            'Company': getattr(exp, 'company', 'Unknown'),
                            'Title': getattr(exp, 'title', 'Unknown'),
                            'Duration': getattr(exp, 'duration', 'Unknown')
                        })
                    
                    exp_df = pd.DataFrame(exp_data)
                    st.dataframe(exp_df, width="stretch", hide_index=True)
                else:
                    st.info("No work experience data available.")
            
            # Resume optimization suggestions
            st.markdown("**Optimization Suggestions:**")
            
            suggestions = self._generate_optimization_suggestions(resume_data, word_count)
            
            for suggestion in suggestions:
                st.info(f"💡 {suggestion}")
        
        except Exception as e:
            st.error(f"Error generating analytics: {str(e)}")
    
    def _create_sample_template(self):
        """Create a sample resume template."""
        try:
            sample_template = """# {name}
**{title}**

📧 {email} | 📱 {phone} | 🔗 {linkedin_url} | 📍 {location}

---

## Professional Summary
Experienced software engineer with expertise in full-stack development, cloud technologies, and team leadership. Passionate about building scalable solutions and mentoring junior developers.

---

## Work Experience

### Senior Software Engineer — Current Company
*Jan 2020 – Present | Location*
- Led development of microservices architecture serving 1M+ users
- Implemented CI/CD pipelines reducing deployment time by 75%
- Mentored 5+ junior developers and conducted technical interviews

### Software Engineer — Previous Company
*Jun 2018 – Dec 2019 | Location*
- Developed RESTful APIs and web applications using modern frameworks
- Collaborated with cross-functional teams to deliver features on time
- Optimized database queries improving application performance by 40%

---

## Technical Skills
- **Languages:** Python, JavaScript, TypeScript, Java, SQL
- **Frameworks:** React, Node.js, Django, Flask, Spring Boot
- **Cloud & DevOps:** AWS, Docker, Kubernetes, Jenkins, Terraform
- **Databases:** PostgreSQL, MongoDB, Redis, Elasticsearch

---

## Education
**Bachelor of Computer Science** — University Name, 2018
- Relevant Coursework: Data Structures, Algorithms, Software Engineering
- GPA: 3.8/4.0
"""
            
            template_path = Path(self.config.template_dir) / "resume_template.md"
            template_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(sample_template)
            
            st.success("✅ Sample resume template created successfully!")
            st.info("🔄 Please reload the application to load the new template.")
            
        except Exception as e:
            st.error(f"Error creating sample template: {str(e)}")
    
    def _reload_resume_handler(self):
        """Reload the resume handler."""
        try:
            if 'resume_handler' in st.session_state:
                del st.session_state['resume_handler']
            
            from src.document_manager.resume_handler import load_resume_template
            st.session_state.resume_handler = load_resume_template()
            
            st.success("✅ Resume handler reloaded successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error reloading resume handler: {str(e)}")
    
    def _save_template(self, content):
        """Save the resume template."""
        try:
            template_path = Path(self.config.template_dir) / "resume_template.md"
            template_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Reload resume handler
            self._reload_resume_handler()
            
            st.success("✅ Resume template saved successfully!")
            
        except Exception as e:
            st.error(f"Error saving template: {str(e)}")
    
    def _ai_customize_resume(self, job_description, focus_skills, customization_level):
        """Use AI to customize resume for specific job."""
        st.info("🚧 AI resume customization coming soon!")
        # This would integrate with the LLM manager to customize the resume
    
    def _get_customization_suggestions(self, job_description):
        """Get AI-powered customization suggestions."""
        st.info("🚧 AI customization suggestions coming soon!")
        # This would analyze the job description and provide suggestions
    
    def _generate_optimization_suggestions(self, resume_data, word_count):
        """Generate resume optimization suggestions."""
        suggestions = []
        
        # Word count suggestions
        if word_count < 300:
            suggestions.append("Consider adding more detail to your experience descriptions")
        elif word_count > 800:
            suggestions.append("Consider condensing your resume to be more concise")
        
        # Experience suggestions
        if len(resume_data.work_experience) < 2:
            suggestions.append("Add more work experience entries if available")
        
        # Skills suggestions
        if len(resume_data.technical_skills) < 3:
            suggestions.append("Consider organizing your skills into more categories")
        
        # Contact info suggestions
        if not resume_data.contact_info.linkedin_url:
            suggestions.append("Add your LinkedIn profile URL")
        
        if not suggestions:
            suggestions.append("Your resume looks well-structured!")
        
        return suggestions
    
    def _show_template_loader(self):
        """Show template loading interface."""
        st.info("🚧 Template loading interface coming soon!")
    
    def _show_template_saver(self):
        """Show template saving interface."""
        st.info("🚧 Template saving interface coming soon!")
    
    def _show_template_manager(self):
        """Show template management interface."""
        st.info("🚧 Template management interface coming soon!")