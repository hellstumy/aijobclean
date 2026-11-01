"""Unit tests for the Antigravity CLI (agy) Adapter and Agent API.

All tests use mocks to ensure no actual subprocess calls to agy or external
LLM services are executed during automated test runs.
"""

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app import app
from services.agent_service import (
    AGY_CLI_PATH,
    ROOT,
    run_agy_agent,
    handle_agent_command,
    build_conversational_prompt,
    build_workflow_prompt,
    handle_profile_command,
    WORKFLOW_TIMEOUT_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
)


class TestAgentAdapter(unittest.TestCase):
    """Test suite covering agy adapter behavior under various execution conditions."""

    def setUp(self):
        self.client = app.test_client()
        from services.candidate_service import PROFILE_01
        self.profile_01 = PROFILE_01
        self.orig_profile_text = PROFILE_01.read_text(encoding="utf-8") if PROFILE_01.is_file() else None

    def tearDown(self):
        if self.orig_profile_text is not None and self.profile_01.is_file():
            self.profile_01.write_text(self.orig_profile_text, encoding="utf-8")

    @patch("services.agent_service.subprocess.Popen")
    @patch.object(Path, "is_file", return_value=True)
    @patch("services.agent_service.os.access", return_value=True)
    def test_adapter_successful_response(self, mock_access, mock_is_file, mock_popen):
        """1. Successful agy response parses output and returns success=True."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("Привет! Я агент Antigravity, готов к поиску вакансий.\n", "")
        mock_proc.returncode = 0
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        result = run_agy_agent("Привет", agy_path=Path("/mock/agy"))
        self.assertTrue(result["success"])
        self.assertIn("готов к поиску", result["response"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["returncode"], 0)

    def test_adapter_agy_not_found(self):
        """2. Non-existent agy binary path returns clean error without crashing."""
        non_existent = Path("/path/to/nonexistent/agy_binary")
        result = run_agy_agent("test", agy_path=non_existent)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "binary_not_found")
        self.assertIn("not found", result["response"])

    @patch("services.agent_service.subprocess.Popen")
    @patch.object(Path, "is_file", return_value=True)
    @patch("services.agent_service.os.access", return_value=True)
    def test_adapter_timeout(self, mock_access, mock_is_file, mock_popen):
        """3. Execution exceeding timeout returns timeout error."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd=["agy", "-p", "slow"], timeout=10),
            ("", ""),
        ]
        mock_proc.returncode = -9
        mock_popen.return_value = mock_proc

        result = run_agy_agent("slow query", agy_path=Path("/mock/agy"), timeout=10)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "timeout")
        self.assertIn("timed out", result["response"])

    @patch("services.agent_service.subprocess.Popen")
    @patch.object(Path, "is_file", return_value=True)
    @patch("services.agent_service.os.access", return_value=True)
    def test_adapter_nonzero_exit_code(self, mock_access, mock_is_file, mock_popen):
        """4. Non-zero exit code captures stderr and reports failure."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "Flag parse error: unknown option --bad")
        mock_proc.returncode = 2
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        result = run_agy_agent("bad", agy_path=Path("/mock/agy"))
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "exit_code_2")
        self.assertIn("Flag parse error", result["response"])
        self.assertEqual(result["returncode"], 2)

    @patch("services.agent_service.subprocess.Popen")
    @patch.object(Path, "is_file", return_value=True)
    @patch("services.agent_service.os.access", return_value=True)
    def test_adapter_empty_response(self, mock_access, mock_is_file, mock_popen):
        """5. Empty stdout from agent returns empty_response error."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("   \n\t  ", "")
        mock_proc.returncode = 0
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        result = run_agy_agent("silent", agy_path=Path("/mock/agy"))
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "empty_response")
        self.assertIn("empty response", result["response"])

    @patch("services.agent_service.run_agy_agent")
    def test_api_command_success_response(self, mock_agy):
        """6. POST /api/agent/command returns HTTP 200 and success=True JSON schema."""
        mock_agy.return_value = {
            "success": True,
            "response": "Найдено 3 подходящих Junior вакансии.",
            "error": None,
            "returncode": 0,
        }

        resp = self.client.post(
            "/api/agent/command",
            data=json.dumps({"command": "Найди вакансии"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.get_data(as_text=True))
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("Найдено 3", data.get("response"))
        self.assertIsNone(data.get("error"))

    @patch("services.agent_service.run_agy_agent")
    def test_api_command_error_response(self, mock_agy):
        """7. POST /api/agent/command on failure returns HTTP 500 and error details."""
        mock_agy.return_value = {
            "success": False,
            "response": "Agent request timed out after 90 seconds.",
            "error": "timeout",
            "returncode": None,
        }

        resp = self.client.post(
            "/api/agent/command",
            data=json.dumps({"command": "Сложный запрос"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 500)
        data = json.loads(resp.get_data(as_text=True))
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("status"), "error")
        self.assertEqual(data.get("error"), "timeout")
        self.assertIn("timed out", data.get("response"))

    @patch("services.agent_service.subprocess.Popen")
    @patch.object(Path, "is_file", return_value=True)
    @patch("services.agent_service.os.access", return_value=True)
    def test_prompt_not_executed_as_shell_command(self, mock_access, mock_is_file, mock_popen):
        """8. Prompt with shell metacharacters is safely passed as argv, never via shell."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("Safe response", "")
        mock_proc.returncode = 0
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        # Dangerous payload containing subshell expansion and chained commands
        malicious_input = "; rm -rf / ; $(whoami) && cat /etc/passwd | echo 'hacked'"

        run_agy_agent(malicious_input, agy_path=Path("/mock/agy"))

        # Verify subprocess.Popen was called
        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args.kwargs
        call_args = mock_popen.call_args.args[0]

        # Ensure shell=False is explicitly enforced and start_new_session is set
        self.assertFalse(call_kwargs.get("shell", False))
        self.assertTrue(call_kwargs.get("start_new_session", False))

        # Ensure the prompt is preserved as a single literal argument in argv, not executed
        self.assertEqual(call_args[0], "/mock/agy")
        self.assertEqual(call_args[1], "--dangerously-skip-permissions")
        self.assertEqual(call_args[2], "-p")
        self.assertEqual(call_args[3], malicious_input)

    @patch("services.agent_service.subprocess.Popen")
    @patch.object(Path, "is_file", return_value=True)
    @patch("services.agent_service.os.access", return_value=True)
    def test_adapter_includes_dangerously_skip_permissions_flag(self, mock_access, mock_is_file, mock_popen):
        """9. Regression test: ensures --dangerously-skip-permissions flag is supplied."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("Ответ", "")
        mock_proc.returncode = 0
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        run_agy_agent("тест", agy_path=Path("/mock/agy"))
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args.args[0]
        self.assertIn("--dangerously-skip-permissions", cmd)

    @patch("services.agent_service.subprocess.Popen")
    @patch.object(Path, "is_file", return_value=True)
    @patch("services.agent_service.os.access", return_value=True)
    def test_adapter_empty_stdout_captures_stderr_diagnostic(self, mock_access, mock_is_file, mock_popen):
        """10. Regression test: empty stdout extracts stderr diagnostic message."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "jetski: no output produced — permission auto-denied.")
        mock_proc.returncode = 0
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        result = run_agy_agent("тест", agy_path=Path("/mock/agy"))
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "empty_response")
        self.assertIn("Details: jetski: no output produced", result["response"])

    def test_conversational_prompt_builder_includes_safeguards(self):
        """11. Conversational prompt builder embeds read-only instructions and disables test suites."""
        prompt = build_conversational_prompt("What is my tech stack?")
        self.assertIn("What is my tech stack?", prompt)
        self.assertIn("Do NOT modify any files", prompt)
        self.assertIn("Do NOT run tests", prompt)
        self.assertIn("Zero Fabrication", prompt)

    def test_workflow_prompt_builder_includes_workflow_bounds(self):
        """12. Workflow prompt builder enforces skill boundary without running unrelated tests."""
        prompt = build_workflow_prompt("/apply")
        self.assertIn("/apply", prompt)
        self.assertIn("Do NOT run the repository test suite", prompt)
        self.assertIn("Zero Fabrication", prompt)

    @patch("services.agent_service.run_agy_agent")
    def test_profile_update_command_handles_portfolio_without_agy(self, mock_agy):
        """13. /profile portfolio: URL updates canonical profile directly without executing agy or tests."""
        result = handle_agent_command("/profile portfolio: https://example.com/portfolio")
        mock_agy.assert_not_called()
        self.assertTrue(result["success"])
        self.assertEqual(result["action_taken"], "profile_updated")
        self.assertIn("Portfolio", result["response"])
        self.assertIn("https://example.com/portfolio", result["response"])

    @patch("services.agent_service.run_agy_agent")
    def test_profile_view_command_returns_summary_without_agy(self, mock_agy):
        """14. /profile view returns canonical profile summary directly without agy."""
        result = handle_agent_command("/profile")
        mock_agy.assert_not_called()
        self.assertTrue(result["success"])
        self.assertEqual(result["action_taken"], "profile_viewed")
        self.assertIn("Name:", result["response"])
        self.assertIn("Canonical Candidate Profile Summary", result["response"])

    @patch("services.agent_service.run_agy_agent")
    def test_status_command_returns_diagnostics_without_agy(self, mock_agy):
        """15. /status command returns runtime diagnostics directly without executing agy."""
        result = handle_agent_command("/status")
        mock_agy.assert_not_called()
        self.assertTrue(result["success"])
        self.assertEqual(result["action_taken"], "status_check")
        self.assertIn("Agent & Pipeline Status", result["response"])

    @patch("services.agent_service.run_agy_agent")
    def test_conversational_command_wraps_prompt_with_safeguards(self, mock_agy):
        """16. Normal conversational queries wrap user prompt with read-only instructions before invoking agy."""
        mock_agy.return_value = {
            "success": True,
            "response": "У вас отличный стек: React, TypeScript, NestJS.",
            "error": None,
            "returncode": 0,
        }
        result = handle_agent_command("Расскажи, кто я и какие у меня основные навыки")
        mock_agy.assert_called_once()
        sent_prompt = mock_agy.call_args.args[0]
        self.assertIn("Расскажи, кто я и какие у меня основные навыки", sent_prompt)
        self.assertIn("Do NOT modify any files", sent_prompt)
        self.assertIn("Do NOT run tests", sent_prompt)
        self.assertTrue(result["success"])

    @patch("services.agent_service.run_agy_agent")
    def test_scrape_command_routed_to_workflow(self, mock_agy):
        """17. Regression test: /scrape is routed to workflow_dispatched with WORKFLOW_TIMEOUT_SECONDS."""
        mock_agy.return_value = {
            "success": True,
            "response": "| Title | Company |\n| Frontend | Test |",
            "error": None,
            "returncode": 0,
        }
        result = handle_agent_command("/scrape")
        mock_agy.assert_called_once()
        sent_prompt = mock_agy.call_args.args[0]
        timeout_arg = mock_agy.call_args.kwargs.get("timeout")
        self.assertIn("You are executing the /scrape workflow", sent_prompt)
        self.assertEqual(timeout_arg, WORKFLOW_TIMEOUT_SECONDS)
        self.assertEqual(result["action_taken"], "workflow_dispatched")
        self.assertTrue(result["success"])

    @patch("services.agent_service.run_agy_agent")
    def test_conversational_queries_do_not_trigger_scrape(self, mock_agy):
        """18. Regression test: conversational queries are not dispatched as workflows."""
        mock_agy.return_value = {
            "success": True,
            "response": "Here is information about your skills.",
            "error": None,
            "returncode": 0,
        }
        result = handle_agent_command("scrape some jobs for me please")
        mock_agy.assert_called_once()
        sent_prompt = mock_agy.call_args.args[0]
        timeout_arg = mock_agy.call_args.kwargs.get("timeout")
        self.assertNotIn("You are executing the /scrape workflow", sent_prompt)
        self.assertIn("You are answering a user through the Web UI Agent chat", sent_prompt)
        self.assertEqual(timeout_arg, DEFAULT_TIMEOUT_SECONDS)
        self.assertEqual(result["action_taken"], "agent_executed")

    def test_workflow_prompt_bounds_scrape_budget(self):
        """19. Regression test: build_workflow_prompt bounds search budget and gates for /scrape."""
        prompt = build_workflow_prompt("/scrape")
        self.assertIn("1-2 targeted search_web queries", prompt)
        self.assertIn("Junior Frontend", prompt)
        self.assertIn("Junior Fullstack", prompt)
        self.assertIn("Strictly do NOT write or run ad-hoc Python crawler scripts", prompt)
        self.assertIn("strictly exclude internships/staże", prompt)
        self.assertIn("Do NOT run test suites", prompt)

    @patch("services.agent_service.os.killpg")
    @patch("services.agent_service.os.getpgid", return_value=54321)
    @patch("services.agent_service.subprocess.Popen")
    @patch.object(Path, "is_file", return_value=True)
    @patch("services.agent_service.os.access", return_value=True)
    def test_timeout_terminates_process_group_cleanly(
        self, mock_access, mock_is_file, mock_popen, mock_getpgid, mock_killpg
    ):
        """20. Regression test: timeout triggers os.killpg(pgid, SIGKILL) to reap all child processes."""
        import signal
        mock_proc = MagicMock()
        mock_proc.pid = 54321
        mock_proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd=["agy", "-p", "scrape"], timeout=180),
            ("partial stdout output", "diagnostic stderr output"),
        ]
        mock_proc.returncode = -9
        mock_popen.return_value = mock_proc

        result = run_agy_agent("long workflow", agy_path=Path("/mock/agy"), timeout=180)
        mock_getpgid.assert_called_once_with(54321)
        mock_killpg.assert_called_once_with(54321, signal.SIGKILL)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "timeout")
        self.assertIn("Details: diagnostic stderr output", result["response"])
        self.assertEqual(result["partial_stdout"], "partial stdout output")

    @patch("services.agent_service.run_agy_agent")
    def test_rank_command_routed_to_workflow(self, mock_agy):
        """21. Regression test: /rank is routed to workflow_dispatched with WORKFLOW_TIMEOUT_SECONDS."""
        mock_agy.return_value = {
            "success": True,
            "response": "| # | Score | Band | Title | Company |\n| 1 | 82/100 | Strong Fit | Fullstack | Citi |",
            "error": None,
            "returncode": 0,
        }
        result = handle_agent_command("/rank")
        mock_agy.assert_called_once()
        sent_prompt = mock_agy.call_args.args[0]
        timeout_arg = mock_agy.call_args.kwargs.get("timeout")
        self.assertIn("You are executing the /rank workflow", sent_prompt)
        self.assertEqual(timeout_arg, WORKFLOW_TIMEOUT_SECONDS)
        self.assertEqual(result["action_taken"], "workflow_dispatched")
        self.assertTrue(result["success"])

    def test_workflow_prompt_bounds_rank_workflow_safety_and_contracts(self):
        """22. Regression test: build_workflow_prompt bounds /rank to local evaluation without network tools."""
        prompt = build_workflow_prompt("/rank")
        self.assertIn("You are executing the /rank workflow", prompt)
        # Forbids network fetching and web research
        self.assertIn("Do NOT fetch job URLs", prompt)
        self.assertIn("Do NOT call `read_url_content` or `search_web`", prompt)
        self.assertIn("Do NOT use `curl`, browser, or network tools", prompt)
        self.assertIn("Do NOT consult `09-web-research.md`", prompt)
        self.assertIn("Do NOT retry Cloudflare/403/404 errors", prompt)
        # Requires cached data
        self.assertIn("Read candidates once", prompt)
        self.assertIn("Rank ONLY jobs with status `new`", prompt)
        # Requires 04-job-evaluation.md
        self.assertIn(".claude/skills/job-application-assistant/04-job-evaluation.md", prompt)
        # Exact JSON contract & scores dimensions
        self.assertIn('"key": "job-key"', prompt)
        self.assertIn('"scores": {', prompt)
        self.assertIn('"technical": 80', prompt)
        self.assertIn('"experience": 70', prompt)
        self.assertIn('"behavioral": 75', prompt)
        self.assertIn('"career": 80', prompt)
        self.assertIn("technical, experience, behavioral, career", prompt)
        # Strengths & gaps limited to 2 bullets
        self.assertIn("strengths`: maximum 2 short bullets", prompt)
        self.assertIn("gaps`: maximum 2 short bullets", prompt)
        # Forbids inspecting rank_state.py source
        self.assertIn("Do NOT inspect `tools/rank_state.py` source code", prompt)
        self.assertIn("Do NOT inspect `cmd_apply`", prompt)
        # Candidate profile facts embedded (avoid profile read)
        self.assertIn("Languages: Ukrainian (Native), Russian (Native), English (B1), Polish (B1)", prompt)
        self.assertIn("do not re-read 01-candidate-profile.md", prompt)
        # Requires writing scratch/rank_results.json and apply
        self.assertIn("scratch/rank_results.json", prompt)
        self.assertIn("python3 tools/rank_state.py apply --results scratch/rank_results.json", prompt)
        # Concise final output
        self.assertIn("Return ONLY a concise Markdown shortlist table", prompt)
        # Forbids invoking other workflows or running tests
        self.assertIn("Do NOT invoke other workflows such as /scrape or /apply", prompt)
        self.assertIn("Do NOT run tests", prompt)


if __name__ == "__main__":
    unittest.main()

