
import os
from pathlib import Path
from dotenv import load_dotenv
# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)
import json
from digistudio.crawlers.linkedin import batch_urls, save_metadata, fetch_jobs
from digistudio.processing.jobs import process_jobs, categorize_jobs 
from digistudio.processing.upload import upload_collection
from digistudio.processing.connections import check_ideal_status, get_user
from digistudio.processing.documents import docx_markdown
from datetime import datetime as dt
from pathlib import Path
import nest_asyncio
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import uuid

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

def job_sourcing_pipeline(keywords_full, minimum_yearly_salary, job_experience_threshold_years, resume_path, job_limit):
    # Derive URN dynamically from LinkedIn auth tokens in .env
    user = get_user(os.getenv('LI_TOKEN'), os.getenv('JSESSION_ID'))
    urn = user['urn']

    resume = docx_markdown(resume_path)
    # Reduced parameters to avoid combinatorial explosion
    PARAMS = { 
        "location": ["New York City"],  # Reduced from 3 to 1
        "experience_level": ["Entry level", "Mid-Senior level"],  # Reduced from 3 to 2
        "remote": ["Remote" ,"Hybrid", "On Site"],  # Reduced from 3 to 1
        "job_type": ["Full-time"],  # Reduced from 2 to 1
        "easy_apply": [""]  # Removed easy_apply for now
    }
    URI = 'https://stupendous-choux-58c6b9.netlify.app/.netlify/functions/jobs'

    data = batch_and_fetch(urn, keywords_full, PARAMS, URI, job_limit)
    data = upload_metadata(urn, data)
    #data = load_collection("jobs-metadata")
    output = upload_jobs(urn, data, minimum_yearly_salary, job_experience_threshold_years, resume)
    return output


app = Flask(__name__)
CORS(app)

def run_pipeline(data):
    keywords_full = data.get('keywords', [])
    minimum_yearly_salary = data.get('min_salary', 0)
    job_experience_threshold_years = data.get('experience', 0)
    resume_path = data.get('resume_path', '')
    job_limit = data.get('job_limit', 10)

    # Starting pipeline with parameters: keywords_count={len(keywords_full)}, min_salary={minimum_yearly_salary}, experience_threshold={job_experience_threshold_years}, resume_path={resume_path}
    # Pipeline will process jobs through: batch_and_fetch -> upload_metadata -> upload_jobs
    try:
        result = job_sourcing_pipeline(keywords_full, minimum_yearly_salary, job_experience_threshold_years, resume_path, job_limit)
        # Pipeline completed successfully. Result contains {len(result) if isinstance(result, list) else 'unknown'} categorized jobs
        return result
    except Exception as e:
        # Pipeline failed with error: {str(e)[:100]}... Check logs for full traceback. Parameters: keywords_count={len(keywords_full)}, min_salary={minimum_yearly_salary}, experience_threshold={job_experience_threshold_years}
        raise


@app.route('/api/jobs', methods=['POST'])
def jobs_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Create a dictionary to store results
    job_results = {}
    job_id = str(uuid.uuid4())

    def run_with_results():
        job_results[job_id] = run_pipeline(data)

    thread = threading.Thread(target=run_with_results)
    thread.daemon = True  # Make thread a daemon so it doesn't prevent program exit
    thread.start()

    # Return a placeholder resultendaited handling using a placeholder result
    return jsonify({"status": "processing_started", "result": job_results}), 202

if __name__ == '__main__':
    import pandas as pd
    import requests
    import json

    # DEBUG: This block runs when script is executed directly (not via Flask)
    keywords_df = pd.read_csv("job-sourcing/other/text/keywords.csv")
    keywords_full = keywords_df['keyword'].tolist()[0:7]
    job_experience_threshold_years = 4.5
    minimum_yearly_salary = 96000
    resume_path = "job-sourcing/other/text/resume.docx"
    job_limit = 12

    # URN is now resolved dynamically inside job_sourcing_pipeline via get_user()
    job_sourcing_pipeline(keywords_full, minimum_yearly_salary, job_experience_threshold_years, resume_path, job_limit)
    #app.run(debug=True, port=5000)
