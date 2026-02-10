
from pathlib import Path
from dotenv import load_dotenv
# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from digistudio.crawlers.linkedin import batch_urls, save_metadata, fetch_jobs
from digistudio.processing.jobs import process_jobs, categorize_jobs 
from digistudio.processing.upload import load_collection, upload_dataframe
from digistudio.processing.documents import docx_markdown
from pathlib import Path
import nest_asyncio
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

def job_sourcing_pipeline(keywords_full, minimum_yearly_salary, job_experience_threshold_years, resume_path):
    resume = docx_markdown(resume_path)
    DEFAULT_LINKEDIN_SEARCH_PARAMS = { "location": ["New York City", "Washington DC", "Los Angeles"], "experience_level": ["Entry level", "Associate", "Mid-Senior level"], "remote": ["Remote", "Hybrid", "On-Site"], "job_type": ["Full-time", "Contract"], "easy_apply": ["", "true"] }
    API_BASE_URL = 'https://stupendous-choux-58c6b9.netlify.app/.netlify/functions/jobs'

    all_jobs = batch_urls(keywords_full, DEFAULT_LINKEDIN_SEARCH_PARAMS)
    upload_dataframe(all_jobs, "jobs-full")
    data, failed = fetch_jobs(all_jobs, API_BASE_URL)
    data = save_metadata(data)
    data = load_collection("jobs")
    jobs = process_jobs(data, minimum_yearly_salary, job_experience_threshold_years, resume)
    output = categorize_jobs(jobs)
    upload_dataframe(output, "jobs-display")
    return output

app = Flask(__name__)
CORS(app)

def run_pipeline(data):
    keywords_full = data.get('keywords', [])
    minimum_yearly_salary = data.get('min_salary', 0)
    job_experience_threshold_years = data.get('experience', 0)
    resume_path = data.get('resume_path', '')

    print("Starting pipeline...")
    try:
        job_sourcing_pipeline(keywords_full, minimum_yearly_salary, job_experience_threshold_years, resume_path)
        print("Pipeline finished successfully.")
    except Exception as e:
        print(f"Pipeline failed: {e}")

@app.route('/api/jobs', methods=['POST'])
def jobs_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    thread = threading.Thread(target=run_pipeline, args=(data,))
    thread.start()
    
    return jsonify({"status": "processing_started"}), 202

if __name__ == '__main__':
    app.run(debug=True, port=5000)