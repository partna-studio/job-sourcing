import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
from utils.web import generate_keyword_urls, fetch_website
from bs4 import BeautifulSoup
import pandas as pd
import json
import requests
import aiohttp
import nest_asyncio
import os
import tempfile
from tqdm import tqdm


def auto_concurrency(per_core_factor=10, cpu_util=0.8):
    """Estimate a sensible concurrency value from CPU cores.

    For network-bound scraping, we allow a multiple of logical cores.
    Example: 8 cores * 10 * 0.8 => 64 concurrent workers
    """
    try:
        cores = os.cpu_count() or 4
    except Exception:
        cores = 4
    return max(5, int(cores * per_core_factor * cpu_util))



def fetch_jobs(df, endpoint):
    """Synchronous wrapper around async_fetch_jobs with sensible defaults.

    This will run an asyncio event loop and return (all_jobs, failed_keywords).
    """
    try:
        return asyncio.run(async_fetch_jobs(df, endpoint))
    except RuntimeError:
        # Likely called from a running event loop (e.g., notebook). Patch and run.
        loop = asyncio.get_event_loop()
        nest_asyncio.apply(loop)
        return loop.run_until_complete(async_fetch_jobs(df, endpoint))


async def async_fetch_jobs(df, endpoint, concurrency=None, delay=0.2, max_retries=3):
    all_jobs = []
    failed_keywords = []

    if concurrency is None:
        concurrency = auto_concurrency()

    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency)

    async def post_for_row(session, row):
        #.write(f"Fetching jobs for keyword: {row.keyword}")
        query_options = {
            'keyword': row.keyword,
            'location': row.location,
            'dateSincePosted': 'past Week',
            'jobType': row.job_type,
            'remoteFilter': row.remote,
            'limit': '10',
            'page': '0'
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        for attempt in range(1, max_retries + 1):
            try:
                async with semaphore:
                    async with session.post(endpoint, json=query_options, headers=headers, timeout=30) as resp:
                        text = await resp.text()
                        if resp.status != 200:
                            raise Exception(f"HTTP {resp.status}: {text}")
                        data = json.loads(text)
                        if data.get('success'):
                            jobs = data.get('data', [])
                            #tqdm.write(f"  ✓ Found {len(jobs)} jobs for {row.keyword}")
                            return ('success', jobs, row.keyword)
                        else:
                            tqdm.write(f"  ✗ API error for {row.keyword}: {data.get('error')}")
                            return ('api_error', data.get('error'), row.keyword)

            except aiohttp.ClientConnectionError:
                tqdm.write(f"  ✗ Connection error for {row.keyword}, attempt {attempt}")
            except Exception as e:
                tqdm.write(f"  ✗ Error for {row.keyword}, attempt {attempt}: {e}")

            # exponential backoff
            await asyncio.sleep(delay * attempt)

        return ('failed', None, row.keyword)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(post_for_row(session, row)) for row in df.itertuples()]
        pbar = tqdm(total=len(tasks), desc="fetch_jobs", unit="req")
        for fut in asyncio.as_completed(tasks):
            status, payload, keyword = await fut
            if status == 'success':
                all_jobs.extend(payload)
            else:
                failed_keywords.append(keyword)
            pbar.update(1)
        pbar.close()

    return all_jobs, failed_keywords

def roles_db(df_loaded, DEFAULT_LINKEDIN_SEARCH_PARAMS):
    
    keywords = df_loaded["keyword"].tolist()
    API_BASE_URL = 'https://stupendous-choux-58c6b9.netlify.app'
    
    JOBS_API_ENDPOINT = f'{API_BASE_URL}/.netlify/functions/jobs'
    tqdm.write(f"Jobs API endpoint: {JOBS_API_ENDPOINT}")
    combined_df = generate_keyword_urls(keywords, DEFAULT_LINKEDIN_SEARCH_PARAMS)
    combined_df = combined_df.merge(
        df_loaded[["keyword", "category"]], 
        on="keyword", 
        how="left"
    )

    all_jobs, failed_keywords = fetch_jobs(combined_df, JOBS_API_ENDPOINT)
    tqdm.write(f"Here are a list of failed keywords: {failed_keywords}")
    return all_jobs

def parse_job(job_content):
    soup = BeautifulSoup(job_content,"html.parser") 
    type2find = "application/ld+json"
    container = soup.find("script", type=type2find)

    if container and container.string:
        data = json.loads(container.string)
        return data
    else:
        tqdm.write("Script tag not found")

async def fetch_metadata(all_jobs, concurrency=None, output_path='data/jobs_data.json', write_every=10):
    jobs_df = pd.DataFrame(all_jobs)
    tqdm.write(f"Total jobs fetched: {len(jobs_df)}")
    if jobs_df.empty:
        return jobs_df

    if concurrency is None:
        concurrency = auto_concurrency()

    semaphore = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()

    # Helper to atomically write the current DataFrame to JSON using a thread executor
    async def atomic_write_json(df, path='jobs_data.json'):
        loop = asyncio.get_event_loop()
        def _write():
            dirpath = os.path.dirname(path) or '.'
            os.makedirs(dirpath, exist_ok=True)
            tmp_fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix='jobs_data_', suffix='.json')
            os.close(tmp_fd)
            try:
                df.to_json(tmp_path, orient='records', indent=4)
                os.replace(tmp_path, path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        await loop.run_in_executor(None, _write)

    async def process_row(index, row):
        job_url = row["jobUrl"]
        #tqdm.write(f"Processing job {index + 1}/{len(jobs_df)}: {job_url}")
        try:
            async with semaphore:
                job_content = await fetch_website(job_url)
            job_data = parse_job(job_content)
            # After processing this job, update the persistent JSON file.
            # Use a lock to avoid concurrent writes and perform the write in an executor.
            async with write_lock:
                # create a shallow copy of DataFrame and assign current metadata snapshot
                snapshot = jobs_df.copy()
                # we expect metadata_list to be maintained outside; fill with None initially
                return job_data
        except Exception as e:
            tqdm.write(f"Error processing {job_url}: {e}")
            return None

    # Maintain a shared metadata list to persist progress incrementally
    metadata_list = [None] * len(jobs_df)

    async def wrapped_process(i, row):
        result = await process_row(i, row)
        metadata_list[i] = result
        # write snapshot periodically to avoid excessive I/O
        completed = sum(1 for v in metadata_list if v is not None)
        if (completed % write_every) == 0 or completed == len(metadata_list):
            async with write_lock:
                snapshot_df = jobs_df.copy()
                snapshot_df['metadata'] = metadata_list
                await atomic_write_json(snapshot_df, path=output_path)
        return result

    tasks = [asyncio.create_task(wrapped_process(i, row)) for i, (_, row) in enumerate(jobs_df.iterrows())]
    pbar = tqdm(total=len(tasks), desc="fetch_metadata", unit="job")
    for fut in asyncio.as_completed(tasks):
        await fut
        pbar.update(1)
    pbar.close()

    jobs_df['metadata'] = metadata_list
    # ensure final atomic write of complete DataFrame
    try:
        await atomic_write_json(jobs_df, path=output_path)
    except Exception:
        tqdm.write(f"Warning: failed final write to {output_path}")

    tqdm.write("All job data processed successfully.")
    return jobs_df


def save_jobs_metadata(all_jobs, output_path='data/jobs_data.json', concurrency=56):
    """Synchronous wrapper to run fetch_metadata and ensure the JSON is written.

    Returns the final DataFrame.
    """
    try:
        return asyncio.run(fetch_metadata(all_jobs, concurrency=concurrency, output_path=output_path))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        nest_asyncio.apply(loop)
        return loop.run_until_complete(fetch_metadata(all_jobs, concurrency=concurrency, output_path=output_path))

# Usage:
# jobs, failed = fetch_jobs_from_df(combined_df, JOBS_API_ENDPOINT)