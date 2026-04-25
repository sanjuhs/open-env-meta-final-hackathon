---
title: DocEdit Game V2 — Document Editing RL Environment
emoji: 📄
colorFrom: indigo
colorTo: red
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# DocEdit Game V2 — Production-Grade Document Editing RL Environment

Train applicator models to perform precise, fast edits on legal and pharmaceutical documents. Procedurally generated tasks with 6 document types, 12 corruption types, 16+ editing tools, and windowed navigation for documents of any size.

## The Problem We Solve

Legal and pharmaceutical professionals spend hours editing massive documents — contracts, affidavits, drug labels, clinical study reports. A frontier LLM can *decide* what edits to make, but executing 200 precise edits on a 2000-page XML document is too slow and expensive for GPT-4o. We train **applicator models** (1-7B params) that execute edits with near-perfect accuracy at 500x lower cost.

## Game Mechanics

1. **Reset**: Environment generates a document with procedural corruptions (spelling, case, names, formatting, PDF artifacts, junk chars)
2. **Observe**: Agent sees a document chunk + edit instruction + similarity score
3. **Act**: Agent calls one tool per step (replace, format, delete, merge_runs, clean_junk_chars, etc.)
4. **Reward**: Incremental similarity improvement to the hidden target, with bonuses for completion and penalties for collateral damage
5. **Win**: Achieve similarity ≥ 0.999

## Domains

| Domain | Document Types | Real-World Scenario |
|--------|---------------|-------------------|
| **Legal** | Contract, Affidavit, Case Brief | Redlining, name changes, section renumbering |
| **Pharmaceutical** | Drug Label, Clinical Study Report | Dosage updates, adverse reaction additions, regulatory formatting |
| **Business** | Business Report | Financial table fixes, executive summary edits |

## 12 Corruption Types (3 Tiers)

**Tier 1 — Content**: spelling, case, names, punctuation, content deletion, content insertion
**Tier 2 — Formatting**: formatting strip, formatting wrong, alignment, spacing
**Tier 3 — Artifacts**: PDF-to-DOCX fragmented runs, junk characters (zero-width spaces, BOMs)

## 16+ Tools (Agent Actions)

```json
{"tool": "replace", "params": {"target": "recieve", "content": "receive"}}
{"tool": "format_text", "params": {"target": "Important Notice", "format": "bold"}}
{"tool": "highlight", "params": {"target": "Section 3.2", "color": "yellow"}}
{"tool": "merge_runs", "params": {"line_index": 23}}
{"tool": "clean_junk_chars", "params": {}}
{"tool": "set_alignment", "params": {"line_index": 5, "alignment": "center"}}
{"tool": "scroll_to", "params": {"chunk": 47}}
```

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `document_chunk` | str | Currently visible document chunk (XML) |
| `chunk_index` / `total_chunks` | int | Navigation position |
| `document_overview` | str | Heading index for navigation |
| `edit_instruction` | str | Natural language edit description |
| `similarity` | float | Overall similarity to target (0-1) |
| `collateral_damage` | float | Fraction of correct text accidentally damaged |
| `task_difficulty` | int | 1-6 severity level |
| `doc_type` / `domain` | str | Document template and domain |

## 5 Fixed Evaluation Tasks

| Task | Domain | Difficulty | Corruptions |
|------|--------|-----------|-------------|
| `legal_easy` | Legal | 2 (easy) | Spelling, punctuation, content insertion |
| `legal_medium` | Legal | 3 (medium) | Mixed Tier 1+2 |
| `legal_hard` | Legal | 5 (expert) | All tiers including PDF artifacts |
| `pharma_easy` | Pharma | 2 (easy) | Spelling, content deletion |
| `pharma_hard` | Pharma | 4 (hard) | Mixed Tier 1+2 |

## Dual-Seed System

```python
reset(doc_seed=42, corruption_seed=9042, difficulty=3, domain="legal")
```

- `doc_seed` controls document generation (template, content, length)
- `corruption_seed` controls corruption application (types, positions)
- 2^32 × 2^32 = ~18 quintillion unique tasks

## Reward Design

```
reward = similarity_after - similarity_before     # incremental
if exact_match: reward += 1.0 + 0.2 * efficiency  # completion bonus scaled by speed
if noop: reward -= 0.01                            # wasted step
if collateral_damage: reward -= 0.02 * damage      # broke something
```

## Quick Start

```bash
cd doc_edit_game_v2 && uv sync
uvicorn server.app:app --host 0.0.0.0 --port 8001

# Or Docker
docker build -t doc_edit_game_v2-env:latest -f server/Dockerfile .
docker run -p 8000:8000 doc_edit_game_v2-env:latest
```

## Human + Model Web UI

The server now includes a browser playground for the same document-generation and grading logic:

- `GET /` serves a human-editing interface
- `POST /api/game/new` creates a new task from a seed, domain, and difficulty
- `POST /api/game/{session_id}/submit-human` grades the human-edited document
- `POST /api/game/{session_id}/model-step` applies model-style tool calls on a parallel workspace
- `POST /api/game/{session_id}/submit-model` grades the model workspace

UI flow:

1. Load a new random seed from the top bar
2. Read the scenario exposition + instruction
3. Edit the corrupted source document in the human lane
4. Optionally apply environment tools in the model lane on the same seed
5. Submit each lane and compare scores side by side

The human lane uses direct document submission for easy play-testing.
The model lane uses the existing tool-based editing logic so it stays compatible with the RL-style environment.

## Architecture

```
doc_edit_game_v2/
├── game/
│   ├── templates/          # 6 document generators (legal, pharma, business)
│   ├── corruptions/        # 12 corruption types in 3 tiers
│   ├── tools/              # 16+ editing tools
│   ├── windowing.py        # Chunked navigation for large docs
│   ├── grader.py           # Multi-level grading (similarity + edit accuracy + collateral)
│   ├── generator.py        # Task orchestrator with dual-seed system
│   └── content_pools.py    # Domain-specific vocabulary
├── models.py               # DocEditAction + DocEditObservation
├── client.py               # WebSocket client
├── inference.py             # Baseline LLM inference script
└── server/
    ├── doc_edit_game_v2_environment.py
    ├── app.py
    └── Dockerfile
```
