
from pathlib import Path
from dotenv import load_dotenv
# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)
import json
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
import uuid



def batch_and_fetch (keywords, params, uri):
    all_jobs = batch_urls(keywords, params)
    upload_dataframe(all_jobs, "jobs-full")
    data, failed = fetch_jobs(all_jobs, uri)
    return data

def upload_metadata(data):
    data = save_metadata(data) #add collection_name as parameter
    upload_dataframe(data, "jobs-metadata")
    return data

def upload_jobs(data,minimum_yearly_salary, job_experience_threshold_years, resume):
    jobs = process_jobs(data, minimum_yearly_salary, job_experience_threshold_years, resume)
    output = categorize_jobs(jobs)
    upload_dataframe(output, "jobs-display")
    return output

def job_sourcing_pipeline(keywords_full, minimum_yearly_salary, job_experience_threshold_years, resume_path):
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

    data = batch_and_fetch(keywords_full, PARAMS, URI)
    data = upload_metadata(data)
    data = load_collection("jobs-metadata")
    output = upload_jobs(data, minimum_yearly_salary, job_experience_threshold_years, resume)
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
        result = job_sourcing_pipeline(keywords_full, minimum_yearly_salary, job_experience_threshold_years, resume_path)
        print("Pipeline finished successfully.")
        return result
    except Exception as e:
        print(f"Pipeline failed: {e}")


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

    keywords_df = pd.read_csv("job-sourcing/other/text/keywords.csv")
    keywords_full = keywords_df['keyword'].tolist()[0:7]

    job_experience_threshold_years = 4.5
    minimum_yearly_salary = 96000
    resume_path = "job-sourcing/other/text/resume.docx"
    url = "http://localhost:5000/api/jobs/"
    payload = {
    "keywords": keywords_full,
    "min_salary": minimum_yearly_salary,
    "experience": job_experience_threshold_years,
    "resume_path": resume_path
    }
    job_sourcing_pipeline(keywords_full, minimum_yearly_salary, job_experience_threshold_years, resume_path)
    #app.run(debug=True, port=5000)