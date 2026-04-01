---
name: build-my-skill
description: >
  Build custom skill trees with advanced orchestration and emit valid SKILL.md files.
  Use when the user says "build a skill", "create a skill tree", "build my skill",
  "design a workflow", "create a pipeline", "skill tree builder", or wants to create
  an agentic workflow with sub-agents, gated checks, improvement loops, or
  multi-perspective analysis.
---

# build-my-skill — Skill Tree Builder

## Step 0 — Setup

### Locate Builder

Find where the skill-inspector package is installed:

```bash
BUILDER_DIR=$(find "$(pwd)" ~/.agents/skills -path '*/skill-inspector/skill_inspector/builder.py' -type f 2>/dev/null -exec dirname {} \; | head -1)
if [ -z "$BUILDER_DIR" ]; then
  BUILDER_DIR=$(find "$(pwd)" -path '*/skill_inspector/builder.py' -type f 2>/dev/null -exec dirname {} \; | head -1)
fi
echo "Builder found at: $BUILDER_DIR"
```

### Ensure Dependencies

```bash
python3 -c "import yaml" 2>/dev/null || pip3 install --user "PyYAML>=6.0"
```

---

## Step 1 — Understand the Goal

Ask the user to describe what they want to build. Gather:

1. **Goal**: What is the end-to-end outcome?
2. **Inputs**: What data, files, or context does it need?
3. **Outputs**: What deliverables should it produce?
4. **Constraints**: Time, quality thresholds, human review points?
5. **Tools**: What external tools or APIs are needed?

If the user is unsure, suggest one of these common patterns:

- **Research Pipeline**: fetch → analyze → synthesize → deliver
- **Goal to Prototype**: context → research → evaluate → diverge → converge → refine → deliver
- **Quality Audit**: scan → check → report → fix → verify
- **Content Generation**: brief → draft → review → iterate → publish

---

## Step 2 — Design the Tree

Based on the user's goal, design the skill tree using these node types.
Read `references/node-types.md` for the full reference.

### Available Node Types

| Type | Use When |
|------|----------|
| `executor` | Agent takes action — writes files, generates content |
| `tool` | External tool invocation — WebSearch, APIs, bash commands |
| `subagent` | Spawn a dedicated sub-agent with its own context and tools |
| `context_loader` | Dynamically inject context from files or URLs |
| `signal_gate` | Gate on computed metrics with pass/fail thresholds |
| `improvement_loop` | RALPH-style iterate until quality threshold met |
| `diverge` | Fork into parallel branches for multi-angle analysis |
| `converge` | Synthesize parallel outputs with a merge strategy |
| `router` | Conditional branching based on computed values |
| `gate` | Human approval checkpoint |
| `file_io` | Read or write specific files |

### Design Principles

Read `references/patterns.md` for orchestration pattern guidance.

1. **Start with context** — load all needed data before processing
2. **Gate early** — check signal quality before expensive operations
3. **Diverge for quality** — multiple perspectives catch blind spots
4. **Converge with strategy** — don't just merge, synthesize with weighting
5. **Loop for excellence** — RALPH loops elevate output beyond first-draft quality
6. **Gate before delivery** — human review on final output

Present the proposed tree to the user as a numbered phase list with node descriptions.
Ask: "Does this structure look right? Any phases to add, remove, or reorder?"

---

## Step 3 — Build the Tree

Generate the Python builder code using the `SkillTreeBuilder` API:

```python
import sys
sys.path.insert(0, "$BUILDER_DIR/..")
from skill_inspector.builder import SkillTreeBuilder
from skill_inspector.emitter import emit_skill_md

tree = SkillTreeBuilder("skill-name", "Description. Use when X, Y, or Z.")

# Phase 1
p = tree.phase("Phase Name")
p.executor("node-id", "What this step does")
p.tool("tool-id", "Tool description", tools=["WebSearch"], commands=["..."])
p.subagent("agent-id", "Agent task", agent_type="Explore", tools=[...])
p.context_loader("ctx-id", "Load context", files=["..."])
p.signal_gate("gate-id", "Check metrics", criteria={"metric": ">= 0.7"}, on_fail="retry")
p.improvement_loop("loop-id", "Improve output", strategy="ralph", max_iterations=5,
                    exit_criteria={"quality": ">= 0.9"},
                    steps=["Reflect", "Analyze", "Learn", "Plan", "Hypothesize"])
p.diverge("fork-id", "Multiple perspectives", branches=[
    {"id": "view-a", "label": "View A", "prompt": "..."},
    {"id": "view-b", "label": "View B", "prompt": "..."},
])
p.converge("join-id", "Synthesize results", strategy="weighted-merge")

# Emit
graph = tree.build()
md = emit_skill_md(graph)
```

Run the generated code to produce the SKILL.md file.

---

## Step 4 — Validate

Parse the generated SKILL.md through the existing parser to verify it round-trips:

```bash
python3 -c "
import sys, json
sys.path.insert(0, '$BUILDER_DIR/..')
from skill_inspector.parser import parse_skill
result = parse_skill('$OUTPUT_PATH/SKILL.md')
print(f'Nodes: {len(result[\"nodes\"])}, Edges: {len(result[\"edges\"])}')
print(f'Pattern: {result[\"pattern\"]}')
print(f'Quality: {result[\"quality\"][\"score\"]}/10')
for issue in result['quality']['top_issues']:
    print(f'  - {issue}')
"
```

If quality score is below 7.0, review and fix the top issues.

---

## Step 5 — Generate Report

Optionally generate the interactive visualization:

```bash
python3 -c "
import sys, json
sys.path.insert(0, '$BUILDER_DIR/..')
from skill_inspector.parser import parse_skill
result = parse_skill('$OUTPUT_PATH/SKILL.md')
payload = json.dumps({'generated_at': '$(date -Iseconds)', 'mode': 'standard', 'skills': [result]})
print(payload)
" | python3 "$BUILDER_DIR/../skills/check-my-skills/scripts/build_report.py" -o "$OUTPUT_PATH/report.html"
```

Present the report and SKILL.md to the user.

---

## Step 6 — Install

Help the user install the new skill:

1. Copy the skill folder to their project's `skills/` directory
2. Verify Claude Code discovers it
3. Test by invoking the skill's trigger phrases

```bash
cp -r "$OUTPUT_PATH" "$(pwd)/skills/$(basename $OUTPUT_PATH)"
echo "Skill installed at: $(pwd)/skills/$(basename $OUTPUT_PATH)"
```

---

## Troubleshooting

If something goes wrong during execution, check these common issues:

**Builder not found:**
- Ensure skill-inspector is installed or cloned locally
- The `skill_inspector/` package must be importable

**Generated SKILL.md has low quality score:**
- Check for orphan nodes (nodes with no connections)
- Ensure fork nodes have matching join nodes
- Verify all file references exist

**Parser fails on generated SKILL.md:**
- Verify YAML frontmatter is valid (no tabs, proper indentation)
- Check that node labels don't conflict with parser keywords

---

## References

- `references/node-types.md` — Full reference for all node types and their options
- `references/patterns.md` — Orchestration pattern guidance and examples
