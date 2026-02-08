import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


def _find_numeric_score(obj: Any, keys: Optional[set] = None) -> Optional[float]:
    if keys is None:
        keys = {"finalScore", "final_score", "finalJobScore", "final_job_score", "score", "finalScoreAvg"}

    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k in keys and isinstance(v, (int, float)):
                return float(v)
            res = _find_numeric_score(v, keys)
            if res is not None:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = _find_numeric_score(item, keys)
            if res is not None:
                return res
    return None


def _collect_skills(obj: Any, keys: Optional[set] = None) -> List[str]:
    if keys is None:
        keys = {"skills", "required_skills", "skillsRequired", "skills_list", "requirements"}

    skills = []

    def _normalize(item: Any) -> List[str]:
        if isinstance(item, list):
            return [str(x).strip() for x in item if x]
        if isinstance(item, str):
            parts = [p.strip() for p in item.split(",") if p.strip()]
            if len(parts) > 1:
                return parts
            # fallback split on semicolon or pipe
            parts2 = [p.strip() for p in item.replace(";", ",").replace("|", ",").split(",") if p.strip()]
            return parts2
        return []

    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k in keys:
                skills.extend(_normalize(v))
            else:
                skills.extend(_collect_skills(v, keys))
    elif isinstance(obj, list):
        for it in obj:
            skills.extend(_collect_skills(it, keys))

    return skills


def generate_job_matcher(input_path: str = "job-sourcing/filename.json", output_path: str = "job-sourcing/job_matcher.json", top_threshold: float = 80.0) -> Dict[str, Any]:
    """Read job data from `input_path`, compute simple metrics, and write a job_matcher JSON summary to `output_path`.

    The function attempts to find numeric final scores in each job record (searching common key names),
    computes totals and averages, and extracts top skills for the `Top Ranking Skills` visualization.
    """
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {p.resolve()}")

    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)

    # filter out empty / invalid records
    records = [r for r in data if isinstance(r, dict) and r]
    total_jobs = len(records)

    scores = []
    skills_counter = Counter()
    company_counter = Counter()
    experience_buckets = Counter()
    date_counter = Counter()

    for rec in records:
        sc = _find_numeric_score(rec)
        if sc is not None:
            scores.append(sc)

        skills = _collect_skills(rec)
        for s in skills:
            # normalize to title case small
            skills_counter[s.lower()] += 1

        # company name extraction (defensive)
        def _extract_company(r: dict) -> Optional[str]:
            if not isinstance(r, dict):
                return None
            # common containers
            for container in ("company_info", "company", "employer", "hiringOrganization"):
                c = r.get(container)
                if isinstance(c, dict):
                    for key in ("name", "companyName", "linkedinCompanyName", "organizationName"):
                        v = c.get(key)
                        if v:
                            return str(v).strip()
                elif isinstance(c, str) and c.strip():
                    return c.strip()
            # fallback top-level keys
            for key in ("companyName", "company", "employer", "organization"):
                v = r.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            return None

        comp = _extract_company(rec)
        if comp:
            company_counter[comp] += 1

        # experience extraction (months -> bucket)
        def _extract_months(r: dict) -> Optional[int]:
            if not isinstance(r, dict):
                return None
            # common path: job_requirements.monthsOfExperience
            jr = r.get("job_requirements")
            if isinstance(jr, dict):
                m = jr.get("monthsOfExperience")
                if isinstance(m, (int, float)):
                    return int(m)
            # fallback keys
            for key in ("monthsOfExperience", "experienceMonths", "experience_in_months"):
                v = r.get(key)
                if isinstance(v, (int, float)):
                    return int(v)
            # look for experienceLevel string
            for key in ("experienceLevel", "level"):
                v = r.get(key)
                if isinstance(v, str) and v.strip():
                    txt = v.lower()
                    if "junior" in txt or "entry" in txt:
                        return 12
                    if "senior" in txt:
                        return 72
            return None

        months = _extract_months(rec)
        if months is not None:
            if months < 24:
                experience_buckets["Junior"] += 1
            elif months < 60:
                experience_buckets["Middle"] += 1
            elif months < 120:
                experience_buckets["Senior"] += 1
            else:
                experience_buckets["Director"] += 1

        # publication date extraction
        def _extract_pub_date(r: dict) -> Optional[str]:
            if not isinstance(r, dict):
                return None
            gi = r.get("general_info")
            candidates = []
            if isinstance(gi, dict):
                for k, v in gi.items():
                    if isinstance(k, str) and ("date" in k.lower() or "posted" in k.lower() or "publication" in k.lower()):
                        candidates.append(v)
            # fallback top-level
            for key in ("datePosted", "publicationDate", "postedDate", "validThrough"):
                v = r.get(key)
                if v:
                    candidates.append(v)

            for v in candidates:
                if not isinstance(v, str):
                    continue
                txt = v.strip()
                if not txt:
                    continue
                # try ISO parse
                try:
                    dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
                    return dt.date().isoformat()
                except Exception:
                    # try chopping to YYYY-MM-DD
                    if len(txt) >= 10:
                        try:
                            return txt[:10]
                        except Exception:
                            continue
            return None

        d = _extract_pub_date(rec)
        if d:
            date_counter[d] += 1

    avg_score = float(sum(scores) / len(scores)) if scores else None
    top_scoring_count = sum(1 for s in scores if s >= top_threshold) if scores else 0

    top_skills = [k.title() for k, _ in skills_counter.most_common(10)]
    # prepare graph data
    open_roles_by_company = [{"company": k, "count": v} for k, v in company_counter.most_common()]
    openings_by_experience = [{"level": k, "count": v} for k, v in experience_buckets.items()]
    jobs_posted_per_day = [{"date": k, "count": v} for k, v in sorted(date_counter.items())]

    output = {
        "airtable_dashboard": {
            "summary_metrics": [
                {
                    "title": "Total Jobs Analyzed",
                    "calculation_logic": f"Count of all records pulled = {total_jobs}",
                    "value": total_jobs,
                    "needs_automation": False,
                    "timestamp_ref": "generated"
                },
                {
                    "title": "Average Final Job Score",
                    "calculation_logic": "Mean of detected final score values",
                    "value": avg_score,
                    "needs_automation": False,
                    "timestamp_ref": "generated"
                },
                {
                    "title": "Top Scoring Jobs",
                    "calculation_logic": f"Count of jobs with score >= {top_threshold}",
                    "value": top_scoring_count,
                    "needs_automation": False,
                    "timestamp_ref": "generated"
                }
            ],
            "visualizations": [
                {
                    "graph_title": "Open Roles by Company",
                    "graph_type": "Bar Chart",
                    "axes": {"x_axis": "Company Name", "y_axis": "Count of Job IDs"},
                    "needs_automation": False,
                    "timestamp_ref": "generated",
                    "data": open_roles_by_company
                },
                {
                    "graph_title": "Openings by Experience Level",
                    "graph_type": "Bar or Pie Chart",
                    "parameters": ["Junior", "Middle", "Senior", "Director"],
                    "needs_automation": True,
                    "timestamp_ref": "generated",
                    "data": openings_by_experience
                },
                {
                    "graph_title": "Jobs Posted per Day",
                    "graph_type": "Timeline",
                    "axes": {"x_axis": "Publication Date", "y_axis": "Count of Records"},
                    "needs_automation": True,
                    "timestamp_ref": "generated",
                    "data": jobs_posted_per_day
                },
                {
                    "graph_title": "Top Ranking Skills",
                    "graph_type": "Word Cloud",
                    "parameters": top_skills,
                    "needs_automation": True,
                    "timestamp_ref": "generated",
                    "data": [{"skill": k.title(), "count": v} for k, v in skills_counter.most_common(20)]
                }
            ],
            "data_table_schema": {
                "metadata_fields": ["Job ID", "Publication Date", "LinkedIn Company Name", "Job Title", "Job Link"],
                "categorization_fields": ["Experience Level", "Required Skills", "Responsibilities", "Company Benefits"],
                "scoring_fields_0_100": ["Skills Score", "Responsibilities Score", "Experience Score", "Benefits Score"],
                "final_output_fields": ["Final Job Score (weighted average)", "Remote/Flexible Work status"],
                "data_source_pipeline": "LinkedIn > RSS.app > n8n > Airtable",
                "needs_automation": True,
                "timestamp_ref": "generated"
            }
        }
    }

    outp = Path(output_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate job_matcher.json from raw job data (filename.json)")
    parser.add_argument("input", nargs="?", default="job-sourcing/filename.json", help="Path to input JSON (filename.json)")
    parser.add_argument("output", nargs="?", default="job-sourcing/job_matcher.json", help="Path to output job_matcher.json")
    parser.add_argument("--threshold", type=float, default=80.0, help="Score threshold for top scoring jobs")
    args = parser.parse_args()

    res = generate_job_matcher(args.input, args.output, args.threshold)
    print(f"Wrote {args.output} — total_jobs={res['airtable_dashboard']['summary_metrics'][0]['value']}")
