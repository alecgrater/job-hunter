# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Job Application Preparation Tool - A comprehensive Python-based system that replicates functionality from Nick's YouTube tutorial. The system scrapes LinkedIn jobs, filters them with AI, customizes resumes for each position, finds contact information, and generates personalized outreach emails. This is a **defensive tool** designed to help job seekers prepare applications more efficiently, not to spam or automate submissions.

**Original Project Goals:**
- Scrape LinkedIn jobs from RSS feeds
- Filter jobs using AI based on user skills/preferences  
- Customize resumes for each position using LLM
- Find contact information for hiring managers
- Generate personalized outreach emails
- Maintain ethical standards through manual review workflows

## Key Architecture

**Core Components:**
- `src/config/` - Configuration management with environment variables and user preferences
- `src/scrapers/` - LinkedIn RSS feed scraping (respectful, rate-limited)
- `src/ai_processing/` - LLM integration (OpenRouter API + local Ollama support)
- `src/contact_finder/` - Email discovery using multiple APIs and patterns
- `src/email_composer/` - Personalized email template generation
- `src/document_manager/` - Resume customization and document handling
- `src/ui/` - Streamlit-based web interface with tabbed components

**Data Flow:**
1. LinkedIn RSS feeds → Job scraping → AI filtering
2. Approved jobs → Resume customization → Contact discovery
3. Email generation → Manual review → Export packages

## Development Commands

```bash
# Setup environment
uv sync

# Run the main application
uv run streamlit run src/ui/app.py

# Run tests (when test files exist)
uv run pytest

# Run from project root
cd ai-job-automation
```

## Configuration

The system uses `.env` file for configuration with the following key sections:

**LLM Backend Options:**
- OpenRouter API: Set `OPENROUTER_API_KEY`
- Local Ollama: Set `USE_LOCAL_LLM=true` (requires Ollama with qwen2.5:32b model)

**Required User Settings:**
- `USER_NAME`, `USER_EMAIL`, `USER_PHONE`, `USER_LOCATION`
- `USER_LINKEDIN_URL`, `USER_GITHUB_URL` (optional)

**API Keys (optional for enhanced features):**
- `HUNTER_IO_API_KEY`, `APOLLO_IO_API_KEY` for contact discovery

Configuration is managed through `src/config/settings.py` with the `ConfigManager` class providing validation and secure handling of API keys.

## Important Implementation Notes

**Ethical Design Principles:**
- All outputs require manual review before use
- Rate limiting and respectful scraping practices
- No automatic submission of applications or emails
- Terms of service compliance built into scraping logic

**UI Architecture:**
- Main entry: `src/ui/app.py` (Streamlit multi-tab interface)
- Components: `src/ui/components/` (dashboard, configuration, resume manager, system status)
- Session management in `src/ui/utils/session.py`

**Data Storage:**
- SQLite database: `data/job_applications.db`
- Export packages: `data/exports/`
- Templates: `data/templates/`
- Logs: `data/logs/`

The system emphasizes preparation over automation - it prepares everything needed for job applications but requires human review and manual sending to maintain professional standards and respect platform policies.

## User Profile Context

**Target User:** Alec Grater - Software Engineer at Apple Inc
- **Skills:** Python, SQL, ETL, LLMs, RAG Systems, CI/CD, Kubernetes, Splunk, Tableau
- **Experience:** Large-scale systems, automation, cost optimization, cross-functional leadership
- **Target Roles:** Software Engineer positions at tech companies
- **Location:** San Francisco, CA
- **Background:** Economics degree, technical leadership, content creation experience

## Outstanding Development Tasks

**Core Features - COMPLETED:**
✅ Job review interface for filtering results approval
✅ AI resume customization engine with LLM backend selection  
✅ Contact finder with free email discovery and paid API fallbacks
✅ Email generation system with LLM-powered personalized templates
✅ Document manager for PDF and HTML resume generation
✅ Batch processing workflow orchestrator
✅ Email preview and editing interface
✅ Summary reporting with preparation status and metrics
✅ Export functionality for approved emails, resumes, and contact lists
✅ Error handling and batch processing recovery

**Implementation Status:**
All core automation features have been implemented and integrated. The system now provides:

- **Complete AI Workflow**: Job filtering → Resume customization → Contact finding → Email generation → Document creation
- **Professional UI**: Streamlit-based interface with job review, email preview, and export management
- **Batch Processing**: Concurrent processing of multiple job applications with progress tracking
- **Multiple Export Formats**: Individual packages, CSV exports, email client ready formats, and ZIP packages
- **LLM Integration**: Support for both OpenRouter API and local Ollama models
- **Document Generation**: PDF, HTML, and Markdown resume formats with professional styling

**Next Steps for Production Use:**
- Comprehensive testing for all components
- User documentation including local model setup guides
- Application tracking system for manual follow-up
- Performance optimization and error recovery testing
- to memorize