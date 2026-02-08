import math 

def job_filter_algo(data, minimum_yearly_salary, job_experience_threshold_years):
    racks = len(data)
    hourly_equivalent = round(minimum_yearly_salary / 2080)
    job_experience_threshold = math.floor(job_experience_threshold_years * 12 * 1.125)
    counter = with_salary = with_experience = 0
    jobs = []
    for item in data:
        metadata = item.get('metadata', {})
        base_salary = metadata.get('baseSalary', {})
        exp_reqs = metadata.get('experienceRequirements', {})

        # 1. Early Exit: Skip if essential data is missing
        if not base_salary or not exp_reqs:
            continue

        counter += 1
        
        # Extract values
        quant_value = base_salary.get('value', {})
        min_val = quant_value.get('minValue')
        max_val = quant_value.get('maxValue')
        avg_val = min_val + max_val / 2 if min_val and max_val else None
        unit = quant_value.get('unitText')
        try:
            months = exp_reqs.get('monthsOfExperience')
        except:
            months = 60

        # 2. Normalize Salary Check
        is_valid_salary = False
        if unit == 'YEAR' and avg_val and avg_val >= minimum_yearly_salary:
            is_valid_salary = True
        elif unit == 'HOUR' and avg_val and avg_val >= hourly_equivalent:
            is_valid_salary = True

        if not is_valid_salary:
            continue
        
        # 3. Process valid salary matches
        with_salary += 1
        
        # Check experience
        if months and months <= job_experience_threshold:
            with_experience += 1
            jobs.append(item)
    print(f"""    --------------- ALGORITHM STATISTICS -------------
    Experience Match Rate: {with_experience / with_salary:.2%} 
    (Filtered {with_experience} out of {with_salary} salary-matching jobs)

    Salary Match Rate: {with_salary / racks:.2%} 
    (Filtered {with_salary} out of {racks} total jobs)

    Filtered Jobs: {with_experience / racks:.2%} 
    (Filtered {with_experience} out of {racks} total jobs)
    --------------------------------------------------
    Total Jobs Processed: {racks} --- Total Jobs Matched: {with_experience}
    """.format(with_experience=with_experience, with_salary=with_salary, racks=racks))
    return jobs