import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
import requests
import pandas as pd



def fetch_jobs_from_df(df, endpoint):
    all_jobs = []
    failed_keywords = []

    for row in df.itertuples():
        try:
            print(f"Fetching jobs for keyword: {row.keyword}")
            
            query_options = {
                'keyword': row.keyword,
                'location': row.location,
                'dateSincePosted': 'past Week',
                'jobType': row.job_type,
                'remoteFilter': row.remote,
                'limit': '10',
                'page': '0'
            }
            
            response = requests.post(endpoint, json=query_options, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                jobs = data.get('data', [])
                all_jobs.extend(jobs)
                print(f"  ✓ Found {len(jobs)} jobs with added break incoming...")
                break
            else:
                print(f"  ✗ API error: {data.get('error')}")
                failed_keywords.append(row.keyword)
                
        except requests.exceptions.ConnectionError:
            print("  ✗ Connection error: Server unreachable.")
            break
        except Exception as e:
            print(f"  ✗ Error for {row.keyword}: {e}")
            failed_keywords.append(row.keyword)

    return all_jobs, failed_keywords

# Usage:
# jobs, failed = fetch_jobs_from_df(combined_df, JOBS_API_ENDPOINT)