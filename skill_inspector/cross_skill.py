"""Cross-skill dependency graph builder.

Extracts spawn/chain edges between skills to build a meta-level
dependency graph. Detects missing targets and cycles.
"""
import re


def build_cross_skill_graph(skills):
    """Build a dependency graph across parsed skills.

    Args:
        skills: list of skill dicts (each with name, nodes, edges)

    Returns:
        dict with nodes (skills), edges (spawn/chain), and warnings
    """
    skill_names = {s["name"] for s in skills}
    meta_nodes = []
    meta_edges = []
    warnings = []

    for skill in skills:
        meta_nodes.append({
            "id": skill["name"],
            "label": skill["name"],
            "node_count": len(skill.get("nodes", [])),
            "score": skill.get("quality", {}).get("score"),
        })

        # Find spawn nodes that reference other skills
        for node in skill.get("nodes", []):
            if node.get("type") == "spawn":
                target_name = _extract_skill_name(node)
                if target_name:
                    meta_edges.append({
                        "source": skill["name"],
                        "target": target_name,
                        "label": node.get("label", ""),
                    })
                    if target_name not in skill_names:
                        warnings.append({
                            "type": "missing_target",
                            "source": skill["name"],
                            "target": target_name,
                            "message": f"Skill '{skill['name']}' chains to '{target_name}' but it was not found among parsed skills.",
                        })

    # Detect cycles
    adj = {}
    for e in meta_edges:
        adj.setdefault(e["source"], []).append(e["target"])

    cycles = _find_cycles(adj, skill_names)
    for cycle in cycles:
        warnings.append({
            "type": "cycle",
            "path": cycle,
            "message": f"Circular dependency: {' -> '.join(cycle)}",
        })

    return {
        "nodes": meta_nodes,
        "edges": meta_edges,
        "warnings": warnings,
    }


def _extract_skill_name(node):
    """Extract a target skill name from a spawn node's label or instruction."""
    text = f"{node.get('label', '')} {node.get('raw_instruction', '')}"

    # Match patterns like "chain to `product-brief` skill" or "chain to prototype skill"
    m = re.search(r"chain to [`\"]?([a-z0-9_-]+)[`\"]?\s*skill", text, re.IGNORECASE)
    if m:
        return m.group(1)

    # Match "/skill-name" invocations
    m = re.search(r"/([a-z0-9_-]+)", text)
    if m:
        return m.group(1)

    # Match "→ skill-name" or "pass to skill-name"
    m = re.search(r"(?:pass to|invoke|trigger)\s+[`\"]?([a-z0-9_-]+)[`\"]?", text, re.IGNORECASE)
    if m:
        return m.group(1)

    # Fall back to the node label if it looks like a skill name
    label = node.get("label", "")
    m = re.match(r"Chain to ([a-z0-9_-]+)", label, re.IGNORECASE)
    if m:
        return m.group(1)

    return None


def _find_cycles(adj, all_nodes):
    """Find all cycles in a directed graph."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in all_nodes}
    cycles = []

    def dfs(node, path):
        color[node] = GRAY
        for neighbor in adj.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY and neighbor in path:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif color[neighbor] == WHITE:
                dfs(neighbor, path + [neighbor])
        color[node] = BLACK

    for node in all_nodes:
        if color[node] == WHITE:
            dfs(node, [node])

    return cycles
