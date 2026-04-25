#!/usr/bin/env node

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const appRoot = path.join(repoRoot, "experiment-2-cadforge");
const input = valueArg("--input") || path.join(appRoot, "data", "sft", "cadquery_agentic_sft.jsonl");
const output = valueArg("--output") || path.join(appRoot, "data", "sft", "cadquery_agentic_sft_positive.jsonl");
const minAfter = Number(valueArg("--min-after") || 0.70);
const minDelta = Number(valueArg("--min-delta") || 0.001);

function valueArg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : "";
}

function main() {
  const rows = readFileSync(input, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
  const filtered = rows.filter((row) => {
    const after = Number(row.reward_after ?? -1);
    const delta = Number(row.reward_delta ?? 0);
    return after >= minAfter && delta >= minDelta;
  });
  mkdirSync(path.dirname(output), { recursive: true });
  writeFileSync(output, filtered.map((row) => JSON.stringify(row)).join("\n") + (filtered.length ? "\n" : ""));
  console.log(JSON.stringify({ input, output, rows: rows.length, kept: filtered.length, minAfter, minDelta }, null, 2));
}

main();
