#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
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
const runLive = args.has("--run");
const provider = valueArg("--provider") || "openai";
const model = valueArg("--model") || "gpt-5.5";
const attempts = Number(valueArg("--attempts") || 3);
const taskLimit = Number(valueArg("--tasks") || 5);
const generationTimeoutMs = Number(valueArg("--timeout-ms") || 180000);
const pythonBin = process.env.PYTHON_SIM_BIN || path.join(repoRoot, ".venv/bin/python");
const reportDir = path.join(appRoot, "reports");
const reportName = runLive
  ? `${provider}-${model}`.replace(/[^a-zA-Z0-9_.-]+/g, "-").replace(/^-|-$/g, "")
  : "dry-run";
const reportPath = path.join(reportDir, `${reportName}-cadquery-benchmark.md`);
const idealCodePath = path.join(repoRoot, "3d-models/ikea_markus_idealish_code.md");

const tasks = [
  {
    id: "markus-baseline",
    prompt:
      "Create an editable CadQuery model of an IKEA Markus-like office chair with a seat, tall mesh-style back, headrest-like upper cushion, armrests, gas cylinder, five-star base, and caster proxies."
  },
  {
    id: "taller-backrest",
    prompt:
      "Create a Markus-like CadQuery chair with a noticeably taller backrest while keeping the seat, armrests, gas cylinder, five-star base, and casters coherent."
  },
  {
    id: "thicker-armrests",
    prompt:
      "Create a Markus-like CadQuery chair with thicker, more visible armrests connected to the seat/back area, preserving an editable parametric structure."
  },
  {
    id: "wide-star-base",
    prompt:
      "Create a Markus-like CadQuery chair with a wider five-star rolling base and central gas cylinder, keeping the upper chair proportions close to the reference."
  },
  {
    id: "repair-floating-chair",
    prompt:
      "Repair a flawed Markus-like chair candidate so it has intentional subassemblies, recognizable chair parts, and stronger similarity to the ideal CadQuery reference."
  }
].slice(0, taskLimit);

function valueArg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : "";
}

function extractCode(text) {
  let value = String(text || "").replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
  const match = value.match(/```(?:python|py)?\s*\n([\s\S]*?)```/i);
  value = (match ? match[1] : value).trim();
  value = value.replace(/^```(?:python|py)?/i, "").replace(/```$/i, "").trim();
  return value;
}

function simpleCandidate() {
  return [
    "import cadquery as cq",
    "",
    "seat = cq.Workplane('XY').box(520, 480, 70).translate((0, 0, 450))",
    "back = cq.Workplane('XY').box(440, 45, 720).translate((0, -235, 760))",
    "column = cq.Workplane('XY').cylinder(360, 28).translate((0, 0, 210))",
    "base = cq.Workplane('XY').cylinder(55, 55).translate((0, 0, 55))",
    "fixture = seat.union(back).union(column).union(base).clean()"
  ].join("\n");
}

function evaluate(code, episodeId, stepId, taskPrompt) {
  const result = spawnSync(
    pythonBin,
    [
      path.join(appRoot, "python_tools/cadquery_env.py"),
      "evaluate",
      "--episode-id",
      episodeId,
      "--step-id",
      stepId,
      "--task-prompt",
      taskPrompt
    ],
    {
      cwd: appRoot,
      input: JSON.stringify({ code }),
      encoding: "utf8",
      timeout: 240000,
      env: {
        ...process.env,
        PYTHONPATH: path.join(appRoot, "python_tools"),
        XDG_CACHE_HOME: process.env.XDG_CACHE_HOME || path.join(appRoot, ".cache")
      }
    }
  );
  if (result.status !== 0) {
    throw new Error(`Evaluator failed: ${result.stderr || result.stdout}`);
  }
  const start = result.stdout.indexOf("{");
  const end = result.stdout.lastIndexOf("}");
  return JSON.parse(result.stdout.slice(start, end + 1));
}

async function generateWithModel(client, task, previousCode, previousEval, attemptIndex) {
  const feedback = previousEval
    ? [
        `Previous reward: ${previousEval.reward.total}`,
        `Reward breakdown: ${JSON.stringify(previousEval.reward)}`,
        `Verifier notes: ${previousEval.notes.join(" ")}`,
        `Previous code:\n${previousCode}`
      ].join("\n\n")
    : "No previous candidate. Start with a clean, editable parametric CadQuery model.";

  if (provider === "ollama") {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), generationTimeoutMs);
    try {
      const response = await fetch(process.env.OLLAMA_URL || "http://localhost:11434/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          model,
          stream: false,
          keep_alive: "10m",
          options: {
            temperature: 0.2,
            num_predict: 1800,
            num_ctx: 8192,
          },
          messages: [
            {
              role: "system",
              content: [
                "You are CADForge, a CadQuery CAD agent.",
                "Return only executable Python CadQuery code. Do not use markdown fences.",
                "Use import cadquery as cq. Assign the final object to fixture.",
                "CadQuery does not have cq.Box or cq.Cylinder constructors. Use cq.Workplane('XY').box(x, y, z) and cq.Workplane('XY').cylinder(height, radius).",
                "Prefer editable functions and named dimensions.",
                "Do not import filesystem, network, subprocess, or unsafe modules.",
                "Avoid loft(), sweep(), mirror(), fragile fillet/chamfer chains, complex sketches, and CQ-editor-only helpers.",
                "Build chairs from robust boxes, cylinders, simple extrusions, rotations, translations, and boolean unions so the code runs headlessly."
              ].join("\n")
            },
            {
              role: "user",
              content: [
                `Task ${task.id}, attempt ${attemptIndex + 1}: ${task.prompt}`,
                feedback,
                "Improve the model by editing the CadQuery code like a CAD REPL. Return the complete updated Python file only."
              ].join("\n\n")
            }
          ]
        })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || `Ollama failed with status ${response.status}`);
      return extractCode(result.message?.content || result.response || "");
    } finally {
      clearTimeout(timeout);
    }
  }

  const response = await client.responses.create({
    model,
    input: [
      {
        role: "system",
        content: [
          "You are CADForge, a CadQuery CAD agent.",
          "Return only executable Python CadQuery code.",
          "Use import cadquery as cq. Assign the final object to fixture, result, model, solid, body, part, or call show_object(obj).",
          "Prefer editable functions and named dimensions. You may use cq.Assembly if useful.",
          "Do not import filesystem, network, subprocess, or unsafe modules.",
          "For this benchmark, avoid loft(), sweep(), mirror(), fragile fillet/chamfer chains, complex sketches, and CQ-editor-only helpers.",
          "Build chairs from robust boxes, cylinders, simple extrusions, rotations, translations, and boolean unions so the code runs headlessly."
        ].join("\n")
      },
      {
        role: "user",
        content: [
          `Task ${task.id}, attempt ${attemptIndex + 1}: ${task.prompt}`,
          feedback,
          "Improve the model by editing the CadQuery code like a CAD REPL."
        ].join("\n\n")
      }
    ]
  });
  return extractCode(response.output_text || "");
}

function reportAttempt(task, attempt, result, code) {
  const renderImages = Object.entries(result.renders || {})
    .map(([view, file]) => `![${task.id} attempt ${attempt} ${view}](${file})`)
    .join("\n");
  return [
    `### Attempt ${attempt}`,
    "",
    `- Reward: \`${result.reward.total.toFixed(3)}\``,
    `- Build: \`${result.reward.build.toFixed(3)}\``,
    `- Topology: \`${result.reward.topology.toFixed(3)}\``,
    `- Contact/gaps: \`${(result.reward.contact ?? 0).toFixed(3)}\``,
    `- Semantic: \`${result.reward.semantic_parts.toFixed(3)}\``,
    `- Reference similarity: \`${result.reward.reference_similarity.toFixed(3)}\``,
    `- Silhouette: \`${result.reward.silhouette.toFixed(3)}\``,
    `- Editability: \`${result.reward.editability.toFixed(3)}\``,
    `- Artifacts: \`${result.artifacts_dir}\``,
    "",
    "Notes:",
    ...result.notes.map((note) => `- ${note}`),
    "",
    "Rendered Views:",
    renderImages || "- none",
    "",
    "<details><summary>CadQuery code</summary>",
    "",
    "```python",
    code,
    "```",
    "",
    "</details>",
    ""
  ].join("\n");
}

async function main() {
  mkdirSync(reportDir, { recursive: true });

  const client = runLive && provider !== "ollama" ? new OpenAI({ apiKey: process.env.OPENAI_API_KEY }) : null;
  if (runLive && provider !== "ollama" && !process.env.OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY is required for --run.");
  }

  const idealCode = extractCode(readFileSync(idealCodePath, "utf8"));
  const summaryRows = [];
  const sections = [];

  for (const task of tasks) {
    let previousCode = "";
    let previousEval = null;
    let best = null;
    const attemptsMarkdown = [];
    for (let i = 0; i < attempts; i += 1) {
      let code;
      if (runLive) {
        code = await generateWithModel(client, task, previousCode, previousEval, i);
      } else {
        code = i === 0 ? simpleCandidate() : idealCode;
      }
      const result = evaluate(code, `gpt-benchmark-${task.id}`, `attempt-${i + 1}`, task.prompt);
      previousCode = code;
      previousEval = result;
      if (!best || result.reward.total > best.reward.total) best = result;
      attemptsMarkdown.push(reportAttempt(task, i + 1, result, code));
    }
    summaryRows.push(
      `| ${task.id} | ${runLive ? `${provider}:${model}` : "dry-run"} | ${attempts} | ${best.reward.total.toFixed(3)} | ${best.reward.build.toFixed(2)} | ${best.reward.topology.toFixed(2)} | ${best.reward.reference_similarity.toFixed(2)} | ${best.reward.editability.toFixed(2)} | ${best.artifacts_dir} |`
    );
    sections.push([`## ${task.id}`, "", task.prompt, "", ...attemptsMarkdown].join("\n"));
  }

  const report = [
    "# GPT CadQuery Tool-Use Benchmark",
    "",
    runLive
      ? `Live benchmark run with \`${provider}:${model}\`.`
      : "Dry-run scaffold. Re-run with `--run` to call the OpenAI model.",
    "",
    "## Summary",
    "",
    "| Task | Model | Attempts | Best Reward | Build | Topology | Reference | Editability | Artifacts |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ...summaryRows,
    "",
    ...sections
  ].join("\n");

  writeFileSync(reportPath, report);
  console.log(JSON.stringify({ reportPath, runLive, provider, model, tasks: tasks.length, attempts }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
