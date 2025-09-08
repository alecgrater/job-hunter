"""
AI Processing module for the AI Job Application Preparation Tool.

This module provides LLM integration and AI-powered functionality.
"""

from .llm_manager import (
    LLMManager,
    LLMProvider,
    LLMResponse,
    OpenRouterProvider,
    OllamaProvider,
    get_llm_manager,
    generate_text,
    generate_structured_response
)

from .job_filter import (
    AIJobFilter,
    FilterCriteria,
    FilterResult,
    FilterDecision,
    create_default_criteria,
    create_criteria_from_dict
)

from .resume_customizer import (
    AIResumeCustomizer,
    CustomizationRequest,
    CustomizationResult,
    create_customization_request_from_job
)

__all__ = [
    'LLMManager',
    'LLMProvider',
    'LLMResponse',
    'OpenRouterProvider',
    'OllamaProvider',
    'get_llm_manager',
    'generate_text',
    'generate_structured_response',
    'AIJobFilter',
    'FilterCriteria',
    'FilterResult',
    'FilterDecision',
    'create_default_criteria',
    'create_criteria_from_dict',
    'AIResumeCustomizer',
    'CustomizationRequest',
    'CustomizationResult',
    'create_customization_request_from_job'
]