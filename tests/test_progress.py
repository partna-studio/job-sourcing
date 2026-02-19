from digistudio.crawlers.linkedin import batch_urls, save_metadata
from digistudio.processing.jobs import process_jobs, categorize_jobs 
from digistudio.processing.upload import load_collection, upload_dataframe
from digistudio.processing.documents import docx_markdown
import pandas as pd



keywords_df = pd.read_csv("other/text/keywords.csv")
keywords_full = keywords_df['keyword'].tolist()

job_experience_threshold_years = 4.5
minimum_yearly_salary = 96000
resume_path = "other/text/resume.docx"

PARAMS = { 
    "location": ["New York City"], 
    "experience_level": ["Entry level"], 
    "remote": ["Remote"], 
    "job_type": ["Full-time"], 
    "easy_apply": [""]
}
URI = 'https://stupendous-choux-58c6b9.netlify.app/.netlify/functions/jobs'

# Step 1: Generate URLs
all_jobs = batch_urls(keywords_full, PARAMS)
print(f"Generated {len(all_jobs)} job URLs")

# Step 2: Fetch job data
data, failed = fetch_jobs(all_jobs, URI)
print(f"Fetched {len(data)} jobs, {len(failed)} failed")

# Step 3: Save metadata (this will show the progress bars)
data = save_metadata(data)
print("Metadata saved successfully")
