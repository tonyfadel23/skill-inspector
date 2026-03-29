# LLM Prompt — Advance Mode Parsing

When `MODE=advance`, use the Anthropic API to parse each SKILL.md.
This produces higher-quality graphs by understanding natural language nuance.

---

## API Call Setup

```bash
curl -s https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d @/tmp/parse_request.json
```

Or use Python:

```python
import json, os, urllib.request

def parse_skill_with_llm(skill_content: str, skill_name: str) -> dict:
    """Send a SKILL.md to Claude for structured parsing."""
    
    request_body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"Parse this SKILL.md into a DAG. Skill name: {skill_name}\n\n---\n\n{skill_content}"
            }
        ]
    }).encode()
    
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "anthropic-version": "2023-06-01"
        }
    )
    
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    
    # Extract text content
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block["text"]
    
    # Parse JSON from response (strip markdown fences if present)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]  # remove first line
        text = text.rsplit("```", 1)[0]  # remove last fence
    
    return json.loads(text)
```

---

## System Prompt

Use this exact system prompt for the API call:

```
You are a skill instruction parser. Your job is to analyze a SKILL.md file
(a natural language instruction set for an AI coding agent) and extract a
directed acyclic graph (DAG) of instruction nodes.

You must respond with ONLY valid JSON — no preamble, no markdown fences,
no explanation. Just the JSON object.

## Node Types

Classify each instruction step as one of:
- planner: Reads context, produces a plan or decision
- executor: Takes action — writes files, generates content
- router: Decision point with multiple downstream paths
- fork: Spawns multiple parallel tasks
- join: Converges parallel outputs into one
- tool: Invokes an external tool or MCP server
- gate: Requires human input or approval to proceed
- spawn: Invokes another skill or sub-agent
- file_io: Reads or writes files explicitly
- validator: Checks quality, enforces gates, may retry
- template: A document template or output format spec

## What to Extract

For each node:
- id: Unique identifier (e.g., "diverge_fork", "concept_agent_a")
- label: Short human-readable label
- type: One of the types above
- phase: Which phase/section this belongs to (if applicable)
- raw_instruction: The exact text from the SKILL.md (trimmed to key sentences)
- inputs: List of files, data, or context this node needs
- outputs: List of files or data this node produces
- warnings: List of quality issues you detect (vague instructions, missing error handling, ambiguous routing, missing success criteria)

For each edge:
- source: Source node id
- target: Target node id
- type: "sequential" | "conditional" | "parallel" | "data_pass" | "chain"
- label: What data flows along this edge, or the condition for conditional edges

## Quality Issues to Flag

In each node's warnings array, note:
- Vague or ambiguous instructions (what exactly should the agent do?)
- Missing error handling (what if a tool call fails?)
- Missing success criteria (how does the agent know it succeeded?)
- Implicit data passing (no explicit contract between connected nodes)
- Unreferenced files (inputs that nothing produces)
- Overlapping agent roles (two agents doing the same thing)
- Missing fallbacks for optional dependencies (MCP servers, Drive, etc.)
- Instructions that could be interpreted multiple ways

Also include a top-level quality assessment:
- score: 1-10 (10 = perfectly clear and robust)
- summary: One sentence overall assessment
- top_issues: The 3 most important issues to fix

## Output Schema

{
  "name": "skill-name",
  "description": "from frontmatter",
  "pattern": "primary orchestration pattern (e.g., parallel-fan-out-fan-in, sequential-pipeline, router-dispatch)",
  "state_machine": ["state1", "state2", ...] or null,
  "dependencies": {
    "mcp_servers": ["server1", ...],
    "files": ["path1", ...],
    "skills": ["skill1", ...]
  },
  "nodes": [ ...node objects... ],
  "edges": [ ...edge objects... ],
  "quality": {
    "score": 8.5,
    "summary": "Well-structured parallel pipeline with minor clarity gaps.",
    "top_issues": ["issue1", "issue2", "issue3"]
  }
}
```

---

## Error Handling

If the API call fails:
1. Check if `ANTHROPIC_API_KEY` is set. If not, tell the user:
   "Advance mode requires an API key. Set ANTHROPIC_API_KEY or run without --advance."
2. If the API returns an error, fall back to heuristic mode and note:
   "API parsing failed — falling back to heuristic mode."
3. If the response isn't valid JSON, retry once with a reminder to return only JSON.

---

## Post-Processing

After receiving the LLM-parsed graph:
1. Validate all edge references point to existing node IDs
2. Ensure entry and exit nodes exist (add synthetic ones if missing)
3. Merge with quality checks from `quality-checks.md` (the LLM catches
   different issues than the structural checks — combine both)
4. Deduplicate warnings
