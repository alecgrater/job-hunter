"""
Configuration Tab Component for AI Job Application Automation System.

This module provides comprehensive configuration management for all system settings
including LLM providers, user information, scraping parameters, and advanced options.
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import validate_config, config_manager
from src.ui.utils.styling import create_info_card, create_status_badge

class ConfigurationTab:
    """Configuration tab component for managing all system settings."""
    
    def __init__(self):
        """Initialize the configuration tab."""
        self.config = st.session_state.get('config')
        
    def render(self):
        """Render the configuration tab content."""
        st.markdown("### ⚙️ System Configuration")
        
        # Configuration validation status
        self._render_validation_status()
        
        # Configuration sections
        self._render_configuration_sections()
    
    def _render_validation_status(self):
        """Render configuration validation status."""
        st.markdown("#### 🔍 Configuration Status")
        
        try:
            # Force reload configuration to ensure fresh validation
            config_manager.load_config()
            validation_issues = validate_config()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if validation_issues["errors"]:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-error">{len(validation_issues["errors"])}</div>
                        <div class="metric-label">Errors</div>
                    </div>
                    """
                else:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-healthy">0</div>
                        <div class="metric-label">Errors</div>
                    </div>
                    """
                st.markdown(status_html, unsafe_allow_html=True)
            
            with col2:
                if validation_issues["warnings"]:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-warning">{len(validation_issues["warnings"])}</div>
                        <div class="metric-label">Warnings</div>
                    </div>
                    """
                else:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-healthy">0</div>
                        <div class="metric-label">Warnings</div>
                    </div>
                    """
                st.markdown(status_html, unsafe_allow_html=True)
            
            with col3:
                if not validation_issues["errors"] and not validation_issues["warnings"]:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-healthy">✅</div>
                        <div class="metric-label">Status</div>
                    </div>
                    """
                else:
                    status_html = f"""
                    <div class="metric-card">
                        <div class="metric-value status-error">⚠️</div>
                        <div class="metric-label">Status</div>
                    </div>
                    """
                st.markdown(status_html, unsafe_allow_html=True)
            
            # Display issues if any
            if validation_issues["errors"]:
                st.error("**Configuration Errors:**")
                for error in validation_issues["errors"]:
                    st.error(f"• {error}")
            
            if validation_issues["warnings"]:
                st.warning("**Configuration Warnings:**")
                for warning in validation_issues["warnings"]:
                    st.warning(f"• {warning}")
            
            if not validation_issues["errors"] and not validation_issues["warnings"]:
                st.success("✅ All configuration settings are valid!")
                
        except Exception as e:
            st.error(f"Error validating configuration: {str(e)}")
    
    def _render_configuration_sections(self):
        """Render all configuration sections in tabs."""
        if not self.config:
            st.error("Configuration not loaded. Please check system status.")
            return
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🤖 LLM Settings", 
            "👤 User Profile", 
            "🕷️ Scraping", 
            "📧 Contact Finder",
            "🔧 Advanced"
        ])
        
        with tab1:
            self._render_llm_settings()
        
        with tab2:
            self._render_user_profile()
        
        with tab3:
            self._render_scraping_settings()
        
        with tab4:
            self._render_contact_finder_settings()
        
        with tab5:
            self._render_advanced_settings()
    
    def _render_llm_settings(self):
        """Render LLM configuration settings."""
        st.markdown("#### 🤖 Language Model Configuration")
        
        # Provider selector - first item under the heading
        st.markdown("**Configure LLM Providers:**")
        provider_choice = st.radio(
            "LLM Provider",  # Provide a proper label
            options=["OpenRouter", "Local LLM"],
            index=0 if not self.config.llm.use_local_llm else 1,
            horizontal=True,
            help="Choose between cloud-based OpenRouter or local Ollama instance",
            label_visibility="collapsed"  # Hide the label since we have markdown above
        )
        use_local = provider_choice == "Local LLM"
        
        # Add helpful info box for local LLM users
        if use_local:
            st.info("ℹ️ **Local LLM Setup:** If using local LLM, ensure Ollama is running. Use the test button below to verify connectivity.")
        
        # Configuration form
        with st.form("llm_config_form"):
            # Always show all configuration options, but highlight the active one
            col1, col2 = st.columns(2)
            
            # Determine disabled states
            openrouter_disabled = (provider_choice != "OpenRouter")
            local_disabled = (provider_choice != "Local LLM")
            
            with col1:
                st.markdown("**OpenRouter API:**")
                openrouter_key = st.text_input(
                    "OpenRouter API Key",
                    value="***" if self.config.llm.openrouter_api_key else "",
                    type="password",
                    help="Get your API key from openrouter.ai",
                    disabled=openrouter_disabled
                )
                
                default_model = st.selectbox(
                    "Default Model",
                    options=[
                        "anthropic/claude-3.5-sonnet",
                        "openai/gpt-4o",
                        "openai/gpt-4o-mini",
                        "meta-llama/llama-3.1-8b-instruct",
                        "google/gemini-pro-1.5",
                        "anthropic/claude-3-haiku"
                    ],
                    index=0 if not hasattr(self.config.llm, 'default_model') else 0,
                    disabled=openrouter_disabled
                )
            
            with col2:
                st.markdown("**Local LLM (Ollama):**")
                local_model = st.text_input(
                    "Local Model Name",
                    value=self.config.llm.local_llm_model,
                    help="e.g., qwen2.5:32b, llama3.1:8b",
                    disabled=local_disabled
                )
                
                ollama_url = st.text_input(
                    "Ollama Base URL",
                    value=self.config.llm.ollama_base_url,
                    help="Usually http://localhost:11434",
                    disabled=local_disabled
                )
            
            # Advanced LLM settings
            st.markdown("---")
            st.markdown("**Advanced Settings:**")
            col3, col4, col5 = st.columns(3)
            
            with col3:
                temperature = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=2.0,
                    value=self.config.llm.temperature,
                    step=0.1,
                    help="Controls randomness in responses"
                )
            
            with col4:
                max_tokens = st.number_input(
                    "Max Tokens",
                    min_value=100,
                    max_value=8000,
                    value=self.config.llm.max_tokens,
                    step=100,
                    help="Maximum response length"
                )
            
            with col5:
                timeout = st.number_input(
                    "Timeout (seconds)",
                    min_value=10,
                    max_value=300,
                    value=getattr(self.config.llm, 'timeout', 60),
                    step=5,
                    help="Request timeout"
                )
            
            # Save button
            if st.form_submit_button("💾 Save LLM Configuration", width="stretch"):
                self._save_llm_config(
                    openrouter_key, default_model, use_local, local_model,
                    ollama_url, temperature, max_tokens, timeout
                )
        
        # Test buttons for current configuration - after the form
        st.markdown("**Test LLM Providers:**")
        col_test1, col_test2 = st.columns(2)
        
        with col_test1:
            if st.button("🧪 Test OpenRouter API", width="stretch"):
                self._test_openrouter_connection()
        
        with col_test2:
            if st.button("🧪 Test Local LLM", width="stretch"):
                self._test_ollama_connection()
        
        # Current LLM status - at the bottom
        llm_manager = st.session_state.get('llm_manager')
        if llm_manager:
            providers = llm_manager.get_available_providers()
            provider_info = llm_manager.get_provider_info()
            
            if providers:
                st.success(f"✅ Available providers: {', '.join(providers)}")
                
                # Show provider details with test buttons
                for provider, info in provider_info.items():
                    with st.expander(f"{provider.title()} Provider Details"):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.write(f"**Status:** {'🟢 Available' if info['available'] else '🔴 Unavailable'}")
                            st.write(f"**Model:** {info['model']}")
                        with col2:
                            st.write(f"**Primary:** {'Yes' if info['is_primary'] else 'No'}")
                        with col3:
                            if st.button(f"🧪 Test {provider.title()}", key=f"config_test_{provider}"):
                                self._test_llm_provider(provider, llm_manager)
            else:
                st.error("❌ No LLM providers configured!")
    
    def _render_user_profile(self):
        """Render user profile configuration."""
        st.markdown("#### 👤 User Profile Information")
        
        user_config = self.config.user
        
        with st.form("user_profile_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Personal Information:**")
                name = st.text_input("Full Name*", value=user_config.name)
                email = st.text_input("Email Address*", value=user_config.email)
                phone = st.text_input("Phone Number", value=user_config.phone)
                location = st.text_input("Location", value=user_config.location)
            
            with col2:
                st.markdown("**Professional Links:**")
                linkedin_url = st.text_input("LinkedIn URL", value=user_config.linkedin_url)
                github_url = st.text_input("GitHub URL", value=user_config.github_url)
                portfolio_url = st.text_input("Portfolio URL", value=getattr(user_config, 'portfolio_url', ''))
                website_url = st.text_input("Personal Website", value=getattr(user_config, 'website_url', ''))
            
            # Professional summary
            st.markdown("**Professional Summary:**")
            summary = st.text_area(
                "Professional Summary",
                value=getattr(user_config, 'summary', ''),
                help="Brief professional summary for email templates",
                height=100
            )
            
            # Skills and preferences
            col3, col4 = st.columns(2)
            
            with col3:
                st.markdown("**Key Skills:**")
                skills = st.text_area(
                    "Technical Skills",
                    value=getattr(user_config, 'skills', ''),
                    help="Comma-separated list of skills",
                    height=80
                )
            
            with col4:
                st.markdown("**Job Preferences:**")
                job_titles = st.text_area(
                    "Preferred Job Titles",
                    value=getattr(user_config, 'preferred_titles', ''),
                    help="Comma-separated list of job titles",
                    height=80
                )
            
            if st.form_submit_button("💾 Save User Profile", width="stretch"):
                self._save_user_profile(
                    name, email, phone, location, linkedin_url, github_url,
                    portfolio_url, website_url, summary, skills, job_titles
                )
    
    def _render_scraping_settings(self):
        """Render web scraping configuration."""
        st.markdown("#### 🕷️ Web Scraping Configuration")
        
        scraping_config = self.config.scraping
        
        with st.form("scraping_config_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Rate Limiting:**")
                max_jobs = st.number_input(
                    "Max Jobs per Batch",
                    min_value=1,
                    max_value=500,
                    value=scraping_config.max_jobs_per_batch,
                    help="Maximum jobs to process in one session"
                )
                
                delay_seconds = st.number_input(
                    "Delay Between Requests (seconds)",
                    min_value=0.5,
                    max_value=30.0,
                    value=scraping_config.delay_seconds,
                    step=0.5,
                    help="Respectful delay between requests"
                )
                
                rate_limit = st.number_input(
                    "Rate Limit (requests/minute)",
                    min_value=1,
                    max_value=300,
                    value=scraping_config.rate_limit_per_minute,
                    help="Maximum requests per minute"
                )
            
            with col2:
                st.markdown("**Request Settings:**")
                timeout_seconds = st.number_input(
                    "Request Timeout (seconds)",
                    min_value=5,
                    max_value=300,
                    value=scraping_config.timeout_seconds,
                    help="How long to wait for responses"
                )
                
                retry_attempts = st.number_input(
                    "Retry Attempts",
                    min_value=1,
                    max_value=10,
                    value=scraping_config.retry_attempts,
                    help="Number of retry attempts for failed requests"
                )
                
                user_agent = st.text_input(
                    "User Agent",
                    value=scraping_config.user_agent,
                    help="Browser user agent string"
                )
            
            # Advanced scraping options
            st.markdown("**Advanced Options:**")
            col3, col4 = st.columns(2)
            
            with col3:
                use_proxy = st.checkbox(
                    "Use Proxy Rotation",
                    value=getattr(scraping_config, 'use_proxy', False),
                    help="Enable proxy rotation for scraping"
                )
                
                headless_browser = st.checkbox(
                    "Headless Browser Mode",
                    value=getattr(scraping_config, 'headless', True),
                    help="Run browser in headless mode"
                )
            
            with col4:
                respect_robots = st.checkbox(
                    "Respect robots.txt",
                    value=getattr(scraping_config, 'respect_robots', True),
                    help="Follow robots.txt guidelines"
                )
                
                cache_responses = st.checkbox(
                    "Cache Responses",
                    value=getattr(scraping_config, 'cache_responses', True),
                    help="Cache responses to avoid duplicate requests"
                )
            
            if st.form_submit_button("💾 Save Scraping Configuration", width="stretch"):
                self._save_scraping_config(
                    max_jobs, delay_seconds, rate_limit, timeout_seconds,
                    retry_attempts, user_agent, use_proxy, headless_browser,
                    respect_robots, cache_responses
                )
    
    def _render_contact_finder_settings(self):
        """Render contact finder configuration."""
        st.markdown("#### 📧 Contact Finder Configuration")
        
        contact_config = self.config.contact_finder
        
        # Contact method selector outside the form for dynamic updates
        st.markdown("---")
        contact_method = st.radio(
            "Select Contact Discovery Method:",
            options=["API Services", "Free Email Discovery"],
            index=1 if contact_config.use_free_methods else 0,
            horizontal=True,
            help="Choose between paid API services or free discovery methods"
        )
        use_free_methods = contact_method == "Free Email Discovery"
        st.markdown("---")
        
        with st.form("contact_finder_form"):
            # Always show all configuration options, but highlight the active one
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**API Services:**")
                hunter_key = st.text_input(
                    "Hunter.io API Key",
                    value="***" if contact_config.hunter_io_api_key else "",
                    type="password",
                    help="Get your API key from hunter.io",
                    disabled=(contact_method != "API Services")
                )
                
                apollo_key = st.text_input(
                    "Apollo.io API Key",
                    value="***" if contact_config.apollo_io_api_key else "",
                    type="password",
                    help="Get your API key from apollo.io",
                    disabled=(contact_method != "API Services")
                )
            
            with col2:
                st.markdown("**Search Options:**")
                max_contacts = st.number_input(
                    "Max Contacts per Company",
                    min_value=1,
                    max_value=20,
                    value=getattr(contact_config, 'max_contacts_per_company', 5),
                    help="Maximum contacts to find per company"
                )
                
                if contact_method == "Free Email Discovery":
                    st.info("🆓 **Free Discovery Methods:**\n\n• Domain pattern analysis\n• Common email formats\n• Public directory search")
                else:
                    st.info("💳 **API Services:**\n\n• Hunter.io email finder\n• Apollo.io contact database\n• Enhanced accuracy")
            
            # Email validation settings
            st.markdown("---")
            st.markdown("**Email Validation:**")
            col3, col4 = st.columns(2)
            
            with col3:
                validate_emails = st.checkbox(
                    "Validate Email Addresses",
                    value=getattr(contact_config, 'validate_emails', True),
                    help="Verify email addresses before use"
                )
            
            with col4:
                confidence_threshold = st.slider(
                    "Confidence Threshold",
                    min_value=0.1,
                    max_value=1.0,
                    value=getattr(contact_config, 'confidence_threshold', 0.7),
                    step=0.1,
                    help="Minimum confidence score for contacts"
                )
            
            if st.form_submit_button("💾 Save Contact Finder Settings", width="stretch"):
                self._save_contact_finder_config(
                    hunter_key, apollo_key, use_free_methods, max_contacts,
                    validate_emails, confidence_threshold
                )
    
    def _render_advanced_settings(self):
        """Render advanced system settings."""
        st.markdown("#### 🔧 Advanced System Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Logging configuration
            st.markdown("**Logging Configuration:**")
            with st.form("logging_form"):
                log_level = st.selectbox(
                    "Log Level",
                    options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    index=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].index(self.config.log_level)
                )
                
                log_to_file = st.checkbox(
                    "Enable File Logging",
                    value=self.config.log_to_file
                )
                
                max_log_size = st.number_input(
                    "Max Log File Size (MB)",
                    min_value=1,
                    max_value=100,
                    value=getattr(self.config, 'max_log_size_mb', 10),
                    help="Maximum size before log rotation"
                )
                
                if st.form_submit_button("💾 Save Logging Settings"):
                    self._save_logging_config(log_level, log_to_file, max_log_size)
        
        with col2:
            # System directories and paths
            st.markdown("**System Information:**")
            info_content = f"""
            <strong>Data Directory:</strong> {self.config.data_dir}<br>
            <strong>Export Directory:</strong> {self.config.export_dir}<br>
            <strong>Template Directory:</strong> {self.config.template_dir}<br>
            <strong>Log Directory:</strong> {self.config.data_dir}/logs<br><br>
            <strong>Current Log Level:</strong> {self.config.log_level}<br>
            <strong>File Logging:</strong> {'Enabled' if self.config.log_to_file else 'Disabled'}<br>
            <strong>Free Contact Methods:</strong> {'Enabled' if self.config.contact_finder.use_free_methods else 'Disabled'}
            """
            st.markdown(create_info_card("System Directories", info_content), unsafe_allow_html=True)
        
        # Configuration management
        st.markdown("**Configuration Management:**")
        col3, col4, col5 = st.columns(3)
        
        with col3:
            if st.button("📥 Export Configuration", width="stretch"):
                try:
                    config_dict = config_manager.mask_sensitive_config()
                    st.download_button(
                        "💾 Download Config JSON",
                        data=json.dumps(config_dict, indent=2),
                        file_name=f"ai_job_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        width="stretch"
                    )
                except Exception as e:
                    st.error(f"Error exporting configuration: {str(e)}")
        
        with col4:
            if st.button("🔄 Reload Configuration", width="stretch"):
                try:
                    # Refresh session state
                    if 'config' in st.session_state:
                        del st.session_state['config']
                    st.success("Configuration reloaded successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error reloading configuration: {str(e)}")
        
        with col5:
            if st.button("⚠️ Reset to Defaults", width="stretch", type="secondary"):
                st.warning("⚠️ This will reset all configuration to defaults. This action cannot be undone.")
                if st.button("Confirm Reset", type="primary", key="confirm_reset"):
                    st.info("🚧 Reset functionality will be implemented in a future version")
    
    def _save_llm_config(self, openrouter_key, default_model, use_local, local_model, 
                         ollama_url, temperature, max_tokens, timeout):
        """Save LLM configuration."""
        try:
            updates = {
                'llm.default_model': default_model,
                'llm.use_local_llm': use_local,
                'llm.local_llm_model': local_model,
                'llm.ollama_base_url': ollama_url,
                'llm.temperature': temperature,
                'llm.max_tokens': max_tokens,
                'llm.timeout': timeout
            }
            
            if openrouter_key and openrouter_key != "***":
                updates['llm.openrouter_api_key'] = openrouter_key
            
            config_manager.update_config(**updates)
            config_manager.save_to_env_file()
            
            # Reinitialize LLM manager
            if 'llm_manager' in st.session_state:
                del st.session_state['llm_manager']
            
            st.success("✅ LLM configuration saved successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Failed to save LLM configuration: {str(e)}")
    
    def _save_user_profile(self, name, email, phone, location, linkedin_url, 
                          github_url, portfolio_url, website_url, summary, skills, job_titles):
        """Save user profile configuration."""
        try:
            updates = {
                'user.name': name,
                'user.email': email,
                'user.phone': phone,
                'user.location': location,
                'user.linkedin_url': linkedin_url,
                'user.github_url': github_url,
                'user.portfolio_url': portfolio_url,
                'user.website_url': website_url,
                'user.summary': summary,
                'user.skills': skills,
                'user.preferred_titles': job_titles
            }
            
            config_manager.update_config(**updates)
            
            # Save to preferences file
            preferences = {k.replace('user.', 'user_'): v for k, v in updates.items()}
            config_manager.save_user_preferences(preferences)
            
            config_manager.save_to_env_file()
            
            st.success("✅ User profile saved successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Failed to save user profile: {str(e)}")
    
    def _save_scraping_config(self, max_jobs, delay_seconds, rate_limit, timeout_seconds,
                             retry_attempts, user_agent, use_proxy, headless_browser,
                             respect_robots, cache_responses):
        """Save scraping configuration."""
        try:
            updates = {
                'scraping.max_jobs_per_batch': max_jobs,
                'scraping.delay_seconds': delay_seconds,
                'scraping.rate_limit_per_minute': rate_limit,
                'scraping.timeout_seconds': timeout_seconds,
                'scraping.retry_attempts': retry_attempts,
                'scraping.user_agent': user_agent,
                'scraping.use_proxy': use_proxy,
                'scraping.headless': headless_browser,
                'scraping.respect_robots': respect_robots,
                'scraping.cache_responses': cache_responses
            }
            
            config_manager.update_config(**updates)
            config_manager.save_to_env_file()
            
            st.success("✅ Scraping configuration saved successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Failed to save scraping configuration: {str(e)}")
    
    def _save_contact_finder_config(self, hunter_key, apollo_key, use_free_methods,
                                   max_contacts, validate_emails, confidence_threshold):
        """Save contact finder configuration."""
        try:
            updates = {
                'contact_finder.use_free_methods': use_free_methods,
                'contact_finder.max_contacts_per_company': max_contacts,
                'contact_finder.validate_emails': validate_emails,
                'contact_finder.confidence_threshold': confidence_threshold
            }
            
            if hunter_key and hunter_key != "***":
                updates['contact_finder.hunter_io_api_key'] = hunter_key
            
            if apollo_key and apollo_key != "***":
                updates['contact_finder.apollo_io_api_key'] = apollo_key
            
            config_manager.update_config(**updates)
            config_manager.save_to_env_file()
            
            st.success("✅ Contact finder configuration saved successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Failed to save contact finder configuration: {str(e)}")
    
    def _save_logging_config(self, log_level, log_to_file, max_log_size):
        """Save logging configuration."""
        try:
            updates = {
                'log_level': log_level,
                'log_to_file': log_to_file,
                'max_log_size_mb': max_log_size
            }
            
            config_manager.update_config(**updates)
            config_manager.save_to_env_file()
            
            st.success("✅ Logging configuration saved successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Failed to save logging configuration: {str(e)}")
    
    def _test_llm_provider(self, provider_name: str, llm_manager):
        """Test a specific LLM provider."""
        try:
            with st.spinner(f"Testing {provider_name} provider..."):
                import asyncio
                
                # Create a simple test message
                test_messages = [
                    {"role": "user", "content": "This is a connection test. Please respond with exactly: 'Connection test successful - LLM is working properly'"}
                ]
                
                # Test the provider
                response = asyncio.run(llm_manager.generate(
                    messages=test_messages,
                    provider=provider_name,
                    max_tokens=50,
                    temperature=0.1
                ))
                
                if response.error:
                    st.error(f"❌ {provider_name.title()} test failed: {response.error}")
                else:
                    st.success(f"✅ {provider_name.title()} test successful!")
                    st.info(f"**Response:** {response.content}")
                    
        except Exception as e:
            st.error(f"❌ Error testing {provider_name}: {str(e)}")
    
    def _test_openrouter_connection(self):
        """Test OpenRouter API connection."""
        try:
            with st.spinner("Testing OpenRouter API connection..."):
                from src.ai_processing import LLMManager
                import asyncio
                
                # Create a temporary LLM manager with current config
                llm_manager = LLMManager()
                
                if 'openrouter' not in llm_manager.get_available_providers():
                    st.warning("⚠️ OpenRouter not configured. Please add your API key first.")
                    return
                
                # Test with a simple message
                test_messages = [
                    {"role": "user", "content": "This is an OpenRouter API connection test. Please respond with exactly: 'OpenRouter API connection successful - service is working properly'"}
                ]
                
                response = asyncio.run(llm_manager.generate(
                    messages=test_messages,
                    provider="openrouter",
                    max_tokens=50,
                    temperature=0.1
                ))
                
                if response.error:
                    st.error(f"❌ OpenRouter connection failed: {response.error}")
                    if "api key" in response.error.lower():
                        st.info("💡 **Tip:** Make sure your OpenRouter API key is valid and has sufficient credits.")
                    elif "network" in response.error.lower() or "timeout" in response.error.lower():
                        st.info("💡 **Tip:** Check your internet connection and try again.")
                else:
                    st.success("✅ OpenRouter connection successful!")
                    st.info(f"**Model:** {response.model}")
                    st.info(f"**Response:** {response.content}")
                    if response.usage:
                        st.info(f"**Tokens used:** {response.usage.get('total_tokens', 'N/A')}")
                        
        except Exception as e:
            st.error(f"❌ Error testing OpenRouter: {str(e)}")
            st.info("💡 **Troubleshooting:**\n- Verify your API key is correct\n- Check your internet connection\n- Ensure you have OpenRouter credits")
    
    def _test_ollama_connection(self):
        """Test Ollama (Local LLM) connection."""
        try:
            with st.spinner("Testing Ollama connection..."):
                from src.ai_processing import LLMManager
                import asyncio
                
                # Create a temporary LLM manager with current config
                llm_manager = LLMManager()
                
                if 'ollama' not in llm_manager.get_available_providers():
                    st.warning("⚠️ Ollama not available. Please check the configuration below:")
                    
                    # Show detailed troubleshooting
                    st.info("""
                    **Ollama Setup Checklist:**
                    
                    1. **Install Ollama:** Download from [ollama.ai](https://ollama.ai)
                    2. **Start Ollama:** Run `ollama serve` in terminal
                    3. **Pull a model:** Run `ollama pull llama3.1:8b` (or your preferred model)
                    4. **Verify service:** Check if http://localhost:11434 is accessible
                    5. **Update config:** Set the correct model name in the configuration above
                    """)
                    
                    # Test basic connectivity
                    try:
                        import requests
                        response = requests.get(self.config.llm.ollama_base_url, timeout=5)
                        if response.status_code == 200:
                            st.info("✅ Ollama service is running, but no models may be available.")
                        else:
                            st.error(f"❌ Ollama service responded with status {response.status_code}")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ Cannot connect to Ollama service. Is it running?")
                    except Exception as e:
                        st.error(f"❌ Connection test failed: {str(e)}")
                    
                    return
                
                # Test with a simple message
                test_messages = [
                    {"role": "user", "content": "This is a local LLM connection test. Please respond with exactly: 'Local LLM connection successful - model is working properly'"}
                ]
                
                response = asyncio.run(llm_manager.generate(
                    messages=test_messages,
                    provider="ollama",
                    max_tokens=50,
                    temperature=0.1
                ))
                
                if response.error:
                    st.error(f"❌ Ollama connection failed: {response.error}")
                    
                    # Provide specific troubleshooting based on error
                    if "connection" in response.error.lower():
                        st.info("💡 **Tip:** Make sure Ollama is running with `ollama serve`")
                    elif "model" in response.error.lower():
                        st.info(f"💡 **Tip:** Pull the model with `ollama pull {self.config.llm.local_llm_model}`")
                    else:
                        st.info("💡 **Tip:** Check Ollama logs for more details")
                else:
                    st.success("✅ Ollama connection successful!")
                    st.info(f"**Model:** {response.model}")
                    st.info(f"**Response:** {response.content}")
                    
        except Exception as e:
            st.error(f"❌ Error testing Ollama: {str(e)}")
            st.info("""
            💡 **Troubleshooting Steps:**
            1. Install Ollama from https://ollama.ai
            2. Run `ollama serve` in terminal
            3. Pull a model: `ollama pull llama3.1:8b`
            4. Verify the model name matches your configuration
            """)