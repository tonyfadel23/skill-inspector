"""CLI entry point for skill-inspector.

Usage:
    python3 -m skill_inspector <path> [--easy] [--output report.html]
"""
import argparse
import json
import os
import sys

from .parser import parse_skill_folder
from .best_practices import run_all_checks
from .patches import suggest_patches
from .data_flow import check_data_flow
from .cross_skill import build_cross_skill_graph


def main():
    parser = argparse.ArgumentParser(
        prog="skill-inspector",
        description="Parse, visualize, and audit SKILL.md files as interactive DAGs",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root directory to scan for SKILL.md files (default: current directory)",
    )
    parser.add_argument(
        "--easy",
        action="store_true",
        help="Use fast heuristic parsing instead of LLM-powered analysis",
    )
    parser.add_argument(
        "--output", "-o",
        default="skill-inspector.html",
        help="Output HTML report path (default: skill-inspector.html)",
    )
    args = parser.parse_args()

    mode = "standard" if args.easy else "advance"
    scan_path = os.path.abspath(args.path)

    if not os.path.isdir(scan_path):
        print(f"Error: '{scan_path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Parse all SKILL.md files
    print(f"Scanning {scan_path} for SKILL.md files...")
    result = parse_skill_folder(scan_path, mode=mode)

    if not result["skills"]:
        print("No SKILL.md files found.", file=sys.stderr)
        sys.exit(1)

    # Run quality checks on each skill
    for skill in result["skills"]:
        skill_path = skill.get("path", "")
        skill_dir = os.path.dirname(skill_path)
        files_in_folder = os.listdir(skill_dir) if skill_dir and os.path.isdir(skill_dir) else []

        # Best practice checks
        skill_info = {
            "filename": os.path.basename(skill_path),
            "folder_name": os.path.basename(skill_dir),
            "files_in_folder": files_in_folder,
            "frontmatter": skill.get("_frontmatter_raw", ""),
            "name": skill.get("name", ""),
            "description": skill.get("description", ""),
            "body": skill.get("_body_raw", ""),
            "resource_files": _find_resource_files(skill_path),
            "has_references_dir": os.path.isdir(os.path.join(skill_dir, "references")),
        }
        bp_result = run_all_checks(skill_info)
        bp_checks = bp_result.get("checks", [])

        # Structural patch checks
        patches = suggest_patches(skill.get("nodes", []), skill.get("edges", []))

        # Data flow checks
        skill_dir = os.path.dirname(skill.get("path", ""))
        df_issues = check_data_flow(
            skill.get("nodes", []),
            skill.get("edges", []),
            skill_dir=skill_dir if skill_dir else None,
        )

        # Merge all issues
        all_issues = bp_checks + patches + df_issues
        if "quality" not in skill:
            skill["quality"] = {}
        skill["quality"]["checks"] = all_issues

    # Build cross-skill dependency graph
    cross_graph = build_cross_skill_graph(result["skills"])
    result["cross_skill_graph"] = cross_graph

    # Write JSON for report generator
    json_path = os.path.join("/tmp", "skills_graph.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)

    # Find and run build_report.py
    report_script = _find_report_script()
    if report_script:
        os.system(f'python3 "{report_script}" --input "{json_path}" --output "{args.output}"')
    else:
        print(f"JSON output written to {json_path}")
        print("Could not find build_report.py — run it manually to generate the HTML report.")
        sys.exit(0)

    # Print summary
    print(f"\nSkills: {len(result['skills'])}")
    for skill in result["skills"]:
        score = skill.get("quality", {}).get("score", "?")
        nodes = len(skill.get("nodes", []))
        print(f"  - {skill['name']} -- score: {score}, nodes: {nodes}")
    print(f"\nReport: {args.output}")


def _find_report_script():
    """Locate build_report.py relative to this package or common install paths."""
    # Check relative to this file (package is inside the repo)
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(pkg_dir)
    candidates = [
        os.path.join(repo_dir, "skills", "check-my-skills", "scripts", "build_report.py"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _find_resource_files(skill_path):
    """Find files in references/ and scripts/ directories relative to a SKILL.md."""
    if not skill_path:
        return []
    skill_dir = os.path.dirname(skill_path)
    files = []
    for subdir in ("references", "scripts"):
        d = os.path.join(skill_dir, subdir)
        if os.path.isdir(d):
            for f in os.listdir(d):
                files.append(os.path.join(subdir, f))
    return files


if __name__ == "__main__":
    main()
