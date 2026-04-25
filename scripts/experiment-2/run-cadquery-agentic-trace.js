#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const appRoot = path.join(repoRoot, "experiment-2-cadforge");
const requireFromApp = createRequire(path.join(appRoot, "package.json"));
const dotenv = requireFromApp("dotenv");
const { default: OpenAI } = requireFromApp("openai");

dotenv.config({ path: path.join(repoRoot, ".env") });
dotenv.config({ path: path.join(appRoot, ".env") });

const args = new Set(process.argv.slice(2));
const provider = valueArg("--provider") || "openai";
const model = valueArg("--model") || (provider === "ollama" ? "qwen3.5:0.8b" : "gpt-5.4");
const steps = Number(valueArg("--steps") || 4);
const taskId = valueArg("--task-id") || "markus-agentic-repair";
const seedKind = valueArg("--seed-kind") || "weak";
const timeoutMs = Number(valueArg("--timeout-ms") || 180000);
const useVision = args.has("--vision") && provider === "openai";
const fromTracePath = valueArg("--from-trace");
const taskSpecArg = valueArg("--task-spec");
const taskSpec = loadTaskSpec(taskSpecArg);
const referenceRoot = valueArg("--reference-root") || defaultReferenceRoot(taskSpec);
const promptSuffix = valueArg("--prompt-suffix");
const pythonBin = process.env.PYTHON_SIM_BIN || path.join(repoRoot, ".venv/bin/python");
const traceRoot = path.join(appRoot, "reports", "agentic-traces");
const dataRoot = path.join(appRoot, "data");
const runId = `${provider}-${model}-${taskId}-${seedKind}-${new Date().toISOString().replace(/[:.]/g, "-")}`.replace(/[^a-zA-Z0-9_.-]+/g, "-");
const runDir = path.join(traceRoot, runId);

const taskPrompt =
  [
    valueArg("--prompt") ||
      taskSpec?.prompt ||
      "Create an editable CadQuery model of an IKEA Markus-like office chair with a seat, tall backrest, headrest-like upper cushion, armrests, central gas cylinder, five-star base, and caster proxies. Improve the model step by step using verifier feedback.",
    promptSuffix,
  ]
    .filter(Boolean)
    .join("\n\n");

function valueArg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : "";
}

function loadTaskSpec(pathOrId) {
  if (!pathOrId) return null;
  const maybePath = path.isAbsolute(pathOrId) ? pathOrId : path.join(repoRoot, pathOrId);
  if (exists(maybePath)) return JSON.parse(readFileSync(maybePath, "utf8"));
  const tasksPath = path.join(appRoot, "data", "cad_tasks.json");
  if (exists(tasksPath)) {
    const task = JSON.parse(readFileSync(tasksPath, "utf8")).find((item) => item.id === pathOrId);
    if (task) return task;
  }
  throw new Error(`Task spec not found: ${pathOrId}`);
}

function exists(filePath) {
  try {
    readFileSync(filePath);
    return true;
  } catch {
    return false;
  }
}

function defaultReferenceRoot(spec) {
  if (!spec?.id) return "";
  return path.join(appRoot, "runs", "cadquery-task-references", spec.id);
}

function extractCode(text) {
  let value = String(text || "").replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
  const match = value.match(/```(?:python|py)?\s*\n([\s\S]*?)```/i);
  value = (match ? match[1] : value).trim();
  return value.replace(/^```(?:python|py)?/i, "").replace(/```$/i, "").trim();
}

function seedCode() {
  if (seedKind === "build_error") {
    return [
      "import cadquery as cq",
      "",
      "# Intentional build failure seed: undefined dimensions and missing final fixture.",
      "base = cq.Workplane('XY').box(width_mm, depth_mm, thickness_mm)",
      "support = cq.Workplane('XY').cylinder(load_height, boss_radius).translate((60, 0, 30))",
      "result = base.union(support)",
    ].join("\n");
  }
  if (seedKind === "bad_dimensions") {
    return [
      "import cadquery as cq",
      "",
      "# Intentional bad-dimensions seed: builds, but proportions are wrong and required details are absent.",
      "tiny_plate = cq.Workplane('XY').box(60, 30, 12).translate((0, 0, 6))",
      "oversized_boss = cq.Workplane('XY').cylinder(260, 75).translate((0, 0, 140))",
      "fixture = tiny_plate.union(oversized_boss).clean()",
    ].join("\n");
  }
  if (seedKind === "disconnected") {
    return [
      "import cadquery as cq",
      "",
      "# Intentional disconnected seed: recognizable primitives float apart instead of forming one CAD assembly.",
      "base = cq.Workplane('XY').box(180, 80, 24).translate((0, 0, 12))",
      "left_part = cq.Workplane('XY').box(40, 40, 160).translate((-220, 0, 110))",
      "right_part = cq.Workplane('XY').cylinder(80, 32).translate((240, 0, 140))",
      "fixture = base.union(left_part).union(right_part).clean()",
    ].join("\n");
  }
  if (seedKind === "missing_features") {
    const hintComment = taskSpec?.semantic_hints?.slice(0, 3).join(", ") || "missing required features";
    return [
      "import cadquery as cq",
      "",
      `# Intentional missing-features seed: only starts ${hintComment}; many required task details are absent.`,
      "main_body_width = 180",
      "main_body_depth = 80",
      "main_body_height = 32",
      "main_body = cq.Workplane('XY').box(main_body_width, main_body_depth, main_body_height).translate((0, 0, main_body_height / 2))",
      "fixture = main_body.clean()",
    ].join("\n");
  }
  if (taskSpec?.family === "furniture") {
    return [
      "import cadquery as cq",
      "",
      "# Intentional weak furniture baseline: simple disconnected blocks with missing details.",
      "seat = cq.Workplane('XY').box(420, 420, 45).translate((0, 0, 450))",
      "back = cq.Workplane('XY').box(360, 35, 420).translate((0, -260, 720))",
      "leg = cq.Workplane('XY').box(35, 35, 420).translate((-170, -170, 220))",
      "fixture = seat.union(back).union(leg).clean()",
    ].join("\n");
  }
  if (taskSpec?.family === "electromechanical") {
    return [
      "import cadquery as cq",
      "",
      "# Intentional weak stator baseline: ring only, missing slots/teeth.",
      "outer = cq.Workplane('XY').circle(90).extrude(20)",
      "inner = cq.Workplane('XY').circle(35).extrude(24)",
      "fixture = outer.cut(inner).clean()",
    ].join("\n");
  }
  if (taskSpec) {
    return [
      "import cadquery as cq",
      "",
      "# Intentional weak mechanical baseline: blocky part with one boss and missing required details.",
      "base = cq.Workplane('XY').box(160, 60, 20).translate((0, 0, 10))",
      "boss = cq.Workplane('XY').cylinder(30, 24).translate((55, 0, 35))",
      "fixture = base.union(boss).clean()",
    ].join("\n");
  }
  return [
    "import cadquery as cq",
    "",
    "seat = cq.Workplane('XY').box(520, 480, 70).translate((0, 0, 450))",
    "# Intentional weak baseline: back is disconnected and many required details are missing.",
    "backrest = cq.Workplane('XY').box(440, 45, 720).translate((0, -360, 780))",
    "column = cq.Workplane('XY').cylinder(360, 28).translate((0, 0, 210))",
    "hub = cq.Workplane('XY').cylinder(55, 55).translate((0, 0, 55))",
    "fixture = seat.union(backrest).union(column).union(hub).clean()",
  ].join("\n");
}

function evaluate(code, episodeId, stepId, rewardMode = "full") {
  const result = spawnSync(
    pythonBin,
    [
      path.join(appRoot, "python_tools", "cadquery_env.py"),
      "evaluate",
      "--episode-id",
      episodeId,
      "--step-id",
      stepId,
      "--task-prompt",
      taskPrompt,
      "--reward-mode",
      rewardMode,
      ...(taskSpecArg ? ["--task-spec", taskSpecArg] : []),
      ...(referenceRoot ? ["--reference-root", referenceRoot] : []),
    ],
    {
      cwd: appRoot,
      input: JSON.stringify({ code }),
      encoding: "utf8",
      timeout: 240000,
      env: {
        ...process.env,
        PYTHONPATH: path.join(appRoot, "python_tools"),
        XDG_CACHE_HOME: process.env.XDG_CACHE_HOME || path.join(appRoot, ".cache"),
      },
    },
  );
  if (result.status !== 0) {
    throw new Error(`Evaluator failed: ${result.stderr || result.stdout}`);
  }
  const start = result.stdout.indexOf("{");
  const end = result.stdout.lastIndexOf("}");
  return JSON.parse(result.stdout.slice(start, end + 1));
}

function summarizeReward(evaluation) {
  return {
    total: evaluation.reward.total,
    build: evaluation.reward.build,
    topology: evaluation.reward.topology,
    contact: evaluation.reward.contact || 0,
    semantic_parts: evaluation.reward.semantic_parts,
    reference_similarity: evaluation.reward.reference_similarity,
    silhouette: evaluation.reward.silhouette,
    editability: evaluation.reward.editability,
    notes: evaluation.notes || [],
    artifacts_dir: evaluation.artifacts_dir,
    renders: evaluation.renders || {},
  };
}

function imageInputs(evaluation) {
  if (!useVision || !evaluation?.renders) return [];
  return ["isometric", "front", "left", "top"]
    .filter((view) => evaluation.renders[view])
    .map((view) => {
      const bytes = readFileSync(evaluation.renders[view]);
      return {
        type: "input_image",
        image_url: `data:image/png;base64,${bytes.toString("base64")}`,
      };
    });
}

function systemPrompt() {
  return [
    "You are CADForge, a careful CadQuery CAD repair agent.",
    "Return only a complete executable Python CadQuery file. Do not return markdown fences.",
    "Use `import cadquery as cq`.",
    "Assign the final exportable object to `fixture`.",
    "CadQuery does not have `cq.Box`, `cq.Cylinder`, `box(...)`, `cylinder(...)`, or `dimension(...)`; use `cq.Workplane('XY').box(x, y, z)` and `cq.Workplane('XY').cylinder(height, radius)`.",
    "Avoid loft(), sweep(), mirror(), fragile fillet/chamfer chains, file IO, network, subprocesses, and CQ-editor-only helpers.",
    "Make small, purposeful edits that improve the reward. Prefer named dimensions and helper functions.",
    "For disconnected chair parts, move/extend parts so major assemblies overlap or sit close enough to be intentional.",
  ].join("\n");
}

async function generateOpenAI(client, observation, currentCode, stepIndex) {
  const text = [
    `Task: ${taskPrompt}`,
    `Agentic step: ${stepIndex}`,
    `Current reward JSON:\n${JSON.stringify(summarizeReward(observation), null, 2)}`,
    `Current CadQuery code:\n${currentCode}`,
    "Revise the code to improve the reward. Focus on the biggest verifier failure first. Return only the complete updated Python file.",
  ].join("\n\n");

  const content = useVision
    ? [{ type: "input_text", text }, ...imageInputs(observation)]
    : text;

  const response = await client.responses.create({
    model,
    input: [
      { role: "system", content: systemPrompt() },
      { role: "user", content },
    ],
  });
  const raw = response.output_text || "";
  return { raw, code: extractCode(raw) };
}

async function generateOllama(observation, currentCode, stepIndex) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(process.env.OLLAMA_URL || "http://localhost:11434/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        model,
        stream: false,
        think: false,
        keep_alive: "10m",
        options: {
          temperature: 0.2,
          num_predict: 2000,
          num_ctx: 8192,
        },
        messages: [
          { role: "system", content: systemPrompt() },
          {
            role: "user",
            content: [
              `Task: ${taskPrompt}`,
              `Agentic step: ${stepIndex}`,
              `Current reward JSON:\n${JSON.stringify(summarizeReward(observation), null, 2)}`,
              `Current CadQuery code:\n${currentCode}`,
              "Revise the code to improve the reward. Return only the complete updated Python file.",
            ].join("\n\n"),
          },
        ],
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Ollama failed with status ${response.status}`);
    const raw = result.message?.content || result.response || result.message?.thinking || "";
    return { raw, code: extractCode(raw) };
  } finally {
    clearTimeout(timeout);
  }
}

function markdownForTrace(trace) {
  const lines = [
    "# CadQuery Agentic Trace",
    "",
    `- Provider: \`${provider}\``,
    `- Model: \`${model}\``,
    `- Vision: \`${useVision ? "yes" : "no"}\``,
    `- Task: ${taskPrompt}`,
    "",
  ];
  for (const step of trace.steps) {
    lines.push(`## Step ${step.step}`);
    lines.push("");
    lines.push(`- Previous reward: \`${step.before.reward.total.toFixed(3)}\``);
    lines.push(`- New reward: \`${step.after.reward.total.toFixed(3)}\``);
    lines.push(`- Reward delta: \`${(step.after.reward.total - step.before.reward.total).toFixed(3)}\``);
    lines.push(`- Before artifacts: \`${step.before.artifacts_dir}\``);
    lines.push(`- After artifacts: \`${step.after.artifacts_dir}\``);
    lines.push("");
    lines.push("Notes:");
    for (const note of step.after.notes || []) lines.push(`- ${note}`);
    lines.push("");
    lines.push("Rendered Views:");
    for (const [view, file] of Object.entries(step.after.renders || {})) {
      lines.push(`![step ${step.step} ${view}](${file})`);
    }
    lines.push("");
    lines.push("<details><summary>Updated CadQuery code</summary>");
    lines.push("");
    lines.push("```python");
    lines.push(step.action_code);
    lines.push("```");
    lines.push("");
    lines.push("</details>");
    lines.push("");
  }
  return lines.join("\n");
}

function appendTrainingData(trace) {
  const sftPath = path.join(dataRoot, "sft", "cadquery_agentic_sft.jsonl");
  const prefPath = path.join(dataRoot, "preferences", "cadquery_agentic_preferences.jsonl");
  const rolloutPath = path.join(dataRoot, "rl", "cadquery_rollouts.jsonl");
  mkdirSync(path.dirname(sftPath), { recursive: true });
  mkdirSync(path.dirname(prefPath), { recursive: true });
  mkdirSync(path.dirname(rolloutPath), { recursive: true });

  for (const step of trace.steps) {
    const observation = [
      `Task: ${trace.task_prompt}`,
      `Current reward JSON:\n${JSON.stringify(summarizeReward(step.before), null, 2)}`,
      `Current CadQuery code:\n${step.before_code}`,
      "Revise the code to improve the reward. Return only the complete updated Python file.",
    ].join("\n\n");
    appendFileSync(
      sftPath,
      `${JSON.stringify({
        messages: [
          { role: "system", content: systemPrompt() },
          { role: "user", content: observation },
          { role: "assistant", content: step.action_code },
        ],
        reward_before: step.before.reward.total,
        reward_after: step.after.reward.total,
        reward_delta: step.after.reward.total - step.before.reward.total,
        artifacts_dir: step.after.artifacts_dir,
      })}\n`,
    );

    appendFileSync(
      rolloutPath,
      `${JSON.stringify({
        task_id: trace.task_id || taskId,
        provider: trace.provider || provider,
        model: trace.model || model,
        step: step.step,
        observation,
        action: step.action_code,
        reward: step.after.reward.total,
        reward_delta: step.after.reward.total - step.before.reward.total,
        done: step.step === trace.steps.length,
        before_artifacts: step.before.artifacts_dir,
        after_artifacts: step.after.artifacts_dir,
      })}\n`,
    );

    const improved = step.after.reward.total >= step.before.reward.total;
    appendFileSync(
      prefPath,
      `${JSON.stringify({
        prompt: observation,
        chosen: improved ? step.action_code : step.before_code,
        rejected: improved ? step.before_code : step.action_code,
        chosen_reward: improved ? step.after.reward.total : step.before.reward.total,
        rejected_reward: improved ? step.before.reward.total : step.after.reward.total,
      })}\n`,
    );
  }
}

async function main() {
  if (fromTracePath) {
    const trace = JSON.parse(readFileSync(fromTracePath, "utf8"));
    appendTrainingData(trace);
    const mdPath = path.join(path.dirname(fromTracePath), "trace.md");
    writeFileSync(mdPath, markdownForTrace(trace));
    console.log(JSON.stringify({ tracePath: fromTracePath, mdPath, exportedTrainingRows: trace.steps.length }, null, 2));
    return;
  }

  mkdirSync(runDir, { recursive: true });
  const client = provider === "openai" ? new OpenAI({ apiKey: process.env.OPENAI_API_KEY }) : null;
  if (provider === "openai" && !process.env.OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY is required for OpenAI traces.");
  }

  let currentCode = seedCode();
  let before = evaluate(currentCode, runId, "seed", "full");
  const trace = {
    run_id: runId,
    provider,
    model,
    vision: useVision,
    task_id: taskId,
    seed_kind: seedKind,
    task_spec: taskSpec,
    task_prompt: taskPrompt,
    seed_code: currentCode,
    seed_reward: before.reward,
    steps: [],
  };

  for (let step = 1; step <= steps; step += 1) {
    const generation = provider === "openai"
      ? await generateOpenAI(client, before, currentCode, step)
      : await generateOllama(before, currentCode, step);
    const nextCode = generation.code;
    const after = evaluate(nextCode, runId, `step-${step}`, "full");
    trace.steps.push({
      step,
      before_code: currentCode,
      action_code: nextCode,
      raw_model_output: generation.raw,
      before,
      after,
    });
    currentCode = nextCode;
    before = after;
  }

  const tracePath = path.join(runDir, "trace.json");
  const mdPath = path.join(runDir, "trace.md");
  writeFileSync(tracePath, JSON.stringify(trace, null, 2));
  writeFileSync(mdPath, markdownForTrace(trace));
  appendTrainingData(trace);
  console.log(JSON.stringify({ runDir, tracePath, mdPath, steps: trace.steps.length, finalReward: before.reward.total }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
