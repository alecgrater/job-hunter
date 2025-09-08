"""
Configuration management for the AI Job Application Preparation Tool.

This module handles loading environment variables, user preferences,
and application settings with secure API key management.
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv
import logging
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)

@dataclass
class LLMConfig:
    """Configuration for LLM backends."""
    openrouter_api_key: Optional[str] = None
    use_local_llm: bool = False
    local_llm_model: str = "qwen2.5:32b"
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "anthropic/claude-3.5-sonnet"
    temperature: float = 0.7
    max_tokens: int = 4000

@dataclass
class ContactFinderConfig:
    """Configuration for contact discovery services."""
    hunter_io_api_key: Optional[str] = None
    apollo_io_api_key: Optional[str] = None
    use_free_methods: bool = True
    email_patterns: List[str] = None
    
    def __post_init__(self):
        if self.email_patterns is None:
            self.email_patterns = [
                "{first}.{last}@{domain}",
                "{first}{last}@{domain}",
                "{first}@{domain}",
                "{last}@{domain}",
                "{first_initial}{last}@{domain}",
                "{first}{last_initial}@{domain}"
            ]

@dataclass
class UserConfig:
    """User information configuration."""
    name: str = "Your Name"
    email: str = "your.email@example.com"
    phone: str = "+1-555-123-4567"
    location: str = "San Francisco, CA"
    linkedin_url: str = ""
    github_url: str = ""

@dataclass
class ScrapingConfig:
    """Web scraping configuration."""
    max_jobs_per_batch: int = 50
    delay_seconds: float = 2.0
    rate_limit_per_minute: int = 30
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    timeout_seconds: int = 30
    retry_attempts: int = 3

@dataclass
class AppConfig:
    """Main application configuration."""
    log_level: str = "INFO"
    log_to_file: bool = True
    secret_key: str = "your-secret-key-change-this"
    data_dir: str = "data"
    export_dir: str = "data/exports"
    template_dir: str = "data/templates"
    
    # Component configurations
    llm: LLMConfig = None
    contact_finder: ContactFinderConfig = None
    user: UserConfig = None
    scraping: ScrapingConfig = None
    
    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMConfig()
        if self.contact_finder is None:
            self.contact_finder = ContactFinderConfig()
        if self.user is None:
            self.user = UserConfig()
        if self.scraping is None:
            self.scraping = ScrapingConfig()

class ConfigManager:
    """Manages application configuration from environment variables and settings."""
    
    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration manager."""
        self.env_file = env_file or ".env"
        self.config = AppConfig()
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from environment variables."""
        # Load .env file if it exists
        if Path(self.env_file).exists():
            load_dotenv(self.env_file)
            logger.info(f"Loaded environment from {self.env_file}")
        
        # LLM Configuration
        self.config.llm.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.config.llm.use_local_llm = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
        self.config.llm.local_llm_model = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:32b")
        self.config.llm.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.config.llm.default_model = os.getenv("DEFAULT_LLM_MODEL", "anthropic/claude-3.5-sonnet")
        
        # Contact Finder Configuration
        self.config.contact_finder.hunter_io_api_key = os.getenv("HUNTER_IO_API_KEY")
        self.config.contact_finder.apollo_io_api_key = os.getenv("APOLLO_IO_API_KEY")
        
        # User Configuration
        self.config.user.name = os.getenv("USER_NAME", "Your Name")
        self.config.user.email = os.getenv("USER_EMAIL", "your.email@example.com")
        self.config.user.phone = os.getenv("USER_PHONE", "+1-555-123-4567")
        self.config.user.location = os.getenv("USER_LOCATION", "San Francisco, CA")
        self.config.user.linkedin_url = os.getenv("USER_LINKEDIN_URL", "")
        self.config.user.github_url = os.getenv("USER_GITHUB_URL", "")
        
        # Scraping Configuration
        self.config.scraping.max_jobs_per_batch = int(os.getenv("MAX_JOBS_PER_BATCH", "50"))
        self.config.scraping.delay_seconds = float(os.getenv("SCRAPING_DELAY_SECONDS", "2.0"))
        self.config.scraping.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "30"))
        
        # App Configuration
        self.config.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.config.log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"
        self.config.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this")
        
        # Ensure directories exist
        self._ensure_directories()
        
        logger.info("Configuration loaded successfully")
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        directories = [
            self.config.data_dir,
            self.config.export_dir,
            self.config.template_dir,
            f"{self.config.data_dir}/logs"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        return self.config.llm
    
    def get_contact_finder_config(self) -> ContactFinderConfig:
        """Get contact finder configuration."""
        return self.config.contact_finder
    
    def get_user_config(self) -> UserConfig:
        """Get user configuration."""
        return self.config.user
    
    def get_scraping_config(self) -> ScrapingConfig:
        """Get scraping configuration."""
        return self.config.scraping
    
    def get_app_config(self) -> AppConfig:
        """Get full application configuration."""
        return self.config
    
    def validate_config(self) -> Dict[str, List[str]]:
        """Validate configuration and return any issues."""
        issues = {
            "errors": [],
            "warnings": []
        }
        
        # Check LLM configuration
        if not self.config.llm.openrouter_api_key and not self.config.llm.use_local_llm:
            issues["errors"].append("No LLM backend configured. Set OPENROUTER_API_KEY or USE_LOCAL_LLM=true")
        
        # Note: Local LLM connectivity is now tested via UI test buttons
        # No need for passive warnings here
        
        # Check user configuration
        if self.config.user.name == "Your Name":
            issues["warnings"].append("Default user name detected - update USER_NAME in .env")
        
        if self.config.user.email == "your.email@example.com":
            issues["warnings"].append("Default email detected - update USER_EMAIL in .env")
        
        # Check secret key
        if self.config.secret_key == "your-secret-key-change-this":
            issues["warnings"].append("Default secret key detected - update SECRET_KEY in .env")
        
        # Check contact finder APIs
        if not self.config.contact_finder.hunter_io_api_key and not self.config.contact_finder.apollo_io_api_key:
            issues["warnings"].append("No contact finder APIs configured - will use free methods only")
        
        return issues
    
    def mask_sensitive_config(self) -> Dict[str, Any]:
        """Get configuration with sensitive values masked for display."""
        config_dict = asdict(self.config)
        
        # Mask API keys
        sensitive_keys = [
            "openrouter_api_key", "hunter_io_api_key", "apollo_io_api_key", "secret_key"
        ]
        
        def mask_value(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key in sensitive_keys and value:
                        obj[key] = f"{value[:8]}..." if len(value) > 8 else "***"
                    elif isinstance(value, dict):
                        mask_value(value, current_path)
            return obj
        
        return mask_value(config_dict)
    
    def save_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """Save user preferences to a JSON file."""
        prefs_file = Path(self.config.data_dir) / "user_preferences.json"
        
        try:
            with open(prefs_file, 'w') as f:
                json.dump(preferences, f, indent=2)
            logger.info("User preferences saved successfully")
        except Exception as e:
            logger.error(f"Failed to save user preferences: {e}")
    
    def load_user_preferences(self) -> Dict[str, Any]:
        """Load user preferences from JSON file."""
        prefs_file = Path(self.config.data_dir) / "user_preferences.json"
        
        if not prefs_file.exists():
            return {}
        
        try:
            with open(prefs_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load user preferences: {e}")
            return {}
    
    def update_config(self, **kwargs) -> None:
        """Update configuration values dynamically."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                # Handle nested config updates
                parts = key.split('.')
                if len(parts) == 2:
                    section, setting = parts
                    if hasattr(self.config, section):
                        section_obj = getattr(self.config, section)
                        if hasattr(section_obj, setting):
                            setattr(section_obj, setting, value)
        
        logger.info(f"Configuration updated: {list(kwargs.keys())}")
    
    def save_to_env_file(self) -> None:
        """Save current configuration to .env file."""
        env_file_path = Path(self.env_file)
        
        # Read existing .env file if it exists
        existing_vars = {}
        if env_file_path.exists():
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_vars[key] = value
        
        # Update with current configuration
        env_vars = {
            'OPENROUTER_API_KEY': self.config.llm.openrouter_api_key or '',
            'USE_LOCAL_LLM': str(self.config.llm.use_local_llm).lower(),
            'LOCAL_LLM_MODEL': self.config.llm.local_llm_model,
            'OLLAMA_BASE_URL': self.config.llm.ollama_base_url,
            'DEFAULT_LLM_MODEL': self.config.llm.default_model,
            'HUNTER_IO_API_KEY': self.config.contact_finder.hunter_io_api_key or '',
            'APOLLO_IO_API_KEY': self.config.contact_finder.apollo_io_api_key or '',
            'USER_NAME': self.config.user.name,
            'USER_EMAIL': self.config.user.email,
            'USER_PHONE': self.config.user.phone,
            'USER_LOCATION': self.config.user.location,
            'USER_LINKEDIN_URL': self.config.user.linkedin_url,
            'USER_GITHUB_URL': self.config.user.github_url,
            'MAX_JOBS_PER_BATCH': str(self.config.scraping.max_jobs_per_batch),
            'SCRAPING_DELAY_SECONDS': str(self.config.scraping.delay_seconds),
            'RATE_LIMIT_REQUESTS_PER_MINUTE': str(self.config.scraping.rate_limit_per_minute),
            'LOG_LEVEL': self.config.log_level,
            'LOG_TO_FILE': str(self.config.log_to_file).lower(),
            'SECRET_KEY': self.config.secret_key
        }
        
        # Merge with existing variables (preserve comments and other vars)
        existing_vars.update(env_vars)
        
        # Write to .env file
        try:
            with open(env_file_path, 'w') as f:
                f.write("# AI Job Application Preparation Tool Configuration\n")
                f.write("# This file is automatically generated by the UI\n\n")
                
                f.write("# LLM Configuration\n")
                f.write(f"OPENROUTER_API_KEY={existing_vars.get('OPENROUTER_API_KEY', '')}\n")
                f.write(f"USE_LOCAL_LLM={existing_vars.get('USE_LOCAL_LLM', 'false')}\n")
                f.write(f"LOCAL_LLM_MODEL={existing_vars.get('LOCAL_LLM_MODEL', 'qwen2.5:32b')}\n")
                f.write(f"OLLAMA_BASE_URL={existing_vars.get('OLLAMA_BASE_URL', 'http://localhost:11434')}\n")
                f.write(f"DEFAULT_LLM_MODEL={existing_vars.get('DEFAULT_LLM_MODEL', 'anthropic/claude-3.5-sonnet')}\n\n")
                
                f.write("# Contact Finder APIs\n")
                f.write(f"HUNTER_IO_API_KEY={existing_vars.get('HUNTER_IO_API_KEY', '')}\n")
                f.write(f"APOLLO_IO_API_KEY={existing_vars.get('APOLLO_IO_API_KEY', '')}\n\n")
                
                f.write("# User Information\n")
                f.write(f"USER_NAME={existing_vars.get('USER_NAME', 'Your Full Name')}\n")
                f.write(f"USER_EMAIL={existing_vars.get('USER_EMAIL', 'your.email@example.com')}\n")
                f.write(f"USER_PHONE={existing_vars.get('USER_PHONE', '+1-555-123-4567')}\n")
                f.write(f"USER_LOCATION={existing_vars.get('USER_LOCATION', 'San Francisco, CA')}\n")
                f.write(f"USER_LINKEDIN_URL={existing_vars.get('USER_LINKEDIN_URL', '')}\n")
                f.write(f"USER_GITHUB_URL={existing_vars.get('USER_GITHUB_URL', '')}\n\n")
                
                f.write("# Application Settings\n")
                f.write(f"MAX_JOBS_PER_BATCH={existing_vars.get('MAX_JOBS_PER_BATCH', '50')}\n")
                f.write(f"SCRAPING_DELAY_SECONDS={existing_vars.get('SCRAPING_DELAY_SECONDS', '2.0')}\n")
                f.write(f"RATE_LIMIT_REQUESTS_PER_MINUTE={existing_vars.get('RATE_LIMIT_REQUESTS_PER_MINUTE', '30')}\n\n")
                
                f.write("# Logging\n")
                f.write(f"LOG_LEVEL={existing_vars.get('LOG_LEVEL', 'INFO')}\n")
                f.write(f"LOG_TO_FILE={existing_vars.get('LOG_TO_FILE', 'true')}\n\n")
                
                f.write("# Security\n")
                f.write(f"SECRET_KEY={existing_vars.get('SECRET_KEY', 'your_secret_key_for_streamlit_auth')}\n")
            
            logger.info(f"Configuration saved to {env_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration to .env file: {e}")
            raise

# Global configuration instance
config_manager = ConfigManager()

def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config_manager.get_app_config()

def get_llm_config() -> LLMConfig:
    """Get LLM configuration."""
    return config_manager.get_llm_config()

def get_contact_finder_config() -> ContactFinderConfig:
    """Get contact finder configuration."""
    return config_manager.get_contact_finder_config()

def get_user_config() -> UserConfig:
    """Get user configuration."""
    return config_manager.get_user_config()

def get_scraping_config() -> ScrapingConfig:
    """Get scraping configuration."""
    return config_manager.get_scraping_config()

def validate_config() -> Dict[str, List[str]]:
    """Validate current configuration."""
    return config_manager.validate_config()