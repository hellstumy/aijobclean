"""Tests for the interactive setup wizard and skill checklist parser."""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from setup_wizard import (
    find_skills_for_role,
    generate_skills_checklist,
    parse_skills_checklist,
    update_profile_files,
    is_setup_completed,
    CHECKLIST_FILE,
    CONFIGURED_MARKER,
)


class TestSetupWizard(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.checklist_backup = None
        if CHECKLIST_FILE.is_file():
            self.checklist_backup = CHECKLIST_FILE.read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if self.checklist_backup is not None:
            CHECKLIST_FILE.write_text(self.checklist_backup, encoding="utf-8")
        elif CHECKLIST_FILE.is_file():
            CHECKLIST_FILE.unlink()
        if CONFIGURED_MARKER.is_file():
            CONFIGURED_MARKER.unlink()

    def test_find_skills_for_known_roles(self):
        """Role matcher returns specialized skill tracks for common roles."""
        fe = find_skills_for_role("Junior Frontend Developer")
        self.assertIn("React", fe["programming"])
        self.assertIn("TypeScript", fe["programming"])

        py = find_skills_for_role("Python Backend Engineer")
        self.assertIn("FastAPI", py["programming"])
        self.assertIn("PostgreSQL", py["databases"])

        devops = find_skills_for_role("DevOps / SRE")
        self.assertIn("Docker", devops["tools"])
        self.assertIn("Kubernetes (K8s)", devops["tools"])

    def test_generate_and_parse_skills_checklist(self):
        """Generates checklist and parses marked items with [x] or (y)."""
        gen_file = generate_skills_checklist("Frontend Developer", "Jane Doe")
        self.assertTrue(gen_file.is_file())
        
        content = gen_file.read_text(encoding="utf-8")
        self.assertIn("Jane Doe", content)
        self.assertIn("Frontend Developer", content)
        self.assertIn("TypeScript", content)

        # Mark some skills with [x] and some with (y)
        modified_content = content.replace("- [ ] React (y/n)", "- [x] React")
        modified_content = modified_content.replace("- [ ] TypeScript (y/n)", "- [ ] TypeScript (y)")
        modified_content = modified_content.replace("- [ ] Vite (y/n)", "- [X] Vite")
        gen_file.write_text(modified_content, encoding="utf-8")

        parsed = parse_skills_checklist()
        self.assertIn("React", parsed["programming"])
        self.assertIn("TypeScript", parsed["programming"])
        self.assertIn("Vite", parsed["programming"])
        self.assertNotIn("Next.js", parsed["programming"])

    def test_is_setup_completed_flag(self):
        """Detects whether setup is completed based on marker or placeholders."""
        if CONFIGURED_MARKER.is_file():
            CONFIGURED_MARKER.unlink()
        
        # When clean template has [YOUR_NAME]
        self.assertFalse(is_setup_completed())

        # Once marker exists
        CONFIGURED_MARKER.write_text("candidate=Test User\n", encoding="utf-8")
        self.assertTrue(is_setup_completed())


if __name__ == "__main__":
    unittest.main()
