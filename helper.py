import os
import logging
from pathlib import Path
from dotenv import load_dotenv
# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from digistudio.crawlers.linkedin import batch_urls, save_metadata, fetch_jobs
from digistudio.processing.jobs import process_jobs, categorize_jobs 
from digistudio.processing.upload import upload_collection
from digistudio.processing.connections import check_ideal_status, get_user
from digistudio.processing.documents import docx_markdown
from digistudio.integrations.firebase import get_firebase_client
from datetime import timedelta, datetime as dt
from pathlib import Path
from typing import Union
import pandas as pd


LI_TOKEN = os.getenv('LI_TOKEN')
JSESSION_ID = os.getenv('JSESSION_ID')

client = get_firebase_client()

logger = logging.getLogger(__name__)

def batch_and_fetch (urn, keywords, params, uri, job_limit):
    all_jobs = batch_urls(keywords, params, job_limit)
    data_entry = {"id": urn, "jobs": all_jobs, "time": dt.now().isoformat()}
    upload_collection(data_entry, "jobs-urls", 'jobs', user_id=urn)
    data, failed = fetch_jobs(all_jobs, uri)
    #data = data[0:2]
    return data

def upload_metadata(urn, data):
    data = save_metadata(data) #add collection_name as parameter
    data_entry = {"id": urn, "jobs": data, "time": dt.now().isoformat()}
    upload_collection(data_entry, "jobs-metadata", 'jobs', user_id=urn)
    return data

def upload_jobs(urn, data,minimum_yearly_salary, job_experience_threshold_years, resume):
    jobs, statsistics = process_jobs(data, minimum_yearly_salary, job_experience_threshold_years, resume)
    data_entry = {"id": urn, "stats": statsistics, "time": dt.now().isoformat()}
    upload_collection(data_entry, 'job-board', keyword='stats', compare_stats=True, user_id=urn)
    jobs = check_ideal_status(jobs, urn)
    output = categorize_jobs(jobs)
    data_entry = {"id": urn, "stats": output, "time": dt.now().isoformat()}
    upload_collection(data_entry, "jobs-display", keyword='stats', user_id=urn)
    return output

def get_resume_from_firestore(urn: str) -> Union[str, bytes]:
    """
    Fetch resume data from Firestore.
    If resume_data exists in user document, return bytes.
    Otherwise, return path to fallback resume.docx.
    """
    
    user_doc = client.find("users", {"urn": urn}, limit=1)
    
    if user_doc and len(user_doc) > 0:
        user_data = user_doc[0]
        if "resume_data" in user_data and isinstance(user_data["resume_data"], bytes):
            return user_data["resume_data"]
    
    # Fallback to local resume if not found in Firestore
    return "./other/text/resume.docx"

def job_sourcing_pipeline(user):
    
    keywords_full = user['payload']['keywords']
    urn = user['urn']

    try:
        minimum_yearly_salary = user['payload'].get('minimum_yearly_salary', 0)
        job_experience_threshold_years = user['payload'].get('job_experience_threshold_years', 0)
        job_limit = user['payload'].get('job_limit', 10)
    except (ValueError, TypeError) as e:
        logger.exception("Error casting payload values from user %s", urn)
        # Handle error or set defaults
        minimum_yearly_salary = 0
        job_experience_threshold_years = 0
        job_limit = 10
    
    # Fetch resume (either bytes or file path)
    resume = docx_markdown(get_resume_from_firestore(urn))
    
    # Extract search_params from user payload (now under 'search_params' key)
    PARAMS = user['payload'].get('search_params', { 
        "location": ["New York City"],  # Reduced from 3 to 1
        "experience_level": ["Entry level", "Mid-Senior level"],  # Reduced from 3 to 2
        "remote": ["Remote" ,"Hybrid", "On Site"],  # Reduced from 3 to 1
        "job_type": ["Full-time"],  # Reduced from 2 to 1
        "easy_apply": [""]  # Removed easy_apply for now
    })
    
    URI = 'https://stupendous-choux-58c6b9.netlify.app/.netlify/functions/jobs'

    data = batch_and_fetch(urn, keywords_full, PARAMS, URI, job_limit)
    data = upload_metadata(urn, data)
    #data = load_collection("jobs-metadata")
    output = upload_jobs(urn, data, minimum_yearly_salary, job_experience_threshold_years, resume)
    return output


def get_cached_jobs_from_firestore(urn: str):
    """
    Fetch cached job results from 'jobs-display' collection if within 7 days.
    Returns: dict (the 'stats' field) or None if not found or expired.
    """
    docs = client.find("jobs-display", {"id": urn}, limit=1)
    
    if not docs or len(docs) == 0:
        logger.debug("No cached job document found for urn %s", urn)
        return None
    
    doc = docs[0]
    time_str = doc.get("time")
    if not time_str:
        return None
    
    try:
        last_run = dt.fromisoformat(time_str)
        if dt.now() - last_run < timedelta(days=1):
            logger.info("Returning cached results for urn %s (age %s)", urn, dt.now() - last_run)
            return doc.get("stats")  # Return cached results
        else:
            logger.debug("Cache expired for urn %s (age %s)", urn, dt.now() - last_run)
    except ValueError:
        logger.warning("Invalid timestamp in cache for urn %s: %s", urn, time_str)
        # Invalid timestamp → treat as expired
    
    return None  # Expired or invalid

def _process_single_user(user_doc, uri_override=None):
    """Run the sourcing pipeline steps for a single user document without LinkedIn re-auth.

    This mirrors `job_sourcing_pipeline` but skips the `get_user` URN check so it can
    be invoked for arbitrary user documents from Firestore.
    """
    urn = user_doc.get('urn')
    logger.info("_process_single_user started for urn %s", urn)
    try:
        payload = user_doc.get('payload', {})
        params = payload.get('search_params', {})

        # Extract params and apply fallbacks similar to run_pipeline
        keywords_full = params.get('keywords')
        minimum_yearly_salary = params.get('min_salary')
        job_experience_threshold_years = params.get('experience')
        job_limit = params.get('job_limit')

        if not keywords_full:
            try:
                keywords_df = pd.read_csv("job-sourcing/other/text/keywords.csv")
                keywords_full = keywords_df['keyword'].tolist()[0:7]
            except Exception:
                keywords_full = []

        if minimum_yearly_salary is None or minimum_yearly_salary == 0:
            minimum_yearly_salary = 96000
        if job_experience_threshold_years is None or job_experience_threshold_years == 0:
            job_experience_threshold_years = 4.5
        if job_limit is None or job_limit == 0:
            job_limit = 12

        # Ensure PARAMS structure contains expected keys (fallback to defaults used elsewhere)
        PARAMS = params or {
            "location": ["New York City"],
            "experience_level": ["Entry level", "Mid-Senior level"],
            "remote": ["Remote", "Hybrid", "On Site"],
            "job_type": ["Full-time"],
            "easy_apply": [""]
        }

        URI = uri_override or 'https://stupendous-choux-58c6b9.netlify.app/.netlify/functions/jobs'

        # Run the core pipeline steps (without LinkedIn auth/URN validation)
        data = batch_and_fetch(urn, keywords_full, PARAMS, URI, job_limit)
        data = upload_metadata(urn, data)
        resume = docx_markdown(get_resume_from_firestore(urn))
        output = upload_jobs(urn, data, minimum_yearly_salary, job_experience_threshold_years, resume)

        return {"urn": urn, "status": "completed", "result_count": len(output) if isinstance(output, list) else None}
    except Exception as e:
        logger.exception("_process_single_user failed for urn %s", user_doc.get('urn'))
        return {"urn": user_doc.get('urn'), "status": "error", "error": str(e)}

def run_pipeline(user):
    # Extract user auth tokens
   
    
    # Extract pipeline parameters from Firestore user payload
    
    user_data = user
    urn = user['urn']
    logger.info("Extracting pipeline parameters from user:", user_data)
    payload = user_data.get('payload', {})
    
    # Parameters now live under 'search_params' key in payload
    params = payload.get('search_params', {})
    keywords_full = params.get('keywords')
    minimum_yearly_salary = params.get('min_salary')
    job_experience_threshold_years = params.get('experience')
    job_limit = params.get('job_limit')

    # ------------------------------------------------------------------
    # apply fallback defaults similar to the debug entrypoint at bottom
    # ------------------------------------------------------------------
    # load keyword list from csv if none provided
    if not keywords_full:
        try:
            keywords_df = pd.read_csv("job-sourcing/other/text/keywords.csv")
            keywords_full = keywords_df['keyword'].tolist()[0:7]
        except Exception:
            keywords_full = []  # still allow pipeline to run with empty list

    # default salary/exposure values if not supplied or zero-ish
    if minimum_yearly_salary is None or minimum_yearly_salary == 0:
        minimum_yearly_salary = 96000
    if job_experience_threshold_years is None or job_experience_threshold_years == 0:
        job_experience_threshold_years = 4.5
    if job_limit is None or job_limit == 0:
        job_limit = 12

    # Starting pipeline with parameters: keywords_count={len(keywords_full)}, min_salary={minimum_yearly_salary}, experience_threshold={job_experience_threshold_years}, urn={urn}
    # Pipeline will process jobs through: batch_and_fetch -> upload_metadata -> upload_jobs
    try:
        result = job_sourcing_pipeline(user)
        logger.info("job_sourcing_pipeline succeeded for urn %s, returned %s items", urn, len(result) if isinstance(result, list) else 'unknown')
        return result
    except Exception as e:
        logger.exception("job_sourcing_pipeline failed -- keywords_count=%s min_salary=%s experience_threshold=%s urn=%s", 
                         len(keywords_full), minimum_yearly_salary, job_experience_threshold_years, urn)
        raise


if __name__ == '__main__':
    import pandas as pd
    import requests
    import json

    # DEBUG: This block runs when script is executed directly (not via Flask)
    keywords_df = pd.read_csv("./other/text/keywords.csv")
    keywords_full = keywords_df['keyword'].tolist()[0:7]
    job_experience_threshold_years = 4.5
    minimum_yearly_salary = 96000
    job_limit = 12

    # Get user to extract URN (same as API flow)
    user = get_user(LI_TOKEN, JSESSION_ID)
    urn = user['urn']


    payload = user.get('payload', {})
    
    # Parameters now live under 'search_params' key in payload
    params = payload.get('search_params', {})
    keywords_full = params.get('keywords', keywords_full)  # fallback to debug value if missing
    minimum_yearly_salary = params.get('min_salary', minimum_yearly_salary)
    job_experience_threshold_years = params.get('experience', job_experience_threshold_years)
    job_limit = params.get('job_limit', job_limit)

    # Run pipeline using URN and fallback resume if needed
    job_sourcing_pipeline(user)