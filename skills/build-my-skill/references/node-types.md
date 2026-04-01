# Node Types Reference

Complete reference for all node types available in the Skill Tree Builder.

## Core Nodes

### executor
Default action node. The agent takes action — writes files, generates content, processes data.

```python
phase.executor("node-id", "What this step does")
```

### tool
External tool invocation — WebSearch, WebFetch, MCP servers, bash commands.

```python
phase.tool("search", "Search the web for data",
           tools=["WebSearch", "WebFetch"],
           commands=["curl https://api.example.com/data"],
           mcp_servers=["postgres-mcp"])
```

**Fields:**
- `tools`: List of agent tools to use (WebSearch, WebFetch, Read, Write, Bash, etc.)
- `commands`: Bash commands to execute
- `mcp_servers`: MCP servers required (added to skill dependencies)

### file_io
Explicit file read/write operations.

```python
phase.file_io("load-data", "Load the input dataset",
              inputs=["data/input.csv"],
              outputs=["data/processed.json"])
```

### gate
Human approval checkpoint. Pauses execution for user confirmation.

```python
phase.gate("review", "Present results for human review")
```

---

## Agent Nodes

### subagent
Spawns a dedicated sub-agent with its own context, tools, and task.

```python
phase.subagent("analyst", "Analyze market trends",
               agent_type="Explore",           # Agent specialization
               tools=["WebSearch", "WebFetch"], # Tools available to the sub-agent
               context_files=["market.md"])     # Files loaded before execution
```

**Agent types:**
- `general-purpose` — Default. Full capability agent.
- `Explore` — Fast codebase/web exploration. Read-only.
- `Plan` — Architecture and planning. No edits.

### context_loader
Dynamically injects context from files and URLs before processing.

```python
phase.context_loader("load-ctx", "Load user context",
                     files=["references/personas.md", "references/company.md"],
                     urls=["https://api.example.com/context"])
```

---

## Control Flow Nodes

### router
Conditional branching based on computed values. Creates edges to each target.

```python
phase.router("decide", "Route based on quality score",
             conditions=[
                 {"if": "score >= 0.8", "then": "fast-track"},
                 {"if": "score >= 0.5", "then": "standard-path"},
                 {"if": "score < 0.5", "then": "deep-research"},
             ])
```

### signal_gate
Quality gate with metric thresholds. Can retry or branch on failure.

```python
phase.signal_gate("quality-check", "Verify signal quality",
                  criteria={
                      "confidence": ">= 0.7",
                      "signal_strength": ">= 0.5",
                  },
                  on_fail="retry",       # "retry" or "branch"
                  max_retries=3,         # Max attempts when retrying
                  fail_target="fallback") # Target node when branching
```

**on_fail modes:**
- `retry` — Re-run the preceding steps up to `max_retries` times
- `branch` — Route to `fail_target` node instead of proceeding

---

## Parallel Nodes

### diverge (fork)
Spawns parallel branches for multi-perspective analysis.

```python
phase.diverge("multi-angle", "Analyze from multiple perspectives",
              branches=[
                  {"id": "tech", "label": "Technical Assessment", "prompt": "Evaluate..."},
                  {"id": "market", "label": "Market Assessment", "prompt": "Assess..."},
                  {"id": "user", "label": "User Assessment", "prompt": "Evaluate..."},
              ])
```

Creates a fork node + one executor per branch + parallel edges.

### converge (join)
Synthesizes parallel outputs into a unified result.

```python
phase.converge("synthesize", "Merge all perspectives",
               strategy="weighted-merge")
```

**Strategies:**
- `merge` — Combine all outputs into one document
- `best-of` — Select the highest quality output
- `weighted-merge` — Synthesize with weighted importance per source
- `consensus` — Extract consensus points across all outputs

---

## Improvement Nodes

### improvement_loop
Iterates until quality threshold met. Supports RALPH methodology.

```python
phase.improvement_loop("refine", "Improve output quality",
                       strategy="ralph",
                       max_iterations=5,
                       exit_criteria={"quality": ">= 0.9", "completeness": ">= 0.85"},
                       steps=[
                           "Reflect on current output quality",
                           "Analyze specific gaps and weaknesses",
                           "Learn from what worked and what didn't",
                           "Plan targeted improvements",
                           "Hypothesize improved version and test",
                       ])
```

**Strategies:**
- `ralph` — Reflect, Analyze, Learn, Plan, Hypothesize (structured improvement)
- `iterate` — Simple retry with feedback loop

**RALPH Steps:**
1. **Reflect** — What's the current state? What's working?
2. **Analyze** — What gaps exist? What's missing?
3. **Learn** — What patterns or approaches could help?
4. **Plan** — What specific changes will improve the output?
5. **Hypothesize** — Propose the improved version and verify
