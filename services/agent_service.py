"""Service for Agent inspection, skill management, and interactive command dispatching.

Discovers skills in .agents/skills/ and provides runtime diagnostics.
"""

import os
import sys
import shutil
import subprocess
import signal
import yaml
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
AGENTS_SKILLS_DIR = ROOT / ".agents" / "skills"
SEEN_JOBS_FILE = ROOT / "job_scraper" / "seen_jobs.json"
TRACKER_FILE = ROOT / "job_search_tracker.csv"

# Global action log
ACTION_LOGS = [
    {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": "Web UI Initialized",
        "details": "AI Job Assistant dashboard started on port 5000"
    },
    {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": "Cache Loaded",
        "details": "Loaded 10 discovered & ranked vacancies from seen_jobs.json"
    }
]


def get_installed_skills() -> list[dict]:
    """Inspect and return all installed skills from .agents/skills/."""
    skills = []
    if not AGENTS_SKILLS_DIR.is_dir():
        return skills

    for skill_path in sorted(AGENTS_SKILLS_DIR.glob("*/SKILL.md")):
        name = skill_path.parent.name
        text = skill_path.read_text(encoding="utf-8")
        meta = {"name": name, "description": "", "enabled": True}

        if text.startswith("---\n"):
            end = text.find("\n---", 4)
            if end != -1:
                try:
                    data = yaml.safe_load(text[4:end])
                    if isinstance(data, dict):
                        meta.update(data)
                except Exception:
                    pass

        # Identify type
        is_core = name in ["setup", "scrape", "rank", "apply", "interview", "outcome"]
        skills.append({
            "name": name,
            "category": "Core Workflow" if is_core else "Portal Search CLI",
            "description": meta.get("description", "").strip(),
            "enabled": meta.get("enabled", True),
            "file": str(skill_path.relative_to(ROOT))
        })

    return skills


def get_system_diagnostics() -> dict:
    """Check availability of external runtimes and internal tools."""
    bun_installed = shutil.which("bun") is not None
    latex_installed = any(shutil.which(cmd) is not None for cmd in ["lualatex", "xelatex", "pdflatex"])
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    tools_available = {
        "rank_state.py": (ROOT / "tools" / "rank_state.py").is_file(),
        "job_key.py": (ROOT / "tools" / "job_key.py").is_file(),
        "verify_pdf.py": (ROOT / "tools" / "verify_pdf.py").is_file(),
        "verify_layout.py": (ROOT / "tools" / "verify_layout.py").is_file(),
    }

    seen_count = 0
    if SEEN_JOBS_FILE.is_file():
        try:
            import json
            data = json.loads(SEEN_JOBS_FILE.read_text(encoding="utf-8"))
            seen_count = len(data.get("seen", {}))
        except Exception:
            pass

    return {
        "python_version": python_version,
        "bun_available": bun_installed,
        "bun_mode": "Native Portal CLIs" if bun_installed else "Web Search Fallback (Active)",
        "latex_available": latex_installed,
        "latex_mode": "Native PDF Compilation" if latex_installed else "Plain Text Preview (Active)",
        "tools_ready": all(tools_available.values()),
        "tools_status": tools_available,
        "seen_jobs_count": seen_count,
        "tracker_ready": TRACKER_FILE.is_file(),
        "readiness": "READY (Core Search & Ranking operational)"
    }


def add_action_log(action: str, details: str):
    """Append an event to the recent actions history."""
    ACTION_LOGS.insert(0, {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": action,
        "details": details
    })
    # Keep last 20
    if len(ACTION_LOGS) > 20:
        ACTION_LOGS.pop()


def get_action_logs() -> list[dict]:
    """Retrieve action log history."""
    return ACTION_LOGS


# ---------------------------------------------------------------------------
# Antigravity CLI (agy) Adapter
# ---------------------------------------------------------------------------

_detected_agy = shutil.which("agy") or str(Path.home() / ".gemini" / "antigravity-cli" / "bin" / "agy")
AGY_CLI_PATH = Path(os.environ.get("AGY_CLI_PATH", _detected_agy))
DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("AGY_TIMEOUT_SECONDS", "120"))
WORKFLOW_TIMEOUT_SECONDS = int(os.environ.get("AGY_WORKFLOW_TIMEOUT_SECONDS", "180"))


def run_agy_agent(
    prompt: str,
    agy_path: Path | str | None = None,
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Execute a user prompt via the local Antigravity CLI (agy) non-interactively.

    Security & execution guarantees:
    - shell=False is strictly enforced (never invokes /bin/sh or bash)
    - Prompt is passed as an isolated argv element to prevent command injection
    - Working directory defaults to PROJECT_ROOT so the agent loads GEMINI.md and .agents/skills/
    - Process group isolation (start_new_session=True) guarantees all child processes
      are cleanly reaped on timeout without leaving background orphans
    """
    target_bin = Path(agy_path) if agy_path is not None else AGY_CLI_PATH
    target_cwd = cwd or ROOT

    cleaned_prompt = (prompt or "").strip()
    if not cleaned_prompt:
        return {
            "success": False,
            "response": "Empty prompt provided.",
            "error": "empty_prompt",
            "returncode": None,
        }

    # Verify binary presence and execution permission
    if not target_bin.is_file() or not os.access(target_bin, os.X_OK):
        return {
            "success": False,
            "response": f"Antigravity CLI binary not found or not executable at '{target_bin}'.",
            "error": "binary_not_found",
            "returncode": None,
        }

    cmd = [str(target_bin), "--dangerously-skip-permissions", "-p", cleaned_prompt]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(target_cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            shell=False,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            # Terminate the entire process group cleanly to prevent lingering background children
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.kill()
                except Exception:
                    pass
            stdout, stderr = proc.communicate()
            captured_stdout = (stdout or getattr(exc, "stdout", "") or "").strip()
            captured_stderr = (stderr or getattr(exc, "stderr", "") or "").strip()
            detail = f" (Details: {captured_stderr})" if captured_stderr else ""
            return {
                "success": False,
                "response": f"Agent request timed out after {timeout} seconds.{detail}",
                "error": "timeout",
                "returncode": proc.returncode,
                "partial_stdout": captured_stdout,
            }
    except FileNotFoundError:
        return {
            "success": False,
            "response": f"Antigravity CLI binary could not be found at '{target_bin}'.",
            "error": "binary_not_found",
            "returncode": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "response": f"Execution error while invoking agent: {str(exc)}",
            "error": "execution_failed",
            "returncode": None,
        }

    if proc.returncode != 0:
        err_msg = (stderr or "").strip() or f"Process exited with code {proc.returncode}"
        return {
            "success": False,
            "response": f"Agent error (exit code {proc.returncode}): {err_msg}",
            "error": f"exit_code_{proc.returncode}",
            "returncode": proc.returncode,
        }

    output = (stdout or "").strip()
    if not output:
        stderr_msg = (stderr or "").strip()
        detail = f" (Details: {stderr_msg})" if stderr_msg else ""
        return {
            "success": False,
            "response": f"Agent returned an empty response.{detail}",
            "error": "empty_response",
            "returncode": proc.returncode,
        }

    return {
        "success": True,
        "response": output,
        "error": None,
        "returncode": proc.returncode,
    }


CORE_WORKFLOW_COMMANDS = {
    "/setup": "setup",
    "/scrape": "scrape",
    "/rank": "rank",
    "/apply": "apply",
    "/interview": "interview",
    "/outcome": "outcome",
}


def build_conversational_prompt(user_query: str) -> str:
    """Wraps user queries in read-only conversational instructions to prevent unwanted test runs or modifications."""
    return (
        "You are answering a user through the Web UI Agent chat for the AI Job Search Assistant.\n\n"
        f"User query:\n{user_query}\n\n"
        "Guidelines for this response:\n"
        "1. Answer the user's request directly and clearly.\n"
        "2. You may read the existing Candidate Profile (.claude/skills/job-application-assistant/01-candidate-profile.md) "
        "and relevant project files when necessary.\n"
        "3. For this conversational request:\n"
        "   - Do NOT modify any files;\n"
        "   - Do NOT run tests (do not run unittest, pytest, or test suites);\n"
        "   - Do NOT execute repository maintenance tasks;\n"
        "   - Do NOT execute slash commands as workflows;\n"
        "   - Do NOT launch unrelated skills/workflows;\n"
        "   - Do NOT perform external application actions (e.g. submitting applications or contacting recruiters);\n"
        "   - Do NOT invent information (Strict Zero Fabrication: all candidate facts must come from Source of Truth).\n"
        "4. If the user explicitly requests an operation that requires a workflow or file modification "
        "(such as updating files or running automated scraper pipelines), explain that it should be performed "
        "through the appropriate workflow or Web UI interface (e.g. the Profile page /profile or Jobs page /jobs) "
        "rather than silently performing it."
    )


def build_workflow_prompt(command: str) -> str:
    """Wraps explicit workflow commands with bounded instructions."""
    cleaned = command.strip()
    is_scrape = cleaned.startswith("/scrape") or cleaned == "scrape"
    is_rank = cleaned.startswith("/rank") or cleaned == "rank"

    if is_scrape:
        return (
            "You are executing the /scrape workflow for the AI Job Search Assistant.\n\n"
            f"Command: {command}\n\n"
            "Execution guidelines:\n"
            "1. Fast completion is required (target within 45-60 seconds).\n"
            "2. Read job_scraper/seen_jobs.json to know already-seen postings.\n"
            "3. Search budget: run 1-2 targeted search_web queries for the candidate's priority roles (Junior Frontend / Junior Fullstack in Poland/Katowice/Remote).\n"
            "4. Strictly do NOT write or run ad-hoc Python crawler scripts or exploratory API scripts via run_command. Do NOT fetch details in loops.\n"
            "5. From search results, pick 2-4 fresh matching postings (Junior/Entry level, Poland/Katowice/Remote, min 4200 PLN, strictly exclude internships/staże).\n"
            "6. Record them into job_scraper/seen_jobs.json (preserving all existing entries).\n"
            "7. Output the final Markdown results table (with fit assessment and networking search links) and finish immediately.\n"
            "8. Do NOT run test suites (unittest / pytest)."
        )

    if is_rank:
        return (
            "You are executing the /rank workflow for the AI Job Search Assistant.\n\n"
            f"Command: {command}\n\n"
            "Execution guidelines:\n"
            "1. Fast and deterministic local execution is required (finish in under 45 seconds, roughly 4-6 steps total).\n"
            "2. Read candidates once: Query candidate jobs once via `python3 tools/rank_state.py candidates --limit 10`. "
            "Rank ONLY jobs with status `new`.\n"
            "3. Source of truth: Read `.claude/skills/job-application-assistant/04-job-evaluation.md` once for the evaluation matrix. "
            "Preserve the existing ranking formula and weights unchanged: Technical (30%), Experience (25%), Behavioral (15%), Career (30%).\n"
            "4. Candidate profile data (canonical facts, do not re-read 01-candidate-profile.md):\n"
            "   - Languages: Ukrainian (Native), Russian (Native), English (B1), Polish (B1);\n"
            "   - Location constraints: Katowice (Remote / Hybrid / Office). Outside Katowice: Remote only;\n"
            "   - Minimum compensation: 4,200 PLN/month;\n"
            "   - Internships: Strictly excluded (hard veto / FAIL).\n"
            "5. Batch-scoring & compact output contract:\n"
            "   Score all `new` candidates in ONE single batch using cached fields (title, company, location, salary, strengths, gaps). "
            "Generate and write `scratch/rank_results.json` as a compact JSON array matching exactly this structure:\n"
            "   [\n"
            "     {\n"
            "       \"key\": \"job-key\",\n"
            "       \"scores\": {\n"
            "         \"technical\": 80,\n"
            "         \"experience\": 70,\n"
            "         \"behavioral\": 75,\n"
            "         \"career\": 80\n"
            "       },\n"
            "       \"location_verdict\": \"PASS\",\n"
            "       \"language_gate\": \"PASS\",\n"
            "       \"strengths\": [\n"
            "         \"React/TypeScript match\",\n"
            "         \"Relevant PostgreSQL experience\"\n"
            "       ],\n"
            "       \"gaps\": [\n"
            "         \"Missing Go experience\"\n"
            "       ]\n"
            "     }\n"
            "   ]\n"
            "   - `scores` must contain ONLY the four existing dimensions: technical, experience, behavioral, career;\n"
            "   - `location_verdict` must be PASS, FAIL, or FLAG according to the location gate;\n"
            "   - `language_gate` must be PASS, FAIL, or FLAG according to the language gate;\n"
            "   - `strengths`: maximum 2 short bullets per vacancy;\n"
            "   - `gaps`: maximum 2 short bullets per vacancy;\n"
            "   - Do NOT duplicate long descriptions from seen_jobs.json;\n"
            "   - Do NOT write explanations, prose, or comments in the JSON;\n"
            "   - Keep the JSON as compact as reasonably possible.\n"
            "6. Source code inspection strictly FORBIDDEN:\n"
            "   - Do NOT inspect `tools/rank_state.py` source code;\n"
            "   - Do NOT inspect `cmd_apply` or implementation details;\n"
            "   - The JSON contract above is complete. After writing `scratch/rank_results.json`, immediately run:\n"
            "     `python3 tools/rank_state.py apply --results scratch/rank_results.json`\n"
            "7. Network tools strictly FORBIDDEN:\n"
            "   - Do NOT fetch job URLs;\n"
            "   - Do NOT call `read_url_content` or `search_web`;\n"
            "   - Do NOT use `curl`, browser, or network tools;\n"
            "   - Do NOT consult `09-web-research.md`;\n"
            "   - Do NOT retry Cloudflare/403/404 errors;\n"
            "   - Do NOT run tests (unittest / pytest);\n"
            "   - Do NOT invoke other workflows such as /scrape or /apply.\n"
            "8. Concise final response:\n"
            "   Return ONLY a concise Markdown shortlist table and vetoed list (do not write large explanations for every dimension):\n"
            "   | # | Job | Company | Score | Verdict |\n"
            "   |---|---|---|---:|---|\n"
            "   | 1 | Junior Frontend Developer | Example | 82 | Strong Fit |\n\n"
            "   Rejected:\n"
            "   - Example — Location Gate FAIL\n"
            "   Stop immediately after outputting this concise response."
        )

    return (
        "You are executing an explicit workflow command for the AI Job Search Assistant.\n\n"
        f"Command: {command}\n\n"
        "Guidelines for this workflow execution:\n"
        "1. Execute only the requested workflow as described in .agents/skills/.\n"
        "2. Do NOT run the repository test suite (unittest / pytest) unless the workflow specifically requires it.\n"
        "3. Do NOT execute unrelated maintenance tasks.\n"
        "4. Strictly adhere to Zero Fabrication: do NOT invent skills, credentials, or facts."
    )


def handle_profile_command(args: str) -> dict:
    """Handles /profile commands directly via Candidate Profile service."""
    from services.candidate_service import get_canonical_profile, save_candidate_identity

    args = (args or "").strip()
    if not args or args.lower() in ["view", "show", "summary", "info", "status"]:
        profile = get_canonical_profile()
        identity = profile.get("identity", {})
        roles = ", ".join(profile.get("preferred_roles", []))
        summary_lines = [
            "👤 **Canonical Candidate Profile Summary** (Source of Truth: `01-candidate-profile.md`):",
            f"- **Name:** {identity.get('name') or 'N/A'}",
            f"- **Location:** {identity.get('location') or 'N/A'}",
            f"- **Target Roles:** {roles}",
            f"- **Portfolio:** {identity.get('portfolio') or 'Not provided'}",
            f"- **GitHub:** {identity.get('github') or 'Not provided'}",
            f"- **Status:** {identity.get('status') or 'N/A'}",
            f"- **Constraints:** {identity.get('constraints') or 'N/A'}",
            "\n💡 *You can view and edit all fields on the Web UI [Profile page](/profile), or update a field here with `/profile <field>: <value>` (e.g. `/profile portfolio: https://...`).*"
        ]
        return {
            "success": True,
            "response": "\n".join(summary_lines),
            "error": None,
            "action_taken": "profile_viewed",
            "details": "Canonical profile summary retrieved",
        }

    # Match "field: value" or "field=value"
    match = re.match(r"^([a-zA-Z_]+)\s*[:=]\s*(.+)$", args)
    if match:
        field_raw = match.group(1).strip().lower()
        value = match.group(2).strip()

        field_map = {
            "portfolio": "portfolio",
            "website": "portfolio",
            "site": "portfolio",
            "name": "name",
            "full_name": "name",
            "location": "location",
            "phone": "phone",
            "email": "email",
            "linkedin": "linkedin",
            "github": "github",
            "status": "status",
            "constraints": "constraints",
        }
        canonical_field = field_map.get(field_raw, field_raw)
        success = save_candidate_identity({canonical_field: value})
        if success:
            add_action_log(
                "Profile Updated via Command",
                f"Updated '{canonical_field}' to '{value}' in canonical profile",
            )
            return {
                "success": True,
                "response": (
                    f"✓ Candidate profile updated: **{canonical_field.capitalize()}** has been updated to `{value}` "
                    f"in `01-candidate-profile.md`.\n\n"
                    f"You can review the updated profile on the Web UI [Profile page](/profile)."
                ),
                "error": None,
                "action_taken": "profile_updated",
                "details": f"Field '{canonical_field}' updated in 01-candidate-profile.md",
            }
        else:
            return {
                "success": False,
                "response": "Failed to update profile: canonical file could not be written.",
                "error": "write_failed",
                "action_taken": "profile_error",
                "details": "01-candidate-profile.md not found or unwritable",
            }

    return {
        "success": True,
        "response": (
            f"Command `/profile` received with unrecognized syntax: `{args}`.\n\n"
            "To update a profile field directly, use: `/profile <field>: <value>`\n"
            "Supported fields: `portfolio`, `name`, `location`, `phone`, `email`, `linkedin`, `github`, `status`, `constraints`.\n"
            "Example: `/profile portfolio: https://example.com/portfolio`\n\n"
            "Or edit your profile through the Web UI on the [Profile page](/profile)."
        ),
        "error": None,
        "action_taken": "profile_help",
        "details": "Profile command guidance",
    }


def handle_agent_command(command: str) -> dict:
    """Dispatches a user command to the appropriate handler or Antigravity Agent.

    Routing rules:
    1. /profile commands: safely view or update canonical profile directly
    2. /status command: returns runtime diagnostics directly
    3. Explicit workflow commands (/setup, /scrape, /rank, /apply, /interview, /outcome):
       executed with workflow-bounded instructions
    4. Conversational chat requests:
       wrapped with read-only instructions (no tests, no file modifications, Zero Fabrication)
    """
    cleaned = (command or "").strip()
    if not cleaned:
        return {
            "success": False,
            "response": "Empty command provided.",
            "error": "empty_command",
            "action_taken": "none",
            "details": "No input provided",
        }

    # 1. Profile command
    if cleaned.startswith("/profile"):
        args = cleaned[len("/profile"):].strip()
        result = handle_profile_command(args)
        truncated_prompt = (cleaned[:50] + "...") if len(cleaned) > 50 else cleaned
        add_action_log(
            "Profile Command",
            f"Command: '{truncated_prompt}' → Status: {'OK' if result['success'] else 'FAILED'}"
        )
        return result

    # 2. Status command
    if cleaned.lower() in ["/status", "status"]:
        diag = get_system_diagnostics()
        summary = (
            f"📊 **Agent & Pipeline Status:** {diag['readiness']}\n\n"
            f"- **Python:** `{diag['python_version']}`\n"
            f"- **Search Mode:** `{diag['bun_mode']}`\n"
            f"- **PDF Toolchain:** `{diag['latex_mode']}`\n"
            f"- **Jobs in Cache:** `{diag['seen_jobs_count']}` vacancies (in `job_scraper/seen_jobs.json`)\n"
            f"- **Core Workflows:** Installed & ready (`.agents/skills/`)"
        )
        add_action_log("Status Check", "Runtime diagnostics returned")
        return {
            "success": True,
            "response": summary,
            "error": None,
            "action_taken": "status_check",
            "details": "Local diagnostics retrieved",
        }

    # 3. Explicit workflow vs Conversational request
    first_word = cleaned.split()[0].lower() if cleaned else ""
    if first_word in CORE_WORKFLOW_COMMANDS:
        prompt_to_send = build_workflow_prompt(cleaned)
        action_type = "workflow_dispatched"
        timeout_to_use = WORKFLOW_TIMEOUT_SECONDS
    else:
        prompt_to_send = build_conversational_prompt(cleaned)
        action_type = "agent_executed"
        timeout_to_use = DEFAULT_TIMEOUT_SECONDS

    result = run_agy_agent(prompt_to_send, timeout=timeout_to_use)

    action_label = "Agent Response" if result["success"] else "Agent Error"
    status_detail = "OK" if result["success"] else result.get("error", "FAILED")
    truncated_prompt = (cleaned[:50] + "...") if len(cleaned) > 50 else cleaned

    add_action_log(action_label, f"Prompt: '{truncated_prompt}' → Status: {status_detail}")

    return {
        "success": result["success"],
        "response": result["response"],
        "error": result.get("error"),
        "action_taken": action_type if result["success"] else "agent_error",
        "details": f"Engine: agy CLI (exit {result.get('returncode')})",
    }

