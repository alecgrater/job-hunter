"""
Custom CSS styling for the Streamlit application.

This module provides consistent styling and theming across all UI components.
"""

import streamlit as st

def apply_custom_css():
    """Apply custom CSS styling to the Streamlit application."""
    
    st.markdown("""
    <style>
    /* Hide Streamlit default elements */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    .stToolbar {
        display: none !important;
    }
    
    .stStatusWidget {
        display: none !important;
    }
    
    .stDeployButton {
        display: none !important;
    }
    
    button[title="View fullscreen"] {
        display: none !important;
    }
    
    /* Main container styling */
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px;
    }
    
    /* Application header */
    .app-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .app-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .app-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.2rem;
        opacity: 0.9;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        padding: 0.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Metric cards */
    .metric-card {
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: transform 0.2s ease;
        margin-bottom: 1rem;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        margin: 0.5rem 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 0.8;
    }
    
    /* Status indicators */
    .status-healthy {
        color: #28a745;
        font-weight: 600;
    }
    
    .status-warning {
        color: #ffc107;
        font-weight: 600;
    }
    
    .status-error {
        color: #dc3545;
        font-weight: 600;
    }
    
    /* Cards and containers */
    .info-card {
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    .info-card h3 {
        margin-top: 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    /* Form styling */
    .stForm {
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Progress bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        border-radius: 8px;
    }
    
    /* Footer */
    .app-footer {
        margin-top: 3rem;
        text-align: center;
        font-size: 0.9rem;
        opacity: 0.8;
    }
    
    .app-footer hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, rgba(255, 255, 255, 0.3), transparent);
        margin: 2rem 0 1rem 0;
    }
    
    /* Alert styling */
    .stAlert {
        border-radius: 8px;
        border: none;
    }
    
    /* Code blocks */
    .stCodeBlock {
        border-radius: 8px;
    }
    
    /* Data tables */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Custom utility classes */
    .text-center {
        text-align: center;
    }
    
    .text-muted {
        color: #6c757d;
    }
    
    .mb-3 {
        margin-bottom: 1rem;
    }
    
    .mt-3 {
        margin-top: 1rem;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .app-header h1 {
            font-size: 2rem;
        }
        
        .app-header p {
            font-size: 1rem;
        }
        
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def create_metric_card(value, label, status=None):
    """Create a styled metric card."""
    status_class = ""
    if status:
        status_class = f"status-{status}"
    
    return f"""
    <div class="metric-card">
        <div class="metric-value {status_class}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """

def create_info_card(title, content):
    """Create a styled information card."""
    return f"""
    <div class="info-card">
        <h3>{title}</h3>
        {content}
    </div>
    """

def create_status_badge(status, text):
    """Create a status badge with appropriate styling."""
    return f'<span class="status-{status}">● {text}</span>'