"""Emit valid SKILL.md files from SkillTreeBuilder output.

Generates markdown that round-trips through the existing heuristic parser
by using the exact keywords the parser detects for each node type.
"""


def emit_skill_md(graph: dict) -> str:
    """Convert a builder graph dict into a SKILL.md string.

    The emitted markdown uses keywords that the parser's heuristics detect,
    ensuring the SKILL.md can be parsed back into an equivalent DAG.
    """
    lines: list[str] = []

    # --- Frontmatter ---
    lines.append("---")
    lines.append(f"name: {graph['name']}")
    desc = graph["description"]
    if "\n" in desc or len(desc) > 80:
        lines.append("description: >")
        for dline in desc.splitlines():
            lines.append(f"  {dline}")
    else:
        lines.append(f"description: >{'' if desc.startswith(' ') else ' '}{desc}")
    deps = graph.get("dependencies", {})
    if deps.get("mcp_servers"):
        lines.append(f"mcp_servers: [{', '.join(deps['mcp_servers'])}]")
    lines.append("---")
    lines.append("")

    # --- Title ---
    lines.append(f"# {graph['name']}")
    lines.append("")

    # --- Phases ---
    phases = graph.get("phases", [])
    nodes_by_phase: dict[str, list[dict]] = {}
    for node in graph["nodes"]:
        phase = node.get("phase", "")
        nodes_by_phase.setdefault(phase, []).append(node)

    # Build edge lookup for fork children
    fork_children = set()
    for edge in graph["edges"]:
        if edge["type"] == "parallel":
            fork_children.add(edge["target"])

    for phase in phases:
        phase_nodes = nodes_by_phase.get(phase, [])
        if not phase_nodes:
            continue

        lines.append(f"## {phase}")
        lines.append("")

        for node in phase_nodes:
            if node["id"] in fork_children:
                continue  # rendered as H3 children of their fork
            lines.extend(_emit_node(node, graph))
            lines.append("")

    # --- Troubleshooting ---
    lines.append("## Troubleshooting")
    lines.append("")
    lines.append("If something goes wrong during execution, check these common issues:")
    lines.append("")
    if deps.get("tools"):
        lines.append("**Tool access issues:**")
        lines.append(f"Ensure the following tools are available: {', '.join(deps['tools'])}")
        lines.append("")
    if deps.get("mcp_servers"):
        lines.append("**MCP server issues:**")
        for srv in deps["mcp_servers"]:
            lines.append(f"- Verify `{srv}` is configured and running")
        lines.append("")
    if deps.get("files"):
        lines.append("**Missing files:**")
        lines.append("Ensure these files exist before running:")
        for f in deps["files"]:
            lines.append(f"- `{f}`")
        lines.append("")

    # --- References ---
    if deps.get("files"):
        lines.append("## References")
        lines.append("")
        for f in deps["files"]:
            lines.append(f"- `{f}`")
        lines.append("")

    return "\n".join(lines)


def _emit_node(node: dict, graph: dict) -> list[str]:
    """Emit markdown lines for a single node."""
    ntype = node["type"]
    emitter = _NODE_EMITTERS.get(ntype, _emit_executor)
    return emitter(node, graph)


def _emit_executor(node: dict, graph: dict) -> list[str]:
    lines = [f"### {node['label']}", ""]
    lines.append(node.get("raw_instruction", node["label"]))
    return lines


def _emit_tool(node: dict, graph: dict) -> list[str]:
    lines = [f"### {node['label']}", ""]
    lines.append(node.get("raw_instruction", "").split("\n```")[0].strip())
    if node.get("tools"):
        lines.append("")
        lines.append(f"Fetch data using: {', '.join(node['tools'])}")
    # Extract and emit code blocks from raw_instruction
    raw = node.get("raw_instruction", "")
    if "```bash" in raw:
        idx = raw.index("```bash")
        lines.append("")
        lines.append(raw[idx:].strip())
    elif node.get("commands"):
        lines.append("")
        lines.append("```bash")
        for cmd in node["commands"]:
            lines.append(cmd)
        lines.append("```")
    return lines


def _emit_subagent(node: dict, graph: dict) -> list[str]:
    agent_type = node.get("agent_type", "general-purpose")
    lines = [f"### {node['label']}", ""]
    lines.append(f"Launch a **{agent_type}** sub-agent to run in parallel with the following task:")
    lines.append("")
    lines.append(f"> {node.get('raw_instruction', node['label'])}")
    if node.get("tools"):
        lines.append("")
        lines.append(f"Tools available: {', '.join(node['tools'])}")
    if node.get("context_files"):
        lines.append("")
        lines.append("Load the following context before starting:")
        for f in node["context_files"]:
            lines.append(f"- Read `{f}`")
    return lines


def _emit_context_loader(node: dict, graph: dict) -> list[str]:
    lines = [f"### {node['label']}", ""]
    lines.append("Read and load the following context files:")
    lines.append("")
    for f in node.get("inputs", []):
        lines.append(f"- Load `{f}`")
    if node.get("urls"):
        lines.append("")
        lines.append("Also fetch data from:")
        for url in node["urls"]:
            lines.append(f"- Fetch `{url}`")
    return lines


def _emit_signal_gate(node: dict, graph: dict) -> list[str]:
    lines = [f"### {node['label']}", ""]
    lines.append("Check whether the following criteria are met before proceeding:")
    lines.append("")
    for metric, threshold in node.get("criteria", {}).items():
        lines.append(f"- **{metric}**: {threshold}")
    lines.append("")
    on_fail = node.get("on_fail", "retry")
    max_retries = node.get("max_retries", 3)
    if on_fail == "retry":
        lines.append(f"If any criterion fails, retry up to {max_retries} times.")
        lines.append("On each retry, analyze what went wrong and adjust the approach.")
    elif on_fail == "branch":
        fail_target = node.get("fail_target", "fallback")
        lines.append(f"If criteria pass → proceed to next step.")
        lines.append(f'If criteria fail → "{fail_target}" → route to remediation.')
    return lines


def _emit_improvement_loop(node: dict, graph: dict) -> list[str]:
    strategy = node.get("strategy", "ralph")
    max_iter = node.get("max_iterations", 5)
    lines = [f"### {node['label']}", ""]

    if strategy == "ralph":
        lines.append(f"Apply the RALPH methodology (up to {max_iter} iterations):")
    else:
        lines.append(f"Iterate up to {max_iter} times to improve the output:")
    lines.append("")

    steps = node.get("steps", [])
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}. {step}")

    exit_criteria = node.get("exit_criteria", {})
    if exit_criteria:
        lines.append("")
        lines.append("**Exit when all criteria are met:**")
        for metric, threshold in exit_criteria.items():
            lines.append(f"- {metric}: {threshold}")

    lines.append("")
    lines.append("Validate the output against criteria after each iteration. "
                 "Fix failures before proceeding.")
    return lines


def _emit_fork(node: dict, graph: dict) -> list[str]:
    lines = [f"### {node['label']} (parallel)", ""]
    lines.append("Run the following tasks simultaneously in parallel:")
    lines.append("")

    # Find children via parallel edges
    children = []
    for edge in graph["edges"]:
        if edge["source"] == node["id"] and edge["type"] == "parallel":
            child = next((n for n in graph["nodes"] if n["id"] == edge["target"]), None)
            if child:
                children.append(child)

    for child in children:
        lines.append(f"#### {child['label']}")
        lines.append("")
        lines.append(child.get("raw_instruction", child["label"]))
        lines.append("")

    return lines


def _emit_join(node: dict, graph: dict) -> list[str]:
    strategy = node.get("strategy", "merge")
    lines = [f"### {node['label']}", ""]
    strategy_desc = {
        "merge": "Read all outputs and merge them into a unified result.",
        "best-of": "Read all outputs, compare quality, and select the best result.",
        "weighted-merge": "Read all outputs and synthesize them with weighted importance.",
        "consensus": "Read all outputs and converge on consensus points.",
    }
    lines.append(strategy_desc.get(strategy,
                                    f"Synthesize and converge all parallel outputs using {strategy} strategy."))
    return lines


def _emit_router(node: dict, graph: dict) -> list[str]:
    lines = [f"### {node['label']}", ""]
    lines.append("Based on the computed metrics, route to the appropriate path:")
    lines.append("")
    for cond in node.get("conditions", []):
        lines.append(f"- If {cond['if']} then → **{cond['then']}**")
    return lines


def _emit_gate(node: dict, graph: dict) -> list[str]:
    lines = [f"### {node['label']}", ""]
    lines.append("Ask the user to confirm before proceeding:")
    lines.append("")
    lines.append(f"> {node.get('raw_instruction', node['label'])}")
    return lines


def _emit_file_io(node: dict, graph: dict) -> list[str]:
    lines = [f"### {node['label']}", ""]
    if node.get("inputs"):
        lines.append("Read the following input files:")
        for f in node["inputs"]:
            lines.append(f"- Input: `{f}`")
        lines.append("")
    if node.get("outputs"):
        lines.append("Save to the following output files:")
        for f in node["outputs"]:
            lines.append(f"- Write to `{f}`")
    if not node.get("inputs") and not node.get("outputs"):
        lines.append(node.get("raw_instruction", node["label"]))
    return lines


_NODE_EMITTERS = {
    "executor": _emit_executor,
    "tool": _emit_tool,
    "subagent": _emit_subagent,
    "context_loader": _emit_context_loader,
    "signal_gate": _emit_signal_gate,
    "improvement_loop": _emit_improvement_loop,
    "fork": _emit_fork,
    "join": _emit_join,
    "router": _emit_router,
    "gate": _emit_gate,
    "file_io": _emit_file_io,
}
