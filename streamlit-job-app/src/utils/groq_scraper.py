import os
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
#GROQ_API_KEY= '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'

# --- LLM Client Setup ---
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

def _infer_company_domain(company_name: str) -> str | None:
    """
    Use Groq API to guess the official domain of a company.
    Example: 'Vedant Infra' -> 'vedantinfra.com'
    """
    try:
        prompt = f"Find the most likely official domain name of the company '{company_name}'. Only return the domain, no extra text."
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.2
        )
        domain = response.choices[0].message.content.strip()
        # Normalize domain
        domain = re.sub(r"^https?://", "", domain)
        domain = domain.split("/")[0]
        return domain
    except Exception as e:
        print(f"[Groq] Failed to infer domain for {company_name}: {e}")
        return None


def _scrape_domain_fallback(company_name: str) -> str | None:
    """
    Fallback: scrape Google search results to extract a domain.
    """
    try:
        query = f"{company_name} official site"
        url = f"https://www.google.com/search?q={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        links = [a["href"] for a in soup.select("a[href]") if "http" in a["href"]]

        for link in links:
            match = re.search(r"https?://([a-zA-Z0-9.-]+)", link)
            if match:
                domain = match.group(1)
                if not domain.startswith("google"):
                    return domain
        return None
    except Exception as e:
        print(f"[Scraper] Fallback failed for {company_name}: {e}")
        return None


def generate_hr_emails(hr_name: str, company_name: str) -> list[str]:
    """
    Generate possible HR email IDs using Groq domain inference with a web scrape fallback.
    """
    domain = _infer_company_domain(company_name) or _scrape_domain_fallback(company_name)
    if not domain:
        return []

    # Split HR name
    parts = hr_name.lower().split()
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    # Generate common email patterns
    candidates = [
        f"{first}.{last}@{domain}",
        f"{first}@{domain}",
        f"{first}{last}@{domain}",
        f"{first}_{last}@{domain}",
        f"{first[0]}{last}@{domain}",
    ]

    return list(set(candidates))  # unique


# --- Exposed API for app.py ---
def get_recruiter_emails(hr_name: str, company_name: str) -> list[str]:
    """
    Public function to be called from app.py
    Returns list of candidate HR emails.
    """
    return generate_hr_emails(hr_name, company_name)


def scrape_recruiter_email(job_description: str) -> str:
    """
    Extract recruiter email from job description text using regex.
    If no email is found, return an empty string.
    """
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", job_description)
    if match:
        return match.group(0)
    return ""
