"""Contract tests for Google Antigravity migration architecture and Source of Truth.

Verifies:
1. GEMINI.md exists, is a Thin-Pointer, references all 5 canonical Source of Truth
   files, contains the canonical directive, and has no candidate personal data or placeholders.
2. The 5 canonical Source of Truth files exist, are non-empty, and maintain expected structure.
3. The 6 core migrated Antigravity Skills (setup, scrape, rank, apply, interview, outcome)
   exist with valid frontmatter.
4. Migrated skills do not leak candidate personal data (emails, phone numbers).
5. setup SKILL.md restricts normal setup writes to approved files and explicitly
   does NOT instruct setup to modify GEMINI.md, AGENTS.md, or CLAUDE.md.
"""

import re
import unittest
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parent.parent

CANONICAL_SOURCE_OF_TRUTH_FILES = [
    REPO / ".claude" / "skills" / "job-application-assistant" / "01-candidate-profile.md",
    REPO / ".claude" / "skills" / "job-application-assistant" / "02-behavioral-profile.md",
    REPO / ".claude" / "skills" / "job-application-assistant" / "04-job-evaluation.md",
    REPO / ".claude" / "skills" / "job-application-assistant" / "07-interview-prep.md",
    REPO / "cv" / "main_example.tex",
]

MIGRATED_SKILL_NAMES = [
    "setup",
    "scrape",
    "rank",
    "apply",
    "interview",
    "outcome",
]


class TestGeminiThinPointer(unittest.TestCase):
    """Guards for GEMINI.md as the Antigravity Thin-Pointer entry point."""

    def setUp(self):
        self.gemini_path = REPO / "GEMINI.md"
        self.assertTrue(self.gemini_path.is_file(), "GEMINI.md must exist at repository root")
        self.text = self.gemini_path.read_text(encoding="utf-8")

    def test_gemini_md_is_thin_pointer(self):
        """GEMINI.md must remain concise (Thin-Pointer) and not inline full profiles."""
        lines = self.text.splitlines()
        self.assertLess(
            len(lines),
            120,
            f"GEMINI.md must remain a thin pointer (<120 lines), found {len(lines)} lines",
        )
        self.assertLess(
            len(self.text.encode("utf-8")),
            12000,
            f"GEMINI.md must not become a bloated file (<12KB), size is {len(self.text.encode('utf-8'))} bytes",
        )

    def test_gemini_md_references_all_five_source_of_truth_files(self):
        """GEMINI.md must reference all 5 canonical Source of Truth files."""
        for path in CANONICAL_SOURCE_OF_TRUTH_FILES:
            rel_name = path.name
            self.assertIn(
                rel_name,
                self.text,
                f"GEMINI.md must reference canonical file {rel_name}",
            )

    def test_gemini_md_contains_source_of_truth_directive(self):
        """GEMINI.md must declare explicit directive enforcing Source of Truth files."""
        self.assertIn(
            "Source of Truth",
            self.text,
            "GEMINI.md must designate the Source of Truth section",
        )
        # Direct instruction in Russian pointing to canonical files
        self.assertIn(
            "01-candidate-profile.md",
            self.text,
        )
        self.assertIn(
            "02-behavioral-profile.md",
            self.text,
        )
        self.assertIn(
            "04-job-evaluation.md",
            self.text,
        )
        self.assertIn(
            "07-interview-prep.md",
            self.text,
        )
        self.assertIn(
            "cv/main_example.tex",
            self.text,
        )

    def test_gemini_md_does_not_contain_candidate_personal_data_or_placeholders(self):
        """GEMINI.md must not contain candidate personal data or template placeholders."""
        placeholder_tokens = [
            "[YOUR_NAME]",
            "[YOUR_EMAIL]",
            "[YOUR_PHONE]",
            "[YOUR_ADDRESS]",
            "[Candidate Name]",
            "[Your Name]",
        ]
        for token in placeholder_tokens:
            self.assertNotIn(
                token,
                self.text,
                f"GEMINI.md must not contain template placeholder token {token}",
            )

        # No real email addresses
        email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        emails = email_pattern.findall(self.text)
        self.assertEqual(
            emails,
            [],
            f"GEMINI.md must not contain hardcoded email addresses, found: {emails}",
        )

        # No phone numbers (+XX XXXXXXXX)
        phone_pattern = re.compile(r"\+\d{1,3}[-\s\d]{7,}")
        phones = phone_pattern.findall(self.text)
        self.assertEqual(
            phones,
            [],
            f"GEMINI.md must not contain hardcoded phone numbers, found: {phones}",
        )


class TestCanonicalSourceOfTruth(unittest.TestCase):
    """Guards asserting that the 5 canonical Source of Truth files remain canonical."""

    def test_canonical_files_exist_and_non_empty(self):
        """All 5 canonical Source of Truth files must exist on disk and be non-empty."""
        for path in CANONICAL_SOURCE_OF_TRUTH_FILES:
            self.assertTrue(
                path.is_file(),
                f"Canonical Source of Truth file must exist: {path}",
            )
            size = path.stat().st_size
            self.assertGreater(
                size,
                500,
                f"Canonical file {path.name} must not be empty or stub (size: {size} bytes)",
            )

    def test_canonical_files_contain_expected_structural_sections(self):
        """Canonical files must preserve their required domain structure."""
        p1 = (REPO / ".claude/skills/job-application-assistant/01-candidate-profile.md").read_text(encoding="utf-8")
        self.assertIn("Languages", p1)
        self.assertIn("Experience", p1)

        p2 = (REPO / ".claude/skills/job-application-assistant/02-behavioral-profile.md").read_text(encoding="utf-8")
        self.assertIn("Behavioral Profile", p2)

        p4 = (REPO / ".claude/skills/job-application-assistant/04-job-evaluation.md").read_text(encoding="utf-8")
        self.assertIn("Language Gate", p4)
        self.assertIn("Thresholds", p4)
        self.assertIn("Dimensions", p4)

        p7 = (REPO / ".claude/skills/job-application-assistant/07-interview-prep.md").read_text(encoding="utf-8")
        self.assertIn("STAR", p7)

        tex = (REPO / "cv/main_example.tex").read_text(encoding="utf-8")
        self.assertIn(r"\documentclass", tex)
        self.assertIn(r"\begin{document}", tex)


class TestMigratedSkills(unittest.TestCase):
    """Guards for all 6 core Antigravity Skills."""

    def test_all_migrated_skills_exist(self):
        """Each core skill must have its SKILL.md under .agents/skills/<name>/."""
        for name in MIGRATED_SKILL_NAMES:
            skill_path = REPO / ".agents" / "skills" / name / "SKILL.md"
            self.assertTrue(
                skill_path.is_file(),
                f"Antigravity skill {name} must exist at {skill_path}",
            )

    def test_migrated_skills_have_valid_frontmatter(self):
        """Each migrated SKILL.md must have valid YAML frontmatter matching its name."""
        for name in MIGRATED_SKILL_NAMES:
            skill_path = REPO / ".agents" / "skills" / name / "SKILL.md"
            text = skill_path.read_text(encoding="utf-8")
            self.assertTrue(
                text.startswith("---\n"),
                f"{name}/SKILL.md must start with YAML frontmatter delimiters",
            )
            end = text.find("\n---", 4)
            self.assertNotEqual(end, -1, f"{name}/SKILL.md must have closing frontmatter delimiter")
            data = yaml.safe_load(text[4:end])
            self.assertIsInstance(data, dict, f"{name}/SKILL.md frontmatter must parse to mapping")
            self.assertEqual(data.get("name"), name, f"Frontmatter 'name' must match folder name '{name}'")
            self.assertTrue(
                bool(data.get("description")),
                f"{name}/SKILL.md frontmatter must contain non-empty description",
            )


class TestCandidateDataIsolation(unittest.TestCase):
    """Guards ensuring no personal candidate data leaked into migrated SKILL files."""

    def test_no_hardcoded_personal_data_in_migrated_skills(self):
        """No migrated skill may contain hardcoded personal contact details."""
        email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        phone_pattern = re.compile(r"\+\d{1,3}[-\s\d]{7,}")

        for name in MIGRATED_SKILL_NAMES:
            skill_path = REPO / ".agents" / "skills" / name / "SKILL.md"
            text = skill_path.read_text(encoding="utf-8")

            # Ignore ko-fi link in outcome confirmation
            clean_text = text.replace("https://ko-fi.com/madslorentzen", "")

            emails = email_pattern.findall(clean_text)
            self.assertEqual(
                emails,
                [],
                f"{name}/SKILL.md must not contain hardcoded emails, found: {emails}",
            )

            phones = phone_pattern.findall(clean_text)
            self.assertEqual(
                phones,
                [],
                f"{name}/SKILL.md must not contain hardcoded phone numbers, found: {phones}",
            )


class TestSetupWriteBoundary(unittest.TestCase):
    """Guards for setup SKILL.md write boundaries."""

    def setUp(self):
        self.setup_path = REPO / ".agents" / "skills" / "setup" / "SKILL.md"
        self.text = self.setup_path.read_text(encoding="utf-8")

    def test_setup_restricts_writes_to_approved_files(self):
        """setup SKILL.md must explicitly restrict its writes to the approved files."""
        self.assertIn("Step 3: Generate Profile Files", self.text)
        approved_files = [
            "01-candidate-profile.md",
            "02-behavioral-profile.md",
            "04-job-evaluation.md",
            "07-interview-prep.md",
            "cv/main_example.tex",
            "05-cv-templates.md",
            "06-cover-letter-templates.md",
            "search-queries.md",
        ]
        for f in approved_files:
            self.assertIn(
                f,
                self.text,
                f"setup SKILL.md must explicitly name approved file {f}",
            )

    def test_setup_does_not_modify_guideline_pointers(self):
        """setup SKILL.md must NOT instruct setup to modify GEMINI.md, AGENTS.md, or CLAUDE.md."""
        self.assertIn("GEMINI.md", self.text)
        self.assertIn("AGENTS.md", self.text)
        self.assertIn("CLAUDE.md", self.text)
        # Check explicit non-modification instruction
        step3_idx = self.text.find("## Step 3: Generate Profile Files")
        step3_text = self.text[step3_idx:]
        self.assertRegex(
            step3_text,
            re.compile(r"NOT modified during normal setup", re.IGNORECASE),
            "setup SKILL.md Step 3 must declare that pointer files are NOT modified during normal setup",
        )


if __name__ == "__main__":
    unittest.main()
