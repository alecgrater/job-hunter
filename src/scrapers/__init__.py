"""
Scrapers module for job data extraction.

This module contains scrapers for various job sources including LinkedIn RSS feeds.
"""

from .linkedin_scraper import LinkedInRSScraper

__all__ = ['LinkedInRSScraper']