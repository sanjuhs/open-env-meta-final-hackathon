#!/usr/bin/env node

import { spawn } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const appRoot = path.join(repoRoot, "experiment-2-cadforge");
const tasksPath = valueArg("--tasks") || path.join(appRoot, "data", "cad_tasks.json");
const outPath = valueArg("--out") || path.join(appRoot, "reports", "teacher-trace-batch.json");
const provider = valueArg("--provider") || "openai";
const model = valueArg("--model") || "gpt-5.4";
const steps = valueArg("--steps") || "3";
const limit = Number(valueArg("--limit") || 0);
const concurrency = Number(valueArg("--concurrency") || 1);
const seeds = (valueArg("--seeds") || "weak").split(",").map((item) => item.trim()).filter(Boolean);
const promptSuffix = valueArg("--prompt-suffix");
const levels = new Set((valueArg("--levels") || "easy,medium,hard").split(",").map((item) => item.trim()).filter(Boolean));
const vision = process.argv.includes("--vision");

function valueArg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : "";
}

function selectTasks() {
  let tasks = JSON.parse(readFileSync(tasksPath, "utf8")).filter((task) => levels.has(task.level));
  if (limit > 0) tasks = tasks.slice(0, limit);
  return tasks;
}

function runTask(task, seedKind) {
  const referenceRoot = path.join(appRoot, "runs", "cadquery-task-references", task.id);
  const args = [
    path.join(repoRoot, "scripts", "experiment-2", "run-cadquery-agentic-trace.js"),
    "--provider",
    provider,
    "--model",
    model,
    "--steps",
    steps,
    "--task-id",
    task.id,
    "--seed-kind",
    seedKind,
    "--task-spec",
    task.id,
    "--reference-root",
    referenceRoot,
    "--timeout-ms",
    "300000",
  ];
  if (promptSuffix) args.push("--prompt-suffix", promptSuffix);
  if (vision) args.push("--vision");
  return new Promise((resolve) => {
    const child = spawn(args[0], args.slice(1), {
      cwd: repoRoot,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      stderr += "\nTimed out after 900000ms.";
    }, 900000);
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("close", (status) => {
      clearTimeout(timer);
      resolve({
        task_id: task.id,
        seed_kind: seedKind,
        ok: status === 0,
        stdout,
        stderr,
        status,
      });
    });
  });
}

async function mapLimit(items, count, fn) {
  const results = [];
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const index = next++;
      results[index] = await fn(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.max(1, count) }, worker));
  return results;
}

async function main() {
  const tasks = selectTasks();
  const jobs = [];
  for (const task of tasks) {
    for (const seed of seeds) jobs.push({ task, seed });
  }
  mkdirSync(path.dirname(outPath), { recursive: true });
  const results = [];
  await mapLimit(jobs, concurrency, async ({ task, seed }) => {
    console.log(`[trace] ${task.id} / ${seed}`);
    const result = await runTask(task, seed);
    results.push(result);
    writeFileSync(outPath, JSON.stringify({ provider, model, steps: Number(steps), vision, seeds, results }, null, 2));
    if (!result.ok) {
      console.error(`[trace failed] ${task.id} / ${seed}`);
      console.error(result.stderr || result.stdout);
    }
  });
  console.log(JSON.stringify({ outPath, count: results.length, ok: results.filter((item) => item.ok).length }, null, 2));
}

main();
