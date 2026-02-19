import pandas as pd

def transform_jobs(jobs_dict):
    """
    Transform a nested dictionary with 'high', 'med', 'low' keys into a DataFrame
    with a 'Compatibility' column, flattening metadata and stats into individual columns.
    
    Args:
        jobs_dict: Dictionary with keys 'high', 'med', 'low', each containing a list of job objects
        
    Returns:
        pandas.DataFrame: DataFrame with all job data flattened into columns including metadata and stats
    """
    flattened_jobs = []
    
    # Process each compatibility level
    for compatibility, jobs in jobs_dict.items():
        if compatibility == "_id":
            continue 
        for job in jobs:
            # Create a flat dictionary for this job
            flat_job = {}
            
            # Add top-level job fields
            flat_job['Compatibility'] = compatibility
            flat_job['position'] = job.get('position')
            flat_job['company'] = job.get('company')
            flat_job['location'] = job.get('location')
            flat_job['date'] = job.get('date')
            flat_job['salary'] = job.get('salary')
            flat_job['jobUrl'] = job.get('jobUrl')
            flat_job['companyLogo'] = job.get('companyLogo')
            flat_job['agoTime'] = job.get('agoTime')
            
            # Flatten metadata.general_info
            if 'metadata' in job and 'general_info' in job['metadata']:
                general_info = job['metadata']['general_info']
                flat_job['datePosted'] = general_info.get('datePosted')
                flat_job['employmentTitle'] = general_info.get('employmentTitle')
                flat_job['employmentType'] = general_info.get('employmentType')
                flat_job['description'] = general_info.get('description')
                flat_job['validThrough'] = general_info.get('validThrough')
            
            # Flatten metadata.company_info
            if 'metadata' in job and 'company_info' in job['metadata']:
                company_info = job['metadata']['company_info']
                flat_job['hiringOrganization'] = company_info.get('hiringOrganization')
                flat_job['industry'] = company_info.get('industry')
                flat_job['addressCountry'] = company_info.get('addressCountry')
                flat_job['addressLocality'] = company_info.get('addressLocality')
            
            # Flatten metadata.job_requirements
            if 'metadata' in job and 'job_requirements' in job['metadata']:
                job_requirements = job['metadata']['job_requirements']
                flat_job['skills'] = job_requirements.get('skills')
                flat_job['credentialCategory'] = job_requirements.get('credentialCategory')
                flat_job['monthsOfExperience'] = job_requirements.get('monthsOfExperience')
            
            # Flatten metadata.salary_info
            if 'metadata' in job and 'salary_info' in job['metadata']:
                salary_info = job['metadata']['salary_info']
                flat_job['currency'] = salary_info.get('currency')
                flat_job['minValue'] = salary_info.get('minValue')
                flat_job['maxValue'] = salary_info.get('maxValue')
                flat_job['unitText'] = salary_info.get('unitText')
            
            # Flatten stats
            if 'stats' in job:
                stats = job['stats']
                flat_job['score'] = stats.get('score')
                flat_job['rationale'] = stats.get('rationale')
            
            flattened_jobs.append(flat_job)
    
    # Convert to DataFrame
    return pd.DataFrame(flattened_jobs)