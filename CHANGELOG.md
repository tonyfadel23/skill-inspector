# Changelog

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
- Packaged as a Claude Code plugin (`claude plugin add github:tonyfadel23/skill-inspector`)
