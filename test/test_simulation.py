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


class TestSimulationIndependentFork(unittest.TestCase):
    """Fork without a downstream join — branches activate simultaneously."""

    def test_independent_fork_activates_all_children(self):
        """Branches with no join node activate all at once."""
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
        sim.step()  # fork -> a, b, c (all active simultaneously)
        state = sim.get_state()
        self.assertEqual(sorted(state["active"]), ["a", "b", "c"])
        self.assertIsNone(state["converging_fork"])

    def test_independent_fork_reports_count(self):
        """State reports how many independent branches were activated."""
        g = make_graph(
            [("fork", "fork"), ("a", "executor"), ("b", "executor"), ("c", "executor")],
            [
                ("fork", "a", "parallel"),
                ("fork", "b", "parallel"),
                ("fork", "c", "parallel"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()   # fork is entry
        sim.step()    # fork -> a, b, c
        state = sim.get_state()
        self.assertEqual(state["independent_fork_count"], 3)

    def test_independent_fork_advances_together(self):
        """All independent branches advance in one step."""
        g = make_graph(
            [("fork", "fork"), ("a", "executor"), ("b", "executor"),
             ("a2", "executor"), ("b2", "executor")],
            [
                ("fork", "a", "parallel"),
                ("fork", "b", "parallel"),
                ("a", "a2", "sequential"),
                ("b", "b2", "sequential"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()   # fork -> a, b
        sim.step()   # a -> a2, b -> b2 (both advance together)
        state = sim.get_state()
        self.assertEqual(sorted(state["active"]), ["a2", "b2"])


class TestSimulationConvergingFork(unittest.TestCase):
    """Fork with a downstream join — branches step one at a time."""

    def test_converging_fork_starts_first_branch(self):
        """When fork has a downstream join, only first branch activates."""
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
        sim.start()   # fork is entry
        sim.step()    # fork -> first branch only (a)
        state = sim.get_state()
        self.assertEqual(state["active"], ["a"])
        self.assertIsNotNone(state["converging_fork"])
        self.assertEqual(state["converging_fork"]["current_branch_index"], 0)
        self.assertEqual(len(state["converging_fork"]["branches"]), 2)

    def test_converging_fork_steps_one_branch_at_a_time(self):
        """Each step advances the current branch, then moves to next."""
        g = make_graph(
            [("fork", "fork"), ("a", "executor"), ("b", "executor"),
             ("c", "executor"), ("join", "join")],
            [
                ("fork", "a", "parallel"),
                ("fork", "b", "parallel"),
                ("fork", "c", "parallel"),
                ("a", "join", "data_pass"),
                ("b", "join", "data_pass"),
                ("c", "join", "data_pass"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()   # fork -> a (branch 1)
        self.assertEqual(sim.get_state()["active"], ["a"])

        sim.step()   # a reaches join, branch transition -> b (branch 2)
        self.assertEqual(sim.get_state()["active"], ["b"])
        self.assertIn("a", sim.get_state()["visited"])

        sim.step()   # b reaches join, branch transition -> c (branch 3)
        self.assertEqual(sim.get_state()["active"], ["c"])

        sim.step()   # c reaches join, all arrived -> join activates
        state = sim.get_state()
        self.assertEqual(state["active"], ["join"])
        self.assertIsNone(state["converging_fork"])

    def test_converging_fork_with_unequal_branch_lengths(self):
        """Branches can have different lengths before reaching the join."""
        g = make_graph(
            [("fork", "fork"), ("a", "executor"), ("b1", "executor"),
             ("b2", "executor"), ("join", "join")],
            [
                ("fork", "a", "parallel"),
                ("fork", "b1", "parallel"),
                ("a", "join", "data_pass"),
                ("b1", "b2", "sequential"),
                ("b2", "join", "data_pass"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()   # fork -> a (branch 1)
        self.assertEqual(sim.get_state()["active"], ["a"])

        sim.step()   # a reaches join -> b1 (branch 2)
        self.assertEqual(sim.get_state()["active"], ["b1"])

        sim.step()   # b1 -> b2 (branch 2 continues)
        self.assertEqual(sim.get_state()["active"], ["b2"])

        sim.step()   # b2 reaches join, all arrived -> join activates
        self.assertEqual(sim.get_state()["active"], ["join"])

    def test_converging_fork_join_activates_only_after_all(self):
        """Join node doesn't activate until every branch has arrived."""
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
        sim.start()
        sim.step()   # fork -> a (branch 1)
        sim.step()   # a reaches join -> b (branch 2)
        # After first branch, join should NOT be active yet
        state = sim.get_state()
        self.assertNotIn("join", state["active"])
        self.assertEqual(state["active"], ["b"])

    def test_converging_fork_state_tracks_arrived_branches(self):
        """State shows which branches have arrived at the join."""
        g = make_graph(
            [("fork", "fork"), ("a", "executor"), ("b", "executor"),
             ("c", "executor"), ("join", "join")],
            [
                ("fork", "a", "parallel"),
                ("fork", "b", "parallel"),
                ("fork", "c", "parallel"),
                ("a", "join", "data_pass"),
                ("b", "join", "data_pass"),
                ("c", "join", "data_pass"),
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()   # fork -> a
        sim.step()   # a done -> b
        cf = sim.get_state()["converging_fork"]
        self.assertEqual(cf["arrived_at_join"], ["a"])
        self.assertEqual(cf["current_branch_index"], 1)


class TestSimulationMixedFork(unittest.TestCase):
    """Fork with some converging and some independent branches."""

    def test_mixed_fork_handles_both(self):
        """Converging branches step one-at-a-time, independent activates alongside."""
        g = make_graph(
            [("fork", "fork"), ("a", "executor"), ("b", "executor"),
             ("ind", "executor"), ("join", "join")],
            [
                ("fork", "a", "parallel"),
                ("fork", "b", "parallel"),
                ("fork", "ind", "parallel"),
                ("a", "join", "data_pass"),
                ("b", "join", "data_pass"),
                # ind has no path to join — it's independent
            ],
        )
        sim = SimulationEngine(g["nodes"], g["edges"])
        sim.start()
        sim.step()   # fork -> a (first converging branch) + ind (independent)
        state = sim.get_state()
        self.assertIn("ind", state["active"])
        self.assertIn("a", state["active"])
        self.assertNotIn("b", state["active"])


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
        self.assertIn("converging_fork", state)
        self.assertIn("independent_fork_count", state)


if __name__ == "__main__":
    unittest.main()
