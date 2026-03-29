"""Tests for best practice checks (BP1-BP15).

TDD Red Phase — these tests define expected behavior for the
best_practices module before any implementation exists.
"""
import unittest
from skill_inspector.best_practices import (
    check_bp1_filename,
    check_bp2_folder_name,
    check_bp3_no_readme,
    check_bp4_description_completeness,
    check_bp5_description_length,
    check_bp6_no_xml_in_frontmatter,
    check_bp7_no_forbidden_names,
    check_bp8_body_length,
    check_bp9_specific_instructions,
    check_bp10_error_handling_section,
    check_bp11_directive_density,
    check_bp12_progressive_disclosure,
    check_bp13_resource_references,
    check_bp14_description_trigger_phrases,
    check_bp15_repeated_patterns,
    run_all_checks,
)


class TestBP1Filename(unittest.TestCase):
    """SKILL.md filename must be exactly SKILL.md (case-sensitive)."""

    def test_correct_filename(self):
        result = check_bp1_filename("SKILL.md")
        self.assertTrue(result["passed"])

    def test_lowercase_fails(self):
        result = check_bp1_filename("skill.md")
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "error")

    def test_uppercase_md_fails(self):
        result = check_bp1_filename("SKILL.MD")
        self.assertFalse(result["passed"])

    def test_wrong_name_fails(self):
        result = check_bp1_filename("README.md")
        self.assertFalse(result["passed"])


class TestBP2FolderName(unittest.TestCase):
    """Folder name must be kebab-case (no spaces, underscores, capitals)."""

    def test_kebab_case_passes(self):
        result = check_bp2_folder_name("my-cool-skill")
        self.assertTrue(result["passed"])

    def test_single_word_passes(self):
        result = check_bp2_folder_name("deploy")
        self.assertTrue(result["passed"])

    def test_spaces_fail(self):
        result = check_bp2_folder_name("my cool skill")
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "error")

    def test_underscores_fail(self):
        result = check_bp2_folder_name("my_cool_skill")
        self.assertFalse(result["passed"])

    def test_capitals_fail(self):
        result = check_bp2_folder_name("MyCoolSkill")
        self.assertFalse(result["passed"])

    def test_camelcase_fails(self):
        result = check_bp2_folder_name("myCoolSkill")
        self.assertFalse(result["passed"])


class TestBP3NoReadme(unittest.TestCase):
    """No README.md inside skill folder."""

    def test_no_readme_passes(self):
        files = ["SKILL.md", "scripts/build.py", "references/guide.md"]
        result = check_bp3_no_readme(files)
        self.assertTrue(result["passed"])

    def test_readme_present_fails(self):
        files = ["SKILL.md", "README.md"]
        result = check_bp3_no_readme(files)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "error")

    def test_readme_case_insensitive(self):
        files = ["SKILL.md", "readme.md"]
        result = check_bp3_no_readme(files)
        self.assertFalse(result["passed"])


class TestBP4DescriptionCompleteness(unittest.TestCase):
    """Description must include both what it does and when to trigger."""

    def test_complete_description_passes(self):
        desc = "Analyzes Figma design files and generates developer handoff documentation. Use when user uploads .fig files, asks for design specs, or mentions design-to-code handoff."
        result = check_bp4_description_completeness(desc)
        self.assertTrue(result["passed"])

    def test_missing_trigger_fails(self):
        desc = "Creates sophisticated multi-page documentation systems."
        result = check_bp4_description_completeness(desc)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "error")

    def test_empty_description_fails(self):
        result = check_bp4_description_completeness("")
        self.assertFalse(result["passed"])

    def test_only_trigger_no_what(self):
        desc = "Use when user asks about deployment."
        result = check_bp4_description_completeness(desc)
        self.assertFalse(result["passed"])


class TestBP5DescriptionLength(unittest.TestCase):
    """Description under 1024 characters."""

    def test_short_description_passes(self):
        result = check_bp5_description_length("A short description.")
        self.assertTrue(result["passed"])

    def test_exactly_1024_passes(self):
        result = check_bp5_description_length("x" * 1024)
        self.assertTrue(result["passed"])

    def test_over_1024_fails(self):
        result = check_bp5_description_length("x" * 1025)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "error")


class TestBP6NoXmlInFrontmatter(unittest.TestCase):
    """No XML angle brackets in frontmatter."""

    def test_clean_frontmatter_passes(self):
        fm = "name: my-skill\ndescription: Does cool stuff"
        result = check_bp6_no_xml_in_frontmatter(fm)
        self.assertTrue(result["passed"])

    def test_angle_brackets_fail(self):
        fm = "name: my-skill\ndescription: Does <cool> stuff"
        result = check_bp6_no_xml_in_frontmatter(fm)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "error")

    def test_backtick_code_with_brackets_still_fails(self):
        fm = "name: my-skill\ndescription: Use `<tag>` in output"
        result = check_bp6_no_xml_in_frontmatter(fm)
        self.assertFalse(result["passed"])


class TestBP7NoForbiddenNames(unittest.TestCase):
    """No 'claude' or 'anthropic' in skill name."""

    def test_clean_name_passes(self):
        result = check_bp7_no_forbidden_names("deploy-helper")
        self.assertTrue(result["passed"])

    def test_claude_in_name_fails(self):
        result = check_bp7_no_forbidden_names("claude-helper")
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "error")

    def test_anthropic_in_name_fails(self):
        result = check_bp7_no_forbidden_names("anthropic-tools")
        self.assertFalse(result["passed"])

    def test_case_insensitive(self):
        result = check_bp7_no_forbidden_names("Claude-Deploy")
        self.assertFalse(result["passed"])


class TestBP8BodyLength(unittest.TestCase):
    """SKILL.md body under 500 lines."""

    def test_short_body_passes(self):
        body = "line\n" * 100
        result = check_bp8_body_length(body)
        self.assertTrue(result["passed"])

    def test_exactly_500_passes(self):
        body = "line\n" * 500
        result = check_bp8_body_length(body)
        self.assertTrue(result["passed"])

    def test_over_500_fails(self):
        body = "line\n" * 501
        result = check_bp8_body_length(body)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "error")


# --- Soft checks (warnings) ---


class TestBP9SpecificInstructions(unittest.TestCase):
    """Instructions should be specific, not vague."""

    def test_specific_instruction_passes(self):
        text = "Run `python scripts/validate.py --input {filename}` to check data format."
        result = check_bp9_specific_instructions(text)
        self.assertTrue(result["passed"])

    def test_vague_instruction_warns(self):
        text = "Validate the data before proceeding."
        result = check_bp9_specific_instructions(text)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")

    def test_multiple_vague_phrases(self):
        text = "Handle things as needed. Process the input appropriately. Do what makes sense."
        result = check_bp9_specific_instructions(text)
        self.assertFalse(result["passed"])
        self.assertGreater(len(result.get("matches", [])), 1)


class TestBP10ErrorHandlingSection(unittest.TestCase):
    """Include error handling / common issues section."""

    def test_has_error_section_passes(self):
        body = "## Instructions\nDo stuff.\n\n## Common Issues\nIf X fails, try Y."
        result = check_bp10_error_handling_section(body)
        self.assertTrue(result["passed"])

    def test_has_troubleshooting_passes(self):
        body = "## Instructions\n\n## Troubleshooting\nIf error, fix it."
        result = check_bp10_error_handling_section(body)
        self.assertTrue(result["passed"])

    def test_has_error_handling_header_passes(self):
        body = "## Instructions\n\n## Error Handling\nCatch exceptions."
        result = check_bp10_error_handling_section(body)
        self.assertTrue(result["passed"])

    def test_missing_error_section_warns(self):
        body = "## Instructions\nDo stuff.\n\n## Output\nProduce result."
        result = check_bp10_error_handling_section(body)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")


class TestBP11DirectiveDensity(unittest.TestCase):
    """Avoid heavy-handed MUSTs/NEVERs — explain the why."""

    def test_low_density_passes(self):
        text = "You should explain why the approach matters. Use clear reasoning."
        result = check_bp11_directive_density(text)
        self.assertTrue(result["passed"])

    def test_high_density_warns(self):
        text = "MUST do X. NEVER do Y. ALWAYS check Z. MUST NOT skip. CRITICAL: follow this."
        result = check_bp11_directive_density(text)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")

    def test_a_few_directives_ok(self):
        text = "You MUST validate input.\n" + ("Regular instruction.\n" * 20)
        result = check_bp11_directive_density(text)
        self.assertTrue(result["passed"])


class TestBP12ProgressiveDisclosure(unittest.TestCase):
    """Use progressive disclosure — large content should be in references/."""

    def test_short_skill_passes(self):
        body = "line\n" * 100
        has_references_dir = False
        result = check_bp12_progressive_disclosure(body, has_references_dir)
        self.assertTrue(result["passed"])

    def test_long_skill_without_references_warns(self):
        body = "line\n" * 400
        has_references_dir = False
        result = check_bp12_progressive_disclosure(body, has_references_dir)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")

    def test_long_skill_with_references_passes(self):
        body = "line\n" * 400
        has_references_dir = True
        result = check_bp12_progressive_disclosure(body, has_references_dir)
        self.assertTrue(result["passed"])


class TestBP13ResourceReferences(unittest.TestCase):
    """Reference bundled resources clearly."""

    def test_referenced_file_passes(self):
        body = "Read `references/api-guide.md` for rate limiting details."
        resource_files = ["references/api-guide.md"]
        result = check_bp13_resource_references(body, resource_files)
        self.assertTrue(result["passed"])

    def test_unreferenced_file_warns(self):
        body = "## Instructions\nDo stuff."
        resource_files = ["references/api-guide.md", "references/examples.md"]
        result = check_bp13_resource_references(body, resource_files)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")

    def test_no_resources_passes(self):
        body = "## Instructions\nDo stuff."
        resource_files = []
        result = check_bp13_resource_references(body, resource_files)
        self.assertTrue(result["passed"])


class TestBP14DescriptionTriggerPhrases(unittest.TestCase):
    """Description should be 'pushy' enough to trigger reliably."""

    def test_pushy_description_passes(self):
        desc = "Manages sprint planning. Use when user mentions sprint, tasks, planning, or asks to create tickets."
        result = check_bp14_description_trigger_phrases(desc)
        self.assertTrue(result["passed"])

    def test_too_generic_warns(self):
        desc = "Helps with projects."
        result = check_bp14_description_trigger_phrases(desc)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")

    def test_technical_no_user_phrases_warns(self):
        desc = "Implements the Project entity model with hierarchical relationships."
        result = check_bp14_description_trigger_phrases(desc)
        self.assertFalse(result["passed"])


class TestBP15RepeatedPatterns(unittest.TestCase):
    """Look for repeated patterns that should be bundled scripts."""

    def test_no_repeats_passes(self):
        body = "## Step 1\nRun the build.\n## Step 2\nDeploy."
        result = check_bp15_repeated_patterns(body)
        self.assertTrue(result["passed"])

    def test_repeated_bash_blocks_warns(self):
        block = "```bash\npython scripts/process.py --input data.csv\n```"
        body = f"## Phase 1\n{block}\n## Phase 2\n{block}\n## Phase 3\n{block}"
        result = check_bp15_repeated_patterns(body)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")


class TestRunAllChecks(unittest.TestCase):
    """Integration: run_all_checks returns a list of results with score."""

    def test_returns_list_of_results(self):
        skill_info = {
            "filename": "SKILL.md",
            "folder_name": "my-skill",
            "files_in_folder": ["SKILL.md", "references/guide.md"],
            "frontmatter": "name: my-skill\ndescription: Does X. Use when user asks for Y.",
            "name": "my-skill",
            "description": "Does X. Use when user asks for Y.",
            "body": "## Instructions\nDo stuff.\n\n## Common Issues\nIf broken, fix.",
            "resource_files": ["references/guide.md"],
            "has_references_dir": True,
        }
        results = run_all_checks(skill_info)
        self.assertIsInstance(results, dict)
        self.assertIn("checks", results)
        self.assertIn("score", results)
        self.assertIsInstance(results["checks"], list)
        self.assertEqual(len(results["checks"]), 15)
        self.assertGreaterEqual(results["score"], 1)
        self.assertLessEqual(results["score"], 10)

    def test_perfect_skill_scores_high(self):
        skill_info = {
            "filename": "SKILL.md",
            "folder_name": "my-skill",
            "files_in_folder": ["SKILL.md"],
            "frontmatter": "name: my-skill\ndescription: Manages deploy workflows. Use when user says deploy, push, or release.",
            "name": "my-skill",
            "description": "Manages deploy workflows. Use when user says deploy, push, or release.",
            "body": "## Instructions\nRun `./deploy.sh`.\n\n## Error Handling\nIf deploy fails, check logs.",
            "resource_files": [],
            "has_references_dir": False,
        }
        results = run_all_checks(skill_info)
        self.assertGreaterEqual(results["score"], 8.0)


if __name__ == "__main__":
    unittest.main()
