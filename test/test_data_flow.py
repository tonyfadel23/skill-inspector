"""Tests for data flow checks."""
import os
import tempfile
import unittest

from skill_inspector.data_flow import check_data_flow


def make_nodes_edges(nodes, edges):
    return (
        [{"id": n[0], "type": n[1], "label": n[2], "inputs": n[3] if len(n) > 3 else [],
          "outputs": n[4] if len(n) > 4 else [], "phase": n[5] if len(n) > 5 else ""}
         for n in nodes],
        [{"source": e[0], "target": e[1], "type": e[2]} for e in edges],
    )


class TestUnproducedInput(unittest.TestCase):
    """D1 — Node expects input not produced by any upstream node."""

    def test_missing_input_flagged(self):
        nodes, edges = make_nodes_edges(
            [("a", "executor", "Step A", [], ["out.md"]),
             ("b", "executor", "Step B", ["missing.md"], [])],
            [("a", "b", "sequential")],
        )
        issues = check_data_flow(list(nodes), list(edges))
        d1 = [i for i in issues if i["check_id"] == "D1"]
        self.assertEqual(len(d1), 1)
        self.assertIn("missing.md", d1[0]["message"])

    def test_produced_input_ok(self):
        nodes, edges = make_nodes_edges(
            [("a", "executor", "Step A", [], ["out.md"]),
             ("b", "executor", "Step B", ["out.md"], [])],
            [("a", "b", "sequential")],
        )
        issues = check_data_flow(list(nodes), list(edges))
        d1 = [i for i in issues if i["check_id"] == "D1"]
        self.assertEqual(len(d1), 0)


class TestUnconsumedOutput(unittest.TestCase):
    """D2 — Node produces output not consumed downstream."""

    def test_unconsumed_flagged(self):
        nodes, edges = make_nodes_edges(
            [("a", "executor", "Step A", [], ["orphan.md"]),
             ("b", "executor", "Step B", [], [])],
            [("a", "b", "sequential")],
        )
        issues = check_data_flow(list(nodes), list(edges))
        d2 = [i for i in issues if i["check_id"] == "D2"]
        self.assertEqual(len(d2), 1)
        self.assertIn("orphan.md", d2[0]["message"])


class TestMissingFileReference(unittest.TestCase):
    """D3 — Referenced files should exist on disk."""

    def test_missing_reference_file(self):
        with tempfile.TemporaryDirectory() as d:
            nodes = [{"id": "a", "type": "file_io", "label": "Read refs",
                       "inputs": ["references/examples.md"], "outputs": []}]
            issues = check_data_flow(nodes, [], skill_dir=d)
            d3 = [i for i in issues if i["check_id"] == "D3"]
            self.assertEqual(len(d3), 1)

    def test_existing_reference_ok(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "references"))
            with open(os.path.join(d, "references", "examples.md"), "w") as f:
                f.write("content")
            nodes = [{"id": "a", "type": "file_io", "label": "Read refs",
                       "inputs": ["references/examples.md"], "outputs": []}]
            issues = check_data_flow(nodes, [], skill_dir=d)
            d3 = [i for i in issues if i["check_id"] == "D3"]
            self.assertEqual(len(d3), 0)


class TestImplicitDataPassing(unittest.TestCase):
    """D4 — Connected executors with no data contract."""

    def test_implicit_flagged(self):
        nodes = [
            {"id": "a", "type": "executor", "label": "Step A", "inputs": [], "outputs": []},
            {"id": "b", "type": "executor", "label": "Step B", "inputs": [], "outputs": []},
        ]
        edges = [{"source": "a", "target": "b", "type": "sequential"}]
        issues = check_data_flow(nodes, edges)
        d4 = [i for i in issues if i["check_id"] == "D4"]
        self.assertEqual(len(d4), 1)


if __name__ == "__main__":
    unittest.main()
