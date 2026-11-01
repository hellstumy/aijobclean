"""Workflow contract tests for Antigravity core pipeline transitions.

Verifies the documented data contracts and state transitions across:
  setup -> scrape -> rank -> apply -> interview -> outcome -> setup

Checks that:
1. All referenced input/output files and templates exist on disk.
2. State fields, caches, and tracker schemas are mutually consistent.
3. Transition rules and boundaries between skills are maintained.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / ".agents" / "skills"

TRACKER_HEADER = (
    "date,company,sector,role,role_type,channel,status,"
    "contact_person,fit_rating,notes,cv_file,cover_letter_file,source,deadline"
)

CANONICAL_TRACKER_STATUSES = {
    "drafted",
    "applied",
    "interview",
    "offer",
    "hired",
    "rejected",
    "no_response",
    "offer_declined",
    "withdrawn",
}


class TestSetupToScrapeContract(unittest.TestCase):
    """Guards contract between /setup output and /scrape input."""

    def setUp(self):
        self.setup_skill = (SKILLS / "setup" / "SKILL.md").read_text(encoding="utf-8")
        self.scrape_skill = (SKILLS / "scrape" / "SKILL.md").read_text(encoding="utf-8")

    def test_search_queries_and_profile_references_exist(self):
        """Files populated by setup and consumed by scrape must exist."""
        queries_file = REPO / ".claude" / "skills" / "job-scraper" / "search-queries.md"
        profile_file = REPO / ".claude" / "skills" / "job-application-assistant" / "01-candidate-profile.md"
        evaluation_file = REPO / ".claude" / "skills" / "job-application-assistant" / "04-job-evaluation.md"

        self.assertTrue(queries_file.is_file(), "search-queries.md must exist")
        self.assertTrue(profile_file.is_file(), "01-candidate-profile.md must exist")
        self.assertTrue(evaluation_file.is_file(), "04-job-evaluation.md must exist")

        # Verify scrape references these exact dependencies
        self.assertIn("search-queries.md", self.scrape_skill)
        self.assertIn("01-candidate-profile.md", self.scrape_skill)
        self.assertIn("04-job-evaluation.md", self.scrape_skill)

    def test_language_gate_and_query_categories_consistency(self):
        """Languages and queries defined in profile/queries are consumed by scrape."""
        profile_text = (REPO / ".claude" / "skills" / "job-application-assistant" / "01-candidate-profile.md").read_text(encoding="utf-8")
        queries_text = (REPO / ".claude" / "skills" / "job-scraper" / "search-queries.md").read_text(encoding="utf-8")

        self.assertIn("Languages", profile_text, "Profile must contain Languages section for scraping filter")
        self.assertIn("Priority 1", queries_text, "search-queries.md must define Priority query tiers")


class TestScrapeToRankContract(unittest.TestCase):
    """Guards contract between /scrape output and /rank input."""

    def setUp(self):
        self.scrape_skill = (SKILLS / "scrape" / "SKILL.md").read_text(encoding="utf-8")
        self.rank_skill = (SKILLS / "rank" / "SKILL.md").read_text(encoding="utf-8")

    def test_seen_jobs_cache_reference_and_tools_exist(self):
        """seen_jobs.json cache and rank_state.py tool must be mutually referenced."""
        rank_state_tool = REPO / "tools" / "rank_state.py"
        self.assertTrue(rank_state_tool.is_file(), "tools/rank_state.py must exist")

        self.assertIn("job_scraper/seen_jobs.json", self.scrape_skill)
        self.assertIn("job_scraper/seen_jobs.json", self.rank_skill)
        self.assertIn("tools/rank_state.py", self.rank_skill)

    def test_deduplication_tracker_reference(self):
        """Both scrape and rank must reference job_search_tracker.csv for deduplication."""
        self.assertIn("job_search_tracker.csv", self.scrape_skill)
        self.assertIn("job_search_tracker.csv", self.rank_skill)


class TestRankToApplyContract(unittest.TestCase):
    """Guards contract between /rank output and /apply input."""

    def setUp(self):
        self.rank_skill = (SKILLS / "rank" / "SKILL.md").read_text(encoding="utf-8")
        self.apply_skill = (SKILLS / "apply" / "SKILL.md").read_text(encoding="utf-8")

    def test_required_templates_and_verification_tools_exist(self):
        """Templates and PDF verification tools referenced in apply must exist on disk."""
        tools_and_templates = [
            REPO / "tools" / "verify_pdf.py",
            REPO / "tools" / "verify_layout.py",
            REPO / ".claude" / "skills" / "job-application-assistant" / "03-writing-style.md",
            REPO / ".claude" / "skills" / "job-application-assistant" / "05-cv-templates.md",
            REPO / ".claude" / "skills" / "job-application-assistant" / "06-cover-letter-templates.md",
            REPO / "cover_letters" / "cover.cls",
            REPO / "cv" / "main_example.tex",
        ]
        for path in tools_and_templates:
            self.assertTrue(path.is_file(), f"Required file must exist: {path}")

        # Check references in apply skill
        self.assertIn("verify_pdf.py", self.apply_skill)
        self.assertIn("verify_layout.py", self.apply_skill)
        self.assertIn("03-writing-style.md", self.apply_skill)
        self.assertIn("05-cv-templates.md", self.apply_skill)
        self.assertIn("06-cover-letter-templates.md", self.apply_skill)

    def test_fit_score_tiers_match(self):
        """Score rating vocabulary in rank must match apply triage expectations."""
        self.assertIn("Strong Fit", self.rank_skill)
        self.assertIn("Good Fit", self.rank_skill)
        self.assertIn("Strong", self.apply_skill)
        self.assertIn("Good", self.apply_skill)


class TestApplyToInterviewContract(unittest.TestCase):
    """Guards contract between /apply output and /interview input."""

    def setUp(self):
        self.apply_skill = (SKILLS / "apply" / "SKILL.md").read_text(encoding="utf-8")
        self.interview_skill = (SKILLS / "interview" / "SKILL.md").read_text(encoding="utf-8")

    def test_interview_prep_source_file_exists(self):
        """07-interview-prep.md must exist and be referenced by interview skill."""
        prep_file = REPO / ".claude" / "skills" / "job-application-assistant" / "07-interview-prep.md"
        self.assertTrue(prep_file.is_file(), "07-interview-prep.md must exist")
        self.assertIn("07-interview-prep.md", self.interview_skill)

    def test_interview_reads_applied_tracker_rows_and_archives(self):
        """interview skill must read job_search_tracker.csv and application archives."""
        self.assertIn("job_search_tracker.csv", self.interview_skill)
        self.assertIn("documents/applications/", self.interview_skill)
        self.assertIn("documents/applications/", self.apply_skill)


class TestApplyToOutcomeContract(unittest.TestCase):
    """Guards contract between /apply output and /outcome input."""

    def setUp(self):
        self.apply_skill = (SKILLS / "apply" / "SKILL.md").read_text(encoding="utf-8")
        self.outcome_skill = (SKILLS / "outcome" / "SKILL.md").read_text(encoding="utf-8")

    def test_tracker_header_is_consistent(self):
        """Both apply and outcome must use the canonical tracker CSV header."""
        self.assertIn(TRACKER_HEADER, self.apply_skill)
        self.assertIn(TRACKER_HEADER, self.outcome_skill)

    def test_drafted_status_lifecycle_contract(self):
        """apply writes 'drafted' rows, and outcome handles drafted rows without chasing."""
        self.assertIn("drafted", self.apply_skill)
        self.assertIn("drafted", self.outcome_skill)
        # outcome explicitly isolates drafted rows from days-quiet count
        self.assertIn("Drafted, not yet submitted", self.outcome_skill)

    def test_outcome_enforces_safe_notes_rule(self):
        """outcome must enforce no commas, quotes, or newlines in tracker notes."""
        self.assertIn("no commas", self.outcome_skill)
        self.assertIn("no double quotes", self.outcome_skill)
        self.assertIn("no line breaks", self.outcome_skill)


class TestOutcomeToSetupContract(unittest.TestCase):
    """Guards contract between /outcome output and /setup recalibration input."""

    def setUp(self):
        self.outcome_skill = (SKILLS / "outcome" / "SKILL.md").read_text(encoding="utf-8")
        self.setup_skill = (SKILLS / "setup" / "SKILL.md").read_text(encoding="utf-8")

    def test_outcome_schema_documented_and_shared(self):
        """outcome.md schema written by outcome must match schema read by setup Path A."""
        readme = (REPO / "documents" / "README.md").read_text(encoding="utf-8")

        # Schema elements in documents/README.md
        self.assertIn("# Outcome: <Company> — <Role>", readme)
        self.assertIn("**Status:**", readme)
        self.assertIn("## Interview stages reached", readme)
        self.assertIn("## Notes", readme)

        # Same schema elements in outcome SKILL.md
        self.assertIn("# Outcome: <Company> — <Role>", self.outcome_skill)
        self.assertIn("**Status:**", self.outcome_skill)
        self.assertIn("## Interview stages reached", self.outcome_skill)
        self.assertIn("## Notes", self.outcome_skill)

    def test_calibration_handoff_trigger(self):
        """outcome must suggest running /setup Path A when 3+ applications resolve."""
        self.assertIn("Step 5: Calibration Handoff", self.outcome_skill)
        self.assertIn("Run `/setup` (Path A)", self.outcome_skill)
        self.assertIn("Path A", self.setup_skill)


if __name__ == "__main__":
    unittest.main()

