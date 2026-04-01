"""Skill Tree Builder — fluent API for constructing skill DAGs.

Build skill trees programmatically with support for:
- Sub-agent execution with dedicated tools and context
- Multi-agent diverge/converge patterns
- Dynamic context injection from files and URLs
- RALPH improvement loops (Reflect, Analyze, Learn, Plan, Hypothesize)
- Signal-gated quality checks with retry logic
- Conditional routing with computed metrics
"""


class PhaseBuilder:
    """Builder for adding nodes within a phase."""

    def __init__(self, tree: "SkillTreeBuilder", phase_name: str):
        self._tree = tree
        self._phase = phase_name
        self._node_ids: list[str] = []

    def _add_node(self, node: dict) -> "PhaseBuilder":
        nid = node["id"]
        if any(n["id"] == nid for n in self._tree._nodes):
            raise ValueError(f"Duplicate node id: '{nid}'")
        node.setdefault("phase", self._phase)
        node.setdefault("inputs", [])
        node.setdefault("outputs", [])
        node.setdefault("warnings", [])
        self._tree._nodes.append(node)
        self._node_ids.append(nid)
        return self

    def executor(self, nid: str, instruction: str) -> "PhaseBuilder":
        """Add an executor node — takes action, writes files, generates content."""
        return self._add_node({
            "id": nid, "label": instruction, "type": "executor",
            "raw_instruction": instruction,
        })

    def tool(self, nid: str, instruction: str, *,
             tools: list[str] | None = None,
             commands: list[str] | None = None,
             mcp_servers: list[str] | None = None) -> "PhaseBuilder":
        """Add a tool node — invokes external tools, MCP servers, or shell commands."""
        raw = instruction
        if commands:
            raw += "\n\n```bash\n" + "\n".join(commands) + "\n```"
        node = {
            "id": nid, "label": instruction, "type": "tool",
            "raw_instruction": raw,
            "tools": tools or [],
        }
        if mcp_servers:
            self._tree._mcp_servers.update(mcp_servers)
        return self._add_node(node)

    def subagent(self, nid: str, instruction: str, *,
                 agent_type: str = "general-purpose",
                 tools: list[str] | None = None,
                 context_files: list[str] | None = None) -> "PhaseBuilder":
        """Add a sub-agent node — spawns a specialized agent with its own context."""
        return self._add_node({
            "id": nid, "label": instruction, "type": "subagent",
            "raw_instruction": instruction,
            "agent_type": agent_type,
            "tools": tools or [],
            "context_files": context_files or [],
        })

    def context_loader(self, nid: str, instruction: str, *,
                       files: list[str] | None = None,
                       urls: list[str] | None = None) -> "PhaseBuilder":
        """Add a context loader — dynamically injects context from files/URLs."""
        return self._add_node({
            "id": nid, "label": instruction, "type": "context_loader",
            "raw_instruction": instruction,
            "inputs": files or [],
            "urls": urls or [],
        })

    def signal_gate(self, nid: str, instruction: str, *,
                    criteria: dict[str, str],
                    on_fail: str = "retry",
                    max_retries: int = 3,
                    fail_target: str | None = None) -> "PhaseBuilder":
        """Add a signal gate — gates on computed metrics with thresholds.

        Args:
            criteria: Dict of metric_name -> threshold expression (e.g. ">= 0.7")
            on_fail: "retry" to loop back, "branch" to go to fail_target
            max_retries: Max retry attempts when on_fail="retry"
            fail_target: Node id to branch to when on_fail="branch"
        """
        return self._add_node({
            "id": nid, "label": instruction, "type": "signal_gate",
            "raw_instruction": instruction,
            "criteria": criteria,
            "on_fail": on_fail,
            "max_retries": max_retries,
            "fail_target": fail_target,
        })

    def improvement_loop(self, nid: str, instruction: str, *,
                         strategy: str = "ralph",
                         max_iterations: int = 5,
                         exit_criteria: dict[str, str] | None = None,
                         steps: list[str] | None = None) -> "PhaseBuilder":
        """Add an improvement loop — iterates until quality threshold met.

        Strategies:
            ralph: Reflect, Analyze, Learn, Plan, Hypothesize
            iterate: Simple retry with feedback
        """
        return self._add_node({
            "id": nid, "label": instruction, "type": "improvement_loop",
            "raw_instruction": instruction,
            "strategy": strategy,
            "max_iterations": max_iterations,
            "exit_criteria": exit_criteria or {},
            "steps": steps or [],
        })

    def diverge(self, nid: str, instruction: str, *,
                branches: list[dict]) -> "PhaseBuilder":
        """Add a diverge (fork) — spawns parallel branches for multi-angle analysis.

        Each branch dict: {"id": str, "label": str, "prompt": str}
        """
        # Create fork node
        fork_id = f"{nid}_fork"
        self._add_node({
            "id": fork_id, "label": instruction, "type": "fork",
            "raw_instruction": instruction,
        })
        # Create branch nodes and parallel edges
        for branch in branches:
            branch_node = {
                "id": branch["id"], "label": branch["label"], "type": "executor",
                "raw_instruction": branch.get("prompt", branch["label"]),
                "phase": self._phase,
            }
            if any(n["id"] == branch["id"] for n in self._tree._nodes):
                raise ValueError(f"Duplicate node id: '{branch['id']}'")
            branch_node.setdefault("inputs", [])
            branch_node.setdefault("outputs", [])
            branch_node.setdefault("warnings", [])
            self._tree._nodes.append(branch_node)
            self._tree._edges.append({
                "source": fork_id, "target": branch["id"],
                "type": "parallel", "label": "",
            })
        return self

    def converge(self, nid: str, instruction: str, *,
                 strategy: str = "merge") -> "PhaseBuilder":
        """Add a converge (join) — synthesizes parallel outputs.

        Strategies: merge, best-of, weighted-merge, consensus
        """
        return self._add_node({
            "id": nid, "label": instruction, "type": "join",
            "raw_instruction": instruction,
            "strategy": strategy,
        })

    def router(self, nid: str, instruction: str, *,
               conditions: list[dict]) -> "PhaseBuilder":
        """Add a router — conditional branching based on computed values.

        Each condition dict: {"if": str, "then": str}
        """
        self._add_node({
            "id": nid, "label": instruction, "type": "router",
            "raw_instruction": instruction,
            "conditions": conditions,
        })
        # Create conditional edges to targets
        for cond in conditions:
            target_id = cond["then"]
            self._tree._edges.append({
                "source": nid, "target": target_id,
                "type": "conditional", "label": cond["if"],
            })
        return self

    def gate(self, nid: str, instruction: str) -> "PhaseBuilder":
        """Add a human approval gate — pauses for user confirmation."""
        return self._add_node({
            "id": nid, "label": instruction, "type": "gate",
            "raw_instruction": instruction,
        })

    def file_io(self, nid: str, instruction: str, *,
                inputs: list[str] | None = None,
                outputs: list[str] | None = None) -> "PhaseBuilder":
        """Add a file I/O node — reads or writes files."""
        return self._add_node({
            "id": nid, "label": instruction, "type": "file_io",
            "raw_instruction": instruction,
            "inputs": inputs or [],
            "outputs": outputs or [],
        })


class SkillTreeBuilder:
    """Fluent builder for constructing skill DAGs.

    Usage:
        tree = SkillTreeBuilder("my-skill", "Description. Use when X.")
        tree.phase("Setup").executor("init", "Initialize workspace")
        tree.phase("Work").tool("fetch", "Fetch data", tools=["WebSearch"])
        result = tree.build()
    """

    def __init__(self, name: str, description: str):
        self._name = name
        self._description = description
        self._nodes: list[dict] = []
        self._edges: list[dict] = []
        self._phases: list[str] = []
        self._mcp_servers: set[str] = set()

    def phase(self, name: str) -> PhaseBuilder:
        """Start a new phase (H2 section). Returns a PhaseBuilder for adding nodes."""
        self._phases.append(name)
        return PhaseBuilder(self, name)

    def build(self) -> dict:
        """Build the final graph structure.

        Returns dict compatible with the parser output schema, plus extended
        fields for advanced node types.
        """
        nodes = list(self._nodes)
        edges = list(self._edges)

        # Auto-generate sequential edges within and across phases
        self._auto_edges(nodes, edges)

        # Generate signal gate conditional edges
        self._gate_edges(nodes, edges)

        # Detect pattern
        pattern = self._detect_pattern(nodes, edges)

        # Collect dependencies
        all_tools = []
        all_files = []
        for n in nodes:
            all_tools.extend(n.get("tools", []))
            all_files.extend(n.get("inputs", []))
            all_files.extend(n.get("outputs", []))
            all_files.extend(n.get("context_files", []))

        return {
            "name": self._name,
            "description": self._description,
            "pattern": pattern,
            "phases": list(self._phases),
            "nodes": nodes,
            "edges": edges,
            "dependencies": {
                "mcp_servers": sorted(self._mcp_servers),
                "files": sorted(set(all_files)),
                "skills": [],
                "tools": sorted(set(all_tools)),
            },
        }

    def _auto_edges(self, nodes: list, edges: list):
        """Add sequential edges between consecutive nodes in same phase."""
        existing = {(e["source"], e["target"]) for e in edges}

        # Group nodes by phase, preserving insertion order
        phase_nodes: dict[str, list[str]] = {}
        for n in nodes:
            phase = n.get("phase", "")
            phase_nodes.setdefault(phase, []).append(n["id"])

        # Sequential within phase (skip fork children — they already have parallel edges)
        fork_children = {e["target"] for e in edges if e["type"] == "parallel"}
        for phase, nids in phase_nodes.items():
            top_level = [nid for nid in nids if nid not in fork_children]
            for i in range(len(top_level) - 1):
                pair = (top_level[i], top_level[i + 1])
                if pair not in existing:
                    edges.append({"source": pair[0], "target": pair[1],
                                  "type": "sequential", "label": ""})
                    existing.add(pair)

        # Cross-phase: last top-level node of phase N → first top-level node of phase N+1
        ordered_phases = list(phase_nodes.keys())
        for i in range(len(ordered_phases) - 1):
            src = phase_nodes[ordered_phases[i]]
            tgt = phase_nodes[ordered_phases[i + 1]]
            src_top = [nid for nid in src if nid not in fork_children]
            tgt_top = [nid for nid in tgt if nid not in fork_children]
            if src_top and tgt_top:
                pair = (src_top[-1], tgt_top[0])
                if pair not in existing:
                    edges.append({"source": pair[0], "target": pair[1],
                                  "type": "sequential", "label": ""})
                    existing.add(pair)

    def _gate_edges(self, nodes: list, edges: list):
        """Add conditional edges for signal gates with branching."""
        existing = {(e["source"], e["target"]) for e in edges}

        for n in nodes:
            if n["type"] != "signal_gate":
                continue
            nid = n["id"]
            on_fail = n.get("on_fail", "retry")

            if on_fail == "branch" and n.get("fail_target"):
                # Find the next sequential node as pass target
                pass_target = None
                for e in list(edges):
                    if e["source"] == nid and e["type"] == "sequential":
                        pass_target = e["target"]
                        edges.remove(e)
                        existing.discard((nid, pass_target))
                        break

                if pass_target:
                    edges.append({"source": nid, "target": pass_target,
                                  "type": "conditional", "label": "pass"})
                fail_target = n["fail_target"]
                pair = (nid, fail_target)
                if pair not in existing:
                    edges.append({"source": nid, "target": fail_target,
                                  "type": "conditional", "label": "fail"})

    def _detect_pattern(self, nodes: list, edges: list) -> str:
        types = {n["type"] for n in nodes}
        edge_types = {e["type"] for e in edges}

        if "fork" in types and "join" in types:
            return "parallel-fan-out-fan-in"
        if "fork" in types:
            return "parallel-fan-out"
        if "parallel" in edge_types:
            return "parallel"
        if "router" in types or "conditional" in edge_types:
            return "conditional-routing"
        if "improvement_loop" in types:
            return "iterative"
        return "sequential"
