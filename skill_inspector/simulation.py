"""SimulationEngine — pure state machine for DAG step-through traversal.

Operates on nodes + edges arrays. No DOM dependencies.
Browser code reads state and applies CSS classes.
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

    def start(self):
        self._complete = False
        self._visited = []
        self._waiting_for_selection = False
        self._branch_options = []
        entry = self._find_entry_node()
        if entry:
            self._activate_nodes([entry])
        else:
            self._active = []

    def _activate_nodes(self, node_ids):
        """Set nodes active, auto-detecting decision nodes that need selection."""
        self._active = node_ids
        # If a single decision node is now active, pause for selection
        if len(node_ids) == 1 and self._is_decision_node(node_ids[0]):
            out = self._outgoing_edges(node_ids[0])
            self._waiting_for_selection = True
            self._branch_options = [
                {"target": e["target"], "label": e.get("label", "")}
                for e in out
            ]

    def step(self):
        if self._complete or not self._active or self._waiting_for_selection:
            return

        # Process ONE active node per step (parallel branches advance one at a time)
        node_id = self._active[0]
        remaining = self._active[1:]
        out = self._outgoing_edges(node_id)

        if not out:
            # Terminal node — mark visited
            if node_id not in self._visited:
                self._visited.append(node_id)
            if not remaining:
                self._complete = True
                self._active = []
            else:
                self._active = remaining
            return

        if node_id not in self._visited:
            self._visited.append(node_id)

        successors = []
        if self._is_fork_node(node_id):
            # Activate ALL parallel children
            for e in out:
                if e["target"] not in successors:
                    successors.append(e["target"])
        else:
            for e in out:
                target = e["target"]
                if self._is_join_node(target):
                    incoming = self._incoming_edges(target)
                    all_visited = all(
                        ie["source"] in self._visited for ie in incoming
                    )
                    if all_visited and target not in successors:
                        successors.append(target)
                else:
                    if target not in successors:
                        successors.append(target)

        new_active = successors + remaining
        if not new_active:
            self._complete = True
            self._active = []
        else:
            self._activate_nodes(new_active)

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

    def is_complete(self):
        return self._complete

    def get_state(self):
        return {
            "active": list(self._active),
            "visited": list(self._visited),
            "waiting_for_selection": self._waiting_for_selection,
            "branch_options": list(self._branch_options),
        }
