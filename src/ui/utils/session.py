"""
Session state management for the Streamlit application.

This module handles initialization and management of session state variables
to ensure consistent state across the application.
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import DatabaseManager, get_config
from src.ai_processing.llm_manager import get_llm_manager
from src.document_manager.resume_handler import load_resume_template
from src.utils import setup_logging, get_ui_logger

def init_session_state():
    """Initialize all session state variables."""
    
    # Initialize logging first
    if 'logger_initialized' not in st.session_state:
        setup_logging()
        st.session_state.logger_initialized = True
        st.session_state.logger = get_ui_logger()
    
    # Initialize database manager
    if 'db' not in st.session_state:
        try:
            st.session_state.db = DatabaseManager()
            st.session_state.db_status = "connected"
        except Exception as e:
            st.session_state.db = None
            st.session_state.db_status = f"error: {str(e)}"
    
    # Initialize configuration
    if 'config' not in st.session_state:
        try:
            st.session_state.config = get_config()
            st.session_state.config_status = "loaded"
        except Exception as e:
            st.session_state.config = None
            st.session_state.config_status = f"error: {str(e)}"
    
    # Initialize LLM manager
    if 'llm_manager' not in st.session_state:
        try:
            st.session_state.llm_manager = get_llm_manager()
            st.session_state.llm_status = "initialized"
        except Exception as e:
            st.session_state.llm_manager = None
            st.session_state.llm_status = f"error: {str(e)}"
    
    # Initialize resume handler
    if 'resume_handler' not in st.session_state:
        try:
            st.session_state.resume_handler = load_resume_template()
            st.session_state.resume_status = "loaded"
        except Exception as e:
            st.session_state.resume_handler = None
            st.session_state.resume_status = f"error: {str(e)}"
    
    # Initialize UI state variables
    if 'selected_job_id' not in st.session_state:
        st.session_state.selected_job_id = None
    
    if 'show_job_details' not in st.session_state:
        st.session_state.show_job_details = False
    
    if 'refresh_data' not in st.session_state:
        st.session_state.refresh_data = False
    
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None

def get_system_health():
    """Get overall system health status."""
    health_status = {
        'database': st.session_state.get('db_status', 'unknown'),
        'config': st.session_state.get('config_status', 'unknown'),
        'llm': st.session_state.get('llm_status', 'unknown'),
        'resume': st.session_state.get('resume_status', 'unknown')
    }
    
    # Determine overall health
    errors = [status for status in health_status.values() if status.startswith('error')]
    if errors:
        overall_status = 'error'
    elif all(status in ['connected', 'loaded', 'initialized'] for status in health_status.values()):
        overall_status = 'healthy'
    else:
        overall_status = 'warning'
    
    return {
        'overall': overall_status,
        'components': health_status,
        'error_count': len(errors)
    }

def refresh_session_data():
    """Refresh session data by reinitializing components."""
    # Clear existing session state
    keys_to_clear = ['db', 'config', 'llm_manager', 'resume_handler']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Reinitialize
    init_session_state()
    st.session_state.last_refresh = st.session_state.get('logger').info("Session data refreshed")