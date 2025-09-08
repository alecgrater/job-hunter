"""
Dashboard Tab Component for AI Job Application Automation System.

This module provides the main dashboard interface with metrics, recent activity,
job management, and quick actions.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.utils.styling import create_metric_card, create_info_card, create_status_badge

class DashboardTab:
    """Dashboard tab component for the main application interface."""
    
    def __init__(self):
        """Initialize the dashboard tab."""
        self.db = st.session_state.get('db')
        self.config = st.session_state.get('config')
        
    def render(self):
        """Render the dashboard tab content."""
        st.markdown("### 📊 Dashboard Overview")
        
        # System health check
        self._render_system_health()
        
        # Key metrics
        self._render_key_metrics()
        
        # Recent activity and charts
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_activity_charts()
        
        with col2:
            self._render_recent_activity()
        
        # Job management section
        self._render_job_management()
        
        # Quick actions
        self._render_quick_actions()
    
    def _render_system_health(self):
        """Render system health status."""
        st.markdown("#### 🏥 System Health")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Database status
        with col1:
            if self.db and st.session_state.get('db_status') == 'connected':
                status_html = create_metric_card("✅", "Database", "healthy")
            else:
                status_html = create_metric_card("❌", "Database", "error")
            st.markdown(status_html, unsafe_allow_html=True)
        
        # LLM status
        with col2:
            llm_manager = st.session_state.get('llm_manager')
            if llm_manager:
                providers = llm_manager.get_available_providers()
                if providers:
                    status_html = create_metric_card(f"{len(providers)}", "LLM Providers", "healthy")
                else:
                    status_html = create_metric_card("0", "LLM Providers", "error")
            else:
                status_html = create_metric_card("❌", "LLM Providers", "error")
            st.markdown(status_html, unsafe_allow_html=True)
        
        # Resume status
        with col3:
            if st.session_state.get('resume_handler'):
                status_html = create_metric_card("✅", "Resume", "healthy")
            else:
                status_html = create_metric_card("❌", "Resume", "error")
            st.markdown(status_html, unsafe_allow_html=True)
        
        # Configuration status
        with col4:
            if self.config:
                status_html = create_metric_card("✅", "Config", "healthy")
            else:
                status_html = create_metric_card("❌", "Config", "error")
            st.markdown(status_html, unsafe_allow_html=True)
    
    def _render_key_metrics(self):
        """Render key application metrics."""
        st.markdown("#### 📈 Key Metrics")
        
        if not self.db:
            st.warning("Database not available. Cannot display metrics.")
            return
        
        try:
            stats = self.db.get_stats()
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            # Total jobs
            with col1:
                job_count = sum(stats.get('jobs_by_status', {}).values())
                metric_html = create_metric_card(str(job_count), "Total Jobs")
                st.markdown(metric_html, unsafe_allow_html=True)
            
            # Applications
            with col2:
                app_count = sum(stats.get('applications_by_status', {}).values())
                metric_html = create_metric_card(str(app_count), "Applications")
                st.markdown(metric_html, unsafe_allow_html=True)
            
            # Success rate
            with col3:
                if app_count > 0:
                    success_count = stats.get('applications_by_status', {}).get('sent', 0)
                    success_rate = round((success_count / app_count) * 100, 1)
                    metric_html = create_metric_card(f"{success_rate}%", "Success Rate")
                else:
                    metric_html = create_metric_card("0%", "Success Rate")
                st.markdown(metric_html, unsafe_allow_html=True)
            
            # Pending jobs
            with col4:
                pending_count = stats.get('jobs_by_status', {}).get('pending', 0)
                metric_html = create_metric_card(str(pending_count), "Pending Jobs")
                st.markdown(metric_html, unsafe_allow_html=True)
            
            # Active applications
            with col5:
                active_count = stats.get('applications_by_status', {}).get('draft', 0)
                metric_html = create_metric_card(str(active_count), "Drafts")
                st.markdown(metric_html, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error loading metrics: {str(e)}")
    
    def _render_activity_charts(self):
        """Render activity charts and visualizations."""
        st.markdown("#### 📊 Activity Overview")
        
        if not self.db:
            st.info("Database not available for charts.")
            return
        
        try:
            stats = self.db.get_stats()
            
            # Jobs by status chart
            jobs_by_status = stats.get('jobs_by_status', {})
            if jobs_by_status:
                fig_jobs = px.pie(
                    values=list(jobs_by_status.values()),
                    names=list(jobs_by_status.keys()),
                    title="Jobs by Status",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_jobs.update_layout(height=300)
                st.plotly_chart(fig_jobs, width="stretch")
            
            # Applications by status chart
            apps_by_status = stats.get('applications_by_status', {})
            if apps_by_status:
                fig_apps = px.bar(
                    x=list(apps_by_status.keys()),
                    y=list(apps_by_status.values()),
                    title="Applications by Status",
                    color=list(apps_by_status.values()),
                    color_continuous_scale="viridis"
                )
                fig_apps.update_layout(height=300)
                st.plotly_chart(fig_apps, width="stretch")
            
            if not jobs_by_status and not apps_by_status:
                st.info("No data available for charts. Start by adding some jobs!")
                
        except Exception as e:
            st.error(f"Error loading charts: {str(e)}")
    
    def _render_recent_activity(self):
        """Render recent activity feed."""
        st.markdown("#### 🕒 Recent Activity")
        
        if not self.db:
            st.info("Database not available.")
            return
        
        try:
            # Get recent jobs (last 10)
            recent_jobs = self.db.get_recent_jobs(limit=10)
            
            if recent_jobs:
                for job in recent_jobs:
                    with st.expander(f"{job.get('title', 'Unknown')} - {job.get('company', 'Unknown')}"):
                        st.write(f"**Status:** {job.get('status', 'Unknown')}")
                        st.write(f"**Location:** {job.get('location', 'Unknown')}")
                        st.write(f"**Added:** {job.get('created_at', 'Unknown')}")
                        
                        if job.get('description'):
                            st.write("**Description:**")
                            st.write(job['description'][:200] + "..." if len(job['description']) > 200 else job['description'])
            else:
                st.info("No recent activity found.")
                
        except Exception as e:
            st.error(f"Error loading recent activity: {str(e)}")
    
    def _render_job_management(self):
        """Render job management interface."""
        st.markdown("#### 💼 Job Management")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Job search and filtering
            search_term = st.text_input("🔍 Search jobs", placeholder="Search by title, company, or keywords...")
            
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            
            with col_filter1:
                status_filter = st.selectbox("Status", ["All", "pending", "approved", "rejected", "applied"])
            
            with col_filter2:
                location_filter = st.text_input("Location", placeholder="Any location")
            
            with col_filter3:
                company_filter = st.text_input("Company", placeholder="Any company")
        
        with col2:
            st.markdown("**Quick Actions**")
            if st.button("🔄 Refresh Data", width="stretch"):
                st.session_state.refresh_data = True
                st.rerun()
            
            if st.button("➕ Add Job", width="stretch"):
                st.session_state.show_add_job = True
        
        # Display jobs table
        if self.db:
            try:
                # Apply filters
                filters = {}
                if status_filter != "All":
                    filters['status'] = status_filter
                if location_filter:
                    filters['location'] = location_filter
                if company_filter:
                    filters['company'] = company_filter
                if search_term:
                    filters['search'] = search_term
                
                jobs = self.db.get_jobs_filtered(filters)
                
                if jobs:
                    # Convert to DataFrame for better display
                    df = pd.DataFrame(jobs)
                    
                    # Select and rename columns for display
                    display_columns = ['title', 'company', 'location', 'status', 'created_at']
                    available_columns = [col for col in display_columns if col in df.columns]
                    
                    if available_columns:
                        df_display = df[available_columns].copy()
                        df_display.columns = [col.replace('_', ' ').title() for col in available_columns]
                        
                        # Display the table
                        st.dataframe(
                            df_display,
                            width="stretch",
                            hide_index=True
                        )
                    else:
                        st.write("Jobs found but no displayable columns available.")
                else:
                    st.info("No jobs found matching the current filters.")
                    
            except Exception as e:
                st.error(f"Error loading jobs: {str(e)}")
        else:
            st.warning("Database not available for job management.")
    
    def _render_quick_actions(self):
        """Render quick action buttons."""
        st.markdown("#### 🚀 Quick Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 Start Job Scraping", width="stretch"):
                st.session_state.show_job_scraping = True
        
        with col2:
            if st.button("🤖 Run AI Analysis", width="stretch"):
                st.info("🚧 AI analysis functionality coming soon!")
        
        with col3:
            if st.button("📝 Generate Applications", width="stretch"):
                st.info("🚧 Application generation coming soon!")
        
        with col4:
            if st.button("📊 Export Report", width="stretch"):
                st.info("🚧 Report export functionality coming soon!")
        
        # Add job modal (if triggered)
        if st.session_state.get('show_add_job'):
            self._render_add_job_modal()
        
        # Job scraping modal (if triggered)
        if st.session_state.get('show_job_scraping'):
            self._show_job_scraping_modal()
    
    def _render_add_job_modal(self):
        """Render add job modal dialog."""
        st.markdown("#### ➕ Add New Job")
        
        with st.form("add_job_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Job Title*", placeholder="e.g., Software Engineer")
                company = st.text_input("Company*", placeholder="e.g., Tech Corp")
                location = st.text_input("Location", placeholder="e.g., San Francisco, CA")
            
            with col2:
                url = st.text_input("Job URL", placeholder="https://...")
                salary_range = st.text_input("Salary Range", placeholder="e.g., $100k - $150k")
                remote_type = st.selectbox("Remote Type", ["On-site", "Remote", "Hybrid"])
            
            description = st.text_area("Job Description", placeholder="Paste the job description here...")
            requirements = st.text_area("Requirements", placeholder="Key requirements and qualifications...")
            
            col_submit, col_cancel = st.columns([1, 1])
            
            with col_submit:
                submitted = st.form_submit_button("💾 Add Job", width="stretch")
            
            with col_cancel:
                cancelled = st.form_submit_button("❌ Cancel", width="stretch")
            
            if submitted:
                if title and company:
                    try:
                        job_data = {
                            'title': title,
                            'company': company,
                            'location': location or 'Not specified',
                            'url': url,
                            'salary_range': salary_range,
                            'remote_type': remote_type,
                            'description': description,
                            'requirements': requirements,
                            'status': 'pending'
                        }
                        
                        if self.db:
                            job_id = self.db.add_job(job_data)
                            st.success(f"✅ Job added successfully! ID: {job_id}")
                            st.session_state.show_add_job = False
                            st.rerun()
                        else:
                            st.error("Database not available. Cannot add job.")
                    except Exception as e:
                        st.error(f"Error adding job: {str(e)}")
                else:
                    st.error("Please fill in required fields (Title and Company)")
            
            if cancelled:
                st.session_state.show_add_job = False
                st.rerun()
    
    def _show_job_scraping_modal(self):
        """Show job scraping modal dialog."""
        st.markdown("#### 🔍 LinkedIn Job Scraping")
        
        with st.form("job_scraping_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                keywords = st.text_input(
                    "Job Keywords*", 
                    placeholder="e.g., Software Engineer, Python Developer",
                    help="Enter job titles or keywords to search for"
                )
                location = st.text_input(
                    "Location", 
                    placeholder="e.g., San Francisco, CA or Remote",
                    help="Job location (leave empty for all locations)"
                )
                max_jobs = st.number_input(
                    "Maximum Jobs to Scrape", 
                    min_value=1, 
                    max_value=100, 
                    value=25,
                    help="Number of jobs to scrape (1-100)"
                )
            
            with col2:
                experience_level = st.selectbox(
                    "Experience Level",
                    ["", "1", "2", "3", "4", "5", "6"],
                    format_func=lambda x: {
                        "": "Any Level",
                        "1": "Internship", 
                        "2": "Entry Level",
                        "3": "Associate",
                        "4": "Mid-Senior Level",
                        "5": "Director",
                        "6": "Executive"
                    }.get(x, x),
                    help="Filter by experience level"
                )
                
                job_type = st.selectbox(
                    "Job Type",
                    ["", "F", "P", "C", "T", "I"],
                    format_func=lambda x: {
                        "": "All Types",
                        "F": "Full-time",
                        "P": "Part-time", 
                        "C": "Contract",
                        "T": "Temporary",
                        "I": "Internship"
                    }.get(x, x),
                    help="Filter by employment type"
                )
                
                auto_save = st.checkbox(
                    "Auto-save to Database", 
                    value=True,
                    help="Automatically save scraped jobs to database"
                )
            
            col_submit, col_cancel = st.columns([1, 1])
            
            with col_submit:
                submitted = st.form_submit_button("🚀 Start Scraping", width="stretch")
            
            with col_cancel:
                cancelled = st.form_submit_button("❌ Cancel", width="stretch")
            
            if submitted:
                if not keywords.strip():
                    st.error("Please enter job keywords to search for.")
                else:
                    self._execute_job_scraping(
                        keywords=keywords.strip(),
                        location=location.strip(),
                        experience_level=experience_level,
                        job_type=job_type,
                        max_jobs=max_jobs,
                        auto_save=auto_save
                    )
            
            if cancelled:
                st.session_state.show_job_scraping = False
                st.rerun()
    
    def _execute_job_scraping(self, keywords, location, experience_level, job_type, max_jobs, auto_save):
        """Execute the job scraping process."""
        try:
            # Import the LinkedIn scraper
            from src.scrapers.linkedin_scraper import LinkedInRSScraper
            
            if not self.db:
                st.error("❌ Database not available. Cannot proceed with scraping.")
                return
            
            # Initialize the scraper
            scraper = LinkedInRSScraper(self.db)
            
            # Start scraping with progress indication
            with st.spinner(f"🔍 Scraping LinkedIn jobs for: {keywords}..."):
                
                # Create progress container
                progress_container = st.container()
                with progress_container:
                    st.info(f"🔍 Searching for jobs: **{keywords}**")
                    if location:
                        st.info(f"📍 Location: **{location}**")
                    st.info(f"📊 Max jobs: **{max_jobs}**")
                
                # Execute scraping
                if auto_save:
                    results = scraper.scrape_and_save_jobs(
                        keywords=keywords,
                        location=location,
                        experience_level=experience_level,
                        job_type=job_type,
                        max_jobs=max_jobs
                    )
                else:
                    jobs = scraper.scrape_jobs(
                        keywords=keywords,
                        location=location,
                        experience_level=experience_level,
                        job_type=job_type,
                        max_jobs=max_jobs
                    )
                    results = {
                        'scraped_count': len(jobs),
                        'saved_count': 0,
                        'duration_seconds': 0,
                        'keywords': keywords,
                        'location': location
                    }
                
                # Display results
                self._display_scraping_results(results)
                
                # Clear the scraping modal state
                if 'show_job_scraping' in st.session_state:
                    del st.session_state['show_job_scraping']
                
                # Refresh the dashboard
                st.rerun()
                
        except ImportError as e:
            st.error(f"❌ Error importing scraper: {str(e)}")
            st.info("Make sure all dependencies are installed.")
        except Exception as e:
            st.error(f"❌ Error during job scraping: {str(e)}")
            st.info("Please check your network connection and try again.")
    
    def _display_scraping_results(self, results):
        """Display job scraping results."""
        st.success("✅ Job scraping completed!")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Jobs Found", results['scraped_count'])
        
        with col2:
            st.metric("Jobs Saved", results['saved_count'])
        
        with col3:
            st.metric("Duration", f"{results['duration_seconds']}s")
        
        if results['scraped_count'] > 0:
            st.info(f"🎉 Successfully scraped {results['scraped_count']} jobs for '{results['keywords']}'")
            if results['saved_count'] > 0:
                st.info(f"💾 {results['saved_count']} new jobs saved to database")
            
            if results['scraped_count'] > results['saved_count']:
                duplicates = results['scraped_count'] - results['saved_count']
                st.info(f"🔄 {duplicates} duplicate jobs were skipped")
        else:
            st.warning("No jobs found matching your criteria. Try different keywords or filters.")