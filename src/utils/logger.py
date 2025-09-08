"""
Logging configuration and utilities for the AI Job Application Preparation Tool.

This module provides structured logging with file rotation, progress tracking,
and different log levels for various components.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

from ..config import get_config

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured logs with context."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information."""
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add component context
        if hasattr(record, 'component'):
            log_entry["component"] = record.component
        
        if hasattr(record, 'job_id'):
            log_entry["job_id"] = record.job_id
        
        if hasattr(record, 'batch_id'):
            log_entry["batch_id"] = record.batch_id
        
        return json.dumps(log_entry)

class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for better readability."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with colors for console output."""
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Create formatted message
        formatted = f"{color}[{timestamp}] {record.levelname:8} {record.name:20} | {record.getMessage()}{reset}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted

class JobApplicationLogger:
    """Enhanced logger with context for job application processing."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Set context fields that will be included in all log messages."""
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context fields."""
        self.context.clear()
    
    def _log_with_context(self, level: int, message: str, **kwargs) -> None:
        """Log message with context fields."""
        extra_fields = {**self.context, **kwargs}
        extra = {"extra_fields": extra_fields} if extra_fields else {}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def job_started(self, job_id: int, job_title: str, company: str) -> None:
        """Log job processing start."""
        self.set_context(job_id=job_id)
        self.info(f"Started processing job: {job_title} at {company}")
    
    def job_completed(self, job_id: int, status: str) -> None:
        """Log job processing completion."""
        self.info(f"Completed job processing with status: {status}")
        # Remove job_id from context
        self.context.pop('job_id', None)
    
    def batch_started(self, batch_id: int, job_count: int) -> None:
        """Log batch processing start."""
        self.set_context(batch_id=batch_id)
        self.info(f"Started batch processing {job_count} jobs")
    
    def batch_completed(self, batch_id: int, processed: int, errors: int) -> None:
        """Log batch processing completion."""
        self.info(f"Completed batch processing: {processed} processed, {errors} errors")
        # Remove batch_id from context
        self.context.pop('batch_id', None)

class ProgressLogger:
    """Logger for tracking progress of long-running operations."""
    
    def __init__(self, logger: JobApplicationLogger, total: int, operation: str):
        self.logger = logger
        self.total = total
        self.operation = operation
        self.current = 0
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1, message: Optional[str] = None) -> None:
        """Update progress and log if significant milestone reached."""
        self.current += increment
        percentage = (self.current / self.total) * 100
        
        # Log at 25%, 50%, 75%, and 100%
        if percentage >= 25 and not hasattr(self, '_logged_25'):
            self._log_milestone(25, message)
            self._logged_25 = True
        elif percentage >= 50 and not hasattr(self, '_logged_50'):
            self._log_milestone(50, message)
            self._logged_50 = True
        elif percentage >= 75 and not hasattr(self, '_logged_75'):
            self._log_milestone(75, message)
            self._logged_75 = True
        elif percentage >= 100 and not hasattr(self, '_logged_100'):
            self._log_milestone(100, message)
            self._logged_100 = True
    
    def _log_milestone(self, percentage: int, message: Optional[str]) -> None:
        """Log progress milestone."""
        elapsed = datetime.now() - self.start_time
        rate = self.current / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
        
        log_message = f"{self.operation} progress: {percentage}% ({self.current}/{self.total})"
        if message:
            log_message += f" - {message}"
        
        self.logger.info(
            log_message,
            progress_percentage=percentage,
            items_processed=self.current,
            total_items=self.total,
            processing_rate=round(rate, 2),
            elapsed_seconds=elapsed.total_seconds()
        )
    
    def complete(self, message: Optional[str] = None) -> None:
        """Mark operation as complete."""
        elapsed = datetime.now() - self.start_time
        rate = self.current / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
        
        log_message = f"{self.operation} completed: {self.current}/{self.total} items"
        if message:
            log_message += f" - {message}"
        
        self.logger.info(
            log_message,
            total_processed=self.current,
            total_time_seconds=elapsed.total_seconds(),
            average_rate=round(rate, 2)
        )

def setup_logging(config: Optional[Any] = None) -> None:
    """Setup logging configuration for the application."""
    if config is None:
        config = get_config()
    
    # Create logs directory
    log_dir = Path(config.data_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredConsoleFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler with rotation if enabled
    if config.log_to_file:
        # Main application log
        app_log_file = log_dir / "app.log"
        file_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(getattr(logging, config.log_level.upper()))
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        
        # Error log (errors and above only)
        error_log_file = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
    
    # Set specific logger levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    logging.info("Logging system initialized")

def get_logger(name: str) -> JobApplicationLogger:
    """Get a logger instance with job application context support."""
    return JobApplicationLogger(name)

def get_progress_logger(logger: JobApplicationLogger, total: int, operation: str) -> ProgressLogger:
    """Get a progress logger for tracking long operations."""
    return ProgressLogger(logger, total, operation)

# Component-specific loggers
def get_scraper_logger() -> JobApplicationLogger:
    """Get logger for scraping components."""
    return get_logger("scraper")

def get_ai_logger() -> JobApplicationLogger:
    """Get logger for AI processing components."""
    return get_logger("ai_processing")

def get_contact_logger() -> JobApplicationLogger:
    """Get logger for contact finder components."""
    return get_logger("contact_finder")

def get_email_logger() -> JobApplicationLogger:
    """Get logger for email generation components."""
    return get_logger("email_composer")

def get_ui_logger() -> JobApplicationLogger:
    """Get logger for UI components."""
    return get_logger("ui")

def get_workflow_logger() -> JobApplicationLogger:
    """Get logger for workflow orchestration."""
    return get_logger("workflow")

# Initialize logging on module import
try:
    setup_logging()
except Exception as e:
    # Fallback to basic logging if setup fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.error(f"Failed to setup advanced logging: {e}")