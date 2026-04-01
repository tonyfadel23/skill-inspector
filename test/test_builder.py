"""Tests for the Skill Tree Builder — fluent API for constructing skill DAGs."""
import pytest
from skill_inspector.builder import SkillTreeBuilder


class TestBuilderConstruction:
    """Test basic tree construction."""

    def test_create_empty_tree(self):
        tree = SkillTreeBuilder("my-skill", "A test skill. Use when testing.")
        result = tree.build()
        assert result["name"] == "my-skill"
        assert result["description"] == "A test skill. Use when testing."
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_add_executor_node(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Setup").executor("init", "Initialize the workspace")
        result = tree.build()
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["type"] == "executor"
        assert result["nodes"][0]["id"] == "init"
        assert result["nodes"][0]["phase"] == "Setup"

    def test_sequential_nodes_auto_edge(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        p = tree.phase("Work")
        p.executor("a", "Step A")
        p.executor("b", "Step B")
        result = tree.build()
        assert len(result["edges"]) == 1
        assert result["edges"][0] == {
            "source": "a", "target": "b", "type": "sequential", "label": ""
        }

    def test_cross_phase_edge(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Phase 1").executor("a", "A")
        tree.phase("Phase 2").executor("b", "B")
        result = tree.build()
        edges = result["edges"]
        assert any(e["source"] == "a" and e["target"] == "b" for e in edges)


class TestToolNodes:
    """Test tool node construction."""

    def test_tool_with_commands(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Fetch").tool("web-search", "Search the web for data",
                                 tools=["WebSearch", "WebFetch"],
                                 commands=["curl https://example.com"])
        result = tree.build()
        node = result["nodes"][0]
        assert node["type"] == "tool"
        assert node["tools"] == ["WebSearch", "WebFetch"]
        assert "curl" in node["raw_instruction"]

    def test_tool_with_mcp(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Data").tool("fetch-db", "Query database",
                                mcp_servers=["postgres-mcp"])
        result = tree.build()
        assert "postgres-mcp" in result["dependencies"]["mcp_servers"]


class TestSubagentNodes:
    """Test sub-agent spawning."""

    def test_subagent_basic(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Research").subagent(
            "market-analyst",
            "Analyze market trends and competitors",
            agent_type="Explore",
            tools=["WebSearch", "WebFetch"],
        )
        result = tree.build()
        node = result["nodes"][0]
        assert node["type"] == "subagent"
        assert node["agent_type"] == "Explore"
        assert node["tools"] == ["WebSearch", "WebFetch"]

    def test_subagent_with_context(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Research").subagent(
            "analyst", "Analyze",
            context_files=["personas.md", "company.md"],
        )
        result = tree.build()
        node = result["nodes"][0]
        assert node["context_files"] == ["personas.md", "company.md"]


class TestContextInjection:
    """Test dynamic context loading nodes."""

    def test_context_loader(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Setup").context_loader(
            "load-context",
            "Load user personas and company profile",
            files=["references/personas.md", "references/company.md"],
            urls=["https://example.com/api/context"],
        )
        result = tree.build()
        node = result["nodes"][0]
        assert node["type"] == "context_loader"
        assert len(node["inputs"]) == 2
        assert node["urls"] == ["https://example.com/api/context"]


class TestGatedChecks:
    """Test gate and signal gate nodes."""

    def test_signal_gate(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Evaluate").signal_gate(
            "quality-check",
            "Check signal quality and strength",
            criteria={"signal_score": ">= 0.7", "confidence": ">= 0.6"},
            on_fail="retry",
            max_retries=3,
        )
        result = tree.build()
        node = result["nodes"][0]
        assert node["type"] == "signal_gate"
        assert node["criteria"]["signal_score"] == ">= 0.7"
        assert node["on_fail"] == "retry"
        assert node["max_retries"] == 3

    def test_gate_with_branches(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        p = tree.phase("Decision")
        p.signal_gate("gate", "Check quality",
                      criteria={"score": ">= 0.8"},
                      on_fail="branch",
                      fail_target="fallback")
        p.executor("proceed", "Continue with high quality")
        p.executor("fallback", "Apply remediation")
        result = tree.build()
        edges = result["edges"]
        assert any(e["source"] == "gate" and e["target"] == "proceed"
                   and e["type"] == "conditional" and "pass" in e["label"] for e in edges)
        assert any(e["source"] == "gate" and e["target"] == "fallback"
                   and e["type"] == "conditional" and "fail" in e["label"] for e in edges)


class TestImprovementLoops:
    """Test RALPH-style improvement loops."""

    def test_improvement_loop(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Refine").improvement_loop(
            "ralph-refine",
            "Apply RALPH methodology to improve output",
            strategy="ralph",
            max_iterations=5,
            exit_criteria={"quality_score": ">= 0.9"},
            steps=["Reflect on output", "Analyze gaps",
                   "Learn from feedback", "Plan improvements",
                   "Hypothesize better approach"],
        )
        result = tree.build()
        node = result["nodes"][0]
        assert node["type"] == "improvement_loop"
        assert node["strategy"] == "ralph"
        assert node["max_iterations"] == 5
        assert len(node["steps"]) == 5


class TestDivergeConverge:
    """Test fork/join with multi-perspective analysis."""

    def test_diverge(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Analysis").diverge(
            "multi-angle",
            "Analyze from multiple perspectives",
            branches=[
                {"id": "tech-view", "label": "Technical feasibility", "prompt": "Assess technical..."},
                {"id": "market-view", "label": "Market viability", "prompt": "Assess market..."},
                {"id": "user-view", "label": "User desirability", "prompt": "Assess user..."},
            ],
        )
        result = tree.build()
        fork_node = next(n for n in result["nodes"] if n["id"] == "multi-angle_fork")
        assert fork_node["type"] == "fork"
        branches = [n for n in result["nodes"] if n["id"] in ("tech-view", "market-view", "user-view")]
        assert len(branches) == 3
        parallel_edges = [e for e in result["edges"] if e["type"] == "parallel"]
        assert len(parallel_edges) == 3

    def test_converge(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Synthesis").converge(
            "synthesize",
            "Merge all perspectives into unified assessment",
            strategy="weighted-merge",
        )
        result = tree.build()
        node = result["nodes"][0]
        assert node["type"] == "join"
        assert node["strategy"] == "weighted-merge"


class TestRouterNode:
    """Test conditional routing."""

    def test_router_with_conditions(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        p = tree.phase("Route")
        p.router("decide", "Route based on signal strength",
                 conditions=[
                     {"if": "signal_score >= 0.8", "then": "fast-track"},
                     {"if": "signal_score >= 0.5", "then": "standard-track"},
                     {"if": "signal_score < 0.5", "then": "deep-research"},
                 ])
        p.executor("fast-track", "Proceed quickly")
        p.executor("standard-track", "Standard process")
        p.executor("deep-research", "Do more research")
        result = tree.build()
        cond_edges = [e for e in result["edges"] if e["type"] == "conditional"]
        assert len(cond_edges) == 3


class TestBuildRoundTrip:
    """Test that built trees are parseable by the existing parser."""

    def test_build_produces_valid_graph(self):
        tree = SkillTreeBuilder("test-skill", "A test. Use when testing.")
        tree.phase("Setup").executor("init", "Initialize")
        tree.phase("Work").tool("fetch", "Fetch data", tools=["WebSearch"])
        tree.phase("Done").executor("finish", "Wrap up")
        result = tree.build()

        # Validate structure matches parser output schema
        assert "name" in result
        assert "nodes" in result
        assert "edges" in result
        assert "pattern" in result
        assert "dependencies" in result
        for node in result["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "type" in node
            assert "phase" in node

    def test_duplicate_node_id_raises(self):
        tree = SkillTreeBuilder("s", "d. Use when x.")
        p = tree.phase("P")
        p.executor("same-id", "First")
        with pytest.raises(ValueError, match="Duplicate node id"):
            p.executor("same-id", "Second")


class TestEmitter:
    """Test SKILL.md generation from builder output."""

    def test_emit_basic(self):
        from skill_inspector.emitter import emit_skill_md
        tree = SkillTreeBuilder("my-skill", "Do something. Use when asked.")
        tree.phase("Setup").executor("init", "Initialize the project workspace")
        tree.phase("Execute").tool("run-tests", "Run the test suite",
                                    commands=["python3 -m pytest"])
        md = emit_skill_md(tree.build())
        assert "---" in md
        assert "name: my-skill" in md
        assert "## Setup" in md
        assert "## Execute" in md
        assert "```bash" in md
        assert "pytest" in md

    def test_emit_subagent(self):
        from skill_inspector.emitter import emit_skill_md
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Research").subagent("analyst", "Analyze market data",
                                         agent_type="Explore",
                                         tools=["WebSearch"])
        md = emit_skill_md(tree.build())
        assert "Agent" in md or "sub-agent" in md or "subagent" in md
        assert "Explore" in md
        assert "WebSearch" in md

    def test_emit_signal_gate(self):
        from skill_inspector.emitter import emit_skill_md
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Check").signal_gate("gate", "Check quality",
                                         criteria={"score": ">= 0.8"},
                                         on_fail="retry", max_retries=3)
        md = emit_skill_md(tree.build())
        assert "score" in md
        assert ">= 0.8" in md
        assert "retry" in md.lower() or "Retry" in md

    def test_emit_improvement_loop(self):
        from skill_inspector.emitter import emit_skill_md
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Refine").improvement_loop(
            "loop", "Improve quality",
            strategy="ralph", max_iterations=3,
            exit_criteria={"quality": ">= 0.9"},
            steps=["Reflect", "Analyze", "Learn", "Plan", "Hypothesize"],
        )
        md = emit_skill_md(tree.build())
        assert "RALPH" in md or "ralph" in md
        assert "Reflect" in md
        assert "Analyze" in md

    def test_emit_diverge_converge(self):
        from skill_inspector.emitter import emit_skill_md
        tree = SkillTreeBuilder("s", "d. Use when x.")
        tree.phase("Diverge").diverge("multi", "Multiple perspectives",
                                       branches=[
                                           {"id": "a", "label": "View A", "prompt": "Analyze A"},
                                           {"id": "b", "label": "View B", "prompt": "Analyze B"},
                                       ])
        tree.phase("Converge").converge("merge", "Synthesize results",
                                         strategy="best-of")
        md = emit_skill_md(tree.build())
        assert "parallel" in md.lower() or "(parallel)" in md.lower()
        assert "View A" in md
        assert "View B" in md
        assert "synthesize" in md.lower() or "merge" in md.lower() or "converge" in md.lower()

    def test_emit_roundtrip_parseable(self):
        """Emitted SKILL.md should be parseable by the existing parser."""
        from skill_inspector.emitter import emit_skill_md
        import tempfile, os
        from skill_inspector.parser import parse_skill

        tree = SkillTreeBuilder("roundtrip-test",
                                "Test round-trip. Use when verifying builder.")
        tree.phase("Setup").executor("init", "Initialize workspace")
        tree.phase("Research").tool("search", "Search for data",
                                     tools=["WebSearch"],
                                     commands=["curl https://api.example.com"])
        tree.phase("Evaluate").signal_gate("check", "Verify quality",
                                            criteria={"score": ">= 0.7"},
                                            on_fail="retry", max_retries=2)
        tree.phase("Done").executor("deliver", "Deliver results")

        md = emit_skill_md(tree.build())

        # Write to temp file and parse
        with tempfile.TemporaryDirectory() as td:
            skill_dir = os.path.join(td, "roundtrip-test")
            os.makedirs(skill_dir)
            path = os.path.join(skill_dir, "SKILL.md")
            with open(path, "w") as f:
                f.write(md)

            parsed = parse_skill(path)
            assert parsed["name"] == "roundtrip-test"
            assert len(parsed["nodes"]) >= 4
            assert len(parsed["edges"]) >= 3
