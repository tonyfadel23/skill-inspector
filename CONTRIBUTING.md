# Contributing to Skill Inspector

Thanks for your interest in contributing! Here's how to get started.

## Reporting Bugs

Open an issue at [github.com/tonyfadel23/skill-inspector/issues](https://github.com/tonyfadel23/skill-inspector/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version (`python3 --version`)

## Development Setup

```bash
git clone https://github.com/tonyfadel23/skill-inspector.git
cd skill-inspector
pip install -r requirements.txt
pip install pytest
```

## Running Tests

```bash
python3 -m pytest test/ -v
```

All tests must pass before submitting a PR. The project follows TDD — if you're adding a feature or fixing a bug, write the test first.

## Submitting a Pull Request

1. Fork the repo and create a branch from `main`
2. Write tests for your changes
3. Make your changes and ensure all tests pass
4. Keep commits focused — one logical change per commit
5. Open a PR against `main`

## Project Structure

- `skill_inspector/` — Python package (parser, quality checks, simulation engine)
- `skills/check-my-skills/` — The Claude Code skill definition and its supporting files
- `test/` — Test suite (pytest)

## Code Style

- Keep it simple — this is a tool, not a framework
- No type annotations unless they clarify something non-obvious
- Tests go in `test/` and mirror the module they test

## Version Bumps

When releasing, update the version in all three locations:
- `pyproject.toml` (`version`)
- `.claude-plugin/plugin.json` (`version`)
- `.claude-plugin/marketplace.json` (`plugins[0].version`)
