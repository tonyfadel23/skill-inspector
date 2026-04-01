# Quality Checks — Skill Instruction Evaluation

Run every check against each parsed skill graph. Each check produces a
severity level and a message. Aggregate into a 1-10 quality score.

> **Implementation status:** The Python package (`skill_inspector/`) implements
> S1-S6, SP1, D1-D4, O5, and BP1-BP15. The remaining clarity (C1-C7) and
> orchestration (O1-O4) checks are best handled by LLM mode (default) or
> spec'd here for future heuristic implementation.

---

## Structural Integrity Checks

### S1 — Orphan Nodes
**Check**: Every node (except entry) has at least one incoming edge.
**Severity**: error
**Message**: "Node '{label}' has no incoming edge — it will never execute."

### S2 — Dead Ends
**Check**: Every node (except exit/gate) has at least one outgoing edge.
**Severity**: warning
**Message**: "Node '{label}' has no outgoing edge — execution stops here unexpectedly."

### S3 — Fork Without Join
**Check**: Every `fork` node has a corresponding `join` node downstream.
**Severity**: error
**Message**: "Parallel fork '{label}' has no convergence point — parallel outputs are never synthesized."

### S4 — Join Without Fork
**Check**: Every `join` node has a corresponding `fork` node upstream.
**Severity**: warning
**Message**: "Join node '{label}' has no upstream fork — may be synthesizing from sequential steps (intentional?)."

### S5 — Unreachable from Entry
**Check**: Every node is reachable from the entry node via edge traversal.
**Severity**: error
**Message**: "Node '{label}' is unreachable from the skill entry point."

### S6 — Cycles
**Check**: The graph is acyclic (DAG). Cycles indicate infinite loops.
**Severity**: error
**Message**: "Cycle detected: {node_a} → {node_b} → ... → {node_a}."
**Exception**: Retry loops (validator → executor) are acceptable if bounded.

---

## Data Flow Checks

### D1 — Unproduced Input
**Check**: Every file in a node's `inputs` appears in some upstream node's `outputs`.
**Severity**: error
**Message**: "Node '{label}' expects input '{file}' but no prior node produces it."

### D2 — Unconsumed Output
**Check**: Every file in a node's `outputs` appears in some downstream node's `inputs`.
**Severity**: info
**Message**: "Node '{label}' produces '{file}' but nothing downstream consumes it."

### D3 — Missing File Reference
**Check**: Referenced files (e.g., `references/examples.md`) actually exist on disk.
**Severity**: warning
**Message**: "Referenced file '{path}' not found on disk."

### D4 — Implicit Data Passing
**Check**: Two connected nodes share no explicit inputs/outputs — data passes implicitly.
**Severity**: info
**Message**: "Edge '{source}' → '{target}' has no explicit data contract — relies on implicit context."

---

## Instruction Clarity Checks

### C1 — Vague Action
**Check**: Executor/planner nodes should have specific, actionable instructions.
Flag nodes whose raw_instruction contains only vague verbs without specifics.
Vague patterns: "handle", "process", "deal with", "take care of", "do the thing",
"as appropriate", "as needed" without specifying what.
**Severity**: warning
**Message**: "Node '{label}' uses vague language: '{phrase}'. Specify the exact action."

### C2 — Missing Error Handling
**Check**: Tool nodes and file_io nodes should specify what happens on failure.
Look for: "if unavailable", "if error", "if not found", fallback instructions.
**Severity**: warning
**Message**: "Node '{label}' ({type}) has no error/fallback handling. What happens if it fails?"

### C3 — Missing Success Criteria
**Check**: Validator nodes should specify explicit pass/fail criteria.
**Severity**: warning
**Message**: "Validator '{label}' has no explicit success criteria — how does it know when to pass?"

### C4 — Ambiguous Routing
**Check**: Router nodes should have mutually exclusive, exhaustive conditions.
Flag if conditions overlap or if there's no default/else branch.
**Severity**: warning
**Message**: "Router '{label}' has overlapping conditions or missing default branch."

### C5 — Unspecified Parallelism
**Check**: Fork nodes should clearly state how many parallel branches and what each does.
**Severity**: info
**Message**: "Fork '{label}' doesn't specify exact number of parallel branches."

### C6 — Template Without Quality Bar
**Check**: Template nodes should reference a quality bar or examples file.
**Severity**: info
**Message**: "Template '{label}' has no linked quality bar or examples reference."

### C7 — Gate Without Options
**Check**: Gate nodes should specify what choices the user has and what each triggers.
**Severity**: warning
**Message**: "Gate '{label}' doesn't specify user options or downstream routing."

---

## Orchestration Pattern Checks

### O1 — Agent Role Clarity
**Check**: Named agents (e.g., "Synthesizer", "Reviewer") should have a clear,
distinct role. Flag if two agents seem to do the same thing.
**Severity**: info
**Message**: "Agents '{agent_a}' and '{agent_b}' appear to have overlapping roles."

### O2 — State Machine Completeness
**Check**: If a state machine is defined, every state should be reachable
and every state should have at least one transition out (except terminal states).
**Severity**: warning
**Message**: "State '{state}' has no outgoing transition — is this intentional?"

### O3 — Cross-Skill Contract
**Check**: When a skill chains to another skill, verify the output format
matches what the target skill expects as input.
**Severity**: warning
**Message**: "Skill '{source}' chains to '{target}' but output format may not match expected input."

### O4 — MCP Dependency Without Fallback
**Check**: If compatibility lists MCP servers, check that the skill has
fallback instructions for when those servers are unavailable.
**Severity**: warning
**Message**: "Skill depends on MCP '{server}' but has no fallback if unavailable."

### O5 — Depth Complexity
**Check**: If the longest path from entry to exit exceeds 12 nodes, flag complexity.
**Severity**: info
**Message**: "Skill has {depth} steps in the longest path — consider simplifying or splitting."

---

## Best Practice Checks

Sourced from Anthropic's official skill-building guidance. Hard checks (error)
are pass/fail requirements. Soft checks (warning) are heuristic signals.

Sources (refresh periodically):
- The Complete Guide to Building Skills for Claude (PDF, Anthropic)
- Improving Skill Creator blog post (claude.com/blog)
- skill-creator SKILL.md (github.com/anthropics/skills)

### BP1 — SKILL.md Filename
**Check**: File must be named exactly `SKILL.md` (case-sensitive).
**Severity**: error

### BP2 — Kebab-Case Folder Name
**Check**: Skill folder must use kebab-case (lowercase letters, numbers, hyphens only).
**Severity**: error

### BP3 — No README.md
**Check**: Skill folder must not contain a README.md. All docs go in SKILL.md or references/.
**Severity**: error

### BP4 — Description Completeness
**Check**: Description must include both what the skill does AND when it should trigger.
**Severity**: error

### BP5 — Description Length
**Check**: Description must be under 1024 characters.
**Severity**: error

### BP6 — No XML in Frontmatter
**Check**: Frontmatter must not contain XML angle brackets (`<` `>`). These could inject into the system prompt.
**Severity**: error

### BP7 — No Forbidden Names
**Check**: Skill name must not contain "claude" or "anthropic".
**Severity**: error

### BP8 — Body Length
**Check**: SKILL.md body should be under 500 lines. Longer content belongs in references/.
**Severity**: error

### BP9 — Specific Instructions
**Check**: Flag vague phrases like "handle as needed", "process appropriately", "validate the data" without specifics.
**Severity**: warning

### BP10 — Error Handling Section
**Check**: Skill should include a Common Issues, Troubleshooting, or Error Handling section.
**Severity**: warning

### BP11 — Directive Density
**Check**: Flag excessive ALL-CAPS directives (MUST, NEVER, ALWAYS, CRITICAL). Prefer explaining the "why".
**Severity**: warning

### BP12 — Progressive Disclosure
**Check**: Skills over 300 lines without a references/ directory should consider splitting.
**Severity**: warning

### BP13 — Resource References
**Check**: Files in references/ or scripts/ should be mentioned in SKILL.md with guidance on when to read them.
**Severity**: warning

### BP14 — Trigger Phrase Coverage
**Check**: Description should include "Use when..." phrases with specific user actions to aid triggering.
**Severity**: warning

### BP15 — Repeated Patterns
**Check**: Duplicated code blocks across phases should be bundled into scripts/.
**Severity**: warning

---

## Scoring Rubric

Start at 10. Deduct points:

| Severity | Deduction per issue |
|----------|-------------------|
| error    | -1.5              |
| warning  | -0.75             |
| info     | -0.25             |

Floor at 1. Round to one decimal place.

### Score Interpretation

| Score | Label | Meaning |
|-------|-------|---------|
| 9-10  | Excellent | Well-structured, clear instructions, robust error handling |
| 7-8.9 | Good | Solid structure with minor gaps |
| 5-6.9 | Needs Work | Structural issues or significant clarity gaps |
| 3-4.9 | Poor | Major structural problems, unclear instructions |
| 1-2.9 | Critical | Fundamental issues — skill likely won't execute as intended |
