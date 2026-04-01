# Orchestration Patterns

Common patterns for structuring skill trees. Mix and match as needed.

## Sequential Pipeline

The simplest pattern. Steps execute one after another.

```
[Load Context] → [Process] → [Generate] → [Deliver]
```

**Use when:** Linear workflows with no branching or parallelism needed.

## Parallel Fan-Out / Fan-In

Fork into parallel branches, then converge results.

```
[Context] → [Fork] → [Agent A] → [Join] → [Deliver]
                   → [Agent B] ↗
                   → [Agent C] ↗
```

**Use when:** Multiple independent analyses that benefit from diverse perspectives.

**Builder pattern:**
```python
p.diverge("fork", "Parallel analysis", branches=[...])
# ... next phase ...
p.converge("join", "Synthesize", strategy="weighted-merge")
```

## Gated Pipeline

Sequential with quality checkpoints that can retry or branch.

```
[Research] → [Gate: signal >= 0.7] → [Build] → [Gate: quality >= 0.9] → [Deliver]
                    ↓ fail                              ↓ fail
              [Retry with RALPH]                  [Improvement Loop]
```

**Use when:** Quality matters and you want to catch problems early.

## Conditional Router

Branch based on computed metrics. Each branch handles a different scenario.

```
[Evaluate] → [Router] → [Fast Track]     (score >= 0.8)
                      → [Standard Path]   (score >= 0.5)
                      → [Deep Research]   (score < 0.5)
```

**Use when:** Different inputs require different processing strategies.

## RALPH Improvement Loop

Iterative refinement using Reflect, Analyze, Learn, Plan, Hypothesize.

```
[Draft] → [RALPH Loop] → [Quality Gate] → [Deliver]
              ↑                ↓ fail
              └────────────────┘
```

**Use when:** Output quality needs to exceed first-draft level. Good for:
- Complex documents (PRDs, research briefs)
- Multi-stakeholder deliverables
- Outputs that will be externally shared

## Multi-Agent Research

Combine parallel sub-agents with signal gating and improvement loops.

```
[Load Context] → [Fork Research Agents] → [Merge] → [Signal Gate]
                                                          ↓ pass
                 [Fork Perspective Agents] ← ─ ─ ─ ─ ─ ─ ┘
                          ↓
                 [Converge] → [RALPH Loop] → [Human Review] → [Deliver]
```

**Use when:** Complex tasks requiring deep research, multiple viewpoints, and
iterative quality improvement. This is the "goal to prototype" pattern.

## Choosing a Pattern

| Situation | Pattern |
|-----------|---------|
| Simple linear task | Sequential Pipeline |
| Need multiple viewpoints | Parallel Fan-Out / Fan-In |
| Quality-critical output | Gated Pipeline |
| Variable input complexity | Conditional Router |
| Need to exceed first-draft quality | RALPH Improvement Loop |
| Complex research + prototyping | Multi-Agent Research |

## Combining Patterns

Most real-world skills combine multiple patterns:

1. Start with **context loading** (always)
2. Add **parallel research** if multiple data sources
3. Add **signal gates** after data gathering
4. Use **diverge/converge** for multi-angle analysis
5. Add **RALPH loops** for quality-critical deliverables
6. End with **human review gate** for high-stakes outputs
