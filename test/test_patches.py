"""Tests for structural patch suggestion engine.

Patch suggestions are natural language restructure recommendations
referencing phase names and node labels. No content editing — only
structural fixes (edges, parallelism, sequencing).
"""
import unittest

from skill_inspector.patches import suggest_patches


def make_graph(nodes, edges):
    """Helper to build a graph dict from shorthand."""
    return {
        "nodes": [
            {"id": n[0], "type": n[1], "label": n[2], "phase": n[3] if len(n) > 3 else ""}
            for n in nodes
        ],
        "edges": [
            {"source": e[0], "target": e[1], "type": e[2], "label": e[3] if len(e) > 3 else ""}
            for e in edges
        ],
    }


class TestOrphanNodePatch(unittest.TestCase):
    """S1 — Orphan nodes get a suggested fix."""

    def test_orphan_detected_with_fix(self):
        g = make_graph(
            [("a", "file_io", "Entry", "Entry"), ("b", "executor", "Step B", "Phase1"), ("c", "executor", "Orphan C", "Phase2")],
            [("a", "b", "sequential")],
        )
        patches = suggest_patches(g["nodes"], g["edges"])
        orphan_patches = [p for p in patches if p["check_id"] == "S1"]
        self.assertEqual(len(orphan_patches), 1)
        self.assertIn("Orphan C", orphan_patches[0]["message"])
        self.assertIn("Phase2", orphan_patches[0]["location"])
        self.assertTrue(len(orphan_patches[0]["suggestion"]) > 0)

    def test_no_orphans_no_patch(self):
        g = make_graph(
            [("a", "file_io", "Entry", "Entry"), ("b", "executor", "Step B", "Phase1")],
            [("a", "b", "sequential")],
        )
        patches = suggest_patches(g["nodes"], g["edges"])
        orphan_patches = [p for p in patches if p["check_id"] == "S1"]
        self.assertEqual(len(orphan_patches), 0)


class TestDeadEndPatch(unittest.TestCase):
    """S2 — Dead-end nodes (non-exit types) get a suggested fix."""

    def test_dead_end_detected(self):
        g = make_graph(
            [("a", "file_io", "Entry", "Entry"), ("b", "executor", "Dead End", "Phase1"), ("c", "executor", "Step C", "Phase1")],
            [("a", "b", "sequential"), ("a", "c", "sequential")],
        )
        patches = suggest_patches(g["nodes"], g["edges"])
        dead_patches = [p for p in patches if p["check_id"] == "S2"]
        self.assertTrue(len(dead_patches) >= 1)
        labels = [p["message"] for p in dead_patches]
        self.assertTrue(any("Dead End" in m for m in labels))

    def test_gate_dead_end_not_flagged(self):
        """Gate/spawn nodes at the end are expected terminal nodes."""
        g = make_graph(
            [("a", "file_io", "Entry", "Entry"), ("b", "gate", "Decision", "End")],
            [("a", "b", "sequential")],
        )
        patches = suggest_patches(g["nodes"], g["edges"])
        dead_patches = [p for p in patches if p["check_id"] == "S2"]
        self.assertEqual(len(dead_patches), 0)


class TestForkWithoutJoinPatch(unittest.TestCase):
    """S3 — Fork without downstream join gets a fix suggestion."""

    def test_fork_without_join(self):
        g = make_graph(
            [("a", "file_io", "Entry", "Entry"), ("f", "fork", "Diverge", "Phase1"),
             ("b", "executor", "Agent A", "Phase1"), ("c", "executor", "Agent B", "Phase1")],
            [("a", "f", "sequential"), ("f", "b", "parallel"), ("f", "c", "parallel")],
        )
        patches = suggest_patches(g["nodes"], g["edges"])
        fork_patches = [p for p in patches if p["check_id"] == "S3"]
        self.assertEqual(len(fork_patches), 1)
        self.assertIn("Diverge", fork_patches[0]["message"])
        self.assertIn("join", fork_patches[0]["suggestion"].lower())

    def test_fork_with_join_no_patch(self):
        g = make_graph(
            [("f", "fork", "Diverge", "Phase1"), ("a", "executor", "A", "Phase1"),
             ("b", "executor", "B", "Phase1"), ("j", "join", "Converge", "Phase2")],
            [("f", "a", "parallel"), ("f", "b", "parallel"),
             ("a", "j", "data_pass"), ("b", "j", "data_pass")],
        )
        patches = suggest_patches(g["nodes"], g["edges"])
        fork_patches = [p for p in patches if p["check_id"] == "S3"]
        self.assertEqual(len(fork_patches), 0)


class TestParallelShouldBeSequential(unittest.TestCase):
    """Detect when parallel nodes have data dependencies suggesting sequential order."""

    def test_parallel_with_dependency(self):
        g = make_graph(
            [("f", "fork", "Fork", "Phase1"),
             ("a", "executor", "Agent A", "Phase1"),
             ("b", "executor", "Agent B", "Phase1")],
            [("f", "a", "parallel"), ("f", "b", "parallel"),
             ("a", "b", "data_pass")],  # A feeds B — shouldn't be parallel
        )
        patches = suggest_patches(g["nodes"], g["edges"])
        seq_patches = [p for p in patches if p["check_id"] == "SP1"]
        self.assertEqual(len(seq_patches), 1)
        self.assertIn("Agent A", seq_patches[0]["message"])
        self.assertIn("Agent B", seq_patches[0]["message"])
        self.assertIn("sequential", seq_patches[0]["suggestion"].lower())


class TestPatchFormat(unittest.TestCase):
    """All patches follow the expected format."""

    def test_patch_has_required_fields(self):
        g = make_graph(
            [("a", "file_io", "Entry", "Entry"), ("c", "executor", "Orphan", "Phase2")],
            [],
        )
        patches = suggest_patches(g["nodes"], g["edges"])
        for p in patches:
            self.assertIn("check_id", p)
            self.assertIn("severity", p)
            self.assertIn("message", p)
            self.assertIn("location", p)
            self.assertIn("suggestion", p)
            self.assertIn(p["severity"], ("error", "warning", "info"))


if __name__ == "__main__":
    unittest.main()
