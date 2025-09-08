"""
Contact Finder Module

This module provides functionality to discover contact information for hiring managers
and decision makers at companies. It uses multiple strategies including free email
pattern generation and paid API services as fallbacks.
"""

import re
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import logging

from ..config import get_config, get_contact_finder_config
from ..config.database import DatabaseManager
from ..utils import get_logger, RateLimiter

logger = get_logger(__name__)

@dataclass
class Contact:
    """Contact information for a person."""
    name: str = ""
    email: str = ""
    title: str = ""
    company: str = ""
    domain: str = ""
    confidence: float = 0.0
    source: str = ""
    verified: bool = False

@dataclass
class ContactSearchResult:
    """Result of contact search for a company."""
    company: str
    domain: str
    contacts: List[Contact]
    search_methods_used: List[str]
    success_rate: float
    processing_time: float
    total_found: int

class EmailPatternGenerator:
    """Generates common email patterns for a domain."""
    
    COMMON_PATTERNS = [
        "{first}.{last}@{domain}",
        "{first}{last}@{domain}",
        "{first}@{domain}",
        "{last}@{domain}",
        "{first_initial}{last}@{domain}",
        "{first}{last_initial}@{domain}",
        "{first_initial}.{last}@{domain}",
        "{last}.{first}@{domain}",
        "{first}_{last}@{domain}",
        "{first}-{last}@{domain}"
    ]
    
    COMMON_TITLES = [
        "ceo", "cto", "vp", "director", "manager", "lead", "head", "chief",
        "president", "founder", "co-founder", "hiring", "hr", "recruiter",
        "talent", "people", "engineering", "tech", "development"
    ]
    
    @staticmethod
    def generate_patterns_for_person(first_name: str, last_name: str, domain: str) -> List[str]:
        """Generate email patterns for a specific person."""
        patterns = []
        
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        first_initial = first[0] if first else ""
        last_initial = last[0] if last else ""
        
        for pattern in EmailPatternGenerator.COMMON_PATTERNS:
            try:
                email = pattern.format(
                    first=first,
                    last=last,
                    first_initial=first_initial,
                    last_initial=last_initial,
                    domain=domain
                )
                patterns.append(email)
            except (KeyError, IndexError):
                continue
        
        return patterns
    
    @staticmethod
    def generate_generic_patterns(domain: str) -> List[str]:
        """Generate generic hiring-related email patterns."""
        generic_patterns = []
        
        for title in EmailPatternGenerator.COMMON_TITLES:
            generic_patterns.extend([
                f"{title}@{domain}",
                f"info@{domain}",
                f"contact@{domain}",
                f"careers@{domain}",
                f"jobs@{domain}",
                f"hiring@{domain}",
                f"hr@{domain}",
                f"talent@{domain}",
                f"people@{domain}"
            ])
        
        return generic_patterns

class HunterIOClient:
    """Client for Hunter.io API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hunter.io/v2"
        self.rate_limiter = RateLimiter(requests_per_minute=300)  # Hunter.io free tier limit
    
    async def find_emails_for_domain(self, domain: str, limit: int = 10) -> List[Contact]:
        """Find emails for a domain using Hunter.io."""
        await self.rate_limiter.acquire()
        
        try:
            url = f"{self.base_url}/domain-search"
            params = {
                "domain": domain,
                "api_key": self.api_key,
                "limit": limit,
                "type": "personal"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_hunter_response(data, domain)
                    else:
                        logger.warning(f"Hunter.io API error {response.status} for domain {domain}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error calling Hunter.io API: {e}")
            return []
    
    def _parse_hunter_response(self, data: Dict[str, Any], domain: str) -> List[Contact]:
        """Parse Hunter.io API response."""
        contacts = []
        
        if "data" not in data:
            return contacts
        
        emails_data = data["data"].get("emails", [])
        
        for email_info in emails_data:
            contact = Contact(
                name=f"{email_info.get('first_name', '')} {email_info.get('last_name', '')}".strip(),
                email=email_info.get("value", ""),
                title=email_info.get("position", ""),
                company=data["data"].get("organization", ""),
                domain=domain,
                confidence=email_info.get("confidence", 0) / 100.0,  # Hunter returns 0-100
                source="hunter.io",
                verified=email_info.get("verification", {}).get("result") == "deliverable"
            )
            
            if contact.email:
                contacts.append(contact)
        
        return contacts

class ApolloIOClient:
    """Client for Apollo.io API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.apollo.io/v1"
        self.rate_limiter = RateLimiter(requests_per_minute=60)  # Conservative rate limiting
    
    async def find_contacts_for_domain(self, domain: str, limit: int = 10) -> List[Contact]:
        """Find contacts for a domain using Apollo.io."""
        await self.rate_limiter.acquire()
        
        try:
            url = f"{self.base_url}/mixed_people/search"
            headers = {
                "Cache-Control": "no-cache",
                "Content-Type": "application/json",
                "X-Api-Key": self.api_key
            }
            
            payload = {
                "q_organization_domains": domain,
                "page": 1,
                "per_page": limit,
                "person_titles": ["CEO", "CTO", "VP", "Director", "Manager", "Lead", "Founder", "Hiring Manager"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_apollo_response(data, domain)
                    else:
                        logger.warning(f"Apollo.io API error {response.status} for domain {domain}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error calling Apollo.io API: {e}")
            return []
    
    def _parse_apollo_response(self, data: Dict[str, Any], domain: str) -> List[Contact]:
        """Parse Apollo.io API response."""
        contacts = []
        
        people = data.get("people", [])
        
        for person in people:
            name = person.get("name", "")
            title = person.get("title", "")
            company = person.get("organization", {}).get("name", "")
            email = person.get("email", "")
            
            if email:
                contact = Contact(
                    name=name,
                    email=email,
                    title=title,
                    company=company,
                    domain=domain,
                    confidence=0.8,  # Apollo generally has high confidence
                    source="apollo.io",
                    verified=False  # Apollo doesn't provide verification status directly
                )
                contacts.append(contact)
        
        return contacts

class FreeEmailFinder:
    """Free email discovery methods."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=30)  # Conservative for free methods
    
    async def find_emails_for_domain(self, domain: str, company_name: str = "") -> List[Contact]:
        """Find emails using free methods."""
        contacts = []
        
        # Generate common email patterns
        generic_emails = EmailPatternGenerator.generate_generic_patterns(domain)
        
        # Test a subset of the most common patterns
        priority_emails = [
            f"careers@{domain}",
            f"jobs@{domain}",
            f"hiring@{domain}",
            f"hr@{domain}",
            f"info@{domain}",
            f"contact@{domain}"
        ]
        
        for email in priority_emails:
            await self.rate_limiter.acquire()
            
            # For now, we'll add them with low confidence since we can't verify
            # In a real implementation, you might use email verification services
            contact = Contact(
                name="",
                email=email,
                title="",
                company=company_name,
                domain=domain,
                confidence=0.3,  # Low confidence for unverified emails
                source="pattern_generation",
                verified=False
            )
            contacts.append(contact)
        
        return contacts[:6]  # Return top 6 to avoid overwhelming
    
    async def find_emails_for_person(self, first_name: str, last_name: str, domain: str, company_name: str = "") -> List[Contact]:
        """Find emails for a specific person using pattern generation."""
        patterns = EmailPatternGenerator.generate_patterns_for_person(first_name, last_name, domain)
        contacts = []
        
        # Take the top 5 most common patterns
        for email in patterns[:5]:
            contact = Contact(
                name=f"{first_name} {last_name}",
                email=email,
                title="",
                company=company_name,
                domain=domain,
                confidence=0.4,  # Slightly higher confidence for named patterns
                source="pattern_generation",
                verified=False
            )
            contacts.append(contact)
        
        return contacts

class ContactFinder:
    """Main contact finder that coordinates different discovery methods."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.config = get_contact_finder_config()
        
        # Initialize API clients
        self.hunter_client = None
        self.apollo_client = None
        
        if self.config.hunter_io_api_key:
            self.hunter_client = HunterIOClient(self.config.hunter_io_api_key)
        
        if self.config.apollo_io_api_key:
            self.apollo_client = ApolloIOClient(self.config.apollo_io_api_key)
        
        self.free_finder = FreeEmailFinder()
    
    async def find_contacts_for_company(self, company_name: str, domain: Optional[str] = None) -> ContactSearchResult:
        """
        Find contacts for a company using all available methods.
        
        Args:
            company_name: Name of the company
            domain: Company domain (will be extracted if not provided)
            
        Returns:
            ContactSearchResult with all discovered contacts
        """
        start_time = asyncio.get_event_loop().time()
        
        # Extract or validate domain
        if not domain:
            domain = self._extract_domain_from_company(company_name)
        
        if not domain:
            logger.warning(f"Could not determine domain for company: {company_name}")
            return ContactSearchResult(
                company=company_name,
                domain="",
                contacts=[],
                search_methods_used=[],
                success_rate=0.0,
                processing_time=0.0,
                total_found=0
            )
        
        # Check cache first
        cached_result = await self._get_cached_contacts(company_name, domain)
        if cached_result:
            logger.info(f"Using cached contacts for {company_name}")
            return cached_result
        
        all_contacts = []
        methods_used = []
        
        # Try paid APIs first (higher quality)
        if self.hunter_client:
            try:
                hunter_contacts = await self.hunter_client.find_emails_for_domain(domain)
                all_contacts.extend(hunter_contacts)
                methods_used.append("hunter.io")
                logger.info(f"Found {len(hunter_contacts)} contacts via Hunter.io for {domain}")
            except Exception as e:
                logger.error(f"Hunter.io search failed for {domain}: {e}")
        
        if self.apollo_client:
            try:
                apollo_contacts = await self.apollo_client.find_contacts_for_domain(domain)
                all_contacts.extend(apollo_contacts)
                methods_used.append("apollo.io")
                logger.info(f"Found {len(apollo_contacts)} contacts via Apollo.io for {domain}")
            except Exception as e:
                logger.error(f"Apollo.io search failed for {domain}: {e}")
        
        # Use free methods if we don't have enough contacts or no paid APIs
        if len(all_contacts) < 3 or self.config.use_free_methods:
            try:
                free_contacts = await self.free_finder.find_emails_for_domain(domain, company_name)
                all_contacts.extend(free_contacts)
                methods_used.append("pattern_generation")
                logger.info(f"Found {len(free_contacts)} contacts via pattern generation for {domain}")
            except Exception as e:
                logger.error(f"Free email search failed for {domain}: {e}")
        
        # Remove duplicates and sort by confidence
        unique_contacts = self._deduplicate_contacts(all_contacts)
        unique_contacts.sort(key=lambda c: c.confidence, reverse=True)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        result = ContactSearchResult(
            company=company_name,
            domain=domain,
            contacts=unique_contacts,
            search_methods_used=methods_used,
            success_rate=len(unique_contacts) / max(len(all_contacts), 1),
            processing_time=processing_time,
            total_found=len(unique_contacts)
        )
        
        # Cache the result
        await self._cache_contacts(result)
        
        logger.info(f"Contact search completed for {company_name}: {len(unique_contacts)} unique contacts found")
        return result
    
    def _extract_domain_from_company(self, company_name: str) -> Optional[str]:
        """Extract or guess domain from company name."""
        # Clean company name
        clean_name = re.sub(r'\b(inc|llc|corp|corporation|company|co|ltd|limited)\b', '', company_name.lower())
        clean_name = re.sub(r'[^a-z0-9\s]', '', clean_name).strip()
        
        # Try common domain patterns
        domain_candidates = [
            f"{clean_name.replace(' ', '')}.com",
            f"{clean_name.replace(' ', '-')}.com",
            f"{clean_name.replace(' ', '')}.io",
            f"{''.join([word[0] for word in clean_name.split()])}.com"  # Acronym
        ]
        
        # For now, return the first candidate
        # In a real implementation, you might validate these domains
        return domain_candidates[0] if domain_candidates else None
    
    def _deduplicate_contacts(self, contacts: List[Contact]) -> List[Contact]:
        """Remove duplicate contacts based on email address."""
        seen_emails = set()
        unique_contacts = []
        
        for contact in contacts:
            if contact.email.lower() not in seen_emails:
                seen_emails.add(contact.email.lower())
                unique_contacts.append(contact)
        
        return unique_contacts
    
    async def _get_cached_contacts(self, company_name: str, domain: str) -> Optional[ContactSearchResult]:
        """Get cached contact results."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                contacts_json TEXT NOT NULL,
                search_methods_used TEXT,
                success_rate REAL,
                processing_time REAL,
                total_found INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_name, domain)
            )
            """)
            
            # Check for cached results (within last 30 days)
            cursor.execute("""
            SELECT contacts_json, search_methods_used, success_rate, processing_time, total_found
            FROM contact_cache
            WHERE company_name = ? AND domain = ?
            AND created_at >= datetime('now', '-30 days')
            ORDER BY created_at DESC
            LIMIT 1
            """, (company_name, domain))
            
            row = cursor.fetchone()
            if row:
                contacts_data = json.loads(row[0])
                contacts = [Contact(**contact_dict) for contact_dict in contacts_data]
                methods_used = json.loads(row[1]) if row[1] else []
                
                return ContactSearchResult(
                    company=company_name,
                    domain=domain,
                    contacts=contacts,
                    search_methods_used=methods_used,
                    success_rate=row[2] or 0.0,
                    processing_time=row[3] or 0.0,
                    total_found=row[4] or 0
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached contacts: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def _cache_contacts(self, result: ContactSearchResult) -> None:
        """Cache contact search results."""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Convert contacts to JSON
            contacts_json = json.dumps([asdict(contact) for contact in result.contacts])
            methods_json = json.dumps(result.search_methods_used)
            
            # Insert or replace cached result
            cursor.execute("""
            INSERT OR REPLACE INTO contact_cache (
                company_name, domain, contacts_json, search_methods_used,
                success_rate, processing_time, total_found
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.company,
                result.domain,
                contacts_json,
                methods_json,
                result.success_rate,
                result.processing_time,
                result.total_found
            ))
            
            conn.commit()
            logger.info(f"Cached contact results for {result.company}")
            
        except Exception as e:
            logger.error(f"Error caching contacts: {e}")
        finally:
            if conn:
                conn.close()
    
    async def find_contacts_for_jobs(self, job_ids: List[int]) -> Dict[int, ContactSearchResult]:
        """Find contacts for multiple jobs in batch."""
        results = {}
        
        try:
            # Get job details
            job_details = await self._get_job_companies_batch(job_ids)
            
            # Process each job
            tasks = []
            for job_id, job_data in job_details.items():
                if job_data:
                    task = self.find_contacts_for_company(
                        company_name=job_data['company'],
                        domain=job_data.get('company_domain')
                    )
                    tasks.append((job_id, task))
                else:
                    results[job_id] = ContactSearchResult(
                        company="Unknown",
                        domain="",
                        contacts=[],
                        search_methods_used=[],
                        success_rate=0.0,
                        processing_time=0.0,
                        total_found=0
                    )
            
            # Execute searches concurrently (with some delay to respect rate limits)
            for i, (job_id, task) in enumerate(tasks):
                if i > 0:
                    await asyncio.sleep(2)  # Rate limiting delay
                
                try:
                    result = await task
                    results[job_id] = result
                except Exception as e:
                    logger.error(f"Error finding contacts for job {job_id}: {e}")
                    results[job_id] = ContactSearchResult(
                        company=job_details.get(job_id, {}).get('company', 'Unknown'),
                        domain="",
                        contacts=[],
                        search_methods_used=[],
                        success_rate=0.0,
                        processing_time=0.0,
                        total_found=0
                    )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch contact finding: {e}")
            return {job_id: ContactSearchResult(
                company="Unknown",
                domain="",
                contacts=[],
                search_methods_used=[],
                success_rate=0.0,
                processing_time=0.0,
                total_found=0
            ) for job_id in job_ids}
    
    async def _get_job_companies_batch(self, job_ids: List[int]) -> Dict[int, Optional[Dict[str, Any]]]:
        """Get company information for multiple jobs."""
        job_details = {}
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(job_ids))
            cursor.execute(f"""
            SELECT id, company, url
            FROM jobs
            WHERE id IN ({placeholders})
            """, job_ids)
            
            rows = cursor.fetchall()
            
            for row in rows:
                job_id, company, url = row
                
                # Try to extract domain from job URL
                domain = None
                if url:
                    try:
                        parsed_url = urlparse(url)
                        domain = parsed_url.netloc.replace('www.', '')
                    except:
                        pass
                
                job_details[job_id] = {
                    'company': company,
                    'company_domain': domain
                }
            
            # Add None for missing jobs
            for job_id in job_ids:
                if job_id not in job_details:
                    job_details[job_id] = None
            
            return job_details
            
        except Exception as e:
            logger.error(f"Error getting job company details: {e}")
            return {job_id: None for job_id in job_ids}
        finally:
            if conn:
                conn.close()

async def find_contacts_for_company(company_name: str, domain: Optional[str] = None, db_manager: Optional[DatabaseManager] = None) -> ContactSearchResult:
    """
    Convenience function to find contacts for a company.
    
    Args:
        company_name: Name of the company
        domain: Optional company domain
        db_manager: Optional database manager instance
        
    Returns:
        ContactSearchResult with discovered contacts
    """
    if not db_manager:
        from ..config.database import get_db_manager
        db_manager = get_db_manager()
    
    finder = ContactFinder(db_manager)
    return await finder.find_contacts_for_company(company_name, domain)