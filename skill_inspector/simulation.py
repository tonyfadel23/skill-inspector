"""SimulationEngine — pure state machine for DAG step-through traversal.

Operates on nodes + edges arrays. No DOM dependencies.
Browser code reads state and applies CSS classes.

Fork behavior:
- Converging fork: branches that reach a common join node step one-at-a-time.
- Independent fork: branches with no downstream join activate simultaneously.
"""


class SimulationEngine:
    def __init__(self, nodes, edges):
        self._nodes = nodes
        self._edges = edges
        self._active = []
        self._visited = []
        self._waiting_for_selection = False
        self._branch_options = []
        self._complete = False
        self._converging_fork = None
        self._independent_fork_count = 0

    def _find_entry_node(self):
        """Entry node = first node with no incoming edges."""
        targets = {e["target"] for e in self._edges}
        for node in self._nodes:
            if node["id"] not in targets:
                return node["id"]
        return self._nodes[0]["id"] if self._nodes else None

    def _get_node_type(self, node_id):
        for node in self._nodes:
            if node["id"] == node_id:
                return node.get("type", "")
        return ""

    def _outgoing_edges(self, node_id):
        return [e for e in self._edges if e["source"] == node_id]

    def _incoming_edges(self, node_id):
        return [e for e in self._edges if e["target"] == node_id]

    def _is_decision_node(self, node_id):
        node_type = self._get_node_type(node_id)
        if node_type in ("router", "gate"):
            return True
        out = self._outgoing_edges(node_id)
        return any(e.get("type") == "conditional" for e in out)

    def _is_fork_node(self, node_id):
        return self._get_node_type(node_id) == "fork"

    def _is_join_node(self, node_id):
        return self._get_node_type(node_id) == "join"

    def _find_join_for_branch(self, start_id):
        """Walk forward from start_id to find a downstream join node.

        Returns the join node ID if found, None otherwise.
        """
        visited = set()
        queue = [start_id]
        while queue:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            if self._is_join_node(nid):
                return nid
            for e in self._outgoing_edges(nid):
                queue.append(e["target"])
        return None

    def start(self):
        self._complete = False
        self._visited = []
        self._waiting_for_selection = False
        self._branch_options = []
        self._converging_fork = None
        self._independent_fork_count = 0
        entry = self._find_entry_node()
        if entry:
            self._activate_nodes([entry])
        else:
            self._active = []

    def _activate_nodes(self, node_ids):
        """Set nodes active, auto-detecting decision nodes that need selection."""
        self._active = node_ids
        if len(node_ids) == 1 and self._is_decision_node(node_ids[0]):
            out = self._outgoing_edges(node_ids[0])
            self._waiting_for_selection = True
            self._branch_options = [
                {"target": e["target"], "label": e.get("label", "")}
                for e in out
            ]

    def _step_converging(self):
        """Process one step inside a converging fork — advance current branch."""
        cf = self._converging_fork
        branch = cf["branches"][cf["current_branch_index"]]

        # Process all currently active nodes (within current branch)
        all_successors = []
        for node_id in self._active:
            if node_id not in self._visited:
                self._visited.append(node_id)
            out = self._outgoing_edges(node_id)
            for e in out:
                if e["target"] not in all_successors:
                    all_successors.append(e["target"])

        # Check if any successor is the join node
        join_id = cf["join_id"]
        reached_join = join_id in all_successors
        non_join_successors = [s for s in all_successors if s != join_id]

        if reached_join and not non_join_successors:
            # This branch reached the join
            cf["arrived_at_join"].append(branch[0])
            cf["current_branch_index"] += 1

            if cf["current_branch_index"] >= len(cf["branches"]):
                # All branches arrived — activate the join node
                self._converging_fork = None
                self._activate_nodes([join_id])
            else:
                # Move to next branch
                next_branch = cf["branches"][cf["current_branch_index"]]
                self._activate_nodes([next_branch[0]])
        elif non_join_successors:
            # Branch continues (hasn't reached join yet)
            self._activate_nodes(non_join_successors)
        else:
            # Dead end within branch — move to next branch
            cf["arrived_at_join"].append(branch[0])
            cf["current_branch_index"] += 1
            if cf["current_branch_index"] >= len(cf["branches"]):
                self._converging_fork = None
                self._activate_nodes([join_id])
            else:
                next_branch = cf["branches"][cf["current_branch_index"]]
                self._activate_nodes([next_branch[0]])

    def step(self):
        if self._complete or not self._active or self._waiting_for_selection:
            return

        self._independent_fork_count = 0

        # Case 1: Inside a converging fork playback
        if self._converging_fork is not None:
            self._step_converging()
            return

        # Case 2 & 3: Normal processing (may encounter a fork)
        all_successors = []

        for node_id in self._active:
            if node_id not in self._visited:
                self._visited.append(node_id)

            out = self._outgoing_edges(node_id)
            if not out:
                continue

            if self._is_fork_node(node_id):
                # Detect converging vs independent branches
                branch_targets = []
                for e in out:
                    if e["target"] not in [bt for bt, _ in branch_targets]:
                        join_id = self._find_join_for_branch(e["target"])
                        branch_targets.append((e["target"], join_id))

                # Group by join node
                converging = {}  # join_id -> [branch_start_ids]
                independent = []
                for target, join_id in branch_targets:
                    if join_id is not None:
                        converging.setdefault(join_id, []).append(target)
                    else:
                        independent.append(target)

                # Find converging groups (2+ branches sharing a join)
                conv_group = None
                conv_join = None
                for jid, branches in converging.items():
                    if len(branches) >= 2:
                        conv_group = branches
                        conv_join = jid
                        break
                    else:
                        # Single branch to a join — treat as independent
                        independent.extend(branches)

                if conv_group:
                    # Set up converging fork state
                    self._converging_fork = {
                        "fork_id": node_id,
                        "join_id": conv_join,
                        "branches": [[b] for b in conv_group],
                        "current_branch_index": 0,
                        "arrived_at_join": [],
                    }
                    # Start first converging branch + any independent branches
                    first_converging = [conv_group[0]]
                    activate = first_converging + independent
                    if independent:
                        self._independent_fork_count = len(independent)
                    self._activate_nodes(activate)
                else:
                    # All branches are independent
                    self._independent_fork_count = len(independent)
                    for target in independent:
                        if target not in all_successors:
                            all_successors.append(target)
            else:
                for e in out:
                    target = e["target"]
                    if self._is_join_node(target):
                        incoming = self._incoming_edges(target)
                        all_visited = all(
                            ie["source"] in self._visited for ie in incoming
                        )
                        if all_visited and target not in all_successors:
                            all_successors.append(target)
                    else:
                        if target not in all_successors:
                            all_successors.append(target)

        # If we set up a converging fork, _activate_nodes was already called
        if self._converging_fork is not None:
            return

        if not all_successors:
            self._complete = True
            self._active = []
        else:
            self._activate_nodes(all_successors)

    def select_branch(self, index):
        if not self._waiting_for_selection or index >= len(self._branch_options):
            return

        chosen = self._branch_options[index]
        current = self._active[0] if self._active else None
        if current and current not in self._visited:
            self._visited.append(current)

        self._active = [chosen["target"]]
        self._waiting_for_selection = False
        self._branch_options = []

    def reset(self):
        self._active = []
        self._visited = []
        self._waiting_for_selection = False
        self._branch_options = []
        self._complete = False
        self._converging_fork = None
        self._independent_fork_count = 0

    def is_complete(self):
        return self._complete

    def get_state(self):
        return {
            "active": list(self._active),
            "visited": list(self._visited),
            "waiting_for_selection": self._waiting_for_selection,
            "branch_options": list(self._branch_options),
            "converging_fork": dict(self._converging_fork) if self._converging_fork else None,
            "independent_fork_count": self._independent_fork_count,
        }
