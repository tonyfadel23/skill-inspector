"""Heuristic SKILL.md parser — extracts DAG (nodes + edges) without API calls.

Implements the 4-pass parsing pipeline from parsing-rules.md:
  Pass 1: Structural segmentation (frontmatter, H2/H3 sections)
  Pass 2: Node extraction (fork, join, router, tool, gate, etc.)
  Pass 3: Edge inference (sequential, data_pass, conditional)
  Pass 4: Entry/exit synthesis
"""
import re
import os
try:
    import yaml
except ImportError:
    yaml = None


def parse_skill(skill_path: str) -> dict:
    """Parse a SKILL.md file into a graph structure.

    Returns dict with: name, path, description, pattern, nodes, edges, quality
    """
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    folder = os.path.basename(os.path.dirname(skill_path))
    filename = os.path.basename(skill_path)

    # Pass 1: Extract frontmatter + sections
    frontmatter, body = _split_frontmatter(content)
    meta = _parse_frontmatter(frontmatter)
    sections = _split_sections(body)

    # Extract H1 title as fallback name
    h1_match = re.match(r"^#\s+(.+)", body.strip())
    h1_title = h1_match.group(1).strip() if h1_match else ""

    # Pass 2: Extract nodes from sections
    nodes = []
    edges = []
    _extract_nodes(sections, nodes, edges)

    # Pass 3: Infer edges
    _infer_edges(nodes, edges)

    # Pass 4: Ensure entry/exit
    _ensure_entry_exit(nodes, edges)

    # Detect pattern
    pattern = _detect_pattern(nodes, edges)

    # Run quality checks
    from skill_inspector.patches import suggest_patches
    patches = suggest_patches(nodes, edges)
    score = 10.0
    for p in patches:
        if p["severity"] == "error":
            score -= 1.5
        elif p["severity"] == "warning":
            score -= 0.75
        elif p["severity"] == "info":
            score -= 0.25
    score = max(1.0, min(10.0, round(score, 1)))

    return {
        "name": meta.get("name", h1_title or folder),
        "path": skill_path,
        "description": meta.get("description", ""),
        "pattern": pattern,
        "state_machine": [],
        "dependencies": {"mcp_servers": [], "files": [], "skills": []},
        "nodes": nodes,
        "edges": edges,
        "quality": {
            "score": score,
            "summary": f"{len(nodes)} nodes, {len(edges)} edges. {len(patches)} structural issues.",
            "top_issues": [p["message"] for p in patches[:5]],
        },
    }


def _split_frontmatter(content: str):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if m:
        return m.group(1), content[m.end():]
    return "", content


def _parse_frontmatter(fm: str) -> dict:
    if not fm.strip():
        return {}
    try:
        if yaml:
            return yaml.safe_load(fm) or {}
        raise ImportError
    except Exception:
        # Fallback: simple key: value parsing
        result = {}
        for line in fm.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                result[k.strip()] = v.strip()
        return result


def _split_sections(body: str) -> list:
    """Split body into (level, title, content) tuples."""
    sections = []
    current_title = ""
    current_level = 0
    current_lines = []

    for line in body.splitlines():
        h2 = re.match(r"^##\s+(.+)", line)
        h3 = re.match(r"^###\s+(.+)", line)
        if h2:
            if current_title or current_lines:
                sections.append((current_level, current_title, "\n".join(current_lines)))
            current_title = h2.group(1).strip()
            current_level = 2
            current_lines = []
        elif h3:
            if current_title or current_lines:
                sections.append((current_level, current_title, "\n".join(current_lines)))
            current_title = h3.group(1).strip()
            current_level = 3
            current_lines = []
        else:
            current_lines.append(line)

    if current_title or current_lines:
        sections.append((current_level, current_title, "\n".join(current_lines)))

    return sections


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:40] if s else "node"


def _extract_nodes(sections, nodes, edges):
    """Pass 2: detect node types from section content."""
    # Track which sections are consumed as fork children so we skip them
    consumed = set()

    for idx, (level, title, content) in enumerate(sections):
        if not title or idx in consumed:
            continue

        text = f"{title}\n{content}"
        phase = title

        # Fork detection
        if _match_any(text, [r"all parallel", r"spawn simultaneously", r"run in parallel",
                             r"in parallel", r"\(parallel\)", r"simultaneously",
                             r"parallel.*agents", r"launch.*parallel"]):
            nid = _slugify(title) + "_fork"
            nodes.append(_make_node(nid, title, "fork", phase, text))

            # First try: look ahead for H3 children under this H2
            h3_children = []
            if level == 2:
                for j in range(idx + 1, len(sections)):
                    cl, ct, cc = sections[j]
                    if cl <= 2:
                        break  # next H2 or higher — stop
                    if cl == 3 and ct:
                        h3_children.append((j, ct, cc))

            if h3_children:
                for j, ct, cc in h3_children:
                    consumed.add(j)
                    child_text = f"{ct}\n{cc}"
                    cid = _slugify(ct)
                    # Detect child type
                    ctype = "executor"
                    if _match_any(child_text, [r"```", r"search drive", r"search web",
                                               r"fetch", r"query", r"pull metrics",
                                               r"Run `/", r"run `/", r"Run `"]):
                        ctype = "tool"
                    nodes.append(_make_node(cid, ct, ctype, phase, child_text))
                    edges.append({"source": nid, "target": cid, "type": "parallel", "label": ""})
            else:
                # Fallback: extract parallel children from bold items or numbered items
                children = _extract_parallel_children(content, phase)
                for child in children:
                    nodes.append(child)
                    edges.append({"source": nid, "target": child["id"], "type": "parallel", "label": ""})
            continue

        # Join detection
        if _match_any(text, [r"read all", r"synthesize", r"merge", r"converge",
                             r"combine results", r"when all complete"]):
            nid = _slugify(title) + "_join"
            nodes.append(_make_node(nid, title, "join", phase, text))
            continue

        # Gate detection
        if _match_any(text, [r"ask:", r"ask the user", r"confirm", r"wait for",
                             r"ready to.*\?", r"approval", r"human review",
                             r"follow-up", r"interactive"]):
            nid = _slugify(title)
            nodes.append(_make_node(nid, title, "gate", phase, text))
            # Extract branch options
            options = re.findall(r'["\u201c]([^"\u201d]+)["\u201d].*?→\s*(.+)', content)
            if not options:
                options = re.findall(r"[-•]\s*(.+?)→\s*(.+)", content)
            for opt_label, opt_target in options:
                target_id = _slugify(opt_target.strip())
                if not any(n["id"] == target_id for n in nodes):
                    nodes.append(_make_node(target_id, opt_target.strip(), "spawn", phase, opt_target))
                edges.append({"source": nid, "target": target_id, "type": "conditional", "label": opt_label.strip()})
            continue

        # Router detection
        if _match_any(text, [r"if\b.*then", r"based on", r"depending on", r"check whether"]):
            nid = _slugify(title)
            nodes.append(_make_node(nid, title, "router", phase, text))
            continue

        # Tool/MCP detection
        code_blocks = re.findall(r"```(?:bash|sh)?\n(.*?)```", content, re.DOTALL)
        if code_blocks or _match_any(text, [r"search drive", r"search web", r"pull.*from.*looker",
                                             r"fetch", r"query", r"pull metrics"]):
            nid = _slugify(title)
            nodes.append(_make_node(nid, title, "tool", phase, text))
            # Also extract tools from code blocks
            for block in code_blocks:
                tool_label = block.strip().split("\n")[0][:60]
                tool_id = _slugify(tool_label) + "_tool"
                if not any(n["id"] == tool_id for n in nodes):
                    nodes.append(_make_node(tool_id, tool_label, "tool", phase, block))
                    edges.append({"source": nid, "target": tool_id, "type": "sequential", "label": ""})
            continue

        # Validator detection
        if _match_any(text, [r"check every.*gate", r"fix failures", r"do not pass",
                             r"reviewer", r"verify", r"validate"]):
            nid = _slugify(title)
            nodes.append(_make_node(nid, title, "validator", phase, text))
            continue

        # Template detection
        if _match_any(text, [r"template", r"format as"]):
            nid = _slugify(title)
            nodes.append(_make_node(nid, title, "template", phase, text))
            continue

        # File I/O detection
        if _match_any(text, [r"save to", r"write to", r"output:", r"read\b", r"input:",
                             r"must exist", r"load"]):
            nid = _slugify(title)
            nodes.append(_make_node(nid, title, "file_io", phase, text))
            # Extract file paths
            paths = re.findall(r"`([^`]+\.\w+)`", text)
            inputs = []
            outputs = []
            for p in paths:
                if _match_any(text, [r"save to.*" + re.escape(p), r"write to.*" + re.escape(p)]):
                    outputs.append(p)
                else:
                    inputs.append(p)
            nodes[-1]["inputs"] = inputs
            nodes[-1]["outputs"] = outputs
            continue

        # Default: executor
        nid = _slugify(title)
        if nid and not any(n["id"] == nid for n in nodes):
            nodes.append(_make_node(nid, title, "executor", phase, text))


def _extract_parallel_children(content: str, phase: str) -> list:
    """Extract bold items or numbered sub-tasks as parallel children."""
    # Skip words that are just inline emphasis, not task names
    _noise = {"important", "note", "critical", "skip", "only", "document",
              "documents", "output", "input", "if", "in parallel", "parallel",
              "optional", "required", "warning", "error", "v1 check"}

    def _is_noise(label):
        low = label.lower().strip().rstrip(".:!?")
        if low in _noise or len(label) < 4:
            return True
        # Filter out full sentences (contain spaces and end with punctuation)
        if len(label.split()) > 5:
            return True
        return False
    children = []
    # Bold items: **Name** — description
    for m in re.finditer(r"\*\*(.+?)\*\*", content):
        label = m.group(1)
        if _is_noise(label):
            continue
        cid = _slugify(label)
        if cid and not any(c["id"] == cid for c in children):
            children.append(_make_node(cid, label, "executor", phase, label))
    # Numbered items: 1. Description
    if not children:
        for m in re.finditer(r"^\d+\.\s+(.+)", content, re.MULTILINE):
            label = m.group(1).strip()
            cid = _slugify(label)
            if cid and not any(c["id"] == cid for c in children):
                children.append(_make_node(cid, label, "executor", phase, label))
    return children


def _make_node(nid, label, ntype, phase, raw_instruction):
    return {
        "id": nid,
        "label": label,
        "type": ntype,
        "phase": phase,
        "raw_instruction": raw_instruction.strip()[:500],
        "inputs": [],
        "outputs": [],
        "warnings": [],
    }


def _match_any(text, patterns):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _infer_edges(nodes, edges):
    """Pass 3: add sequential edges between nodes in same phase without explicit edges."""
    # Group by phase
    phase_nodes = {}
    for n in nodes:
        phase = n.get("phase", "")
        phase_nodes.setdefault(phase, []).append(n["id"])

    existing_sources = {(e["source"], e["target"]) for e in edges}

    # Sequential within phase
    for phase, nids in phase_nodes.items():
        for i in range(len(nids) - 1):
            pair = (nids[i], nids[i + 1])
            if pair not in existing_sources:
                edges.append({"source": nids[i], "target": nids[i + 1], "type": "sequential", "label": ""})

    # Cross-phase: connect last node of phase N to first node of phase N+1
    phases_ordered = list(phase_nodes.keys())
    for i in range(len(phases_ordered) - 1):
        src_nodes = phase_nodes[phases_ordered[i]]
        tgt_nodes = phase_nodes[phases_ordered[i + 1]]
        if src_nodes and tgt_nodes:
            pair = (src_nodes[-1], tgt_nodes[0])
            if pair not in existing_sources:
                edges.append({"source": src_nodes[-1], "target": tgt_nodes[0], "type": "sequential", "label": ""})

    # Data dependency edges
    output_map = {}
    for n in nodes:
        for o in n.get("outputs", []):
            output_map[o] = n["id"]

    for n in nodes:
        for inp in n.get("inputs", []):
            if inp in output_map and output_map[inp] != n["id"]:
                pair = (output_map[inp], n["id"])
                if pair not in existing_sources:
                    edges.append({"source": output_map[inp], "target": n["id"],
                                  "type": "data_pass", "label": os.path.basename(inp)})


def _ensure_entry_exit(nodes, edges):
    """Pass 4: ensure graph has entry and exit nodes."""
    if not nodes:
        return

    # Check if there's already a clear entry (no incoming edges)
    targets = {e["target"] for e in edges}
    has_entry = any(n["id"] not in targets for n in nodes)
    if not has_entry and nodes:
        nodes[0]["type"] = "file_io"


def _detect_pattern(nodes, edges):
    """Detect the high-level orchestration pattern."""
    types = {n["type"] for n in nodes}
    edge_types = {e["type"] for e in edges}

    if "fork" in types and "join" in types:
        return "parallel-fan-out-fan-in"
    if "fork" in types:
        return "parallel-fan-out"
    if "parallel" in edge_types:
        return "parallel"
    if "router" in types or "conditional" in edge_types:
        return "conditional-routing"
    return "sequential"


def parse_skill_folder(folder_path: str) -> dict:
    """Parse all SKILL.md files in a folder tree."""
    skills = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if f == "SKILL.md":
                path = os.path.join(root, f)
                try:
                    skill = parse_skill(path)
                    skills.append(skill)
                except Exception as e:
                    print(f"Warning: failed to parse {path}: {e}")
    return {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "mode": "standard",
        "skills": skills,
    }
