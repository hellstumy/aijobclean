"""Service for reading and managing the Canonical Candidate Profile.

Source of Truth:
- .claude/skills/job-application-assistant/01-candidate-profile.md
- .claude/skills/job-application-assistant/02-behavioral-profile.md
- .claude/skills/job-application-assistant/04-job-evaluation.md

This service treats .claude/skills/job-application-assistant/ as canonical.
It does NOT duplicate profile data into any second storage.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROFILE_01 = ROOT / ".claude" / "skills" / "job-application-assistant" / "01-candidate-profile.md"
BEHAVIORAL_02 = ROOT / ".claude" / "skills" / "job-application-assistant" / "02-behavioral-profile.md"
EVALUATION_04 = ROOT / ".claude" / "skills" / "job-application-assistant" / "04-job-evaluation.md"


def get_canonical_profile() -> dict:
    """Parse structured candidate profile directly from canonical files."""
    if not PROFILE_01.is_file():
        return {"error": "Canonical profile file not found"}

    text = PROFILE_01.read_text(encoding="utf-8")

    # Extract Identity fields
    identity = {}
    for field in ["Name", "Location", "Phone", "Email", "LinkedIn", "Portfolio", "GitHub", "Status", "Constraints"]:
        match = re.search(rf"^-\s+\*\*{field}:\*\*\s*(.*)$", text, re.MULTILINE)
        if match:
            val = match.group(1).strip()
            identity[field.lower()] = val
        else:
            identity[field.lower()] = ""

    # Extract Languages table
    languages = []
    lang_section_match = re.search(r"### Languages.*?\n(\|.*?)(?=\n## |\Z)", text, re.DOTALL)
    if lang_section_match:
        table_lines = [l.strip() for l in lang_section_match.group(1).splitlines() if l.strip().startswith("|")]
        if len(table_lines) >= 3:
            for row in table_lines[2:]:  # Skip header and divider
                cols = [c.strip() for c in row.split("|")[1:-1]]
                if len(cols) >= 2 and cols[0] and not cols[0].startswith("["):
                    languages.append({
                        "language": cols[0],
                        "level": cols[1] if len(cols) > 1 else "",
                        "notes": cols[2] if len(cols) > 2 else ""
                    })

    # Extract Technical Skills from 01-candidate-profile.md
    tech_skills = {
        "programming": [],
        "databases": [],
        "tools": []
    }
    
    tech_match = re.search(r"## Technical Skills.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if tech_match:
        tech_content = tech_match.group(1)
        # Parse Confirmed skills from bullet points
        confirmed_skills = []
        for line in tech_content.splitlines():
            line_str = line.strip()
            if "- **Confirmed:**" in line_str or line_str.startswith("- "):
                skills_part = line_str.replace("- **Confirmed:**", "").replace("- ", "").strip()
                for skill in skills_part.split(","):
                    skill_name = skill.strip()
                    if skill_name and not skill_name.startswith("[") and skill_name not in confirmed_skills:
                        confirmed_skills.append(skill_name)
        
        # Categorize skills generically
        db_keywords = {"sql", "postgres", "postgresql", "mysql", "mongodb", "redis", "prisma", "sqlite", "oracle", "database"}
        tool_keywords = {"git", "github", "gitlab", "docker", "kubernetes", "linux", "npm", "vs code", "postman", "bruno", "ci/cd", "aws", "gcp", "azure", "vite", "webpack", "jira", "bash"}
        
        for sk in confirmed_skills:
            sk_lower = sk.lower()
            if any(k in sk_lower for k in db_keywords):
                tech_skills["databases"].append(sk)
            elif any(k in sk_lower for k in tool_keywords):
                tech_skills["tools"].append(sk)
            else:
                tech_skills["programming"].append(sk)

    # Preferred roles & target stack from Status or default
    preferred_roles = []
    status_val = identity.get("status", "")
    role_match = re.search(r"\((.*?)\)", status_val)
    if role_match:
        roles_raw = role_match.group(1)
        preferred_roles = [r.strip() for r in roles_raw.split("/") if r.strip() and not r.startswith("[")]
    if not preferred_roles:
        if status_val and not status_val.startswith("["):
            preferred_roles = [status_val]
        else:
            preferred_roles = ["Developer"]

    # Preferred locations
    loc = identity.get("location", "")
    constraints = identity.get("constraints", "")
    preferred_locations = []
    if loc and not loc.startswith("["):
        preferred_locations.append(loc)
    if constraints and not constraints.startswith("[") and constraints not in preferred_locations:
        preferred_locations.append(constraints)
    if not preferred_locations:
        preferred_locations = ["Remote / Office"]

    # Read behavioral summary if present
    behavioral_text = BEHAVIORAL_02.read_text(encoding="utf-8") if BEHAVIORAL_02.is_file() else ""
    behavioral_summary = "Candidate profile initialized. Professional and adaptive team contributor."
    overview_match = re.search(r"## Overview\s*\n+([^\n#]+)", behavioral_text)
    if overview_match and not overview_match.group(1).strip().startswith("["):
        behavioral_summary = overview_match.group(1).strip()

    return {
        "identity": identity,
        "languages": languages,
        "tech_skills": tech_skills,
        "preferred_roles": preferred_roles,
        "preferred_locations": preferred_locations,
        "remote_preference": constraints if constraints and not constraints.startswith("[") else "Remote / Office",
        "behavioral_summary": behavioral_summary,
        "raw_markdown_01": text,
        "is_canonical": True,
        "source_file": str(PROFILE_01.relative_to(ROOT))
    }


def save_candidate_identity(updates: dict) -> bool:
    """Safely update identity fields directly in 01-candidate-profile.md."""
    if not PROFILE_01.is_file():
        return False

    text = PROFILE_01.read_text(encoding="utf-8")

    for key, value in updates.items():
        if not key or value is None:
            continue
        field_name = key.capitalize()
        if key.lower() == "linkedin":
            field_name = "LinkedIn"
        elif key.lower() == "github":
            field_name = "GitHub"
        elif key.lower() == "portfolio":
            field_name = "Portfolio"

        pattern = rf"^-\s+\*\*{field_name}:\*\*.*$"
        replacement = f"- **{field_name}:** {value}"
        if re.search(pattern, text, re.MULTILINE):
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        else:
            # If the field does not yet exist in Identity, insert before Languages or after Identity
            if "### Languages" in text:
                text = text.replace("### Languages", f"{replacement}\n\n### Languages", 1)
            elif "## Identity" in text:
                text = text.replace("## Identity", f"## Identity\n{replacement}", 1)

    PROFILE_01.write_text(text, encoding="utf-8")
    return True
