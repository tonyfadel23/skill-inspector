"""
Best practice checks for SKILL.md files (BP1-BP15).

Hard checks (BP1-BP8): pass/fail errors
Soft checks (BP9-BP15): heuristic warnings

Sources:
- https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf
- https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills
- https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
"""
import re


# --- Hard checks (pass/fail, severity: error) ---


def check_bp1_filename(filename: str) -> dict:
    """SKILL.md filename must be exactly SKILL.md (case-sensitive)."""
    passed = filename == "SKILL.md"
    return {
        "id": "BP1",
        "name": "SKILL.md filename",
        "passed": passed,
        "severity": "error" if not passed else None,
        "message": None if passed else f"Filename must be exactly 'SKILL.md', got '{filename}'",
    }


def check_bp2_folder_name(folder_name: str) -> dict:
    """Folder name must be kebab-case (lowercase, hyphens only)."""
    passed = bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", folder_name))
    return {
        "id": "BP2",
        "name": "Kebab-case folder name",
        "passed": passed,
        "severity": "error" if not passed else None,
        "message": None if passed else f"Folder name must be kebab-case, got '{folder_name}'",
    }


def check_bp3_no_readme(files_in_folder: list[str]) -> dict:
    """No README.md inside skill folder."""
    has_readme = any(f.lower() == "readme.md" for f in files_in_folder)
    passed = not has_readme
    return {
        "id": "BP3",
        "name": "No README.md in skill folder",
        "passed": passed,
        "severity": "error" if not passed else None,
        "message": None if passed else "Skill folders should not contain README.md — put docs in SKILL.md or references/",
    }


def check_bp4_description_completeness(description: str) -> dict:
    """Description must include both what it does and when to trigger."""
    if not description.strip():
        return {
            "id": "BP4",
            "name": "Description completeness",
            "passed": False,
            "severity": "error",
            "message": "Description is empty",
        }

    trigger_patterns = [
        r"\buse when\b", r"\btrigger\b", r"\bwhen user\b", r"\bwhen the user\b",
        r"\basks? for\b", r"\bmentions?\b", r"\bsays?\b", r"\bwants? to\b",
    ]
    has_trigger = any(re.search(p, description, re.IGNORECASE) for p in trigger_patterns)

    action_patterns = [
        r"\b(creates?|generates?|builds?|manages?|analyzes?|handles?|runs?|deploys?|reviews?)\b",
        r"\b(orchestrates?|coordinates?|automates?|processes?|transforms?)\b",
    ]
    has_action = any(re.search(p, description, re.IGNORECASE) for p in action_patterns)

    passed = has_trigger and has_action
    parts = []
    if not has_action:
        parts.append("what it does")
    if not has_trigger:
        parts.append("when to trigger (e.g., 'Use when user...')")
    return {
        "id": "BP4",
        "name": "Description completeness",
        "passed": passed,
        "severity": "error" if not passed else None,
        "message": None if passed else f"Description missing: {', '.join(parts)}",
    }


def check_bp5_description_length(description: str) -> dict:
    """Description under 1024 characters."""
    passed = len(description) <= 1024
    return {
        "id": "BP5",
        "name": "Description length",
        "passed": passed,
        "severity": "error" if not passed else None,
        "message": None if passed else f"Description is {len(description)} chars (max 1024)",
    }


def check_bp6_no_xml_in_frontmatter(frontmatter: str) -> dict:
    """No XML angle brackets in frontmatter."""
    has_xml = bool(re.search(r"<[a-zA-Z/]", frontmatter))
    passed = not has_xml
    return {
        "id": "BP6",
        "name": "No XML in frontmatter",
        "passed": passed,
        "severity": "error" if not passed else None,
        "message": None if passed else "Frontmatter contains XML angle brackets (<>) — these could inject into system prompt",
    }


def check_bp7_no_forbidden_names(name: str) -> dict:
    """No 'claude' or 'anthropic' in skill name."""
    lower = name.lower()
    has_forbidden = "claude" in lower or "anthropic" in lower
    passed = not has_forbidden
    return {
        "id": "BP7",
        "name": "No forbidden name terms",
        "passed": passed,
        "severity": "error" if not passed else None,
        "message": None if passed else f"Skill name must not contain 'claude' or 'anthropic', got '{name}'",
    }


def check_bp8_body_length(body: str) -> dict:
    """SKILL.md body under 500 lines."""
    line_count = len(body.splitlines())
    passed = line_count <= 500
    return {
        "id": "BP8",
        "name": "Body length",
        "passed": passed,
        "severity": "error" if not passed else None,
        "message": None if passed else f"SKILL.md body is {line_count} lines (max 500)",
    }


# --- Soft checks (heuristic, severity: warning) ---


VAGUE_PHRASES = [
    r"\bvalidate the data\b",
    r"\bhandle (?:things |it )?as (?:needed|appropriate)\b",
    r"\bprocess (?:the )?(?:input|data) (?:appropriately|accordingly)\b",
    r"\bdo what makes sense\b",
    r"\buse (?:your )?(?:best )?judg[e]?ment\b",
    r"\bas (?:appropriate|necessary)\b",
    r"\bhandle (?:errors? )?(?:gracefully|properly)\b",
    r"\bensure (?:everything|things) (?:work|are ok)\b",
]


def check_bp9_specific_instructions(text: str) -> dict:
    """Instructions should be specific and actionable, not vague."""
    matches = []
    for pattern in VAGUE_PHRASES:
        found = re.findall(pattern, text, re.IGNORECASE)
        matches.extend(found)
    passed = len(matches) == 0
    return {
        "id": "BP9",
        "name": "Specific instructions",
        "passed": passed,
        "severity": "warning" if not passed else None,
        "message": None if passed else f"Found vague phrases: {', '.join(matches[:5])}",
        "matches": matches,
    }


def check_bp10_error_handling_section(body: str) -> dict:
    """Include error handling / common issues section."""
    error_section_patterns = [
        r"^##\s+(?:Common (?:Issues|Problems)|Error Handling|Troubleshooting|Known Issues|Errors?)",
    ]
    has_section = any(
        re.search(p, body, re.IGNORECASE | re.MULTILINE)
        for p in error_section_patterns
    )
    passed = has_section
    return {
        "id": "BP10",
        "name": "Error handling section",
        "passed": passed,
        "severity": "warning" if not passed else None,
        "message": None if passed else "No error handling or troubleshooting section found",
    }


def check_bp11_directive_density(text: str) -> dict:
    """Avoid heavy-handed MUSTs/NEVERs — explain the why."""
    directive_pattern = r"\b(MUST|NEVER|ALWAYS|CRITICAL|DO NOT|IMPORTANT)\b"
    directives = re.findall(directive_pattern, text)
    word_count = len(text.split())
    if word_count == 0:
        return {"id": "BP11", "name": "Directive density", "passed": True, "severity": None, "message": None}

    density = len(directives) / word_count
    # More than 1 directive per 20 words is heavy-handed
    passed = density < 0.05
    return {
        "id": "BP11",
        "name": "Directive density",
        "passed": passed,
        "severity": "warning" if not passed else None,
        "message": None if passed else f"High ALL-CAPS directive density ({len(directives)} directives in {word_count} words) — consider explaining the 'why' instead",
    }


def check_bp12_progressive_disclosure(body: str, has_references_dir: bool) -> dict:
    """Long skills should use references/ for detailed content."""
    line_count = len(body.splitlines())
    # Only flag if body is approaching the 500-line limit and no references dir
    passed = line_count < 300 or has_references_dir
    return {
        "id": "BP12",
        "name": "Progressive disclosure",
        "passed": passed,
        "severity": "warning" if not passed else None,
        "message": None if passed else f"SKILL.md is {line_count} lines with no references/ directory — consider moving detailed content to references/",
    }


def check_bp13_resource_references(body: str, resource_files: list[str]) -> dict:
    """Bundled resource files should be referenced in SKILL.md."""
    if not resource_files:
        return {"id": "BP13", "name": "Resource references", "passed": True, "severity": None, "message": None}

    unreferenced = [f for f in resource_files if f not in body]
    passed = len(unreferenced) == 0
    return {
        "id": "BP13",
        "name": "Resource references",
        "passed": passed,
        "severity": "warning" if not passed else None,
        "message": None if passed else f"Unreferenced resource files: {', '.join(unreferenced)}",
    }


def check_bp14_description_trigger_phrases(description: str) -> dict:
    """Description should be 'pushy' enough to trigger reliably."""
    if len(description.split()) < 5:
        return {
            "id": "BP14",
            "name": "Trigger phrase coverage",
            "passed": False,
            "severity": "warning",
            "message": "Description too short to trigger reliably — include specific user phrases and contexts",
        }

    trigger_indicators = [
        r"\buse when\b", r"\bwhen (?:user|the user)\b", r"\basks?\b",
        r"\bmentions?\b", r"\bsays?\b", r"\bwants?\b",
    ]
    trigger_count = sum(1 for p in trigger_indicators if re.search(p, description, re.IGNORECASE))

    specificity_indicators = [
        r'"[^"]+?"',  # quoted example phrases
        r"\b(?:e\.g\.|for example|such as|including)\b",
    ]
    specificity_count = sum(1 for p in specificity_indicators if re.search(p, description, re.IGNORECASE))

    passed = trigger_count >= 1
    return {
        "id": "BP14",
        "name": "Trigger phrase coverage",
        "passed": passed,
        "severity": "warning" if not passed else None,
        "message": None if passed else "Description lacks trigger phrases — add 'Use when user...' with specific examples",
    }


def check_bp15_repeated_patterns(body: str) -> dict:
    """Look for repeated code blocks that should be bundled as scripts."""
    code_blocks = re.findall(r"```(?:bash|python|sh)?\n(.*?)```", body, re.DOTALL)
    if len(code_blocks) < 2:
        return {"id": "BP15", "name": "Repeated patterns", "passed": True, "severity": None, "message": None}

    seen = {}
    duplicates = []
    for block in code_blocks:
        stripped = block.strip()
        if stripped in seen:
            if stripped not in duplicates:
                duplicates.append(stripped)
        else:
            seen[stripped] = True

    passed = len(duplicates) == 0
    return {
        "id": "BP15",
        "name": "Repeated patterns",
        "passed": passed,
        "severity": "warning" if not passed else None,
        "message": None if passed else f"Found {len(duplicates)} duplicated code block(s) — consider bundling into scripts/",
    }


# --- Aggregate ---


def run_all_checks(skill_info: dict) -> dict:
    """Run all 15 best practice checks and compute a score.

    Args:
        skill_info: dict with keys:
            filename, folder_name, files_in_folder, frontmatter,
            name, description, body, resource_files, has_references_dir

    Returns:
        dict with 'checks' (list of 15 results) and 'score' (1-10)
    """
    checks = [
        check_bp1_filename(skill_info["filename"]),
        check_bp2_folder_name(skill_info["folder_name"]),
        check_bp3_no_readme(skill_info["files_in_folder"]),
        check_bp4_description_completeness(skill_info["description"]),
        check_bp5_description_length(skill_info["description"]),
        check_bp6_no_xml_in_frontmatter(skill_info["frontmatter"]),
        check_bp7_no_forbidden_names(skill_info["name"]),
        check_bp8_body_length(skill_info["body"]),
        check_bp9_specific_instructions(skill_info["body"]),
        check_bp10_error_handling_section(skill_info["body"]),
        check_bp11_directive_density(skill_info["body"]),
        check_bp12_progressive_disclosure(skill_info["body"], skill_info["has_references_dir"]),
        check_bp13_resource_references(skill_info["body"], skill_info["resource_files"]),
        check_bp14_description_trigger_phrases(skill_info["description"]),
        check_bp15_repeated_patterns(skill_info["body"]),
    ]

    # Score: start at 10, deduct per issue
    score = 10.0
    for check in checks:
        if not check["passed"]:
            if check["severity"] == "error":
                score -= 1.5
            elif check["severity"] == "warning":
                score -= 0.75
    score = max(1.0, min(10.0, score))

    return {"checks": checks, "score": round(score, 1)}
