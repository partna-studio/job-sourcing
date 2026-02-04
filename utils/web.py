import asyncio
import sys
import urllib.parse
import itertools
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

async def scrape_website(url, timeout=10000, use_playwright=False):
    """
    Scrape content from a website using BeautifulSoup (via requests).
    Playwright has been removed as a workaround for Windows loop issues.

    Args:
        url (str): The URL to scrape
        timeout (int): Timeout in milliseconds (default: 10000)
        use_playwright (bool): Ignored (kept for backward compatibility)

    Returns:
        str: The scraped content as HTML/text
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Use requests in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.get(url, headers=headers, timeout=timeout/1000, allow_redirects=True)
        )
        response.raise_for_status()
        
        # If the user specifically wants text via BS4, we could parse here, 
        # but usually returning HTML is expected for the downstream "processor".
        return response.text
        
    except Exception as e:
        raise Exception(f"Error scraping {url}: {str(e)}")

def generate_linkedin_uri(keyword="", location="", experience_level="", remote="", job_type="", easy_apply=""):
    """
    Generate a LinkedIn job search URL based on the provided parameters.
    """
    url = "https://www.linkedin.com/jobs/search/?f_TPR=r86400"

    if keyword:
        url += f"&keywords={urllib.parse.quote(keyword)}"
    if location:
        url += f"&location={urllib.parse.quote(location)}"

    if experience_level:
        transformed = []
        mapping = {
            "Internship": "1", "Entry level": "2", "Associate": "3",
            "Mid-Senior level": "4", "Director": "5", "Executive": "6"
        }
        for exp in experience_level.split(","):
            exp = exp.strip()
            if exp in mapping:
                transformed.append(mapping[exp])
        if transformed:
            url += f"&f_E={','.join(transformed)}"

    if remote:
        transformed = []
        mapping = {"Remote": "2", "Hybrid": "3", "On-Site": "1"}
        for r in remote.split(","):
            r = r.strip()
            if r in mapping:
                transformed.append(mapping[r])
        if transformed:
            url += f"&f_WT={','.join(transformed)}"

    if job_type:
        transformed = [jt.strip()[0].upper() for jt in job_type.split(",") if jt.strip()]
        if transformed:
            url += f"&f_JT={','.join(transformed)}"

    if easy_apply:
        url += "&f_EA=true"

    return url

def generate_all_linkedin_urls(keyword):
    """
    Generate all possible LinkedIn job search URLs for a given keyword.
    """
    locations = ["New York", "Atlanta", "Washington DC", "Los Angeles", "Chicago"]
    experience_levels = ["Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"]
    remotes = ["Remote", "Hybrid", "On-Site"]
    job_types = ["Full-time", "Part-time", "Contract"]
    easy_applies = ["", "true"]

    combos = list(itertools.product(locations, experience_levels, remotes, job_types, easy_applies))
    data = []
    for loc, exp, rem, jt, ea in combos:
        url = generate_linkedin_uri(keyword, loc, exp, rem, jt, ea)
        data.append({
            'keyword': keyword, 'location': loc, 'experience_level': exp,
            'remote': rem, 'job_type': jt, 'easy_apply': ea, 'url': url
        })
    return pd.DataFrame(data)

def generate_all_urls_for_keywords(keywords):
    """
    Generate LinkedIn URLs for multiple keywords.
    """
    dfs = [generate_all_linkedin_urls(kw) for kw in keywords]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

if __name__ == "__main__":
    async def main():
        content = await scrape_website("https://example.com")
        print(content[:100])
    asyncio.run(main())
