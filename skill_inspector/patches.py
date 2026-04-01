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
    patches.extend(_check_join_without_fork(nodes, edges))
    patches.extend(_check_unreachable(nodes, edges))
    patches.extend(_check_cycles(nodes, edges))
    patches.extend(_check_parallel_dependencies(nodes, edges))
    patches.extend(_check_depth_complexity(nodes, edges))
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


def _check_join_without_fork(nodes, edges):
    """S4 — Every join node should have an upstream fork."""
    join_ids = [n["id"] for n in nodes if n.get("type") == "join"]
    fork_ids = set(n["id"] for n in nodes if n.get("type") == "fork")

    rev_adj = {}
    for e in edges:
        rev_adj.setdefault(e["target"], []).append(e["source"])

    patches = []
    for jid in join_ids:
        visited = set()
        queue = [jid]
        found_fork = False
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current in fork_ids and current != jid:
                found_fork = True
                break
            for neighbor in rev_adj.get(current, []):
                queue.append(neighbor)

        if not found_fork:
            label = _node_label(nodes, jid)
            phase = _node_phase(nodes, jid)
            patches.append({
                "check_id": "S4",
                "severity": "warning",
                "message": f"Join node '{label}' has no upstream fork — may be synthesizing from sequential steps (intentional?).",
                "location": f"Phase \"{phase}\", node \"{label}\"" if phase else f"Node \"{label}\"",
                "suggestion": (
                    f"If '{label}' is collecting outputs from parallel work, add an "
                    f"upstream fork node. If it's synthesizing sequential outputs, "
                    f"consider changing its type to 'executor'."
                ),
            })

    return patches


def _check_unreachable(nodes, edges):
    """S5 — Every node must be reachable from the entry node."""
    if not nodes:
        return []

    targets = {e["target"] for e in edges}
    entry_id = None
    for n in nodes:
        if n["id"] not in targets:
            entry_id = n["id"]
            break
    if entry_id is None:
        return []

    adj = {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])

    visited = set()
    queue = [entry_id]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for neighbor in adj.get(current, []):
            queue.append(neighbor)

    patches = []
    for n in nodes:
        if n["id"] not in visited:
            label = n.get("label", n["id"])
            phase = n.get("phase", "")
            patches.append({
                "check_id": "S5",
                "severity": "error",
                "message": f"Node '{label}' is unreachable from the skill entry point.",
                "location": f"Phase \"{phase}\", node \"{label}\"" if phase else f"Node \"{label}\"",
                "suggestion": (
                    f"Connect '{label}' to the main flow by adding an edge from "
                    f"an upstream node, or remove it if it's unused."
                ),
            })

    return patches


def _check_cycles(nodes, edges):
    """S6 — The graph should be acyclic. Exempt validator->executor retry loops."""
    adj = {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n["id"]: WHITE for n in nodes}
    patches = []
    cycle_pairs = set()

    def dfs(nid, path):
        color[nid] = GRAY
        for neighbor in adj.get(nid, []):
            if neighbor in path:
                src_type = _node_type(nodes, nid)
                tgt_type = _node_type(nodes, neighbor)
                if src_type == "validator" and tgt_type == "executor":
                    continue
                pair = (nid, neighbor)
                if pair not in cycle_pairs:
                    cycle_pairs.add(pair)
                    src_label = _node_label(nodes, nid)
                    tgt_label = _node_label(nodes, neighbor)
                    patches.append({
                        "check_id": "S6",
                        "severity": "error",
                        "message": f"Cycle detected: '{src_label}' -> '{tgt_label}' -> ... -> '{src_label}'.",
                        "location": f"Node \"{src_label}\"",
                        "suggestion": (
                            f"Break the cycle by removing the edge from '{src_label}' to "
                            f"'{tgt_label}', or restructure into a bounded retry with "
                            f"a validator node."
                        ),
                    })
            elif color.get(neighbor, WHITE) == WHITE:
                dfs(neighbor, path | {nid})
        color[nid] = BLACK

    for n in nodes:
        if color.get(n["id"], WHITE) == WHITE:
            dfs(n["id"], set())

    return patches


def _check_depth_complexity(nodes, edges):
    """O5 — Flag skills where the longest path exceeds 12 nodes."""
    if not nodes:
        return []

    adj = {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])

    targets = {e["target"] for e in edges}
    entry_id = None
    for n in nodes:
        if n["id"] not in targets:
            entry_id = n["id"]
            break
    if entry_id is None:
        return []

    memo = {}

    def longest_from(nid, visited):
        if nid in memo:
            return memo[nid]
        if nid in visited:
            return 0
        best = 0
        for neighbor in adj.get(nid, []):
            best = max(best, 1 + longest_from(neighbor, visited | {nid}))
        memo[nid] = best
        return best

    depth = 1 + longest_from(entry_id, set())

    if depth > 12:
        return [{
            "check_id": "O5",
            "severity": "info",
            "message": f"Skill has {depth} steps in the longest path — consider simplifying or splitting.",
            "location": "Whole graph",
            "suggestion": (
                f"The longest execution path is {depth} nodes deep. Consider "
                f"breaking the skill into smaller composable skills chained via "
                f"spawn nodes, or collapsing sequential steps that could run as one."
            ),
        }]

    return []
