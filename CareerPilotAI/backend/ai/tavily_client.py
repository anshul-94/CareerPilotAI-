"""
CareerPilot AI — Tavily API Client
Handles web search via Tavily API for the AI Job Finder module.
Builds dynamic search queries from resume skills and returns structured results.
"""

import os
import json
import requests
from typing import Optional



# Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_API_URL = os.getenv("TAVILY_API_URL", "https://api.tavily.com/search")
REQUEST_TIMEOUT = 30


def is_api_configured() -> bool:
    """Check if the Tavily API key is configured."""
    return bool(TAVILY_API_KEY and TAVILY_API_KEY != "your-tavily-api-key-here")


def search_jobs(
    query: str,
    max_results: int = 10,
    search_depth: str = "basic",
    include_domains: list[str] = None
) -> dict:
    """
    Search for jobs using the Tavily API.
    
    Args:
        query: Search query string
        max_results: Maximum number of results
        search_depth: 'basic' or 'advanced'
        include_domains: List of domains to prioritize
        
    Returns:
        Dict with 'success', 'results', and optional 'error' keys
    """
    if not is_api_configured():
        print("[INFO] Tavily API not configured.")
        return _get_fallback_results(query, "Tavily API not configured.")
    
    if include_domains is None:
        include_domains = [
            "linkedin.com",
            "indeed.com",
            "glassdoor.com",
            "naukri.com",
            "wellfound.com",
            "remoteok.com",
            "foundit.in",
        ]
    
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_domains": include_domains,
        "include_answer": True,
    }
    
    try:
        response = requests.post(
            TAVILY_API_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            results = _parse_tavily_results(data)
            return {
                "success": True,
                "results": results,
                "query": query,
                "answer": data.get("answer", ""),
                "mock": False
            }
        
        elif response.status_code == 401:
            print("[ERROR] Invalid Tavily API key")
            return _get_fallback_results(query, error="Invalid API key")
            
        else:
            print(f"[ERROR] Tavily API returned {response.status_code}")
            return _get_fallback_results(query, error=f"API error ({response.status_code})")
            
    except requests.exceptions.Timeout:
        print("[WARN] Tavily request timed out")
        return _get_fallback_results(query, error="Request timed out")
        
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to Tavily API")
        return _get_fallback_results(query, error="Connection error")
        
    except Exception as e:
        print(f"[ERROR] Tavily error: {str(e)}")
        return _get_fallback_results(query, error=str(e))


def build_job_search_queries(skills: list[str], role: str = "",
                              location: str = "", experience: str = "fresher") -> list[str]:
    """
    Build dynamic search queries from resume data.
    
    Args:
        skills: List of extracted skills
        role: Target job role
        location: Preferred location
        experience: Experience level
        
    Returns:
        List of search query strings
    """
    queries = []
    
    # Primary role-based query
    if role:
        base = f"{role} {experience} hiring"
        if location:
            base += f" {location}"
        queries.append(base)
    
    # Skill combination queries
    if skills:
        # Top skills combined
        top_skills = skills[:4]
        skill_str = " ".join(top_skills)
        queries.append(f"{skill_str} developer jobs {experience} 2024 2025")
        
        # Individual skill queries for popular skills
        priority_skills = ["Python", "Machine Learning", "AI", "Data Science",
                          "React", "Java", "Cloud", "DevOps", "Full Stack"]
        for skill in skills:
            if skill in priority_skills:
                q = f"{skill} {experience} jobs hiring"
                if location:
                    q += f" {location}"
                queries.append(q)
                if len(queries) >= 5:
                    break
    
    # Fallback query
    if not queries:
        queries.append(f"Software Developer {experience} hiring jobs 2024 2025")
    
    return queries[:5]  # Max 5 queries


def search_multiple_queries(queries: list[str], max_results_per_query: int = 5) -> list[dict]:
    """
    Search multiple queries and combine deduplicated results.
    
    Args:
        queries: List of search queries
        max_results_per_query: Max results per query
        
    Returns:
        Combined list of unique job results
    """
    all_results = []
    seen_urls = set()
    
    for query in queries:
        result = search_jobs(query, max_results=max_results_per_query)
        if result["success"]:
            for job in result["results"]:
                url = job.get("apply_link", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(job)
    
    return all_results


def _parse_tavily_results(data: dict) -> list[dict]:
    """Parse raw Tavily API results into structured job data."""
    results = []
    
    for item in data.get("results", []):
        job = {
            "title": _extract_job_title(item.get("title", "")),
            "company": _extract_company(item.get("title", ""), item.get("url", "")),
            "location": _extract_location(item.get("content", "")),
            "description": item.get("content", "")[:300],
            "apply_link": item.get("url", ""),
            "source": _extract_source(item.get("url", "")),
            "salary": _extract_salary(item.get("content", "")),
            "match_score": 0,  # Will be calculated separately
            "found_at": item.get("published_date", ""),
        }
        results.append(job)
    
    return results


def _extract_job_title(title: str) -> str:
    """Extract clean job title from search result title."""
    # Remove common suffixes
    for sep in [' - ', ' | ', ' at ', ' — ']:
        if sep in title:
            title = title.split(sep)[0]
    return title.strip()[:100]


def _extract_company(title: str, url: str) -> str:
    """Extract company name from title or URL."""
    for sep in [' - ', ' | ', ' at ', ' — ']:
        parts = title.split(sep)
        if len(parts) > 1:
            return parts[-1].strip()[:50]
    
    # Extract from URL domain
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        domain = domain.replace('www.', '').split('.')[0]
        return domain.capitalize()
    except Exception:
        return "Company"


def _extract_location(content: str) -> str:
    """Extract location from job description content."""
    import re
    location_patterns = [
        r'(?:Location|Based in|Office)[\s:]+([A-Za-z\s,]+?)(?:\.|,|\n|$)',
        r'(?:Remote|Hybrid|On-site|Onsite)',
        r'(?:Bangalore|Mumbai|Delhi|Hyderabad|Chennai|Pune|Kolkata|Noida|Gurgaon)',
        r'(?:New York|San Francisco|London|Berlin|Singapore|Toronto)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(0).strip()[:50]
    
    return "Remote / On-site"


def _extract_salary(content: str) -> str:
    """Extract salary information from content."""
    import re
    salary_patterns = [
        r'[\$₹€£]\s*[\d,]+\s*[-–]\s*[\$₹€£]?\s*[\d,]+',
        r'[\d,]+\s*[-–]\s*[\d,]+\s*(?:LPA|CTC|per annum|per year|/yr)',
        r'(?:Salary|CTC|Compensation)[\s:]+[\$₹€£]?\s*[\d,]+',
    ]
    
    for pattern in salary_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    
    return "Not disclosed"


def _extract_source(url: str) -> str:
    """Extract source platform from URL."""
    source_map = {
        "linkedin.com": "LinkedIn",
        "indeed.com": "Indeed",
        "glassdoor.com": "Glassdoor",
        "naukri.com": "Naukri",
        "wellfound.com": "Wellfound",
        "remoteok.com": "RemoteOK",
        "foundit.in": "Foundit",
        "angel.co": "AngelList",
        "github.com": "GitHub",
        "lever.co": "Lever",
        "greenhouse.io": "Greenhouse",
        "workday.com": "Workday",
    }
    
    url_lower = url.lower()
    for domain, name in source_map.items():
        if domain in url_lower:
            return name
    
    return "Web"


def _get_fallback_results(query: str, error: str = None) -> dict:
    """Get fallback results when API is unavailable."""
    result = {
        "success": False,
        "results": [],
        "query": query,
        "answer": f"Unable to fetch real-time jobs due to: {error}",
        "mock": False,
        "error": error
    }
    return result
