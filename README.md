# Skill Inspector

Parse, visualize, and audit SKILL.md agent instruction files as interactive directed acyclic graphs (DAGs).

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-green)](https://python.org)
[![Tests](https://github.com/tonyfadel23/skill-inspector/actions/workflows/tests.yml/badge.svg)](https://github.com/tonyfadel23/skill-inspector/actions/workflows/tests.yml)

## Why Skill Inspector?

SKILL.md files are the instruction layer for Claude Code skills — they define how agents think, branch, loop, and act. As skills grow in complexity, it becomes hard to reason about what's actually happening: Are there dead-end paths? Forks without joins? Vague instructions that will confuse the model?

Skill Inspector makes the invisible visible:

- **See the flow** — Every skill becomes an interactive DAG you can pan, zoom, and step through
- **Catch structural bugs** — Orphan nodes, missing joins, unreachable branches — found automatically
- **Score quality** — 15 best-practice checks with a 1-10 score so you know where to focus
- **Two modes** — Fast heuristic parsing offline, or LLM-powered deep analysis via the Anthropic API

## Install as a Claude Code Skill

Clone the repo and copy the skill into your project:

```bash
git clone https://github.com/tonyfadel23/skill-inspector.git
cp -r skill-inspector/skills/check-my-skills /your-project/.claude/skills/
```

Or install it as a user-level skill (available in all projects):

```bash
git clone https://github.com/tonyfadel23/skill-inspector.git
cp -r skill-inspector/skills/check-my-skills ~/.claude/skills/
```

Then in any Claude Code session, say **"check my skills"** or **"skill inspector"** to scan and visualize your SKILL.md files.

> **Note:** The `.claude-plugin/` directory contains forward-looking plugin manifests for a future Claude Code plugin registry. For now, use the manual install above.

## Quick Start (Standalone)

```bash
# Clone
git clone https://github.com/tonyfadel23/skill-inspector.git
cd skill-inspector

# Install dependencies (only PyYAML, optional)
pip install -r requirements.txt

# Parse skills and generate report
python3 -c "
from skill_inspector.parser import parse_skill_folder
import json
print(json.dumps(parse_skill_folder('/path/to/your/skills/')))
" | python3 skills/check-my-skills/scripts/build_report.py -o report.html

# Open
open report.html
```

## What It Does

Given a folder tree containing SKILL.md files, Skill Inspector:

1. **Discovers** all SKILL.md files recursively
2. **Parses** each into a DAG using a 4-pass heuristic pipeline:
   - Pass 1: Structural segmentation (frontmatter, H2/H3 sections)
   - Pass 2: Node extraction (fork, join, router, tool, gate, spawn, etc.)
   - Pass 3: Edge inference (sequential, data_pass, conditional)
   - Pass 4: Entry/exit synthesis
3. **Evaluates quality** via structural checks and best-practice rules
4. **Generates** an interactive HTML report

## Modes

### Standard Mode (default)
Heuristic parsing — fast, no API calls, works offline.

```bash
python3 -c "
from skill_inspector.parser import parse_skill_folder
import json
print(json.dumps(parse_skill_folder('./skills/')))
" | python3 skills/check-my-skills/scripts/build_report.py -o report.html
```

### Advance Mode
LLM-powered parsing via Anthropic API for deeper, nuance-aware analysis.

Requires an `ANTHROPIC_API_KEY` environment variable:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

See `skills/check-my-skills/SKILL.md` for the full advance mode workflow and `skills/check-my-skills/references/llm-prompt.md` for the system prompt sent to the API.

## Interactive Report Features

- **Pan & zoom** with adjustable speed sliders (1-10x)
- **Step-through simulation** — walk the DAG node by node, edges animate directionally
- **Auto-pan** — simulation smoothly centers on active nodes
- **Node inspector** — click any node to see raw instructions, inputs/outputs, warnings, suggested fixes
- **Fullscreen detail panel** — expand the inspector to fill the screen
- **Quality issues overlay** — collapsible panel showing structural problems
- **Minimap** — overview of the full graph
- **Light / Dark mode** — toggle with the sun/moon button

## Node Types

| Type | Color | Meaning |
|------|-------|---------|
| **Executor** | Green | General instruction step |
| **Fork** | Purple | Parallel fan-out (spawns concurrent branches) |
| **Join** | Purple | Convergence point (waits for parallel branches) |
| **Router** | Yellow | Conditional branching (if/then, based on) |
| **Tool** | Cyan | MCP tool call, CLI command, or API invocation |
| **Gate** | Orange | Human-in-the-loop pause (ask user, confirm, approval) |
| **Spawn** | Pink | Cross-skill chain or subprocess launch |
| **Validator** | Red | Quality check, review, or verification step |
| **File I/O** | Gray | File read/write operation |
| **Template** | Muted | Output template or formatting step |

## Edge Types

| Type | Style | Meaning |
|------|-------|---------|
| Sequential | Solid gray | Step A then step B |
| Parallel | Dashed purple | Concurrent execution from fork |
| Conditional | Dashed yellow | Branch based on condition |
| Data pass | Dotted cyan | File/data dependency |

## Quality Scoring

Each skill gets a score from 1.0 to 10.0 based on structural checks:

- **Errors** (-1.5 each): Dead-end nodes, unreachable nodes, missing entry points
- **Warnings** (-0.75 each): Missing error handling, unbounded loops, unclear gates
- **Info** (-0.25 each): Style suggestions, naming improvements

See `skills/check-my-skills/references/quality-checks.md` for the full evaluation framework.

## Project Structure

```
skill-inspector/
  .claude-plugin/            # Plugin manifests (forward-looking)
    plugin.json
    marketplace.json
  skills/
    check-my-skills/
      SKILL.md               # Skill definition
      references/
        parsing-rules.md     # Heuristic parsing specification
        quality-checks.md    # Quality evaluation criteria
        llm-prompt.md        # System prompt for advance mode
      scripts/
        build_report.py      # HTML report generator
  skill_inspector/           # Python package (for programmatic use)
    __init__.py
    parser.py                # 4-pass heuristic DAG parser
    best_practices.py        # BP1-BP15 quality checks
    patches.py               # Structural issue detection
    simulation.py            # DAG traversal simulation engine
  test/                      # Test suite
    test_best_practices.py
    test_patches.py
    test_simulation.py
```

## Running Tests

```bash
python3 -m pytest test/ -v
```

## Requirements

- Python 3.10+
- PyYAML (optional — falls back to simple key:value parsing without it)
- Anthropic API key (only for advance mode)

## License

MIT
