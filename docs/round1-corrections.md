I went through it. Short version: what passed the OpenEnv hackathon was the **DocEdit Game V2 environment**, not the later trained Qwen model.

The submitted project was [attempt1/doc_edit_game_v2](/Users/sanju/Desktop/coding/python/open-env-meta/attempt1/doc_edit_game_v2/README.md), deployed as HF Space `sanjuhs/doc_edit_v5`. It passed because it satisfied the OpenEnv gates:

1. **HF Space existed and ran**: final target was `https://sanjuhs-doc-edit-v5.hf.space`.
2. **OpenEnv spec**: [openenv.yaml](/Users/sanju/Desktop/coding/python/open-env-meta/attempt1/doc_edit_game_v2/openenv.yaml:1), typed `DocEditAction` / `DocEditObservation`, FastAPI mounted OpenEnv endpoints in [server/app.py](/Users/sanju/Desktop/coding/python/open-env-meta/attempt1/doc_edit_game_v2/server/app.py:29).
3. **Docker build path**: [server/Dockerfile](/Users/sanju/Desktop/coding/python/open-env-meta/attempt1/doc_edit_game_v2/server/Dockerfile:13) used the OpenEnv base image and ran the server.
4. **Baseline inference**: [inference.py](/Users/sanju/Desktop/coding/python/open-env-meta/attempt1/doc_edit_game_v2/inference.py:15) used the OpenAI client, read `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`, emitted `[START]`, `[STEP]`, `[END]`, and ran 5 fixed tasks.
5. **3+ graded tasks**: you actually had 5: `legal_easy`, `legal_medium`, `legal_hard`, `pharma_easy`, `pharma_hard` in [doc_edit_game_v2_environment.py](/Users/sanju/Desktop/coding/python/open-env-meta/attempt1/doc_edit_game_v2/server/doc_edit_game_v2_environment.py:24).

The “finally passed after many iterations” part seems to be these fixes:

- Switched from trying to pull/run the HF registry image to connecting directly to the live HF Space because the validator could not pull `registry.hf.space` cleanly.
- Made the Space/Docker path stable.
- Clamped scores away from exact `0.0` and `1.0` because the validator rejected boundary values.
- Kept the environment lightweight enough for the 2 vCPU / 8 GB RAM constraint.
- Framed the task as a real-world document editing environment, which matched the scoring weights: real-world utility, grader quality, environment design.

Important timeline: the later [training/FINAL_POSTMORTEM.md](/Users/sanju/Desktop/coding/python/open-env-meta/training/FINAL_POSTMORTEM.md:1) was dated **April 17, 2026**, after the hackathon deadline of **April 8, 2026**. That Qwen SFT + GRPO run proved the idea was trainable, but it was not the thing that made the OpenEnv submission pass.

For direction: I agree with your instinct. A pure “applicator model replaces frontier model” story is weaker now because frontier models have strong tool/function calling. OpenAI’s docs describe tool calling as a first-class way for models to call app-defined functions, and they recommend keeping tool sets small and evaluating accuracy as tools scale: [OpenAI function calling docs](https://platform.openai.com/docs/guides/function-calling/parallel-function-calling-and-structured-outputs).

So I’d make the next product a **DocEdit Workbench**:

1. **Frontier planner baseline**: frontier model emits compact edit plans/tool calls.
2. **Verifier + patch engine**: deterministic tools apply changes and score collateral damage.
3. **Small model only where it wins**: train Qwen-sized models to do chunk-level edit localization/parameterization, not broad planning.
4. **React app optional but useful**: not as a generic “look, training curves” page, but as a real evaluation cockpit: source vs target vs model output, tool trace, score, collateral damage, cost, latency, and replay.

For the small model, Qwen still makes sense as an experiment. Qwen2.5-1.5B-Instruct explicitly emphasizes structured output / JSON improvements, and Qwen3-1.7B emphasizes agent/tool capability: [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct), [Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B). But the bar should be: can it beat frontier-tool-calling on **cost, latency, privacy, or batch volume** while staying within acceptable accuracy?

My recommendation: build the next repo around **frontier planner + verifiable editor + optional distilled executor**. That is much stronger than betting the whole project on a tiny model being magically better.