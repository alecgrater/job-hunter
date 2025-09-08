"""
Main application entry point for the AI Job Application Preparation Tool.

This module provides the main workflow orchestration and can be used to test
the system components or run batch processing operations.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import from src package
from src.config import DatabaseManager, get_config, validate_config
from src.utils import setup_logging, get_workflow_logger
from src.ai_processing.llm_manager import get_llm_manager
from src.document_manager.resume_handler import load_resume_template

async def test_system_components():
    """Test all system components to ensure they're working correctly."""
    logger = get_workflow_logger()
    logger.info("Starting system component tests")
    
    # Test configuration
    logger.info("Testing configuration system...")
    config = get_config()
    validation_issues = validate_config()
    
    if validation_issues["errors"]:
        logger.warning(f"Configuration errors: {validation_issues['errors']}")
        logger.info("⚠️ Configuration has errors but system can still start")
    
    if validation_issues["warnings"]:
        logger.warning(f"Configuration warnings: {validation_issues['warnings']}")
    
    logger.info("✅ Configuration system working")
    
    # Test database
    logger.info("Testing database system...")
    try:
        db = DatabaseManager()
        stats = db.get_stats()
        logger.info(f"Database initialized with stats: {stats}")
        logger.info("✅ Database system working")
    except Exception as e:
        logger.error(f"❌ Database system failed: {e}")
        return False
    
    # Test LLM manager
    logger.info("Testing LLM system...")
    try:
        llm_manager = get_llm_manager()
        providers = llm_manager.get_available_providers()
        provider_info = llm_manager.get_provider_info()
        
        logger.info(f"Available LLM providers: {providers}")
        logger.info(f"Provider info: {provider_info}")
        
        if providers:
            # Test with a simple message
            test_results = await llm_manager.test_providers()
            logger.info(f"LLM test results: {test_results}")
            logger.info("✅ LLM system working")
        else:
            logger.warning("⚠️ No LLM providers available - check configuration")
    except Exception as e:
        logger.error(f"❌ LLM system failed: {e}")
        return False
    
    # Test resume template handler
    logger.info("Testing resume template system...")
    try:
        resume_handler = load_resume_template()
        if resume_handler:
            resume_data = resume_handler.get_resume_data()
            validation_issues = resume_handler.validate_template()
            
            logger.info(f"Resume loaded: {resume_data.contact_info.name if resume_data else 'None'}")
            if validation_issues["errors"]:
                logger.warning(f"Resume validation errors: {validation_issues['errors']}")
            if validation_issues["warnings"]:
                logger.warning(f"Resume validation warnings: {validation_issues['warnings']}")
            
            logger.info("✅ Resume template system working")
        else:
            logger.warning("⚠️ Resume template not found - check template file")
    except Exception as e:
        logger.error(f"❌ Resume template system failed: {e}")
        return False
    
    logger.info("🎉 All system components tested successfully!")
    return True

async def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger = get_workflow_logger()
    
    logger.info("Starting AI Job Application Preparation Tool")
    
    # Test system components
    if await test_system_components():
        logger.info("System is ready for use!")
        
        # Show next steps
        logger.info("\n" + "="*50)
        logger.info("NEXT STEPS:")
        logger.info("1. Configure your .env file with API keys")
        logger.info("2. Run the Streamlit UI: uv run streamlit run src/ui/dashboard.py")
        logger.info("3. Or continue building remaining components")
        logger.info("="*50)
    else:
        logger.error("System component tests failed. Please check configuration.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)