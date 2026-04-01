# Changelog

## v0.2.0 — 2026-04-01

### Breaking Changes
- LLM-powered parsing is now the **default mode** (was opt-in via `--advance`)
- Heuristic parsing moved to `--easy` flag (was the default)
- `anthropic` SDK is now a required dependency (was optional)

### Features
- Standalone CLI: `python3 -m skill_inspector <path> [--easy] [--output report.html]`
- Cross-skill dependency graph: detects spawn/chain edges between skills, missing targets, and cycles
- New structural checks: S4 (join without fork), S5 (unreachable nodes), S6 (cycle detection), O5 (depth complexity)
- New data flow checks: D1 (unproduced inputs), D2 (unconsumed outputs), D3 (missing file references), D4 (implicit data passing)
- Improved heuristic parser: better join detection (CONVERGE/SYNTHESIS/MERGE phase names, "run after all...exist"), template header detection, validator patterns, entry/exit node synthesis

## v0.1.0 — 2026-03-31

Initial public release.

### Features
- 4-pass heuristic DAG parser for SKILL.md files
- 10 node types (executor, fork, join, router, tool, gate, spawn, validator, file_io, template)
- 4 edge types (sequential, parallel, conditional, data_pass)
- 15 best-practice quality checks (BP1-BP15) with 1-10 scoring
- 4 structural checks (orphan nodes, dead ends, fork/join mismatch, parallel dependencies)
- Interactive HTML report with pan/zoom, step-through simulation, minimap, and dark/light mode
- Fork-aware simulation engine (converging and independent forks)
- Advance mode with LLM-powered parsing via Anthropic API
- Installable as a Claude Code skill (copy `skills/check-my-skills/` into your project)
