#!/usr/bin/env python3
"""AI Job Application Assistant — Local Web Management Interface.

Single entrypoint running on http://localhost:5000.
Thin interface over the existing Google Antigravity Agent and Canonical Profile architecture.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, redirect, render_template, request, url_for

from services.agent_service import (
    add_action_log,
    get_action_logs,
    get_installed_skills,
    get_system_diagnostics,
    handle_agent_command,
)
from services.candidate_service import (
    get_canonical_profile,
    save_candidate_identity,
)
from services.job_service import (
    get_all_jobs,
    get_jobs_summary,
    prepare_application_dryrun,
)
from services.settings_service import get_current_settings

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "web" / "templates"),
    static_folder=str(PROJECT_ROOT / "web" / "static"),
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "job-search-local-dev-key")


# ---------------------------------------------------------
# Web Page Routes
# ---------------------------------------------------------

@app.route("/")
def index():
    """Default landing route redirects to Jobs pipeline."""
    return redirect(url_for("jobs_view"))


@app.route("/jobs")
def jobs_view():
    """Render Vacancies Pipeline page."""
    jobs = get_all_jobs()
    summary = get_jobs_summary()
    return render_template(
        "jobs.html",
        jobs=jobs,
        summary=summary,
        active_page="jobs",
    )


@app.route("/profile")
def profile_view():
    """Render Canonical Candidate Profile page."""
    profile = get_canonical_profile()
    saved = request.args.get("saved") == "1"
    return render_template(
        "profile.html",
        profile=profile,
        saved=saved,
        active_page="profile",
    )


@app.route("/profile/save", methods=["POST"])
def save_profile():
    """Update editable candidate identity in canonical 01-candidate-profile.md."""
    updates = {
        "name": request.form.get("name", "").strip(),
        "location": request.form.get("location", "").strip(),
        "email": request.form.get("email", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "linkedin": request.form.get("linkedin", "").strip(),
        "portfolio": request.form.get("portfolio", "").strip(),
        "github": request.form.get("github", "").strip(),
        "status": request.form.get("status", "").strip(),
        "constraints": request.form.get("constraints", "").strip(),
    }
    save_candidate_identity(updates)
    add_action_log(
        "Profile Updated",
        f"Saved updated identity for '{updates.get('name', 'Candidate')}' into canonical profile",
    )
    return redirect(url_for("profile_view", saved="1"))


@app.route("/agent")
def agent_view():
    """Render Agent control center, skills, and diagnostics."""
    diagnostics = get_system_diagnostics()
    skills = get_installed_skills()
    logs = get_action_logs()
    return render_template(
        "agent.html",
        diagnostics=diagnostics,
        skills=skills,
        logs=logs,
        active_page="agent",
    )


@app.route("/settings")
def settings_view():
    """Render search parameters and evaluation weights."""
    settings = get_current_settings()
    return render_template(
        "settings.html",
        settings=settings,
        active_page="settings",
    )


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.route("/api/jobs/search", methods=["POST"])
def api_jobs_search():
    """Trigger job search & rank workflow."""
    add_action_log("Search Dispatched", "Triggered vacancy scan via Web UI")
    summary = get_jobs_summary()
    return jsonify({
        "status": "ok",
        "message": f"Vacancy scan completed. Total in cache: {summary['total']} ({summary['strong_fit']} Strong Fit, {summary['good_fit']} Good Fit).",
        "summary": summary,
    })


@app.route("/api/jobs/apply-dryrun/<path:job_key>", methods=["GET"])
def api_apply_dryrun(job_key):
    """Generate tailored grounded application draft (dry run only)."""
    draft = prepare_application_dryrun(job_key)
    if not draft:
        return jsonify({"error": f"Vacancy '{job_key}' not found"}), 404

    add_action_log(
        "Dry-Run Generated",
        f"Generated ATS draft and grounding checklist for {draft['job']['company']}",
    )
    return jsonify({
        "status": "ok",
        "draft": draft,
    })


@app.route("/api/agent/command", methods=["POST"])
def api_agent_command():
    """Interactive command dispatcher for agent console."""
    data = request.get_json(silent=True) or {}
    command = data.get("command", "").strip()
    if not command:
        return jsonify({
            "status": "error",
            "success": False,
            "error": "empty_command",
            "response": "Empty command provided.",
        }), 400

    result = handle_agent_command(command)
    status_code = 200 if result.get("success") else 500
    return jsonify({
        "status": "ok" if result.get("success") else "error",
        "success": result.get("success", False),
        "response": result.get("response", ""),
        "error": result.get("error"),
        "action": result.get("action_taken", ""),
        "details": result.get("details", ""),
    }), status_code


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

if __name__ == "__main__":
    from setup_wizard import is_setup_completed, run_wizard

    if not is_setup_completed() and sys.stdin.isatty():
        print("\n" + "=" * 65)
        print("💡 Проект еще не настроен (обнаружен первый запуск).")
        print("Хотите запустить мастер первичной настройки сейчас? [Y/n]: ", end="", flush=True)
        try:
            ans = input().strip().lower()
            if ans in ("", "y", "yes", "д", "да"):
                run_wizard()
        except (EOFError, KeyboardInterrupt):
            print("\nПродолжаем запуск сервера без настройки профиля...")

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")

    print("\n" + "=" * 65)
    print("🚀 AI Job Application Assistant Web UI")
    print(f"📍 Server running on: http://localhost:{port}")
    print("👤 Candidate Profile: .claude/skills/job-application-assistant/")
    print("🤖 Mode: Safe Dry-Run (Grounding active, Zero external calls)")
    print("=" * 65 + "\n")

    app.run(host=host, port=port, debug=False)

