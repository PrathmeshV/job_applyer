import re
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import os
import difflib
groq_api_key ="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"
# --- LLM Client Setup ---
client = OpenAI(
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1"
)

# Load recruiter Excel (adjust file path)
EXCEL_FILE = "sample_job_details.xlsx"



def _find_in_excel(hr_name: str = "", company_name: str = "") -> str | None:
    try:
        df = pd.read_excel(EXCEL_FILE)

        # Ensure columns exist
        if "Recruiter Email" not in df.columns:
            return None

        # Step 1: If company column exists, try matching company
        if "Company" in df.columns and company_name:
            match = df[df["Company"].astype(str).str.lower().str.contains(company_name.lower(), na=False)]
            if not match.empty:
                email = match["Recruiter Email"].values[0]
                if pd.notna(email) and "@" in str(email):
                    return str(email).strip()

        # Step 2: If recruiter name column exists, try fuzzy match
        if "Recruiter Name" in df.columns and hr_name:
            names = df["Recruiter Name"].dropna().astype(str).str.lower().str.strip().tolist()
            closest = difflib.get_close_matches(hr_name.lower().strip(), names, n=1, cutoff=0.6)

            if closest:
                row = df[df["Recruiter Name"].str.lower().str.strip() == closest[0]]
                email = row["Recruiter Email"].values[0]
                if pd.notna(email) and "@" in str(email):
                    return str(email).strip()

        # Step 3: If no match, just return the first valid email in Excel
        for email in df["Recruiter Email"].dropna().astype(str).str.strip():
            if re.match(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", email):
                return email

        return None
    except Exception as e:
        print(f"[Excel] Error: {e}")
        return None



def _infer_company_domain(company_name: str) -> str | None:
    """
    Use Groq API to guess the official domain of a company.
    """
    try:
        prompt = f"Find the most likely official domain name of the company '{company_name}'. Only return the domain."
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.2
        )
        domain = response.choices[0].message.content.strip()
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


def _generate_email_patterns(hr_name: str, company_name: str) -> list[str]:
    """
    Generate possible HR email IDs using domain inference.
    """
    domain = _infer_company_domain(company_name) or _scrape_domain_fallback(company_name)
    if not domain:
        return []

    parts = hr_name.lower().split()
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    candidates = [
        f"{first}.{last}@{domain}",
        f"{first}@{domain}",
        f"{first}{last}@{domain}",
        f"{first}_{last}@{domain}",
        f"{first[0]}{last}@{domain}",
    ]

    return list(set(candidates))


def scrape_recruiter_email(job_description: str) -> str | None:
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|in|org|net|co|edu)", job_description)
    if match:
        return match.group(0)
    return None



def get_recruiter_email(hr_name: str, company_name: str, job_description: str) -> str | None:
    """
    Main function with priority:
    1. Look inside Excel
    2. Extract from job description
    3. Generate email patterns
    """
    # Step 1: Check Excel
    email = _find_in_excel(hr_name)
    if email:
        return email

    # Step 2: Look in job description
    email = scrape_recruiter_email(job_description)
    if email:
        return email

    # Step 3: Generate possible patterns
    candidates = _generate_email_patterns(hr_name, company_name)
    if candidates:
        return candidates[0]  # return first suggestion

    return None
