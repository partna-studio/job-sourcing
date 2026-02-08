import mammoth
import json
from pathlib import Path
import html
from markdownify import markdownify as md
from utils.algo import job_filter_algo as algo
from utils.lchain import job_matching_agent


def docx2mark(file_path):
    """
    Read a .docx file and convert its content to Markdown format.
    
    Args:
        file_path (str): Path to the .docx file.
    
    Returns:
        str: The content of the document in Markdown format.
    """
    with open(file_path, "rb") as docx_file:
        result = mammoth.convert_to_markdown(docx_file)
        return result.value

def normalize(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if 'jobs' in data and isinstance(data['jobs'], list):
            return data['jobs']
        list_vals = [v for v in data.values() if isinstance(v, list)]
        return list_vals[0] if list_vals else [data]
    return [data]

def filter_jobs_data(input_path, output_path):
    src = Path(input_path)
    dst = Path(output_path)
    raw = src.read_text(encoding='utf-8')
    data = json.loads(raw)
    items = normalize(data)
    filtered = [it for it in items if it.get('metadata') is not None]
    dst.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(filtered)} items to {dst}')

#filter_jobs_data('ole_jobs_data.json', 'ole_jobs.json')

def get_nested_from_jobs_data(data, keys, default=None):
    """Safely navigates nested dictionaries."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return default
    return data if data is not None else default

def get_markdown_keys_from_jobs_data(data):
    raw_html = html.unescape(data.get('description'))
    description = md(raw_html, strip=['script', 'style'])

    general_info = {
        "datePosted":      data.get('datePosted'),
        "employmentTitle": data.get('title'),
        "employmentType":  data.get('employmentType'),
        "description":     description,
        "validThrough":    data.get('validThrough'),
    }

    company_info = {
        "hiringOrganization": get_nested_from_jobs_data(data, ['hiringOrganization', 'name']),
        "name":               data.get('name'),
        "industry":           data.get('industry'),
        "addressCountry":     get_nested_from_jobs_data(data, ['jobLocation', 'address', 'addressCountry']),
        "addressLocality":    get_nested_from_jobs_data(data, ['jobLocation', 'address', 'addressLocality']),
    }

    job_requirements = {
        "skills":             data.get('skills'),
        "credentialCategory": get_nested_from_jobs_data(data, ['educationRequirements', 'credentialCategory']),
        "monthsOfExperience": get_nested_from_jobs_data(data, ['experienceRequirements', 'monthsOfExperience']),
    }

    salary_info = {
        "currency":  get_nested_from_jobs_data(data, ['baseSalary', 'currency']),
        "minValue":  get_nested_from_jobs_data(data, ['baseSalary', 'value', 'minValue']),
        "maxValue":  get_nested_from_jobs_data(data, ['baseSalary', 'value', 'maxValue']),
        "unitText":  get_nested_from_jobs_data(data, ['baseSalary', 'value', 'unitText']),
    }
    
    entry = {
        "general_info":      general_info,
        "company_info":      company_info,
        "job_requirements":  job_requirements,
        "salary_info":       salary_info,
    }
    return entry

def get_cleaned_jobs_data(jobs):
    cleaned_jobs = []
    for job in jobs:
        m = job.get('metadata', {})
        entry = get_markdown_keys_from_jobs_data(m)
        cleaned_jobs.append(entry)
    return cleaned_jobs

def process_jobs(data, minimum_yearly_salary, job_experience_threshold_years, resume):
    jobs = algo(data, minimum_yearly_salary, job_experience_threshold_years)
    cleaned_jobs = get_cleaned_jobs_data(jobs)
    matched_jobs = job_matching_agent(cleaned_jobs, resume)
    return matched_jobs

def categorize_jobs(job_list):
    # Initialize our subgroups
    groups = {
        "high": [],
        "med": [],
        "low": []
    }

    for job in job_list:
        # Extract the score from the nested dictionary
        score = job.get('stats', {}).get('score', 0)
        info = job.get('general_info', {})
        salary = job.get('salary_info', {})
        title = info.get('employmentTitle', 'Unknown Role')

        # Logic for grouping
        if score >= 6:
            groups["high"].append(job)
        elif 4 <= score < 6:
            groups["med"].append(job)
        else:
            groups["low"].append(job)

    # Print totals and categories
    print("--- Job Matching Summary ---")
    for category, jobs in groups.items():
        print(f"{category}: {len(jobs)} jobs")

    return groups