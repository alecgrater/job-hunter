"""
Main Streamlit Application for AI Job Application Automation System.

This is the entry point for the web interface, providing a clean tabbed interface
for managing job applications, configuration, resume management, and system monitoring.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.components.dashboard import DashboardTab
from src.ui.components.configuration import ConfigurationTab
from src.ui.components.resume_manager import ResumeManagerTab
from src.ui.components.system_status import SystemStatusTab
from src.ui.utils.session import init_session_state
from src.ui.utils.styling import apply_custom_css

# Configure Streamlit page
st.set_page_config(
    page_title="AI Job Application Automation",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def main():
    """Main application entry point."""
    # Initialize session state and apply styling
    init_session_state()
    apply_custom_css()
    
    # Application header
    st.markdown("""
    <div class="app-header">
        <h1>🎯 AI Job Application Automation System</h1>
        <p>Streamline your job search with AI-powered automation</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "⚙️ Configuration",
        "📄 Resume Manager",
        "🔧 System Status"
    ])
    
    # Dashboard Tab
    with tab1:
        dashboard = DashboardTab()
        dashboard.render()
    
    # Configuration Tab
    with tab2:
        configuration = ConfigurationTab()
        configuration.render()
    
    # Resume Manager Tab
    with tab3:
        resume_manager = ResumeManagerTab()
        resume_manager.render()
    
    # System Status Tab
    with tab4:
        system_status = SystemStatusTab()
        system_status.render()
    
    # Footer
    st.markdown("""
    <div class="app-footer">
        <hr>
        <p><strong>AI Job Application Automation v2.0</strong> | Built with ❤️ for efficient job searching</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()