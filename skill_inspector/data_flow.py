"""Data flow checks for skill DAGs.

Validates input/output contracts between connected nodes and checks
that referenced files exist on disk.
"""
import os


def check_data_flow(nodes, edges, skill_dir=None):
    """Run all data flow checks. Returns list of issue dicts.

    Args:
        nodes: list of node dicts with id, inputs, outputs
        edges: list of edge dicts with source, target
        skill_dir: absolute path to the skill directory (for D3 file checks)
    """
    issues = []
    issues.extend(_check_unproduced_inputs(nodes, edges))
    issues.extend(_check_unconsumed_outputs(nodes, edges))
    if skill_dir:
        issues.extend(_check_missing_file_references(nodes, skill_dir))
    issues.extend(_check_implicit_data_passing(nodes, edges))
    return issues


def _node_label(nodes, node_id):
    for n in nodes:
        if n["id"] == node_id:
            return n.get("label", node_id)
    return node_id


def _build_adj(edges):
    adj = {}
    rev = {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])
        rev.setdefault(e["target"], []).append(e["source"])
    return adj, rev


def _upstream_outputs(node_id, nodes, edges):
    """Collect all outputs from nodes upstream of node_id."""
    _, rev = _build_adj(edges)
    visited = set()
    queue = list(rev.get(node_id, []))
    outputs = set()
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for n in nodes:
            if n["id"] == current:
                outputs.update(n.get("outputs", []))
                break
        for parent in rev.get(current, []):
            queue.append(parent)
    return outputs


def _downstream_inputs(node_id, nodes, edges):
    """Collect all inputs from nodes downstream of node_id."""
    adj, _ = _build_adj(edges)
    visited = set()
    queue = list(adj.get(node_id, []))
    inputs = set()
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for n in nodes:
            if n["id"] == current:
                inputs.update(n.get("inputs", []))
                break
        for child in adj.get(current, []):
            queue.append(child)
    return inputs


def _check_unproduced_inputs(nodes, edges):
    """D1 — Every file in a node's inputs should be produced by some upstream node."""
    issues = []
    for n in nodes:
        for inp in n.get("inputs", []):
            upstream = _upstream_outputs(n["id"], nodes, edges)
            if inp not in upstream:
                label = n.get("label", n["id"])
                phase = n.get("phase", "")
                issues.append({
                    "check_id": "D1",
                    "severity": "error",
                    "message": f"Node '{label}' expects input '{inp}' but no prior node produces it.",
                    "location": f"Phase \"{phase}\", node \"{label}\"" if phase else f"Node \"{label}\"",
                    "suggestion": (
                        f"Add a file_io or executor node upstream of '{label}' that "
                        f"produces '{inp}', or add '{inp}' to an existing upstream "
                        f"node's outputs."
                    ),
                })
    return issues


def _check_unconsumed_outputs(nodes, edges):
    """D2 — Every file in a node's outputs should be consumed by some downstream node."""
    issues = []
    for n in nodes:
        for out in n.get("outputs", []):
            downstream = _downstream_inputs(n["id"], nodes, edges)
            if out not in downstream:
                label = n.get("label", n["id"])
                phase = n.get("phase", "")
                issues.append({
                    "check_id": "D2",
                    "severity": "info",
                    "message": f"Node '{label}' produces '{out}' but nothing downstream consumes it.",
                    "location": f"Phase \"{phase}\", node \"{label}\"" if phase else f"Node \"{label}\"",
                    "suggestion": (
                        f"If '{out}' is a final deliverable, this is expected. "
                        f"Otherwise, add it to a downstream node's inputs."
                    ),
                })
    return issues


def _check_missing_file_references(nodes, skill_dir):
    """D3 — Referenced files (e.g., references/examples.md) should exist on disk."""
    issues = []
    checked = set()
    for n in nodes:
        for f in n.get("inputs", []) + n.get("outputs", []):
            if f in checked:
                continue
            checked.add(f)
            # Only check paths that look like relative references (not workspace intermediates)
            if f.startswith("references/") or f.startswith("scripts/"):
                full_path = os.path.join(skill_dir, f)
                if not os.path.exists(full_path):
                    label = n.get("label", n["id"])
                    issues.append({
                        "check_id": "D3",
                        "severity": "warning",
                        "message": f"Referenced file '{f}' not found on disk.",
                        "location": f"Node \"{label}\"",
                        "suggestion": (
                            f"Create '{f}' in the skill directory, or remove the "
                            f"reference if the file is no longer needed."
                        ),
                    })
    return issues


def _check_implicit_data_passing(nodes, edges):
    """D4 — Flag connected nodes where neither has explicit inputs/outputs."""
    node_map = {n["id"]: n for n in nodes}
    issues = []
    for e in edges:
        src = node_map.get(e["source"], {})
        tgt = node_map.get(e["target"], {})
        src_has_data = bool(src.get("outputs"))
        tgt_has_data = bool(tgt.get("inputs"))
        # Only flag executor-to-executor connections (tools and file_io are expected to be implicit)
        if (not src_has_data and not tgt_has_data
                and src.get("type") == "executor" and tgt.get("type") == "executor"):
            src_label = src.get("label", e["source"])
            tgt_label = tgt.get("label", e["target"])
            issues.append({
                "check_id": "D4",
                "severity": "info",
                "message": f"Edge '{src_label}' -> '{tgt_label}' has no explicit data contract — relies on implicit context.",
                "location": f"Edge \"{src_label}\" -> \"{tgt_label}\"",
                "suggestion": (
                    f"Consider adding explicit inputs/outputs to clarify what data "
                    f"flows from '{src_label}' to '{tgt_label}'."
                ),
            })
    return issues
