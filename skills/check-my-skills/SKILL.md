---
name: check-my-skills
description: >
  Scan, parse, and visualize the instruction flow of every skill in a project.
  Use whenever a user says "check my skills", "audit my skills", "what are my skills doing",
  "show me the skill graph", "skill inspector", "debug my skill", or wants to understand
  how their SKILL.md files actually propagate instructions. Also triggers on
  "check-my-skills" or "--advance" flags. Produces an interactive HTML report with
  Dagre DAG trees showing agent orchestration, tool calls, control flow, and quality warnings.
---

# check-my-skills — Skill Instruction Inspector

## Purpose

Parse every skill in a project into a directed acyclic graph (DAG) of instruction nodes,
visualize the flow as an interactive Dagre tree, and surface quality issues in the
instruction chain. Two modes:

- **Standard** (default): Heuristic parsing — fast, no API calls
- **Advanced** (`--advance`): LLM-powered parsing via Anthropic API — deeper, catches nuance

---

## Step 0 — Setup

### Detect Mode
Check the user's request for `--advance` or `advance` flag.
- If present → set `MODE=advance`
- If absent → set `MODE=standard`

### Locate Plugin Directory
Find where this skill's supporting files are installed:

```bash
SKILL_DIR=$(dirname "$(find ~/.claude/plugins -path '*/check-my-skills/SKILL.md' -type f 2>/dev/null | head -1)")
```

If not found in the plugin cache, check the current working directory:

```bash
[ -z "$SKILL_DIR" ] && SKILL_DIR=$(find "$(pwd)" -path '*/skills/check-my-skills/SKILL.md' -type f -exec dirname {} \; 2>/dev/null | head -1)
```

### Ensure Dependencies

```bash
python3 -c "import yaml" 2>/dev/null || pip3 install --user "PyYAML>=6.0"
```

If advance mode, also ensure:

```bash
python3 -c "import anthropic" 2>/dev/null || pip3 install --user "anthropic>=0.25.0"
```

---

## Step 1 — Discovery

Scan for all skill directories. Search these locations in order:

```bash
# User skills (highest priority)
find /mnt/skills/user -name "SKILL.md" -type f 2>/dev/null

# Project skills (current working directory)
find "$(pwd)" -name "SKILL.md" -path "*/skills/*" -type f 2>/dev/null
find "$(pwd)" -name "SKILL.md" -path "*/.claude/skills/*" -type f 2>/dev/null

# Also check if user specified a specific path
# e.g., "check my skills in /path/to/project"
```

For each SKILL.md found, read the file and extract:
- `name` (from YAML frontmatter)
- `description` (from YAML frontmatter)
- `path` (absolute path)
- `compatibility` / `mcp_servers` (from frontmatter if present)
- List of referenced files (e.g., `references/examples.md`, other skills mentioned)

Present the inventory to the user:
```
Found N skills:
1. product-brief (/mnt/skills/user/product-brief/SKILL.md)
2. prototype-prd (/mnt/skills/user/prototype-prd/SKILL.md)
...
```

Ask: "Inspect all, or pick specific skills?"

---

## Step 2 — Parse

For each selected skill, produce a structured graph in JSON format.

### Node Schema

```json
{
  "id": "n1",
  "label": "Short descriptive label",
  "type": "planner|executor|router|fork|join|tool|gate|spawn|file_io|validator|template",
  "phase": "Optional phase name (e.g., DIVERGE, STRESS-TEST)",
  "raw_instruction": "The actual text from SKILL.md for this step",
  "inputs": ["list of inputs this node expects"],
  "outputs": ["list of outputs this node produces"],
  "warnings": ["list of quality issues detected"]
}
```

### Edge Schema

```json
{
  "source": "n1",
  "target": "n2",
  "type": "sequential|conditional|parallel|data_pass|chain",
  "label": "what's passed or the condition"
}
```

### Node Type Definitions

| Type | Detect When |
|------|------------|
| `planner` | Agent reads context and produces a plan, list of steps, or decisions |
| `executor` | Agent takes a plan item and runs it (writes files, calls tools) |
| `router` | Decision point — sends work to different paths based on conditions |
| `fork` | Multiple agents/tasks spawned simultaneously ("parallel", "simultaneously", "all parallel") |
| `join` | Convergence — parallel outputs are synthesized ("read all", "synthesize", "merge") |
| `tool` | Explicit tool/MCP invocation (Search Drive, Looker, web search, bash) |
| `gate` | Human approval checkpoint ("ask user", "wait for", "confirm") |
| `spawn` | Invokes another skill or spawns a child process |
| `file_io` | Reads context files or writes output artifacts |
| `validator` | Checks quality before proceeding ("check every gate", "fix failures") |
| `template` | A document template or output format specification |

### Parsing Mode

**If MODE=standard**: Read `references/parsing-rules.md` and follow the heuristic
extraction rules to build the node/edge graph from the SKILL.md text.

**If MODE=advance**: Read `references/llm-prompt.md` and use the Anthropic API
to parse each SKILL.md into the structured graph. Use `claude-sonnet-4-20250514`
with the structured prompt. Parse the JSON response.

---

## Step 3 — Quality Evaluation

Read `references/quality-checks.md`. For each skill graph, run every check and
append warnings to the relevant nodes. Compute an overall quality score (1-10).

---

## Step 4 — Cross-Reference Resolution

For each skill, check if it references other skills (e.g., "chain to `prototype` skill").
For referenced skills that were also parsed:
- Add a `spawn` node with an edge of type `chain`
- Link to the other skill's graph

For referenced files (e.g., `references/examples.md`):
- Add a `file_io` node
- Read the file if it exists and note its size and purpose
- If the file doesn't exist, add a warning: "Referenced file not found"

---

## Step 5 — Generate Report

Collect all parsed skill graphs into a single JSON structure:

```json
{
  "generated_at": "ISO timestamp",
  "mode": "standard|advance",
  "skills": [ ...array of skill graphs... ]
}
```

Run the report generator script (using the plugin directory found in Step 0):

```bash
python3 "$SKILL_DIR/scripts/build_report.py" --input /tmp/skills_graph.json --output skill-inspector.html
```

If `$SKILL_DIR` is not set (e.g., running outside Claude Code), the user can
run the script directly from the repo checkout:

```bash
python3 skills/check-my-skills/scripts/build_report.py --input /tmp/skills_graph.json --output skill-inspector.html
```

Present the HTML file to the user.

---

## Troubleshooting

If something goes wrong during execution, check these common issues:

**Python not found or wrong version:**
```bash
python3 --version
# Requires 3.10+. If missing, install via brew/apt/pyenv.
```

**PyYAML import fails after install:**
```bash
# Try with --user flag if pip install fails
pip3 install --user "PyYAML>=6.0"
```

**SKILL_DIR not resolved (plugin directory not found):**
- The plugin may not be installed yet. Ask the user to run:
  `claude plugin add github:tonyfadel23/skill-inspector`
- Or fall back to running from a local checkout of the repo.

**Advance mode — API key not set:**
```bash
# Must be set before running advance mode
export ANTHROPIC_API_KEY=sk-ant-...
```
If the key is missing, fall back to standard mode and inform the user.

**build_report.py fails with JSON error:**
- Verify the JSON piped to `--input` is valid. Use `python3 -m json.tool < /tmp/skills_graph.json` to check.
- Ensure the JSON follows the expected schema (see Step 5).

**No SKILL.md files found:**
- Confirm the search paths exist and contain SKILL.md files.
- Check if the user meant a different directory — ask them to specify.

---

## Step 6 — Debrief

After presenting the report, summarize:
1. Total skills scanned
2. Top 3 quality issues across all skills
3. Skills with the most complex orchestration (highest node count)
4. Any broken cross-references or missing files
5. Recommended fixes (prioritized by severity)

---

## References

- `references/parsing-rules.md` — Heuristic parsing rules for standard mode
- `references/quality-checks.md` — Quality evaluation criteria and scoring
- `references/llm-prompt.md` — Structured prompt for advance mode API calls
- `scripts/build_report.py` — HTML report generator
