"""Tests for SimulationEngine — DAG step-through traversal.

The engine is a pure state machine operating on nodes + edges arrays.
No DOM dependencies — browser code reads state and applies CSS classes.
"""
import unittest
import json
import os


# We test the JS SimulationEngine by extracting it as a JSON-driven spec.
# The actual engine lives in the HTML, but we validate the logic via Python
# by implementing a reference SimulationEngine in Python that must match.
from skill_inspector.simulation import SimulationEngine


def make_graph(nodes, edges):
    """Helper to build a graph dict from shorthand."""
    return {
        "nodes": [{"id": n[0], "type": n[1], "label": n[0]} for n in nodes],
        "edges": [{"source": e[0], "target": e[1], "type": e[2], "label": e[3] if len(e) > 3 else ""} for e in edges],
    }


class TestSimulationBasicTraversal(unittest.TestCase):
    """Sequential nodes auto-advance."""

    def test_start_sets_entry_node_active(self):
        g = make_graph(
            [("a", "file_io"), ("b", "executor"), ("c", "gate")],
            [("a", "b", "sequential"), ("b", "c", "sequential")],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        self.assertEqual(sim.get_state()["active"], ["a"])
        self.assertFalse(sim.is_complete())

    def test_step_advances_sequentially(self):
        g = make_graph(
            [("a", "file_io"), ("b", "executor"), ("c", "gate")],
            [("a", "b", "sequential"), ("b", "c", "sequential")],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()
        state = sim.get_state()
        self.assertEqual(state["active"], ["b"])
        self.assertIn("a", state["visited"])

    def test_reaching_end_completes(self):
        g = make_graph(
            [("a", "file_io"), ("b", "executor")],
            [("a", "b", "sequential")],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()  # now at b
        sim.step()  # b has no outgoing edges -> complete
        self.assertTrue(sim.is_complete())

    def test_reset_returns_to_initial(self):
        g = make_graph(
            [("a", "file_io"), ("b", "executor")],
            [("a", "b", "sequential")],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()
        sim.reset()
        state = sim.get_state()
        self.assertEqual(state["active"], [])
        self.assertEqual(state["visited"], [])
        self.assertFalse(sim.is_complete())


class TestSimulationForkJoin(unittest.TestCase):
    """Fork activates all parallel children, join waits for all."""

    def test_fork_activates_all_children(self):
        g = make_graph(
            [("entry", "file_io"), ("fork", "fork"), ("a", "executor"), ("b", "executor"), ("c", "executor")],
            [
                ("entry", "fork", "sequential"),
                ("fork", "a", "parallel"),
                ("fork", "b", "parallel"),
                ("fork", "c", "parallel"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()  # entry -> fork
        sim.step()  # fork -> a, b, c (all active)
        state = sim.get_state()
        self.assertEqual(sorted(state["active"]), ["a", "b", "c"])

    def test_join_waits_for_all_incoming(self):
        g = make_graph(
            [("fork", "fork"), ("a", "executor"), ("b", "executor"), ("join", "join")],
            [
                ("fork", "a", "parallel"),
                ("fork", "b", "parallel"),
                ("a", "join", "data_pass"),
                ("b", "join", "data_pass"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()  # fork is entry (no incoming edges)
        sim.step()   # fork -> a, b active
        # Step advances one parallel branch at a time
        sim.step()   # a completes, b still active. join not yet active.
        state = sim.get_state()
        self.assertNotIn("join", state["active"])
        sim.step()   # b completes. All incoming to join are visited. Join activates.
        state = sim.get_state()
        self.assertIn("join", state["active"])


class TestSimulationRouter(unittest.TestCase):
    """Router/gate nodes pause for branch selection."""

    def test_router_pauses_for_selection(self):
        g = make_graph(
            [("entry", "file_io"), ("router", "router"), ("a", "executor"), ("b", "executor")],
            [
                ("entry", "router", "sequential"),
                ("router", "a", "conditional", "option A"),
                ("router", "b", "conditional", "option B"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()  # entry -> router
        state = sim.get_state()
        self.assertEqual(state["active"], ["router"])
        self.assertTrue(state["waiting_for_selection"])
        self.assertEqual(len(state["branch_options"]), 2)

    def test_selecting_branch_advances(self):
        g = make_graph(
            [("entry", "file_io"), ("router", "router"), ("a", "executor"), ("b", "executor")],
            [
                ("entry", "router", "sequential"),
                ("router", "a", "conditional", "option A"),
                ("router", "b", "conditional", "option B"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()  # entry -> router
        sim.select_branch(0)  # choose option A
        state = sim.get_state()
        self.assertEqual(state["active"], ["a"])
        self.assertFalse(state["waiting_for_selection"])

    def test_gate_also_pauses(self):
        g = make_graph(
            [("entry", "file_io"), ("gate", "gate"), ("yes", "executor"), ("no", "executor")],
            [
                ("entry", "gate", "sequential"),
                ("gate", "yes", "conditional", "approve"),
                ("gate", "no", "conditional", "reject"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()  # entry -> gate
        state = sim.get_state()
        self.assertTrue(state["waiting_for_selection"])


class TestSimulationState(unittest.TestCase):
    """State tracking: active, visited, unvisited."""

    def test_state_tracks_visited(self):
        g = make_graph(
            [("a", "file_io"), ("b", "executor"), ("c", "executor")],
            [("a", "b", "sequential"), ("b", "c", "sequential")],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()
        sim.step()
        state = sim.get_state()
        self.assertIn("a", state["visited"])
        self.assertIn("b", state["visited"])
        self.assertEqual(state["active"], ["c"])

    def test_get_state_returns_all_fields(self):
        g = make_graph(
            [("a", "file_io")],
            [],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        state = sim.get_state()
        self.assertIn("active", state)
        self.assertIn("visited", state)
        self.assertIn("waiting_for_selection", state)
        self.assertIn("branch_options", state)


if __name__ == "__main__":
    unittest.main()
