#!/usr/bin/env python3
"""Example: Goal-to-Prototype skill tree.

A complete pipeline that transforms a user's goal into a working prototype,
using multi-agent orchestration, signal gating, RALPH improvement loops,
and diverge/converge analysis patterns.

Usage:
    python3 examples/goal_to_prototype.py

Outputs:
    examples/output/goal-to-prototype/SKILL.md  — the generated skill
    examples/output/goal-to-prototype-report.html — visualization (if parser available)
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_inspector.builder import SkillTreeBuilder
from skill_inspector.emitter import emit_skill_md


def build_goal_to_prototype() -> SkillTreeBuilder:
    tree = SkillTreeBuilder(
        "goal-to-prototype",
        "Transform a high-level goal into a validated prototype with market research, "
        "multi-angle analysis, and iterative refinement. Use when the user says "
        '"build me a prototype", "turn this idea into reality", "goal to prototype", '
        '"validate this concept", or "research and build".',
    )

    # ── Phase 1: Context Loading ─────────────────────────────────────────
    p1 = tree.phase("Step 0 — Context Loading")
    p1.context_loader(
        "load-user-context",
        "Load user personas and company profile",
        files=["references/personas.md", "references/company-profile.md"],
    )
    p1.context_loader(
        "load-market-context",
        "Load market landscape and competitive intel",
        files=["references/market-landscape.md"],
        urls=["https://api.example.com/market-data"],
    )
    p1.executor("parse-goal", "Parse the user's goal statement into structured "
                "requirements: target audience, problem space, desired outcome, "
                "success metrics, and constraints")

    # ── Phase 2: Data Acquisition (parallel sub-agents) ──────────────────
    p2 = tree.phase("Step 1 — Data Acquisition")
    p2.diverge(
        "research-fan-out",
        "Launch parallel research agents to gather data simultaneously",
        branches=[
            {
                "id": "web-research",
                "label": "Web Research Agent",
                "prompt": "Search the web for recent articles, papers, and discussions "
                          "related to the problem space. Fetch at least 10 high-quality "
                          "sources. Use WebSearch and WebFetch tools.",
            },
            {
                "id": "competitor-analysis",
                "label": "Competitor Analysis Agent",
                "prompt": "Identify top 5-10 competitors in the space. For each, analyze: "
                          "product offering, pricing, strengths, weaknesses, market share. "
                          "Use WebSearch to find competitor data.",
            },
            {
                "id": "user-research",
                "label": "User Research Agent",
                "prompt": "Cross-reference the loaded personas against the problem space. "
                          "Identify pain points, unmet needs, willingness to pay, and "
                          "adoption barriers. Load references/personas.md for context.",
            },
            {
                "id": "trend-analysis",
                "label": "Market Trend Agent",
                "prompt": "Analyze market trends, growth trajectories, regulatory changes, "
                          "and technology shifts that could impact the opportunity. "
                          "Use WebSearch for current data.",
            },
        ],
    )

    # ── Phase 3: Signal Evaluation ───────────────────────────────────────
    p3 = tree.phase("Step 2 — Signal Evaluation")
    p3.converge(
        "merge-research",
        "Synthesize all research outputs into a unified intelligence brief",
        strategy="weighted-merge",
    )
    p3.executor(
        "compute-signals",
        "Compute signal quality metrics from the merged research:\n"
        "- **market_signal**: strength of market opportunity (0-1)\n"
        "- **competitive_gap**: size of unserved niche (0-1)\n"
        "- **user_demand**: evidence of user pull (0-1)\n"
        "- **feasibility**: technical buildability (0-1)\n"
        "- **confidence**: data quality and coverage (0-1)",
    )
    p3.signal_gate(
        "signal-quality-gate",
        "Verify signal strength before investing in deep analysis",
        criteria={
            "confidence": ">= 0.6",
            "market_signal": ">= 0.5",
            "user_demand": ">= 0.4",
        },
        on_fail="retry",
        max_retries=3,
    )

    # ── Phase 4: Multi-Angle Analysis (diverge) ──────────────────────────
    p4 = tree.phase("Step 3 — Multi-Angle Analysis")
    p4.diverge(
        "perspective-analysis",
        "Analyze the opportunity from multiple angles in parallel",
        branches=[
            {
                "id": "technical-feasibility",
                "label": "Technical Feasibility Assessment",
                "prompt": "Evaluate: tech stack options, build complexity, infrastructure "
                          "needs, MVP scope, time-to-prototype. Score feasibility 0-1.",
            },
            {
                "id": "market-viability",
                "label": "Market Viability Assessment",
                "prompt": "Evaluate: TAM/SAM/SOM, go-to-market strategy, pricing model, "
                          "distribution channels, competitive moat. Score viability 0-1.",
            },
            {
                "id": "user-desirability",
                "label": "User Desirability Assessment",
                "prompt": "Evaluate: user journey, pain-point alignment, switching cost, "
                          "value proposition clarity, retention hooks. Score desirability 0-1.",
            },
        ],
    )

    # ── Phase 5: Synthesis ───────────────────────────────────────────────
    p5 = tree.phase("Step 4 — Synthesis")
    p5.converge(
        "synthesize-perspectives",
        "Converge all perspective assessments into a unified opportunity score",
        strategy="weighted-merge",
    )
    p5.signal_gate(
        "opportunity-gate",
        "Gate on overall opportunity quality before prototyping",
        criteria={
            "opportunity_score": ">= 0.7",
            "feasibility": ">= 0.6",
        },
        on_fail="branch",
        fail_target="deep-research-loop",
    )
    p5.executor(
        "generate-brief",
        "Generate a structured product brief with: problem statement, target user, "
        "value proposition, key features, success metrics, risks, and mitigations",
    )
    p5.improvement_loop(
        "deep-research-loop",
        "Apply RALPH methodology to strengthen weak signals",
        strategy="ralph",
        max_iterations=5,
        exit_criteria={"opportunity_score": ">= 0.7", "confidence": ">= 0.8"},
        steps=[
            "Reflect on which signals are weak and why",
            "Analyze gaps in the research — what data is missing?",
            "Learn from competitor approaches — what are they doing right?",
            "Plan targeted research to fill specific gaps",
            "Hypothesize an improved positioning and re-score",
        ],
    )

    # ── Phase 6: Prototype Generation ────────────────────────────────────
    p6 = tree.phase("Step 5 — Prototype Generation")
    p6.file_io(
        "write-prd",
        "Generate the Product Requirements Document",
        outputs=["output/prd.md"],
    )
    p6.subagent(
        "wireframe-agent",
        "Generate low-fidelity wireframes for the core user flows",
        agent_type="general-purpose",
        tools=["Write"],
        context_files=["output/prd.md"],
    )
    p6.subagent(
        "implementation-agent",
        "Generate the implementation plan with architecture, tech stack, "
        "milestones, and sprint breakdown",
        agent_type="general-purpose",
        tools=["Write", "Read"],
        context_files=["output/prd.md"],
    )

    # ── Phase 7: Quality Gate ────────────────────────────────────────────
    p7 = tree.phase("Step 6 — Final Review")
    p7.improvement_loop(
        "quality-loop",
        "Iteratively improve prototype quality",
        strategy="ralph",
        max_iterations=3,
        exit_criteria={"completeness": ">= 0.9", "coherence": ">= 0.9"},
        steps=[
            "Reflect on prototype completeness — are all requirements covered?",
            "Analyze coherence — do PRD, wireframes, and plan align?",
            "Learn from quality gaps — what's missing or contradictory?",
            "Plan specific fixes for each gap",
            "Hypothesize the improved version and verify",
        ],
    )
    p7.gate("final-review", "Present the complete prototype package to the user "
            "for review and approval")
    p7.file_io(
        "deliver-package",
        "Save the final deliverables",
        outputs=[
            "output/prd.md",
            "output/wireframes.md",
            "output/implementation-plan.md",
            "output/research-brief.md",
        ],
    )

    return tree


def main():
    tree = build_goal_to_prototype()
    graph = tree.build()

    # Emit SKILL.md
    md = emit_skill_md(graph)
    out_dir = os.path.join(os.path.dirname(__file__), "output", "goal-to-prototype")
    os.makedirs(out_dir, exist_ok=True)
    skill_path = os.path.join(out_dir, "SKILL.md")
    with open(skill_path, "w") as f:
        f.write(md)
    print(f"Generated: {skill_path}")

    # Validate round-trip
    from skill_inspector.parser import parse_skill
    parsed = parse_skill(skill_path)
    print(f"Parsed: {parsed['name']} — {len(parsed['nodes'])} nodes, "
          f"{len(parsed['edges'])} edges, pattern={parsed['pattern']}")
    print(f"Quality: {parsed['quality']['score']}/10")

    # Also dump the builder graph as JSON for inspection
    json_path = os.path.join(out_dir, "graph.json")
    with open(json_path, "w") as f:
        json.dump(graph, f, indent=2)
    print(f"Graph JSON: {json_path}")

    # Print summary
    print(f"\n--- Skill Tree Summary ---")
    print(f"Name: {graph['name']}")
    print(f"Phases: {len(graph['phases'])}")
    print(f"Nodes: {len(graph['nodes'])}")
    print(f"Edges: {len(graph['edges'])}")
    print(f"Pattern: {graph['pattern']}")
    print(f"Dependencies:")
    for k, v in graph['dependencies'].items():
        if v:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
