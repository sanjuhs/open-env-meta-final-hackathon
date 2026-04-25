# Idea Scorecard

## Scoring Rubric

Scores are out of 10 and weighted roughly by the hackathon criteria.

| Field | Meaning |
|---|---|
| Innovation | Would judges find the environment fresh and research-worthy? |
| Story | Can the demo be explained clearly and memorably? |
| Trainability | Can we show reward improvement in the available time? |
| Verifiability | Can rewards be objective and hard to game? |
| Build speed | Can we build a credible OpenEnv environment quickly? |

## Candidate Ideas

| Rank | Idea | Innovation | Story | Trainability | Verifiability | Build speed | Verdict |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | Regulatory Dossier Control Room | 9 | 9 | 8 | 9 | 8 | Best overall. Uses DocEdit leverage but expands into long-horizon professional world modeling. |
| 2 | Personal Chief of Staff Simulator | 8 | 9 | 7 | 7 | 6 | Excellent theme fit, but personalization and reward design may get fuzzy. |
| 3 | Codebase Migration Gym | 7 | 7 | 8 | 9 | 6 | Verifiable with tests, but code agents are crowded and less novel. |
| 4 | Research Reproduction Lab | 9 | 8 | 5 | 7 | 4 | Very ambitious, likely too hard to build and train under time pressure. |
| 5 | Multi-Agent Procurement Negotiation | 8 | 8 | 6 | 6 | 5 | Good multi-agent story, but objective grading and RL loop are harder. |
| 6 | Supply Chain Crisis Planner | 7 | 8 | 7 | 8 | 6 | Solid simulator, but can feel like an operations game if not grounded enough. |

## Recommended Winner Candidate

Build **Regulatory Dossier Control Room**.

One-line pitch:

> Train an agent to manage a 300-step regulatory document crisis: inspect a simulated pharma submission, discover scattered inconsistencies, apply precise cross-document edits, validate the dossier, and improve through adversarially generated new compliance failures.

Why this is the best fit:

- It hits long-horizon planning directly.
- It is professional and high-value.
- It has crisp verification via hidden canonical facts and compliance rules.
- It extends prior DocEdit work instead of restarting from zero.
- It creates a very strong story: "Can a small model learn to behave like a regulatory operations associate?"
- It can show training improvement without requiring a real external system like Kubernetes.
- It can scale from easy 10-step tasks to hard 300-step tasks through curriculum.

## Why Not Just Continue DocEdit V2?

DocEdit V2 is useful but too narrow for this round's themes. It is mostly local edit application. The judging criteria now heavily reward long-horizon behavior, self-improvement, and world modeling.

We should reuse DocEdit-style document generation, corruption, chunking, and grading, but wrap it inside a larger workflow:

- Multiple documents.
- Persistent investigation state.
- Hidden facts.
- Cross-document dependencies.
- Validation loops.
- Audit notes.
- Adaptive scenario generator.

That gives the old strength a much bigger judging surface.

