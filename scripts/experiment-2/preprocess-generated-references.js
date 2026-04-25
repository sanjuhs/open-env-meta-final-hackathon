#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const appRoot = path.join(repoRoot, "experiment-2-cadforge");
const tasksPath = valueArg("--tasks") || path.join(appRoot, "data", "cad_tasks.json");
const assetsRoot = valueArg("--assets") || path.join(appRoot, "data", "generated-assets");
const outRoot = valueArg("--out") || path.join(appRoot, "runs", "cadquery-task-references");
const limit = Number(valueArg("--limit") || 0);
const pythonBin = process.env.PYTHON_SIM_BIN || path.join(repoRoot, ".venv/bin/python");

function valueArg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : "";
}

function main() {
  let tasks = JSON.parse(readFileSync(tasksPath, "utf8"));
  if (limit > 0) tasks = tasks.slice(0, limit);
  mkdirSync(outRoot, { recursive: true });
  const results = [];
  for (const task of tasks) {
    const glbPath = path.join(assetsRoot, task.id, "reference.glb");
    if (!existsSync(glbPath)) {
      results.push({ id: task.id, ok: false, skipped: true, reason: "missing reference.glb" });
      continue;
    }
    const taskOut = path.join(outRoot, task.id);
    console.log(`[preprocess] ${task.id}`);
    const result = spawnSync(
      pythonBin,
      [
        path.join(appRoot, "python_tools", "cadquery_env.py"),
        "preprocess-reference",
        "--glb",
        glbPath,
        "--ideal-code",
        "",
        "--out-root",
        taskOut,
      ],
      { cwd: appRoot, encoding: "utf8", timeout: 300000 },
    );
    results.push({
      id: task.id,
      ok: result.status === 0,
      outRoot: taskOut,
      status: result.status,
      stderr: result.stderr,
      stdout: result.stdout,
    });
    if (result.status !== 0) {
      console.error(`[preprocess failed] ${task.id}`);
      console.error(result.stderr || result.stdout);
    }
  }
  const summaryPath = path.join(outRoot, "preprocess-summary.json");
  writeFileSync(summaryPath, JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ summaryPath, count: results.length, ok: results.filter((item) => item.ok).length }, null, 2));
}

main();
