"""Tests for the heuristic SKILL.md parser."""
import os
import tempfile
import unittest

from skill_inspector.parser import parse_skill


class TestEntryExitSynthesis(unittest.TestCase):
    """Pass 4 — entry and exit node synthesis."""

    def _parse(self, content):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test-skill", "SKILL.md")
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as f:
                f.write(content)
            return parse_skill(path)

    def test_entry_node_exists_when_no_orphans(self):
        """A graph with clear entry should not synthesize extra entry."""
        result = self._parse(
            "---\nname: test\ndescription: test skill\n---\n"
            "## Context\nRead input file.\n\n"
            "## Step 1\nDo something.\n"
        )
        nodes = result["nodes"]
        entry_nodes = [n for n in nodes if n["id"] == "__entry__"]
        # Should not synthesize if a natural entry exists
        self.assertEqual(len(entry_nodes), 0)

    def test_exit_detected(self):
        """Graph should have at least one node without outgoing edges."""
        result = self._parse(
            "---\nname: test\ndescription: test skill\n---\n"
            "## Context\nRead input.\n\n"
            "## Delivery\nAsk: ready?\n"
        )
        nodes = result["nodes"]
        edges = result["edges"]
        sources = {e["source"] for e in edges}
        exit_nodes = [n for n in nodes if n["id"] not in sources]
        self.assertTrue(len(exit_nodes) > 0)


class TestTemplateDetection(unittest.TestCase):
    """Template nodes should be detected from headers and code fences."""

    def _parse(self, content):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test-skill", "SKILL.md")
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as f:
                f.write(content)
            return parse_skill(path)

    def test_template_header_detected(self):
        """## X Template headers should produce template nodes."""
        result = self._parse(
            "---\nname: test\ndescription: test skill\n---\n"
            "## Product Brief Template\n"
            "```markdown\n# Brief\n| Field | Value |\n```\n"
        )
        nodes = result["nodes"]
        template_nodes = [n for n in nodes if n["type"] == "template"]
        self.assertTrue(len(template_nodes) > 0)

    def test_code_fence_with_markdown_detected_as_template(self):
        """Code fences containing markdown headers should trigger template detection."""
        result = self._parse(
            "---\nname: test\ndescription: test skill\n---\n"
            "## Output Format\n"
            "Use this template:\n"
            "```markdown\n# Report Title\n## Section 1\nContent here.\n```\n"
        )
        nodes = result["nodes"]
        template_nodes = [n for n in nodes if n["type"] == "template"]
        self.assertTrue(len(template_nodes) > 0)


class TestJoinDetection(unittest.TestCase):
    """Join nodes should be detected from multiple patterns."""

    def _parse(self, content):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test-skill", "SKILL.md")
            os.makedirs(os.path.dirname(path))
            with open(path, "w") as f:
                f.write(content)
            return parse_skill(path)

    def test_converge_phase_name(self):
        """A section titled 'CONVERGE' should produce a join node."""
        result = self._parse(
            "---\nname: test\ndescription: test skill\n---\n"
            "## Phase 1 — DIVERGE\nAll parallel work.\n\n"
            "## Phase 2 — CONVERGE\nCollect results.\n"
        )
        nodes = result["nodes"]
        join_nodes = [n for n in nodes if n["type"] == "join"]
        self.assertTrue(len(join_nodes) > 0)

    def test_run_after_all_exist(self):
        """'Run after all X exist' should produce a join node."""
        result = self._parse(
            "---\nname: test\ndescription: test skill\n---\n"
            "## Step 1\nGenerate files.\n\n"
            "## Step 2\nRun after all concept files exist.\n"
        )
        nodes = result["nodes"]
        join_nodes = [n for n in nodes if n["type"] == "join"]
        self.assertTrue(len(join_nodes) > 0)


if __name__ == "__main__":
    unittest.main()
