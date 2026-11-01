"""Tests for the Local Web UI, Flask endpoints, and backend services.

Ensures the Web UI adheres to:
1. Canonical Candidate Profile as Single Source of Truth
2. Safe dry-run operations (no automatic applications or emails)
3. Proper HTTP status codes and JSON contract schemas
"""

import unittest
from unittest.mock import patch
from pathlib import Path
import json

from app import app
from services.candidate_service import (
    get_canonical_profile,
    save_candidate_identity,
    PROFILE_01,
)
from services.job_service import (
    get_all_jobs,
    get_jobs_summary,
    prepare_application_dryrun,
)
from services.agent_service import (
    get_system_diagnostics,
    get_installed_skills,
    handle_agent_command,
)
from services.settings_service import get_current_settings


class WebUiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_root_redirects_to_jobs(self):
        """Root / should redirect to /jobs."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/jobs", response.headers["Location"])

    def test_jobs_view_renders(self):
        """GET /jobs returns 200 with pipeline data."""
        response = self.client.get("/jobs")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Vacancy Pipeline", html)
        self.assertIn("MasterBorn", html)
        self.assertIn("EndySoft", html)

    def test_profile_view_renders_canonical_data(self):
        """GET /profile returns 200 and displays canonical data."""
        response = self.client.get("/profile")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Candidate Profile", html)
        self.assertIn("01-candidate-profile.md", html)

    def test_agent_view_renders_diagnostics(self):
        """GET /agent returns 200 and displays diagnostics and skills."""
        response = self.client.get("/agent")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("AI Agent Control Center", html)
        self.assertIn("Agent Command Interface", html)
        self.assertIn("Installed Agent Skills", html)

    def test_settings_view_renders_parameters(self):
        """GET /settings returns 200 and displays evaluation weights."""
        response = self.client.get("/settings")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Agent & Search Settings", html)
        self.assertIn("Evaluation Dimensions & Weights", html)

    def test_api_jobs_search(self):
        """POST /api/jobs/search returns discovery status and summary."""
        response = self.client.post("/api/jobs/search")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("summary", data)
        self.assertGreaterEqual(data["summary"]["total"], 10)

    def test_api_apply_dryrun_existing_job(self):
        """GET /api/jobs/apply-dryrun/<key> generates grounded draft."""
        key = "masterborn_junior-frontend-developer"
        response = self.client.get(f"/api/jobs/apply-dryrun/{key}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data.get("status"), "ok")
        draft = data.get("draft")
        self.assertIsNotNone(draft)
        self.assertEqual(draft["job"]["company"], "MasterBorn")
        self.assertIn("cover_letter", draft)
        self.assertIn("tailored_summary", draft)
        self.assertIn("grounding_checklist", draft)

    def test_api_apply_dryrun_not_found(self):
        """GET /api/jobs/apply-dryrun/<invalid> returns 404."""
        response = self.client.get("/api/jobs/apply-dryrun/nonexistent-key-12345")
        self.assertEqual(response.status_code, 404)

    @patch("app.handle_agent_command")
    def test_api_agent_command_dispatcher(self, mock_cmd):
        """POST /api/agent/command responds to user queries."""
        mock_cmd.return_value = {
            "success": True,
            "response": "Статус агента: READY (online)",
            "error": None,
            "action_taken": "agent_executed",
            "details": "Engine: agy CLI",
        }
        payload = {"command": "Статус агента"}
        response = self.client.post(
            "/api/agent/command",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data.get("status"), "ok")
        self.assertTrue(data.get("success"))
        self.assertIn("Статус агента", data.get("response", ""))

    def test_services_load_canonical_data(self):
        """Services read canonical source of truth directly."""
        profile = get_canonical_profile()
        self.assertIn("identity", profile)
        self.assertIn("languages", profile)
        self.assertIn("tech_skills", profile)
        self.assertTrue(PROFILE_01.is_file())

        summary = get_jobs_summary()
        self.assertGreaterEqual(summary["total"], 10)
        self.assertGreaterEqual(summary["strong_fit"], 2)

        skills = get_installed_skills()
        self.assertGreaterEqual(len(skills), 6)
        skill_names = [s["name"] for s in skills]
        for expected in ["setup", "scrape", "rank", "apply", "interview", "outcome"]:
            self.assertIn(expected, skill_names)


if __name__ == "__main__":
    unittest.main()
