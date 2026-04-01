---
name: goal-to-prototype
description: >
  Transform a high-level goal into a validated prototype with market research, multi-angle analysis, and iterative refinement. Use when the user says "build me a prototype", "turn this idea into reality", "goal to prototype", "validate this concept", or "research and build".
---

# goal-to-prototype

## Step 0 — Context Loading

### Load user personas and company profile

Read and load the following context files:

- Load `references/personas.md`
- Load `references/company-profile.md`

### Load market landscape and competitive intel

Read and load the following context files:

- Load `references/market-landscape.md`

Also fetch data from:
- Fetch `https://api.example.com/market-data`

### Parse the user's goal statement into structured requirements: target audience, problem space, desired outcome, success metrics, and constraints

Parse the user's goal statement into structured requirements: target audience, problem space, desired outcome, success metrics, and constraints

## Step 1 — Data Acquisition

### Launch parallel research agents to gather data simultaneously (parallel)

Run the following tasks simultaneously in parallel:

#### Web Research Agent

Search the web for recent articles, papers, and discussions related to the problem space. Fetch at least 10 high-quality sources. Use WebSearch and WebFetch tools.

#### Competitor Analysis Agent

Identify top 5-10 competitors in the space. For each, analyze: product offering, pricing, strengths, weaknesses, market share. Use WebSearch to find competitor data.

#### User Research Agent

Cross-reference the loaded personas against the problem space. Identify pain points, unmet needs, willingness to pay, and adoption barriers. Load references/personas.md for context.

#### Market Trend Agent

Analyze market trends, growth trajectories, regulatory changes, and technology shifts that could impact the opportunity. Use WebSearch for current data.


## Step 2 — Signal Evaluation

### Synthesize all research outputs into a unified intelligence brief

Read all outputs and synthesize them with weighted importance.

### Compute signal quality metrics from the merged research:
- **market_signal**: strength of market opportunity (0-1)
- **competitive_gap**: size of unserved niche (0-1)
- **user_demand**: evidence of user pull (0-1)
- **feasibility**: technical buildability (0-1)
- **confidence**: data quality and coverage (0-1)

Compute signal quality metrics from the merged research:
- **market_signal**: strength of market opportunity (0-1)
- **competitive_gap**: size of unserved niche (0-1)
- **user_demand**: evidence of user pull (0-1)
- **feasibility**: technical buildability (0-1)
- **confidence**: data quality and coverage (0-1)

### Verify signal strength before investing in deep analysis

Check whether the following criteria are met before proceeding:

- **confidence**: >= 0.6
- **market_signal**: >= 0.5
- **user_demand**: >= 0.4

If any criterion fails, retry up to 3 times.
On each retry, analyze what went wrong and adjust the approach.

## Step 3 — Multi-Angle Analysis

### Analyze the opportunity from multiple angles in parallel (parallel)

Run the following tasks simultaneously in parallel:

#### Technical Feasibility Assessment

Evaluate: tech stack options, build complexity, infrastructure needs, MVP scope, time-to-prototype. Score feasibility 0-1.

#### Market Viability Assessment

Evaluate: TAM/SAM/SOM, go-to-market strategy, pricing model, distribution channels, competitive moat. Score viability 0-1.

#### User Desirability Assessment

Evaluate: user journey, pain-point alignment, switching cost, value proposition clarity, retention hooks. Score desirability 0-1.


## Step 4 — Synthesis

### Converge all perspective assessments into a unified opportunity score

Read all outputs and synthesize them with weighted importance.

### Gate on overall opportunity quality before prototyping

Check whether the following criteria are met before proceeding:

- **opportunity_score**: >= 0.7
- **feasibility**: >= 0.6

If criteria pass → proceed to next step.
If criteria fail → "deep-research-loop" → route to remediation.

### Generate a structured product brief with: problem statement, target user, value proposition, key features, success metrics, risks, and mitigations

Generate a structured product brief with: problem statement, target user, value proposition, key features, success metrics, risks, and mitigations

### Apply RALPH methodology to strengthen weak signals

Apply the RALPH methodology (up to 5 iterations):

1. Reflect on which signals are weak and why
2. Analyze gaps in the research — what data is missing?
3. Learn from competitor approaches — what are they doing right?
4. Plan targeted research to fill specific gaps
5. Hypothesize an improved positioning and re-score

**Exit when all criteria are met:**
- opportunity_score: >= 0.7
- confidence: >= 0.8

Validate the output against criteria after each iteration. Fix failures before proceeding.

## Step 5 — Prototype Generation

### Generate the Product Requirements Document

Save to the following output files:
- Write to `output/prd.md`

### Generate low-fidelity wireframes for the core user flows

Launch a **general-purpose** sub-agent to run in parallel with the following task:

> Generate low-fidelity wireframes for the core user flows

Tools available: Write

Load the following context before starting:
- Read `output/prd.md`

### Generate the implementation plan with architecture, tech stack, milestones, and sprint breakdown

Launch a **general-purpose** sub-agent to run in parallel with the following task:

> Generate the implementation plan with architecture, tech stack, milestones, and sprint breakdown

Tools available: Write, Read

Load the following context before starting:
- Read `output/prd.md`

## Step 6 — Final Review

### Iteratively improve prototype quality

Apply the RALPH methodology (up to 3 iterations):

1. Reflect on prototype completeness — are all requirements covered?
2. Analyze coherence — do PRD, wireframes, and plan align?
3. Learn from quality gaps — what's missing or contradictory?
4. Plan specific fixes for each gap
5. Hypothesize the improved version and verify

**Exit when all criteria are met:**
- completeness: >= 0.9
- coherence: >= 0.9

Validate the output against criteria after each iteration. Fix failures before proceeding.

### Present the complete prototype package to the user for review and approval

Ask the user to confirm before proceeding:

> Present the complete prototype package to the user for review and approval

### Save the final deliverables

Save to the following output files:
- Write to `output/prd.md`
- Write to `output/wireframes.md`
- Write to `output/implementation-plan.md`
- Write to `output/research-brief.md`

## Troubleshooting

If something goes wrong during execution, check these common issues:

**Tool access issues:**
Ensure the following tools are available: Read, Write

**Missing files:**
Ensure these files exist before running:
- `output/implementation-plan.md`
- `output/prd.md`
- `output/research-brief.md`
- `output/wireframes.md`
- `references/company-profile.md`
- `references/market-landscape.md`
- `references/personas.md`

## References

- `output/implementation-plan.md`
- `output/prd.md`
- `output/research-brief.md`
- `output/wireframes.md`
- `references/company-profile.md`
- `references/market-landscape.md`
- `references/personas.md`
