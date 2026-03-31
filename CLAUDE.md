# Skill Inspector — Developer Guide

## Project Overview

Skill Inspector parses SKILL.md files into DAGs, runs quality checks, and generates interactive HTML reports. It ships as a Claude Code plugin and a standalone Python package.

## Running Tests

```bash
python3 -m pytest test/ -v
```

All changes must have tests. Follow TDD: write the failing test first, then implement.

## Version Sync

When bumping the version, update all three locations:
1. `pyproject.toml` — `version` field
2. `.claude-plugin/plugin.json` — `version` field
3. `.claude-plugin/marketplace.json` — `plugins[0].version` field

Then add an entry to `CHANGELOG.md` and tag the release:
```bash
git tag v<version>
git push --tags
```

## Key Directories

- `skill_inspector/` — Python package (parser, best_practices, patches, simulation)
- `skills/check-my-skills/` — The Claude Code skill and its supporting files
  - `references/` — Parsing rules, quality checks, LLM prompt
  - `scripts/` — Report generator (build_report.py)
- `test/` — pytest suite mirroring skill_inspector modules

## How the Skill Works

1. SKILL.md instructs Claude to scan for skill files
2. Claude parses them using heuristic rules (references/parsing-rules.md) or the LLM prompt
3. Quality checks run per references/quality-checks.md
4. JSON output is piped to scripts/build_report.py which produces a self-contained HTML report
