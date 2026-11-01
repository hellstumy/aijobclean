"""Service for reading and managing search & agent configuration.

Source of Truth:
- .claude/skills/job-scraper/search-queries.md
- .claude/skills/job-application-assistant/04-job-evaluation.md
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERIES_FILE = ROOT / ".claude" / "skills" / "job-scraper" / "search-queries.md"
EVALUATION_FILE = ROOT / ".claude" / "skills" / "job-application-assistant" / "04-job-evaluation.md"


def get_current_settings() -> dict:
    """Retrieve current search, evaluation, and safety settings."""
    # Target stack & roles from current active configuration
    target_roles = [
        "Junior Frontend Developer",
        "Junior Fullstack Developer"
    ]
    target_stack = [
        "React",
        "TypeScript",
        "Node.js",
        "NestJS",
        "PostgreSQL",
        "Prisma",
        "Zustand",
        "Vite",
        "HTML / CSS",
        "REST API"
    ]
    locations = [
        {"name": "Katowice (Local)", "tier": "Remote / Hybrid / Office", "status": "Active"},
        {"name": "Outside Katowice (Poland / Global)", "tier": "Remote Only", "status": "Active"}
    ]

    scoring_weights = [
        {"dimension": "Technical Skills", "weight": "25%", "description": "Core frameworks, libraries, language proficiency (React, TS, NestJS, Postgres)"},
        {"dimension": "Experience / Requirements", "weight": "25%", "description": "Hands-on project experience, manageable gaps, realistic requirements"},
        {"dimension": "Personal Preferences & Conditions", "weight": "25%", "description": "Location (Katowice/Remote), contract, salary (min 4200 PLN)"},
        {"dimension": "Career Alignment & Overall Fit", "weight": "25%", "description": "Long-term developer growth, team mentorship, engineering impact"}
    ]

    thresholds = [
        {"band": "Strong Fit", "range": "75 – 100", "policy": "Definitely apply, tailor documents with priority"},
        {"band": "Good Fit", "range": "60 – 74", "policy": "Apply, address technical/domain gaps honestly (60-70% fit target)"},
        {"band": "Moderate Fit", "range": "45 – 59", "policy": "Consider carefully, evaluate stretch vs effort"},
        {"band": "Weak / Poor Fit", "range": "0 – 44", "policy": "Skip unless strategic exceptions exist"}
    ]

    safety_policies = [
        {"name": "Application Approval Policy", "value": "Strict Manual Approval", "description": "Antigravity never dispatches applications or emails automatically"},
        {"name": "Dry-Run Enforcement", "value": "Enabled", "description": "Document generation runs in dry-run mode before user confirmation"},
        {"name": "Zero Fabrication Boundary", "value": "Strict Factual Grounding", "description": "All resume and letter claims must originate from Source of Truth"},
        {"name": "Internship Veto", "value": "Strict Auto-Reject", "description": "Internships / unpaid trainee programs are rejected automatically"},
        {"name": "Minimum Salary Gate", "value": ">= 4200 PLN", "description": "Flag or penalize vacancies offering less than 4200 PLN / month"}
    ]

    return {
        "target_roles": target_roles,
        "target_stack": target_stack,
        "locations": locations,
        "scoring_weights": scoring_weights,
        "thresholds": thresholds,
        "safety_policies": safety_policies,
        "queries_source": str(QUERIES_FILE.relative_to(ROOT)),
        "evaluation_source": str(EVALUATION_FILE.relative_to(ROOT))
    }

