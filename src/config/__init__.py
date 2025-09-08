"""
Configuration module for the AI Job Application Preparation Tool.

This module provides database management and application configuration.
"""

from .database import DatabaseManager
from .settings import (
    ConfigManager,
    AppConfig,
    LLMConfig,
    ContactFinderConfig,
    UserConfig,
    ScrapingConfig,
    get_config,
    get_llm_config,
    get_contact_finder_config,
    get_user_config,
    get_scraping_config,
    validate_config,
    config_manager
)

__all__ = [
    'DatabaseManager',
    'ConfigManager',
    'AppConfig',
    'LLMConfig',
    'ContactFinderConfig',
    'UserConfig',
    'ScrapingConfig',
    'get_config',
    'get_llm_config',
    'get_contact_finder_config',
    'get_user_config',
    'get_scraping_config',
    'validate_config',
    'config_manager'
]