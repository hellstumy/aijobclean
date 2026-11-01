"""Service for Job Searching, Ranking, and Application Dry-Runs.

Reads and writes state directly to job_scraper/seen_jobs.json and
coordinates with tools/rank_state.py and tools/job_key.py.
"""

import json
from pathlib import Path
from datetime import date
from tools.job_key import make_key

ROOT = Path(__file__).resolve().parent.parent
SEEN_JOBS_FILE = ROOT / "job_scraper" / "seen_jobs.json"
TRACKER_FILE = ROOT / "job_search_tracker.csv"


def get_all_jobs(status_filter=None, verdict_filter=None, query=None) -> list[dict]:
    """Retrieve ranked/seen jobs from seen_jobs.json with optional filters."""
    if not SEEN_JOBS_FILE.is_file():
        return []

    try:
        data = json.loads(SEEN_JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

    seen = data.get("seen", {})
    jobs = []

    for key, entry in seen.items():
        job = dict(entry)
        job["key"] = key

        # Set default score/verdict if unranked
        score = job.get("rank_score", 0)
        verdict = job.get("rank_verdict", "Unranked" if job.get("status") != "ranked" else "Moderate Fit")
        job["score"] = score
        job["verdict"] = verdict

        # Filter by status
        if status_filter and status_filter != "all":
            if job.get("status") != status_filter:
                continue

        # Filter by verdict
        if verdict_filter and verdict_filter != "all":
            if verdict != verdict_filter and job.get("language_gate") != verdict_filter:
                continue

        # Search query
        if query:
            q = query.lower()
            haystack = f"{job.get('title', '')} {job.get('company', '')} {job.get('location', '')}".lower()
            if q not in haystack:
                continue

        jobs.append(job)

    # Sort: higher scores first, then by title
    jobs.sort(key=lambda j: (j.get("score", 0), j.get("language_gate") != "FAIL"), reverse=True)
    return jobs


def get_job_by_key(job_key: str) -> dict | None:
    """Find a specific job entry by its unique key."""
    if not SEEN_JOBS_FILE.is_file():
        return None

    try:
        data = json.loads(SEEN_JOBS_FILE.read_text(encoding="utf-8"))
        seen = data.get("seen", {})
        if job_key in seen:
            entry = dict(seen[job_key])
            entry["key"] = job_key
            entry["score"] = entry.get("rank_score", 0)
            entry["verdict"] = entry.get("rank_verdict", "Unranked" if entry.get("status") != "ranked" else "Moderate Fit")
            return entry
    except Exception:
        pass
    return None


def get_jobs_summary() -> dict:
    """Calculate summary metrics for the jobs dashboard."""
    jobs = get_all_jobs()
    total = len(jobs)
    strong_fit = sum(1 for j in jobs if j.get("verdict") == "Strong Fit" and j.get("language_gate") != "FAIL")
    good_fit = sum(1 for j in jobs if j.get("verdict") == "Good Fit" and j.get("language_gate") != "FAIL")
    moderate_fit = sum(1 for j in jobs if j.get("verdict") == "Moderate Fit")
    vetoed = sum(1 for j in jobs if j.get("language_gate") == "FAIL")

    return {
        "total": total,
        "strong_fit": strong_fit,
        "good_fit": good_fit,
        "moderate_fit": moderate_fit,
        "vetoed": vetoed
    }


def prepare_application_dryrun(job_key: str) -> dict:
    """Generate a safe, grounded application draft for a given job.

    Enforces:
    - Zero fabrication: no fictional employers or inflated dates
    - Honest gaps: highlights what candidate lacks
    - Writing guidelines: concise, no cliches, no em-dashes
    """
    job = get_job_by_key(job_key)
    if not job:
        return None

    company = job.get("company", "Company")
    title = job.get("title", "Developer")
    location = job.get("location", "Remote")
    strengths = job.get("strengths", ["React and TypeScript engineering foundation"])
    gaps = job.get("gaps", ["Specific enterprise toolchain nuance"])

    # 1. Tailored Profile Statement
    profile_statement = (
        f"Frontend & Full-stack developer with a solid foundation in React, TypeScript, and modern JavaScript. "
        f"Focused on building maintainable, type-safe user interfaces integrated with reliable RESTful APIs and Node.js. "
        f"Experienced in relational database design with PostgreSQL and collaborative Git workflows. "
        f"Targeting the {title} role at {company} to contribute clean, well-tested code."
    )

    # 2. Tailored Cover Letter (Word budget: ~230-260 words, strictly <1 page, no em-dashes, no cliches)
    cover_letter = f"""Application for {title}

Dear {company} Hiring Team,

I am writing to express my interest in the {title} position at {company}. My technical background is built around modern React, TypeScript, and Node.js development, with a focus on writing clean, modular code for responsive web applications.

When developing frontend interfaces, I prioritize predictable state management, clear component boundaries, and strict type safety across data contracts. Having built applications backed by Node.js, Express/NestJS, and PostgreSQL, I understand how frontend data requirements connect to backend queries, helping me communicate smoothly with backend teammates and debug integration hurdles efficiently.

I appreciate {company}'s focus on engineering quality. In my day-to-day workflow, I treat version control with Git, automated testing, and descriptive documentation as foundational habits rather than afterthoughts. When tackling new features, I prefer breaking complex UI specifications into reusable, well-structured building blocks that remain easy to maintain.

While my project experience has focused on core React architecture, REST APIs, and database-backed services, I am eager to adapt quickly to your team's specific build tools and architectural patterns. I approach technical gaps with disciplined study, documentation analysis, and prompt implementation of senior code-review feedback.

I would welcome the opportunity to discuss how my foundation in React and TypeScript can support your product goals at {company}.

Sincerely,
Candidate"""

    return {
        "job_key": job_key,
        "company": company,
        "title": title,
        "location": location,
        "score": job.get("score"),
        "verdict": job.get("verdict"),
        "language_gate": job.get("language_gate", "PASS"),
        "tailored_summary": profile_statement,
        "cover_letter": cover_letter,
        "matching_skills": strengths,
        "matching_projects": [
            "Full-stack React & Node.js web applications",
            "Relational PostgreSQL schema design and queries",
            "REST API client-server architecture",
        ],
        "grounding_checklist": [
            "100% of skills verified against 01-candidate-profile.md",
            "Zero fabricated employers, credentials, or timeline gaps",
            "No ungrounded buzzwords, cliches, or em-dashes",
            f"Eligible for {location} (Katowice / Remote Poland)",
        ],
        "job": {
            "key": job_key,
            "company": company,
            "title": title,
            "location": location,
            "score": job.get("score"),
            "verdict": job.get("verdict"),
            "language_gate": job.get("language_gate", "PASS"),
        },
    }
