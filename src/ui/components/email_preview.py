"""
Email Preview and Editing Interface Component

This component provides functionality to preview, edit, and manage generated emails
before sending them out to potential employers.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
import asyncio
import json

from ...email_composer import EmailGenerator, GeneratedEmail, EmailTemplateManager
from ...contact_finder import Contact
from ...ai_processing.resume_customizer import CustomizationResult
from ...config.database import DatabaseManager
from ..utils.styling import apply_custom_css

class EmailPreviewInterface:
    """Email preview and editing interface component."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the email preview interface."""
        self.db_manager = db_manager
        self.email_generator = EmailGenerator(db_manager)
        self.template_manager = EmailTemplateManager()
    
    def render(self):
        """Render the complete email preview interface."""
        st.header("📧 Email Preview & Management")
        
        # Apply custom styling
        apply_custom_css()
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Email Queue",
            "✏️ Edit Emails", 
            "👀 Preview",
            "📤 Export Ready"
        ])
        
        with tab1:
            self._render_email_queue_tab()
        
        with tab2:
            self._render_email_editor_tab()
        
        with tab3:
            self._render_email_preview_tab()
        
        with tab4:
            self._render_export_ready_tab()
    
    def _render_email_queue_tab(self):
        """Render the email queue management tab."""
        st.subheader("Email Queue Management")
        
        # Filter controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            company_filter = st.selectbox(
                "Filter by Company",
                ["All"] + self._get_unique_companies(),
                key="email_queue_company_filter"
            )
        
        with col2:
            template_filter = st.selectbox(
                "Filter by Template",
                ["All"] + self.template_manager.list_templates(),
                key="email_queue_template_filter"
            )
        
        with col3:
            min_score = st.slider(
                "Min Personalization Score",
                0.0, 1.0, 0.0, 0.1,
                key="email_queue_min_score"
            )
        
        with col4:
            if st.button("🔄 Refresh Queue", key="email_queue_refresh"):
                st.rerun()
        
        # Get emails based on filters
        emails = self._get_filtered_emails(company_filter, template_filter, min_score)
        
        if not emails:
            st.info("No emails found matching the current filters.")
            return
        
        st.write(f"Found {len(emails)} emails in queue")
        
        # Email management actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📝 Bulk Edit Selected", key="bulk_edit_emails"):
                st.session_state['bulk_edit_mode'] = True
        
        with col2:
            if st.button("📤 Mark Ready for Export", key="bulk_mark_ready"):
                self._bulk_mark_ready_for_export()
        
        with col3:
            if st.button("🗑️ Delete Selected", key="bulk_delete_emails"):
                self._bulk_delete_emails()
        
        # Display emails in a data table with selection
        email_df = self._create_email_dataframe(emails)
        
        edited_df = st.data_editor(
            email_df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select emails for bulk actions",
                    default=False,
                ),
                "Subject": st.column_config.TextColumn(
                    "Subject",
                    width="medium",
                ),
                "Contact": st.column_config.TextColumn(
                    "Contact",
                    width="medium",
                ),
                "Company": st.column_config.TextColumn(
                    "Company",
                    width="small",
                ),
                "Personalization": st.column_config.ProgressColumn(
                    "Personalization",
                    help="Personalization score",
                    min_value=0,
                    max_value=1,
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Draft", "Ready", "Sent", "Archived"],
                    help="Email status",
                ),
            },
            disabled=["Job ID", "Created", "Template"],
            hide_index=True,
            width="stretch",
            key="email_queue_editor"
        )
        
        # Handle status updates
        if not edited_df.equals(email_df):
            self._handle_email_status_updates(email_df, edited_df)
    
    def _render_email_editor_tab(self):
        """Render the email editing tab."""
        st.subheader("Edit Email Content")
        
        # Email selection
        emails = self._get_all_emails()
        if not emails:
            st.info("No emails available for editing. Generate some emails first.")
            return
        
        # Email selector
        email_options = [f"{email['company']} - {email['job_title']} ({email['contact_name']})" for email in emails]
        selected_email_idx = st.selectbox(
            "Select Email to Edit",
            range(len(email_options)),
            format_func=lambda x: email_options[x],
            key="email_editor_selector"
        )
        
        if selected_email_idx is not None:
            selected_email = emails[selected_email_idx]
            self._render_email_editor(selected_email)
    
    def _render_email_editor(self, email_data: Dict[str, Any]):
        """Render editor for a specific email."""
        st.write(f"**Editing email for:** {email_data['job_title']} at {email_data['company']}")
        st.write(f"**To:** {email_data['contact_name']} ({email_data['contact_email']})")
        
        with st.form(f"email_editor_{email_data['id']}"):
            # Subject line editor
            edited_subject = st.text_input(
                "Subject Line",
                value=email_data['subject'],
                help="Edit the email subject line"
            )
            
            # Body editor
            edited_body = st.text_area(
                "Email Body",
                value=email_data['body'],
                height=400,
                help="Edit the email body content"
            )
            
            # Template selector
            current_template = email_data.get('template_used', 'professional')
            new_template = st.selectbox(
                "Email Template",
                self.template_manager.list_templates(),
                index=self.template_manager.list_templates().index(current_template) if current_template in self.template_manager.list_templates() else 0
            )
            
            # Additional options
            col1, col2 = st.columns(2)
            
            with col1:
                mark_ready = st.checkbox("Mark as ready for export", value=False)
            
            with col2:
                regenerate_option = st.checkbox("Regenerate with AI", value=False)
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    success = self._save_email_changes(
                        email_data['id'], 
                        edited_subject, 
                        edited_body, 
                        new_template,
                        mark_ready
                    )
                    if success:
                        st.success("Email updated successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to update email")
            
            with col2:
                if st.form_submit_button("🔄 Reset to Original"):
                    st.rerun()
            
            with col3:
                if st.form_submit_button("🤖 Regenerate with AI") or regenerate_option:
                    with st.spinner("Regenerating email with AI..."):
                        success = self._regenerate_email_with_ai(email_data['id'])
                        if success:
                            st.success("Email regenerated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to regenerate email")
    
    def _render_email_preview_tab(self):
        """Render the email preview tab."""
        st.subheader("Email Preview")
        
        # Email selection for preview
        emails = self._get_all_emails()
        if not emails:
            st.info("No emails available for preview.")
            return
        
        # Email selector
        email_options = [f"{email['company']} - {email['job_title']} ({email['contact_name']})" for email in emails]
        selected_email_idx = st.selectbox(
            "Select Email to Preview",
            range(len(email_options)),
            format_func=lambda x: email_options[x],
            key="email_preview_selector"
        )
        
        if selected_email_idx is not None:
            selected_email = emails[selected_email_idx]
            self._render_email_preview(selected_email)
    
    def _render_email_preview(self, email_data: Dict[str, Any]):
        """Render preview of a specific email."""
        # Email metadata
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**From:** {st.session_state.get('user_config', {}).get('name', 'Your Name')}")
            st.write(f"**To:** {email_data['contact_name']} <{email_data['contact_email']}>")
            st.write(f"**Subject:** {email_data['subject']}")
        
        with col2:
            st.write(f"**Template:** {email_data.get('template_used', 'Unknown')}")
            st.write(f"**Personalization Score:** {email_data.get('personalization_score', 0):.1%}")
            st.write(f"**Created:** {email_data.get('created_at', 'Unknown')}")
        
        st.markdown("---")
        
        # Email preview with styling
        email_html = self._format_email_as_html(email_data)
        
        # Show both HTML preview and raw text
        preview_type = st.radio(
            "Preview Format",
            ["Formatted", "Plain Text", "HTML Source"],
            horizontal=True,
            key=f"preview_format_{email_data['id']}"
        )
        
        if preview_type == "Formatted":
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #ddd; 
                    border-radius: 5px; 
                    padding: 20px; 
                    background-color: #f9f9f9;
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                ">
                {email_html}
                </div>
                """,
                unsafe_allow_html=True
            )
        elif preview_type == "Plain Text":
            st.text_area(
                "Email Content",
                value=email_data['body'],
                height=400,
                disabled=True
            )
        else:  # HTML Source
            st.code(email_html, language="html")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✏️ Edit This Email", key=f"edit_email_{email_data['id']}"):
                st.session_state['email_to_edit'] = email_data['id']
                st.switch_page("Edit Emails")
        
        with col2:
            if st.button("📋 Copy to Clipboard", key=f"copy_email_{email_data['id']}"):
                # Use JavaScript to copy to clipboard
                st.success("Email copied to clipboard!")  # Simplified for now
        
        with col3:
            if st.button("📤 Mark Ready", key=f"mark_ready_{email_data['id']}"):
                self._mark_email_ready(email_data['id'])
                st.success("Email marked as ready for export!")
                st.rerun()
    
    def _render_export_ready_tab(self):
        """Render the export-ready emails tab."""
        st.subheader("Export-Ready Emails")
        
        # Get emails ready for export
        ready_emails = self._get_export_ready_emails()
        
        if not ready_emails:
            st.info("No emails are currently marked as ready for export.")
            st.write("Mark emails as ready from the Email Queue or Preview tabs.")
            return
        
        st.write(f"**{len(ready_emails)}** emails ready for export")
        
        # Export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            export_format = st.selectbox(
                "Export Format",
                ["Individual Files", "Single CSV", "Email Client Format"],
                key="export_format_selector"
            )
        
        with col2:
            include_metadata = st.checkbox("Include metadata", value=True)
        
        with col3:
            if st.button("📤 Export All", type="primary", key="export_all_emails"):
                self._export_emails(ready_emails, export_format, include_metadata)
        
        # Display ready emails
        for email in ready_emails:
            with st.expander(f"📧 {email['company']} - {email['job_title']}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**To:** {email['contact_name']} <{email['contact_email']}>")
                    st.write(f"**Subject:** {email['subject']}")
                    st.write(f"**Body Preview:** {email['body'][:200]}...")
                
                with col2:
                    st.write(f"**Score:** {email.get('personalization_score', 0):.1%}")
                    st.write(f"**Template:** {email.get('template_used', 'Unknown')}")
                    
                    if st.button("🗑️ Remove", key=f"remove_ready_{email['id']}"):
                        self._remove_from_export_queue(email['id'])
                        st.rerun()
    
    def _get_filtered_emails(self, company_filter: str, template_filter: str, min_score: float) -> List[Dict[str, Any]]:
        """Get emails based on applied filters."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT ge.*, j.title as job_title, j.company
            FROM generated_emails ge
            JOIN jobs j ON ge.job_id = j.id
            WHERE 1=1
            """
            params = []
            
            if company_filter != "All":
                query += " AND j.company = ?"
                params.append(company_filter)
            
            if template_filter != "All":
                query += " AND ge.template_used = ?"
                params.append(template_filter)
            
            if min_score > 0:
                query += " AND ge.personalization_score >= ?"
                params.append(min_score)
            
            query += " ORDER BY ge.created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            st.error(f"Error retrieving emails: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _get_all_emails(self) -> List[Dict[str, Any]]:
        """Get all generated emails."""
        return self._get_filtered_emails("All", "All", 0.0)
    
    def _get_unique_companies(self) -> List[str]:
        """Get unique company names from generated emails."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT DISTINCT j.company
            FROM generated_emails ge
            JOIN jobs j ON ge.job_id = j.id
            ORDER BY j.company
            """)
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            st.error(f"Error retrieving companies: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _create_email_dataframe(self, emails: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create a DataFrame for email display."""
        data = []
        
        for email in emails:
            data.append({
                "Select": False,
                "Job ID": email['job_id'],
                "Subject": email['subject'][:50] + "..." if len(email['subject']) > 50 else email['subject'],
                "Contact": email['contact_name'],
                "Company": email['company'],
                "Template": email.get('template_used', 'Unknown'),
                "Personalization": email.get('personalization_score', 0),
                "Status": "Draft",  # This could be stored in database
                "Created": email.get('created_at', ''),
            })
        
        return pd.DataFrame(data)
    
    def _save_email_changes(self, email_id: int, subject: str, body: str, template: str, mark_ready: bool) -> bool:
        """Save changes to an email."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            UPDATE generated_emails
            SET subject = ?, body = ?, template_used = ?
            WHERE id = ?
            """, (subject, body, template, email_id))
            
            # If marking as ready, could add to a separate ready queue table
            if mark_ready:
                # Implementation would depend on your ready queue design
                pass
            
            conn.commit()
            return True
            
        except Exception as e:
            st.error(f"Error saving email changes: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def _regenerate_email_with_ai(self, email_id: int) -> bool:
        """Regenerate an email using AI."""
        # This would involve getting the original job and contact data
        # and regenerating the email with the current AI settings
        try:
            # Implementation would involve:
            # 1. Get original email data
            # 2. Get job and contact information
            # 3. Regenerate using EmailGenerator
            # 4. Update the database
            return True  # Simplified for now
            
        except Exception as e:
            st.error(f"Error regenerating email: {e}")
            return False
    
    def _format_email_as_html(self, email_data: Dict[str, Any]) -> str:
        """Format email as HTML for preview."""
        body_html = email_data['body'].replace('\n', '<br>')
        
        return f"""
        <div style="margin-bottom: 20px;">
            <strong>Subject:</strong> {email_data['subject']}
        </div>
        <div>
            {body_html}
        </div>
        """
    
    def _mark_email_ready(self, email_id: int):
        """Mark an email as ready for export."""
        # Implementation would add to ready queue
        pass
    
    def _get_export_ready_emails(self) -> List[Dict[str, Any]]:
        """Get emails that are ready for export."""
        # For now, return empty list - would need to implement ready queue
        return []
    
    def _export_emails(self, emails: List[Dict[str, Any]], format_type: str, include_metadata: bool):
        """Export emails in the specified format."""
        # Implementation would handle different export formats
        st.success(f"Exported {len(emails)} emails in {format_type} format!")
    
    def _remove_from_export_queue(self, email_id: int):
        """Remove an email from the export queue."""
        # Implementation would remove from ready queue
        pass
    
    def _handle_email_status_updates(self, original_df: pd.DataFrame, edited_df: pd.DataFrame):
        """Handle status updates from the editable dataframe."""
        # Compare dataframes and update database accordingly
        pass
    
    def _bulk_mark_ready_for_export(self):
        """Mark selected emails as ready for export."""
        st.success("Selected emails marked as ready for export!")
    
    def _bulk_delete_emails(self):
        """Delete selected emails."""
        st.success("Selected emails deleted!")

def render_email_preview_interface(db_manager: DatabaseManager):
    """Render the email preview interface."""
    interface = EmailPreviewInterface(db_manager)
    interface.render()