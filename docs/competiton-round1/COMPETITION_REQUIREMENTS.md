# OpenEnv Round 1 — Competition Requirements

**Deadline**: 8 April 2026, 11:59 PM IST
**Competing as**: Solo — Sanjayprasad H S (sanjuhs123@gmail.com)

---

## Mandatory Pass/Fail Gates (all must pass or DQ)

1. **HF Space deploys** — automated ping to Space URL returns 200 + responds to `reset()`
2. **OpenEnv spec compliance** — `openenv validate` passes (openenv.yaml, typed models, step/reset/state endpoints)
3. **Dockerfile builds** — `docker build` succeeds on submitted repo
4. **Baseline reproduces** — `inference.py` runs without error, produces scores
5. **3+ tasks with graders** — each grader returns score in 0.0–1.0 range

## Functional Requirements

| Requirement | Detail |
|---|---|
| Real-world task | Must simulate something humans actually do (not games/toys) |
| OpenEnv spec | Typed `Action`, `Observation` Pydantic models; `step(action)` → obs, reward, done, info; `reset()` → initial obs; `state()` → current state; `openenv.yaml` with metadata |
| 3+ tasks with graders | Each task has a concrete objective + programmatic grader (0.0–1.0). Easy → medium → hard progression. Deterministic, reproducible. |
| Reward function | Signal over full trajectory (not just binary end). Partial progress rewarded. Penalize bad behavior. |
| Baseline inference script | Named `inference.py` in project root. Uses OpenAI API client. Reads `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN` from env vars. Produces reproducible baseline score on all 3 tasks. Must emit `[START]`, `[STEP]`, `[END]` structured stdout logs. |

## Non-Functional Requirements

- Deploy as containerized HF Space tagged `openenv`
- Working Dockerfile (`docker build` + `docker run`)
- README: env description, action/observation spaces, task descriptions, setup instructions, baseline scores

## Scoring Weights

| Parameter | Weight |
|---|---|
| Real-world utility | 30% |
| Task & grader quality | 25% |
| Environment design | 20% |
| Code quality & spec compliance | 15% |
| Creativity & novelty | 10% |

## Infra Constraints

- Inference script runtime < 20 min
- Must run on vcpu=2, memory=8gb
- Use OpenAI Client for all LLM calls

## Env Vars Required

```
API_BASE_URL   — LLM API endpoint
MODEL_NAME     — model identifier for inference
HF_TOKEN       — HF / API key
```

## Pre-Submission Validation

```bash
# Run the validation script before submitting
openenv validate
docker build .
# Then submit HF Spaces URL on platform
```

## Evaluation Pipeline

1. **Phase 1**: Automated validation (pass/fail gate)
2. **Phase 2**: Agentic evaluation — baseline agent + standard Open LLM agent (Nemotron 3 Super) run against all envs
3. **Phase 3**: Human review by Meta + HF engineers
