# Parsing Rules — Heuristic Mode

These rules extract a DAG from a SKILL.md file without API calls.
Apply them in order. Each rule fires independently — a single section
of text can produce multiple nodes.

---

## Pass 1 — Structural Segmentation

Split the SKILL.md into segments using these boundaries:

1. **YAML frontmatter** → Extract metadata (name, description, compatibility)
2. **H2 headers (`##`)** → Major sections (phases, templates, delivery)
3. **H3 headers (`###`)** → Sub-sections within a phase
4. **Code fences with `bash` or tool names** → Tool invocations
5. **Markdown templates** (code fences containing markdown with headers) → Template nodes
6. **ASCII diagrams** (lines with `──▶`, `→`, `|`, boxes) → Engine/flow overview

---

## Pass 2 — Node Extraction

For each segment, apply these detection rules:

### Fork Detection
Trigger phrases (case-insensitive):
- "all parallel", "spawn simultaneously", "run in parallel"
- "(parallel)" annotation
- "3x", "N×", numbered agents with "simultaneously"
- Multiple bold-labeled sub-tasks under a single phase header

When detected:
- Create a `fork` node for the phase header
- Create child `executor` nodes for each parallel task
- Add `parallel` edges from fork to each child

### Join Detection
Trigger phrases:
- "read all", "synthesize", "merge", "converge", "combine results"
- "run after all...exist", "when all complete"
- Phase named "CONVERGE" or "SYNTHESIS" or "MERGE"

When detected:
- Create a `join` node
- Add `parallel` edges from all preceding parallel nodes to the join

### Sequential Flow Detection
Trigger phrases:
- "then", "after", "next", "followed by"
- Numbered steps (1. 2. 3.)
- "(sequential)" annotation
- "Phase N" ordering

When detected:
- Create `executor` nodes for each step
- Add `sequential` edges between consecutive steps

### Router Detection
Trigger phrases:
- "if...then", "based on", "depending on", "check whether"
- "Ask:", followed by bullet options with →
- Decision tables (markdown tables with action columns)
- "requested →", "activating →", multiple "→" on separate lines

When detected:
- Create a `router` node for the decision point
- Create child nodes for each branch
- Add `conditional` edges with the condition as label

### Tool/MCP Detection
Trigger phrases:
- "Search Drive", "search web", "Pull from Looker"
- "Search Drive + web"
- MCP server names from compatibility section
- bash/shell code blocks with tool invocations
- "fetch", "query", "pull metrics"

When detected:
- Create a `tool` node
- Set label to the tool name and action
- Add as child of the current executor context

### File I/O Detection
Trigger phrases:
- "Save to", "Write to", "Output:", "save to `path`"
- "Read", "Input:", "must exist", "read before"
- File paths in backticks (e.g., `_workspace/competitive_intel.md`)
- "present...inline"

When detected:
- Create a `file_io` node
- Classify as read or write
- Extract the file path
- For writes: add to the producing node's `outputs`
- For reads: add to the consuming node's `inputs`

### Gate Detection
Trigger phrases:
- "Ask:", "ask the user", "confirm", "wait for"
- "Ready to...?", "open for challenge until"
- Quoted questions with response options
- "human review", "approval"

When detected:
- Create a `gate` node
- Extract the question or approval criteria
- Connect to the subsequent action nodes

### Spawn Detection
Trigger phrases:
- "chain to `skill-name` skill"
- "pass to", "invoke", "trigger skill"
- "→ chain to", "link to...skill"

When detected:
- Create a `spawn` node
- Extract the target skill name
- Add `chain` edge

### Validator Detection
Trigger phrases:
- "check every gate", "check every quality gate"
- "fix failures", "do not pass with a note"
- "review", "verify", "validate"
- "Reviewer:" as a named agent
- "all gates pass"

When detected:
- Create a `validator` node
- Note what's being validated
- Note the pass/fail criteria
- Note what happens on failure (retry? fix? block?)

### Template Detection
Trigger phrases:
- "## ... Template" headers
- Code fences containing markdown structure (headers, tables, placeholders)
- "Read `references/...` before writing"

When detected:
- Create a `template` node
- Extract the template name
- Note referenced example/quality files

### State Machine Detection
Trigger phrases:
- "State machine:", "state =", "state →"
- Backtick-wrapped state names with arrows
- "set state to"

When detected:
- Don't create a separate node
- Annotate the relevant nodes with their state transitions
- Add state info to the node's metadata

---

## Pass 3 — Edge Inference

After all nodes are extracted, infer edges that weren't explicitly detected:

1. **Implicit sequential**: If two nodes are in the same phase section and no
   explicit relationship was detected, assume sequential ordering by document position.

2. **Data dependency**: If node B's `inputs` contains a file that node A's `outputs`
   produces, add a `data_pass` edge from A to B with the filename as label.

3. **Phase boundaries**: If Phase 2 says "run after all concept files exist" and
   Phase 1 produces concept files, add edges from Phase 1's outputs to Phase 2's fork.

4. **Cross-reference**: If a node references a file in `references/`, add a
   `file_io` read node connected to it.

---

## Pass 4 — Entry and Exit Nodes

Every graph must have:
- **Entry node**: The first action taken when the skill is invoked.
  Usually "Read context" or "Receive input". Type: `file_io` (read).
- **Exit node**: The final delivery action. Usually "Present output" or
  "Ask user for next step". Type: `gate` or `file_io` (write).

If these don't exist explicitly, synthesize them from the Context and Delivery sections.

---

## Output

Produce the complete node and edge arrays in the JSON schema defined in SKILL.md.
Ensure every node has a unique `id` (use `n1`, `n2`, ... or descriptive slugs).
Ensure every edge references valid node IDs.
