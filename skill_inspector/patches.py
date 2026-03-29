"""Structural patch suggestion engine.

Analyzes a DAG (nodes + edges) for structural issues and generates
natural language restructure suggestions referencing phase names and
node labels. No content editing — only structural fixes.
"""

# Terminal node types that are expected to have no outgoing edges
TERMINAL_TYPES = {"gate", "spawn", "exit"}


def suggest_patches(nodes, edges):
    """Run all structural checks and return patch suggestions.

    Args:
        nodes: list of node dicts with id, type, label, phase
        edges: list of edge dicts with source, target, type, label

    Returns:
        list of patch dicts with check_id, severity, message, location, suggestion
    """
    patches = []
    patches.extend(_check_orphan_nodes(nodes, edges))
    patches.extend(_check_dead_ends(nodes, edges))
    patches.extend(_check_fork_without_join(nodes, edges))
    patches.extend(_check_parallel_dependencies(nodes, edges))
    return patches


def _node_label(nodes, node_id):
    for n in nodes:
        if n["id"] == node_id:
            return n.get("label", node_id)
    return node_id


def _node_phase(nodes, node_id):
    for n in nodes:
        if n["id"] == node_id:
            return n.get("phase", "")
    return ""


def _node_type(nodes, node_id):
    for n in nodes:
        if n["id"] == node_id:
            return n.get("type", "")
    return ""


def _check_orphan_nodes(nodes, edges):
    """S1 — Every node (except entry) should have at least one incoming edge."""
    targets = {e["target"] for e in edges}
    sources = {e["source"] for e in edges}

    # Entry node = first node with no incoming edges (the legitimate root)
    entry_ids = set()
    for n in nodes:
        if n["id"] not in targets:
            entry_ids.add(n["id"])

    # If there's only one root, that's the entry — others without incoming are orphans
    patches = []
    if len(entry_ids) <= 1:
        return patches

    # First entry_id is legitimate entry, rest are orphans
    legitimate_entry = None
    for n in nodes:
        if n["id"] in entry_ids:
            if legitimate_entry is None:
                legitimate_entry = n["id"]
            else:
                # This is an orphan
                label = n.get("label", n["id"])
                phase = n.get("phase", "")
                patches.append({
                    "check_id": "S1",
                    "severity": "error",
                    "message": f"Node '{label}' has no incoming edge — it will never execute.",
                    "location": f"Phase \"{phase}\", node \"{label}\"" if phase else f"Node \"{label}\"",
                    "suggestion": (
                        f"Add a sequential edge from an upstream node to '{label}', "
                        f"or move '{label}' into an existing parallel group where it "
                        f"can execute alongside related nodes."
                    ),
                })

    return patches


def _check_dead_ends(nodes, edges):
    """S2 — Every node (except terminal types) should have outgoing edges."""
    sources = {e["source"] for e in edges}
    patches = []

    for n in nodes:
        ntype = n.get("type", "")
        if ntype in TERMINAL_TYPES:
            continue
        if n["id"] not in sources:
            label = n.get("label", n["id"])
            phase = n.get("phase", "")
            patches.append({
                "check_id": "S2",
                "severity": "warning",
                "message": f"Node '{label}' has no outgoing edge — execution stops here unexpectedly.",
                "location": f"Phase \"{phase}\", node \"{label}\"" if phase else f"Node \"{label}\"",
                "suggestion": (
                    f"Add a sequential edge from '{label}' to the next step, "
                    f"or if '{label}' is a terminal node, change its type to "
                    f"'gate' or 'spawn' to indicate it's an intentional endpoint."
                ),
            })

    return patches


def _check_fork_without_join(nodes, edges):
    """S3 — Every fork node should have a downstream join."""
    fork_ids = [n["id"] for n in nodes if n.get("type") == "fork"]
    join_ids = set(n["id"] for n in nodes if n.get("type") == "join")

    # Build reachability from each fork
    adj = {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])

    patches = []
    for fid in fork_ids:
        # BFS from fork to see if we reach any join
        visited = set()
        queue = [fid]
        found_join = False
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current in join_ids and current != fid:
                found_join = True
                break
            for neighbor in adj.get(current, []):
                queue.append(neighbor)

        if not found_join:
            label = _node_label(nodes, fid)
            phase = _node_phase(nodes, fid)
            patches.append({
                "check_id": "S3",
                "severity": "error",
                "message": f"Parallel fork '{label}' has no convergence point — parallel outputs are never synthesized.",
                "location": f"Phase \"{phase}\", node \"{label}\"" if phase else f"Node \"{label}\"",
                "suggestion": (
                    f"Add a join node after the parallel branches spawned by '{label}'. "
                    f"The join node should collect outputs from all branches before "
                    f"passing them to the next sequential step."
                ),
            })

    return patches


def _check_parallel_dependencies(nodes, edges):
    """SP1 — Detect parallel siblings with data dependencies between them."""
    # Find fork nodes and their parallel children
    fork_children = {}
    for e in edges:
        if e.get("type") == "parallel":
            fork_children.setdefault(e["source"], []).append(e["target"])

    patches = []
    for fork_id, children in fork_children.items():
        child_set = set(children)
        # Check if any edge connects two parallel siblings
        for e in edges:
            if e["source"] in child_set and e["target"] in child_set:
                src_label = _node_label(nodes, e["source"])
                tgt_label = _node_label(nodes, e["target"])
                src_phase = _node_phase(nodes, e["source"])
                fork_label = _node_label(nodes, fork_id)
                patches.append({
                    "check_id": "SP1",
                    "severity": "warning",
                    "message": (
                        f"'{src_label}' and '{tgt_label}' are in a parallel group "
                        f"but '{tgt_label}' depends on '{src_label}'s output."
                    ),
                    "location": f"Phase \"{src_phase}\", fork \"{fork_label}\"" if src_phase else f"Fork \"{fork_label}\"",
                    "suggestion": (
                        f"Move '{tgt_label}' out of the parallel group from '{fork_label}'. "
                        f"Create a new sequential phase after the parallel group containing "
                        f"only '{tgt_label}'. '{tgt_label}' should receive '{src_label}'s "
                        f"output as input."
                    ),
                })

    return patches
