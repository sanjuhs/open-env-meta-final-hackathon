#!/usr/bin/env node

import { createWriteStream, mkdirSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { pipeline } from "node:stream/promises";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const appRoot = path.join(repoRoot, "experiment-2-cadforge");
const requireFromApp = createRequire(path.join(appRoot, "package.json"));
const dotenv = requireFromApp("dotenv");
const { default: OpenAI } = requireFromApp("openai");

dotenv.config({ path: path.join(repoRoot, ".env") });
dotenv.config({ path: path.join(appRoot, ".env") });

const args = process.argv.slice(2);
const tasksPath = valueArg("--tasks") || path.join(appRoot, "data", "cad_tasks.json");
const outRoot = valueArg("--out") || path.join(appRoot, "data", "generated-assets");
const limit = Number(valueArg("--limit") || 0);
const concurrency = Number(valueArg("--concurrency") || 3);
const startAt = Number(valueArg("--start-at") || 0);
const imageModel = valueArg("--image-model") || "gpt-image-2";
const falModel = valueArg("--fal-model") || "fal-ai/sam-3/3d-objects";
const skipImages = args.includes("--skip-images");
const skipGlb = args.includes("--skip-glb");
const forceRegenerateImages = args.includes("--force-images");
const exportTexturedGlb = !args.includes("--no-textured-glb");
const samPromptOverride = valueArg("--sam-prompt");

function valueArg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : "";
}

function taskSlice(tasks) {
  const sliced = tasks.slice(startAt);
  return limit > 0 ? sliced.slice(0, limit) : sliced;
}

async function mapLimit(items, count, fn) {
  const results = [];
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const index = next++;
      try {
        results[index] = await fn(items[index], index);
      } catch (error) {
        results[index] = { error };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.max(1, count) }, worker));
  return results;
}

async function writeImage(task, taskDir) {
  const imagePath = path.join(taskDir, "reference.png");
  if (skipImages) return imagePath;
  if (!forceRegenerateImages && fileExists(imagePath)) return imagePath;
  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  if (!process.env.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is required for image generation.");
  const response = await client.images.generate({
    model: imageModel,
    prompt: `${task.image_prompt}\n\nEngineering object only, plain white background, realistic material, no labels, no text, no watermark.`,
    size: "1024x1024",
    quality: "low",
    n: 1,
  });
  const b64 = response.data?.[0]?.b64_json;
  if (!b64) throw new Error(`No image data returned for ${task.id}`);
  writeFileSync(imagePath, Buffer.from(b64, "base64"));
  return imagePath;
}

function fileExists(filePath) {
  try {
    readFileSync(filePath);
    return true;
  } catch {
    return false;
  }
}

async function download(url, destination) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Download failed ${response.status}: ${url}`);
  await pipeline(response.body, createWriteStream(destination));
}

function glbUrlFromFal(data) {
  return (
    data?.model_glb?.url ||
    data?.individual_glbs?.[0]?.url ||
    data?.model_mesh?.url ||
    data?.model_urls?.glb?.url ||
    data?.model_urls?.base_model?.url ||
    data?.model_urls?.pbr_model?.url
  );
}

async function writeGlb(task, taskDir, imagePath) {
  const glbPath = path.join(taskDir, "reference.glb");
  if (skipGlb) return glbPath;
  const falKey = process.env.FAL_KEY || process.env.FAL_AI_API_KEY;
  if (!falKey) throw new Error("FAL_KEY or FAL_AI_API_KEY is required for FAL GLB generation.");
  const { fal } = await import(requireFromApp.resolve("@fal-ai/client"));
  fal.config({ credentials: falKey });

  const bytes = readFileSync(imagePath);
  const file = new File([bytes], `${task.id}.png`, { type: "image/png" });
  const imageUrl = await fal.storage.upload(file);
  const prompts = [...new Set([samPrompt(task), "object", ""].filter((item) => item !== undefined))];
  let result;
  let input;
  let lastError;
  for (const prompt of prompts) {
    input = {
      image_url: imageUrl,
      ...(prompt ? { prompt } : {}),
      ...(exportTexturedGlb ? { export_textured_glb: true } : {}),
    };
    try {
      result = await fal.subscribe(falModel, { input, logs: true });
      break;
    } catch (error) {
      lastError = error;
      const message = JSON.stringify(error.body || error.message || "");
      if (!message.includes("Auto-segmentation produced no masks") && error.status !== 502) {
        throw error;
      }
      console.error(`[asset retry] ${task.id}: ${prompt || "whole image"} failed, trying fallback`);
    }
  }
  if (!result) throw lastError;
  const url = glbUrlFromFal(result.data);
  if (!url) throw new Error(`No GLB URL returned for ${task.id}: ${JSON.stringify(result.data)}`);
  await download(url, glbPath);
  writeFileSync(path.join(taskDir, "fal-result.json"), JSON.stringify({ requestId: result.requestId, model: falModel, input: { ...input, image_url: "[uploaded]" }, data: result.data }, null, 2));
  return glbPath;
}

function samPrompt(task) {
  if (samPromptOverride) return samPromptOverride;
  const labels = {
    table_six_leg_500n: "table",
    four_leg_chair_700n: "chair",
    wall_j_hook_120n: "aluminum wall mounted J hook",
    shelf_bracket_triangular_200n: "aluminum triangular shelf bracket",
    drawer_handle_two_bolt: "brushed aluminum drawer handle",
    caster_wheel_fork: "metal caster wheel assembly",
    bike_accessory_mount_120n: "aluminum bicycle accessory clamp mount",
    shaft_torque_clamp_120nm: "aluminum shaft torque clamp fixture",
    axial_motor_stator_12_slot: "steel circular motor stator ring",
    lightweight_truss_support_250n: "aluminum triangular truss support bracket",
    phone_stand_adjustable_hinge: "phone stand",
    robot_servo_bracket: "servo bracket",
    ergonomic_curvy_chair_1000n: "chair",
    folding_step_stool: "step stool",
    bench_vise_simplified: "bench vise",
    micro_drone_frame: "black carbon fiber micro drone frame",
    gearbox_housing_split: "gearbox housing",
    bottle_cage_bike: "bicycle water bottle cage",
    laptop_riser_vented: "laptop stand",
    pipe_clamp_saddle: "metal pipe clamp saddle",
    hinge_leaf_barrel: "door hinge",
    cable_clip_snap: "plastic snap in cable clip",
    desk_lamp_arm_joint: "adjustable metal desk lamp arm joint",
    robot_gripper_two_finger: "two finger robot gripper",
  };
  return labels[task.id] || task.family?.replace(/_/g, " ") || task.prompt.slice(0, 120);
}

async function main() {
  const tasks = taskSlice(JSON.parse(readFileSync(tasksPath, "utf8")));
  mkdirSync(outRoot, { recursive: true });
  const manifest = [];
  await mapLimit(tasks, concurrency, async (task) => {
    const taskDir = path.join(outRoot, task.id);
    mkdirSync(taskDir, { recursive: true });
    writeFileSync(path.join(taskDir, "task.json"), JSON.stringify(task, null, 2));
    console.log(`[asset] ${task.id}`);
    try {
      const imagePath = await writeImage(task, taskDir);
      const glbPath = await writeGlb(task, taskDir, imagePath);
      removeIfExists(path.join(taskDir, "error.json"));
      manifest.push({ id: task.id, level: task.level, family: task.family, ok: true, taskPath: path.join(taskDir, "task.json"), imagePath, glbPath });
    } catch (error) {
      const failure = {
        id: task.id,
        level: task.level,
        family: task.family,
        ok: false,
        error: error.message,
        status: error.status,
        requestId: error.requestId,
        body: error.body,
      };
      writeFileSync(path.join(taskDir, "error.json"), JSON.stringify(failure, null, 2));
      manifest.push(failure);
      console.error(`[asset failed] ${task.id}: ${error.message}`);
      if (error.body) console.error(JSON.stringify(error.body));
    }
    writeFileSync(path.join(outRoot, "manifest.json"), JSON.stringify(manifest, null, 2));
  });
  console.log(JSON.stringify({ outRoot, count: manifest.length, ok: manifest.filter((item) => item.ok).length, manifest: path.join(outRoot, "manifest.json") }, null, 2));
}

function removeIfExists(filePath) {
  try {
    unlinkSync(filePath);
  } catch {
    // Fine: stale failure file did not exist.
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
