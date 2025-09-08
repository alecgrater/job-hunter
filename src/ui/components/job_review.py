"""
Job Review Interface Component

This component provides a user interface for reviewing and approving AI-filtered job results.
Users can view job details, filtering analysis, and make final decisions on job applications.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json

from ...config.database import DatabaseManager
from ...ai_processing import AIJobFilter, FilterDecision, FilterCriteria, create_default_criteria
from ...scrapers import LinkedInRSScraper
from ..utils.styling import apply_custom_css


class JobReviewInterface:
    """Job review interface for filtering results approval."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the job review interface."""
        self.db_manager = db_manager
        self.job_filter = AIJobFilter(db_manager)
        self.scraper = LinkedInRSScraper(db_manager)
    
    def render(self):
        """Render the complete job review interface."""
        st.header("🔍 Job Review & Filtering")
        
        # Apply custom styling
        apply_custom_css()
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Review Jobs", 
            "⚙️ Filter Settings", 
            "📊 Filter Results", 
            "🔄 Scrape New Jobs"
        ])
        
        with tab1:
            self._render_job_review_tab()
        
        with tab2:
            self._render_filter_settings_tab()
        
        with tab3:
            self._render_filter_results_tab()
        
        with tab4:
            self._render_scraping_tab()
    
    def _render_job_review_tab(self):
        """Render the main job review tab."""
        st.subheader("Review Filtered Jobs")
        
        # Filter controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            decision_filter = st.selectbox(
                "Filter by Decision",
                ["All", "Accept", "Reject", "Maybe"],
                key="job_review_decision_filter"
            )
        
        with col2:
            min_confidence = st.slider(
                "Min Confidence",
                0.0, 1.0, 0.0, 0.1,
                key="job_review_min_confidence"
            )
        
        with col3:
            days_back = st.selectbox(
                "Jobs from last",
                [7, 14, 30, 60, 90],
                index=1,
                key="job_review_days_back"
            )
        
        with col4:
            if st.button("🔄 Refresh", key="job_review_refresh"):
                st.rerun()
        
        # Get filtered jobs
        jobs_data = self._get_jobs_with_filter_results(
            decision_filter, min_confidence, days_back
        )
        
        if not jobs_data:
            st.info("No jobs found matching the current filters.")
            return
        
        st.write(f"Found {len(jobs_data)} jobs matching your criteria")
        
        # Display jobs
        for i, job in enumerate(jobs_data):
            self._render_job_card(job, i)
    
    def _render_job_card(self, job_data: Dict[str, Any], index: int):
        """Render a single job card with review options."""
        with st.expander(
            f"{'✅' if job_data.get('decision') == 'accept' else '❌' if job_data.get('decision') == 'reject' else '❓'} "
            f"{job_data['title']} at {job_data['company']} "
            f"(Confidence: {job_data.get('confidence_score', 0):.1%})",
            expanded=False
        ):
            # Job details
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Company:** {job_data['company']}")
                st.write(f"**Location:** {job_data['location']}")
                st.write(f"**Posted:** {job_data['posted_date']}")
                
                if job_data.get('salary_range'):
                    st.write(f"**Salary:** {job_data['salary_range']}")
                
                if job_data.get('employment_type'):
                    st.write(f"**Type:** {job_data['employment_type']}")
                
                if job_data.get('experience_level'):
                    st.write(f"**Level:** {job_data['experience_level']}")
                
                # Job description (truncated)
                description = job_data.get('description', '')
                if len(description) > 500:
                    description = description[:500] + "..."
                st.write(f"**Description:** {description}")
                
                # Link to original job
                if job_data.get('url'):
                    st.markdown(f"[🔗 View Original Job Posting]({job_data['url']})")
            
            with col2:
                # AI Analysis Results
                if job_data.get('reasoning'):
                    st.write("**AI Analysis:**")
                    st.info(job_data['reasoning'])
                
                if job_data.get('matched_criteria'):
                    st.write("**Matched Criteria:**")
                    for criterion in job_data['matched_criteria']:
                        st.write(f"• {criterion}")
                
                if job_data.get('concerns'):
                    st.write("**Concerns:**")
                    for concern in job_data['concerns']:
                        st.write(f"⚠️ {concern}")
                
                # Scores
                if job_data.get('overall_score'):
                    st.metric("Overall Score", f"{job_data['overall_score']:.1%}")
                
                if job_data.get('skills_match_score'):
                    st.metric("Skills Match", f"{job_data['skills_match_score']:.1%}")
            
            # Action buttons
            st.write("**Actions:**")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("✅ Accept", key=f"accept_{job_data['id']}_{index}"):
                    self._update_job_decision(job_data['id'], 'accept')
                    st.success("Job accepted!")
                    st.rerun()
            
            with col2:
                if st.button("❌ Reject", key=f"reject_{job_data['id']}_{index}"):
                    self._update_job_decision(job_data['id'], 'reject')
                    st.success("Job rejected!")
                    st.rerun()
            
            with col3:
                if st.button("❓ Maybe", key=f"maybe_{job_data['id']}_{index}"):
                    self._update_job_decision(job_data['id'], 'maybe')
                    st.success("Job marked as maybe!")
                    st.rerun()
            
            with col4:
                if st.button("🔄 Re-analyze", key=f"reanalyze_{job_data['id']}_{index}"):
                    with st.spinner("Re-analyzing job..."):
                        self._reanalyze_job(job_data['id'])
                    st.success("Job re-analyzed!")
                    st.rerun()
    
    def _render_filter_settings_tab(self):
        """Render the filter settings configuration tab."""
        st.subheader("Configure Filtering Criteria")
        
        # Load existing criteria or create default
        criteria = self._load_filter_criteria()
        
        with st.form("filter_criteria_form"):
            st.write("### Skills")
            
            col1, col2 = st.columns(2)
            with col1:
                required_skills = st.text_area(
                    "Required Skills (one per line)",
                    value="\n".join(criteria.required_skills),
                    height=100
                )
                
                preferred_skills = st.text_area(
                    "Preferred Skills (one per line)",
                    value="\n".join(criteria.preferred_skills),
                    height=100
                )
            
            with col2:
                excluded_skills = st.text_area(
                    "Excluded Skills (one per line)",
                    value="\n".join(criteria.excluded_skills),
                    height=100
                )
            
            st.write("### Location & Remote")
            col1, col2 = st.columns(2)
            with col1:
                preferred_locations = st.text_area(
                    "Preferred Locations (one per line)",
                    value="\n".join(criteria.preferred_locations or []),
                    height=80
                )
            
            with col2:
                excluded_locations = st.text_area(
                    "Excluded Locations (one per line)",
                    value="\n".join(criteria.excluded_locations or []),
                    height=80
                )
            
            remote_preference = st.selectbox(
                "Remote Work Preference",
                ["no_preference", "required", "preferred", "not_preferred"],
                index=0 if not criteria.remote_preference else 
                      ["no_preference", "required", "preferred", "not_preferred"].index(criteria.remote_preference)
            )
            
            st.write("### Salary & Experience")
            col1, col2 = st.columns(2)
            with col1:
                min_salary = st.number_input(
                    "Minimum Salary ($)",
                    min_value=0,
                    value=criteria.min_salary or 0,
                    step=5000
                )
                
                max_salary = st.number_input(
                    "Maximum Salary ($)",
                    min_value=0,
                    value=criteria.max_salary or 0,
                    step=5000
                )
            
            with col2:
                experience_levels = st.multiselect(
                    "Experience Levels",
                    ["Entry-level", "Junior", "Mid-level", "Senior", "Lead", "Principal", "Manager", "Director"],
                    default=criteria.experience_levels or []
                )
                
                employment_types = st.multiselect(
                    "Employment Types",
                    ["Full-time", "Part-time", "Contract", "Temporary", "Internship", "Freelance"],
                    default=criteria.employment_types or []
                )
            
            st.write("### Companies & Keywords")
            col1, col2 = st.columns(2)
            with col1:
                company_preferences = st.text_area(
                    "Preferred Companies (one per line)",
                    value="\n".join(criteria.company_preferences or []),
                    height=80
                )
                
                keywords_include = st.text_area(
                    "Include Keywords (one per line)",
                    value="\n".join(criteria.keywords_include or []),
                    height=80
                )
            
            with col2:
                excluded_companies = st.text_area(
                    "Excluded Companies (one per line)",
                    value="\n".join(criteria.excluded_companies or []),
                    height=80
                )
                
                keywords_exclude = st.text_area(
                    "Exclude Keywords (one per line)",
                    value="\n".join(criteria.keywords_exclude or []),
                    height=80
                )
            
            # Submit button
            if st.form_submit_button("💾 Save Filter Criteria"):
                # Create new criteria object
                new_criteria = FilterCriteria(
                    required_skills=[s.strip() for s in required_skills.split('\n') if s.strip()],
                    preferred_skills=[s.strip() for s in preferred_skills.split('\n') if s.strip()],
                    excluded_skills=[s.strip() for s in excluded_skills.split('\n') if s.strip()],
                    min_salary=min_salary if min_salary > 0 else None,
                    max_salary=max_salary if max_salary > 0 else None,
                    preferred_locations=[s.strip() for s in preferred_locations.split('\n') if s.strip()],
                    excluded_locations=[s.strip() for s in excluded_locations.split('\n') if s.strip()],
                    experience_levels=experience_levels,
                    employment_types=employment_types,
                    company_preferences=[s.strip() for s in company_preferences.split('\n') if s.strip()],
                    excluded_companies=[s.strip() for s in excluded_companies.split('\n') if s.strip()],
                    keywords_include=[s.strip() for s in keywords_include.split('\n') if s.strip()],
                    keywords_exclude=[s.strip() for s in keywords_exclude.split('\n') if s.strip()],
                    remote_preference=remote_preference if remote_preference != "no_preference" else None
                )
                
                # Save criteria
                self._save_filter_criteria(new_criteria)
                st.success("Filter criteria saved successfully!")
        
        # Test filtering button
        if st.button("🧪 Test Filter on Recent Jobs"):
            with st.spinner("Testing filter on recent jobs..."):
                self._test_filter_criteria()
    
    def _render_filter_results_tab(self):
        """Render the filter results analytics tab."""
        st.subheader("Filter Results Analytics")
        
        # Get filter statistics
        stats = self._get_filter_statistics()
        
        if not stats:
            st.info("No filter results available yet. Run job filtering first.")
            return
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Analyzed", stats['total_jobs'])
        
        with col2:
            st.metric("Accepted", stats['accepted_jobs'], 
                     f"{stats['accepted_jobs']/stats['total_jobs']*100:.1f}%")
        
        with col3:
            st.metric("Rejected", stats['rejected_jobs'],
                     f"{stats['rejected_jobs']/stats['total_jobs']*100:.1f}%")
        
        with col4:
            st.metric("Maybe", stats['maybe_jobs'],
                     f"{stats['maybe_jobs']/stats['total_jobs']*100:.1f}%")
        
        # Charts
        if stats['total_jobs'] > 0:
            # Decision distribution
            decision_data = {
                'Decision': ['Accept', 'Reject', 'Maybe'],
                'Count': [stats['accepted_jobs'], stats['rejected_jobs'], stats['maybe_jobs']]
            }
            
            st.write("### Decision Distribution")
            st.bar_chart(pd.DataFrame(decision_data).set_index('Decision'))
            
            # Confidence distribution
            confidence_data = self._get_confidence_distribution()
            if confidence_data:
                st.write("### Confidence Score Distribution")
                st.histogram_chart(pd.DataFrame({'Confidence': confidence_data}))
    
    def _render_scraping_tab(self):
        """Render the job scraping tab."""
        st.subheader("Scrape New Jobs")
        
        with st.form("scraping_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                keywords = st.text_input("Job Keywords", value="software engineer")
                location = st.text_input("Location", value="")
                max_jobs = st.number_input("Max Jobs to Scrape", min_value=1, max_value=100, value=25)
            
            with col2:
                experience_level = st.selectbox(
                    "Experience Level",
                    ["", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"]
                )
                job_type = st.selectbox(
                    "Job Type",
                    ["", "Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship"]
                )
                auto_filter = st.checkbox("Auto-filter scraped jobs", value=True)
            
            if st.form_submit_button("🔍 Scrape Jobs"):
                with st.spinner("Scraping jobs from LinkedIn..."):
                    results = self.scraper.scrape_and_save_jobs(
                        keywords=keywords,
                        location=location,
                        experience_level=experience_level,
                        job_type=job_type,
                        max_jobs=max_jobs
                    )
                
                st.success(f"Scraped {results['scraped_count']} jobs, saved {results['saved_count']} new jobs")
                
                if auto_filter and results['saved_count'] > 0:
                    with st.spinner("Auto-filtering scraped jobs..."):
                        criteria = self._load_filter_criteria()
                        # Get the newly scraped job IDs (this would need to be implemented)
                        # For now, we'll filter recent jobs
                        recent_jobs = self._get_recent_unfiltered_jobs()
                        if recent_jobs:
                            import asyncio
                            filter_results = asyncio.run(
                                self.job_filter.filter_and_save_jobs(recent_jobs, criteria)
                            )
                            st.success(f"Filtered {filter_results['analyzed_jobs']} jobs")
    
    def _get_jobs_with_filter_results(self, decision_filter: str, min_confidence: float, days_back: int) -> List[Dict[str, Any]]:
        """Get jobs with their filter results."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Build query
            query = """
            SELECT j.*, fr.decision, fr.confidence_score, fr.reasoning,
                   fr.matched_criteria, fr.concerns, fr.salary_match,
                   fr.location_match, fr.skills_match_score, fr.overall_score
            FROM jobs j
            LEFT JOIN filter_results fr ON j.id = fr.job_id
            WHERE j.created_at >= datetime('now', '-{} days')
            """.format(days_back)
            
            params = []
            
            if decision_filter != "All":
                query += " AND fr.decision = ?"
                params.append(decision_filter.lower())
            
            if min_confidence > 0:
                query += " AND fr.confidence_score >= ?"
                params.append(min_confidence)
            
            query += " ORDER BY j.created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            jobs_data = []
            
            for row in rows:
                job_dict = dict(zip(columns, row))
                
                # Parse JSON fields
                if job_dict.get('matched_criteria'):
                    job_dict['matched_criteria'] = json.loads(job_dict['matched_criteria'])
                if job_dict.get('concerns'):
                    job_dict['concerns'] = json.loads(job_dict['concerns'])
                
                jobs_data.append(job_dict)
            
            return jobs_data
            
        except Exception as e:
            st.error(f"Error retrieving jobs: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _load_filter_criteria(self) -> FilterCriteria:
        """Load filter criteria from database or return default."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS filter_criteria (
                id INTEGER PRIMARY KEY,
                criteria_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Get latest criteria
            cursor.execute("SELECT criteria_json FROM filter_criteria ORDER BY updated_at DESC LIMIT 1")
            row = cursor.fetchone()
            
            if row:
                criteria_dict = json.loads(row[0])
                return FilterCriteria(**criteria_dict)
            
        except Exception as e:
            st.error(f"Error loading filter criteria: {e}")
        finally:
            if conn:
                conn.close()
        
        return create_default_criteria()
    
    def _save_filter_criteria(self, criteria: FilterCriteria):
        """Save filter criteria to database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Convert to dict and JSON
            criteria_dict = {
                'required_skills': criteria.required_skills,
                'preferred_skills': criteria.preferred_skills,
                'excluded_skills': criteria.excluded_skills,
                'min_salary': criteria.min_salary,
                'max_salary': criteria.max_salary,
                'preferred_locations': criteria.preferred_locations,
                'excluded_locations': criteria.excluded_locations,
                'experience_levels': criteria.experience_levels,
                'employment_types': criteria.employment_types,
                'company_preferences': criteria.company_preferences,
                'excluded_companies': criteria.excluded_companies,
                'keywords_include': criteria.keywords_include,
                'keywords_exclude': criteria.keywords_exclude,
                'remote_preference': criteria.remote_preference
            }
            
            criteria_json = json.dumps(criteria_dict)
            
            # Insert new criteria
            cursor.execute("""
            INSERT INTO filter_criteria (criteria_json, updated_at)
            VALUES (?, datetime('now'))
            """, (criteria_json,))
            
            conn.commit()
            
        except Exception as e:
            st.error(f"Error saving filter criteria: {e}")
        finally:
            if conn:
                conn.close()
    
    def _update_job_decision(self, job_id: int, decision: str):
        """Update job decision in database."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            UPDATE filter_results 
            SET decision = ?, processed_at = datetime('now')
            WHERE job_id = ?
            """, (decision, job_id))
            
            conn.commit()
            
        except Exception as e:
            st.error(f"Error updating job decision: {e}")
        finally:
            if conn:
                conn.close()
    
    def _reanalyze_job(self, job_id: int):
        """Re-analyze a job with current filter criteria."""
        try:
            criteria = self._load_filter_criteria()
            import asyncio
            asyncio.run(self.job_filter.filter_and_save_jobs([job_id], criteria))
        except Exception as e:
            st.error(f"Error re-analyzing job: {e}")
    
    def _get_filter_statistics(self) -> Optional[Dict[str, int]]:
        """Get filter result statistics."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT 
                COUNT(*) as total_jobs,
                SUM(CASE WHEN decision = 'accept' THEN 1 ELSE 0 END) as accepted_jobs,
                SUM(CASE WHEN decision = 'reject' THEN 1 ELSE 0 END) as rejected_jobs,
                SUM(CASE WHEN decision = 'maybe' THEN 1 ELSE 0 END) as maybe_jobs
            FROM filter_results
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'total_jobs': row[0],
                    'accepted_jobs': row[1],
                    'rejected_jobs': row[2],
                    'maybe_jobs': row[3]
                }
            
        except Exception as e:
            st.error(f"Error getting filter statistics: {e}")
        finally:
            if conn:
                conn.close()
        
        return None
    
    def _get_confidence_distribution(self) -> List[float]:
        """Get confidence score distribution."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT confidence_score FROM filter_results")
            rows = cursor.fetchall()
            
            return [row[0] for row in rows]
            
        except Exception as e:
            st.error(f"Error getting confidence distribution: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _get_recent_unfiltered_jobs(self) -> List[int]:
        """Get IDs of recent jobs that haven't been filtered yet."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT j.id FROM jobs j
            LEFT JOIN filter_results fr ON j.id = fr.job_id
            WHERE fr.job_id IS NULL
            AND j.created_at >= datetime('now', '-7 days')
            ORDER BY j.created_at DESC
            LIMIT 50
            """)
            
            rows = cursor.fetchall()
            return [row[0] for row in rows]
            
        except Exception as e:
            st.error(f"Error getting unfiltered jobs: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _test_filter_criteria(self):
        """Test current filter criteria on recent jobs."""
        try:
            criteria = self._load_filter_criteria()
            recent_jobs = self._get_recent_unfiltered_jobs()
            
            if not recent_jobs:
                st.warning("No recent unfiltered jobs found to test on.")
                return
            
            # Take first 5 jobs for testing
            test_jobs = recent_jobs[:5]
            
            import asyncio
            results = asyncio.run(
                self.job_filter.filter_jobs_batch(test_jobs, criteria)
            )
            
            if results:
                st.success(f"Test completed on {len(results)} jobs")
                
                # Show summary
                accepted = len([r for r in results if r.decision == FilterDecision.ACCEPT])
                rejected = len([r for r in results if r.decision == FilterDecision.REJECT])
                maybe = len([r for r in results if r.decision == FilterDecision.MAYBE])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Accepted", accepted)
                with col2:
                    st.metric("Rejected", rejected)
                with col3:
                    st.metric("Maybe", maybe)
            else:
                st.warning("No results from filter test.")
                
        except Exception as e:
            st.error(f"Error testing filter criteria: {e}")