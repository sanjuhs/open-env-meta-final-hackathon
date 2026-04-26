from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from openenv.core.env_server.http_server import create_app

from cadquery_env import APP_ROOT, evaluate_code, read_task_spec

from .cadforge_environment import CadForgeCadQueryEnvironment
from .openenv_models import CadForgeAction, CadForgeObservation


app = create_app(
    CadForgeCadQueryEnvironment,
    CadForgeAction,
    CadForgeObservation,
    env_name="cadforge_cadquery",
    max_concurrent_envs=4,
)


DEMO_TASKS = {
    "caster_wheel_fork": {
        "label": "Caster wheel fork",
        "prompt": "Design a small caster wheel assembly as editable code-CAD. Include a wheel, axle, U-shaped fork, swivel stem, and top mounting plate with four holes.",
        "broken_code": r'''
import cadquery as cq

# Weak seed: buildable blank plate with almost no requested assembly detail.
plate = cq.Workplane("XY").box(44, 44, 4).translate((0, 0, 2))
fixture = plate.clean()
'''.strip(),
        "code": r'''
import cadquery as cq

plate_w = 44.0
plate_d = 44.0
plate_t = 4.0
stem_d = 10.0
stem_h = 16.0
fork_inside_w = 22.0
fork_leg_t = 4.0
fork_leg_depth = 18.0
fork_leg_h = 24.0
wheel_d = 22.0
wheel_w = 10.0
axle_d = 4.2

def make_top_plate():
    plate = cq.Workplane("XY").box(plate_w, plate_d, plate_t).translate((0, 0, plate_t / 2))
    holes = (
        cq.Workplane("XY")
        .pushPoints([(-14, -14), (-14, 14), (14, -14), (14, 14)])
        .circle(2.1)
        .extrude(plate_t + 2)
        .translate((0, 0, -1))
    )
    return plate.cut(holes)

def make_fork():
    left_x = -(fork_inside_w / 2 + fork_leg_t / 2)
    right_x = fork_inside_w / 2 + fork_leg_t / 2
    left_leg = cq.Workplane("XY").box(fork_leg_t, fork_leg_depth, fork_leg_h).translate((left_x, 0, plate_t + fork_leg_h / 2 - 1))
    right_leg = cq.Workplane("XY").box(fork_leg_t, fork_leg_depth, fork_leg_h).translate((right_x, 0, plate_t + fork_leg_h / 2 - 1))
    bridge = cq.Workplane("XY").box(fork_inside_w + 2 * fork_leg_t, fork_leg_depth, 4).translate((0, 0, plate_t + 1.5))
    return left_leg.union(right_leg).union(bridge)

plate = make_top_plate()
stem = cq.Workplane("XY").cylinder(stem_h, stem_d / 2).translate((0, 0, plate_t + stem_h / 2 - 0.5))
fork = make_fork()
wheel = cq.Workplane("XY").cylinder(wheel_w, wheel_d / 2).cut(cq.Workplane("XY").cylinder(wheel_w + 2, 2.5)).translate((0, 0, 18))
axle = cq.Workplane("XY").cylinder(fork_inside_w + 3, axle_d / 2).translate((0, 0, 18))
fixture = plate.union(stem).union(fork).union(wheel).union(axle).clean()
'''.strip(),
    },
    "axial_motor_stator_12_slot": {
        "label": "12-slot motor stator",
        "prompt": "Design a simple 12-slot axial motor stator concept with a circular ring, radial teeth, and center shaft opening.",
        "broken_code": r'''
import cadquery as cq

# Weak seed: buildable disk with a center bore, but no teeth or slot structure.
outer_radius = 60.0
shaft_radius = 12.0
thickness = 8.0
disk = cq.Workplane("XY").circle(outer_radius).extrude(thickness)
bore = cq.Workplane("XY").circle(shaft_radius).extrude(thickness + 2).translate((0, 0, -1))
fixture = disk.cut(bore).clean()
'''.strip(),
        "code": r'''
import cadquery as cq

# Editable axial motor stator concept with twelve radial teeth and center bore.
stator_slot_count = 12
stator_outer_radius = 60.0
stator_inner_radius = 24.0
stator_shaft_radius = 11.0
stator_thickness = 8.0
radial_tooth_length = 28.0
radial_tooth_width = 10.0
back_iron_width = stator_outer_radius - stator_inner_radius

def make_stator_ring():
    outer = cq.Workplane("XY").circle(stator_outer_radius).extrude(stator_thickness)
    inner_cut = cq.Workplane("XY").circle(stator_inner_radius).extrude(stator_thickness + 2).translate((0, 0, -1))
    return outer.cut(inner_cut)

def make_radial_tooth(index):
    angle = 360.0 * index / stator_slot_count
    tooth_center = stator_inner_radius + radial_tooth_length / 2.0
    tooth = (
        cq.Workplane("XY")
        .center(tooth_center, 0)
        .rect(radial_tooth_length, radial_tooth_width)
        .extrude(stator_thickness + 1.0)
    )
    root_pad = (
        cq.Workplane("XY")
        .center(stator_inner_radius + 2.0, 0)
        .rect(8.0, radial_tooth_width + 4.0)
        .extrude(stator_thickness + 1.0)
    )
    return tooth.union(root_pad).rotate((0, 0, 0), (0, 0, 1), angle)

def make_twelve_slot_tooth_set():
    teeth = None
    for tooth_index in range(stator_slot_count):
        radial_tooth = make_radial_tooth(tooth_index)
        teeth = radial_tooth if teeth is None else teeth.union(radial_tooth)
    return teeth

stator_ring = make_stator_ring()
twelve_radial_teeth = make_twelve_slot_tooth_set()
center_shaft_opening = cq.Workplane("XY").circle(stator_shaft_radius).extrude(stator_thickness + 4).translate((0, 0, -2))
fixture = stator_ring.union(twelve_radial_teeth).cut(center_shaft_opening).clean()
'''.strip(),
    },
}


SPACE_HTML = r'''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CADForge RLVE</title>
    <style>
      :root {
        color-scheme: light;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f5f7fb;
        color: #17202a;
      }
      * { box-sizing: border-box; }
      body { margin: 0; }
      a { color: inherit; }
      .hero {
        min-height: 78vh;
        display: grid;
        grid-template-columns: minmax(320px, 0.9fr) minmax(420px, 1.1fr);
        gap: 28px;
        align-items: stretch;
        padding: 34px;
        background:
          linear-gradient(120deg, rgba(15, 57, 77, 0.92), rgba(16, 86, 93, 0.80)),
          radial-gradient(circle at 80% 20%, rgba(255,255,255,0.18), transparent 34%),
          #0e3446;
        color: #f8fbfd;
      }
      .hero-copy { display: flex; flex-direction: column; justify-content: center; max-width: 760px; }
      .eyebrow { margin: 0 0 10px; color: #aee1ef; font-weight: 800; font-size: 12px; text-transform: uppercase; letter-spacing: 0; }
      h1 { margin: 0; font-size: clamp(42px, 7vw, 88px); line-height: 0.94; letter-spacing: 0; }
      .lede { max-width: 680px; color: #d8e9ef; font-size: 19px; line-height: 1.55; margin: 22px 0 0; }
      .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 26px; }
      .button {
        border: 1px solid rgba(255,255,255,0.34);
        border-radius: 8px;
        padding: 11px 14px;
        background: rgba(255,255,255,0.12);
        color: #fff;
        text-decoration: none;
        font-weight: 800;
        cursor: pointer;
      }
      .button.primary { background: #e5f6ff; color: #0d3446; border-color: #e5f6ff; }
      .viewer-panel {
        min-height: 520px;
        display: grid;
        grid-template-rows: auto 1fr auto;
        border: 1px solid rgba(255,255,255,0.20);
        border-radius: 8px;
        overflow: hidden;
        background: rgba(255,255,255,0.10);
        box-shadow: 0 22px 80px rgba(0,0,0,0.25);
      }
      .viewer-head {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid rgba(255,255,255,0.16);
      }
      .viewer-head h2 { margin: 0; font-size: 22px; }
      .viewer-head p { margin: 5px 0 0; color: #cee4ec; }
      #viewer { min-height: 410px; background: #eff4f7; position: relative; }
      .viewer-foot {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1px;
        background: rgba(255,255,255,0.18);
      }
      .metric { background: rgba(9, 33, 45, 0.82); padding: 12px; }
      .metric span { display: block; color: #aee1ef; font-size: 12px; font-weight: 800; text-transform: uppercase; }
      .metric strong { display: block; margin-top: 4px; font-size: 22px; }
      .trace-strip {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        padding: 12px 16px 16px;
        background: rgba(9, 33, 45, 0.82);
        border-top: 1px solid rgba(255,255,255,0.16);
      }
      .trace-item {
        border: 1px solid rgba(174, 225, 239, 0.30);
        border-radius: 8px;
        padding: 10px;
        color: #d8f3fb;
      }
      .trace-item strong { display: block; color: #fff; margin-bottom: 4px; }
      .trace-item span { color: #aee1ef; font-size: 13px; }
      .viewer-legend {
        position: absolute;
        display: flex;
        gap: 10px;
        left: 14px;
        top: 14px;
        z-index: 2;
        color: #173040;
        font-size: 12px;
        font-weight: 800;
      }
      .viewer-legend span {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 8px;
        border-radius: 8px;
        background: rgba(255,255,255,0.82);
        box-shadow: 0 8px 24px rgba(16, 39, 54, 0.12);
      }
      .swatch { width: 10px; height: 10px; border-radius: 999px; display: inline-block; }
      .seed-dot { background: #d65b5b; }
      .repair-dot { background: #2a9d8f; }
      .band { padding: 36px 34px; }
      .band h2 { font-size: 34px; margin: 0 0 12px; color: #142532; }
      .band p { color: #526170; line-height: 1.55; }
      .repro-banner {
        margin: 0;
        padding: 28px 34px;
        background: #eef8ff;
        border-top: 4px solid #164f73;
        border-bottom: 4px solid #164f73;
        color: #102633;
      }
      .repro-banner h2 {
        margin: 0 0 12px;
        font-size: clamp(30px, 4vw, 52px);
        color: #102633;
      }
      .repro-banner p {
        max-width: 1180px;
        margin: 0 0 16px;
        color: #304b5e;
        font-size: 20px;
        line-height: 1.45;
      }
      .repro-links {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .repro-link {
        display: inline-flex;
        align-items: center;
        min-height: 44px;
        border: 1px solid #164f73;
        border-radius: 8px;
        padding: 10px 12px;
        background: #ffffff;
        color: #0d3446;
        font-weight: 900;
        text-decoration: none;
      }
      .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }
      .card {
        border: 1px solid #dbe4ea;
        border-radius: 8px;
        background: #fff;
        padding: 18px;
      }
      .card h3 { margin: 0 0 8px; color: #17202a; }
      .card p { margin: 0; }
      .model-callout {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        margin-top: 18px;
        border: 1px solid #b9d8c3;
        border-radius: 8px;
        background: #eef9f1;
        padding: 16px;
      }
      .model-callout strong { color: #173b27; }
      .model-callout p { margin: 4px 0 0; color: #395747; }
      .model-link {
        display: inline-flex;
        align-items: center;
        min-height: 44px;
        border: 1px solid #2f8f46;
        border-radius: 8px;
        padding: 10px 12px;
        background: #2f8f46;
        color: #fff;
        font-weight: 900;
        text-decoration: none;
      }
      .results { background: #ffffff; border-top: 1px solid #dde5eb; border-bottom: 1px solid #dde5eb; }
      table { width: 100%; border-collapse: collapse; margin-top: 18px; background: #fff; border: 1px solid #dbe4ea; border-radius: 8px; overflow: hidden; }
      th, td { padding: 12px 14px; border-bottom: 1px solid #edf1f4; text-align: left; }
      th { color: #35566b; font-size: 13px; text-transform: uppercase; }
      td:first-child { font-weight: 800; color: #162a38; }
      .api-list {
        display: grid;
        gap: 10px;
        margin-top: 18px;
      }
      .api-row {
        display: grid;
        grid-template-columns: minmax(180px, 260px) minmax(0, 1fr);
        gap: 12px;
        border: 1px solid #dbe4ea;
        border-radius: 8px;
        background: #fff;
        padding: 12px;
      }
      .api-row code {
        color: #0f5f78;
        font-weight: 900;
        overflow-wrap: anywhere;
      }
      .api-row span { color: #526170; }
      .demo-controls { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
      select {
        border: 1px solid #c9d5df;
        border-radius: 8px;
        padding: 10px 12px;
        background: #fff;
      }
      .light-button {
        border: 1px solid #164f73;
        border-radius: 8px;
        padding: 10px 12px;
        background: #164f73;
        color: #fff;
        font-weight: 800;
        cursor: pointer;
      }
      pre {
        white-space: pre-wrap;
        background: #102633;
        color: #d8f3fb;
        border-radius: 8px;
        padding: 14px;
        overflow: auto;
      }
      .footer { padding: 26px 34px 38px; color: #53616e; }
      @media (max-width: 920px) {
        .hero { grid-template-columns: 1fr; padding: 22px; }
        .grid { grid-template-columns: 1fr; }
        .api-row { grid-template-columns: 1fr; }
        table { display: block; overflow-x: auto; }
        .viewer-foot { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .trace-strip { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">OpenEnv + CadQuery + GRPO</p>
        <h1>CADForge RLVE</h1>
        <p class="lede">Frontier models can describe CAD, but tiny models often fail at executable, editable CADQuery. CADForge turns that gap into an RL environment: write code, compile real geometry, receive reward, repair, and improve.</p>
        <div class="actions">
          <a class="button primary" href="#demo">Run CAD demo</a>
          <a class="button" href="https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/CADFORGE_BLOG.md" target="_blank">Read mini-blog</a>
          <a class="button" href="https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/docs/detailed-blog/cadforge-detailed-blog.md" target="_blank">Detailed blog</a>
          <a class="button" href="https://github.com/sanjuhs/open-env-meta-final-hackathon" target="_blank">Training code</a>
          <a class="button" href="https://gist.github.com/sanjuhs/10596f688e8b4560910a3b1b137bfeeb" target="_blank">Training scripts Gist</a>
          <a class="button" href="https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence" target="_blank">Training logs</a>
          <a class="button" href="https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora" target="_blank">Best trained model</a>
        </div>
      </div>
      <div class="viewer-panel" id="demo">
        <div class="viewer-head">
          <div>
            <h2 id="viewerTitle">Buildable CAD preview</h2>
            <p id="viewerStatus">Choose a task. CADForge will score a weak seed, repair it, verify it, and render the improved STL.</p>
          </div>
          <div class="demo-controls">
            <select id="taskSelect">
              <option value="caster_wheel_fork">Caster wheel fork</option>
              <option value="axial_motor_stator_12_slot">12-slot motor stator</option>
            </select>
            <button class="light-button" id="runDemo">Run repair loop</button>
          </div>
        </div>
        <div id="viewer">
          <div class="viewer-legend">
            <span><i class="swatch seed-dot"></i> weak seed</span>
            <span><i class="swatch repair-dot"></i> repaired CAD</span>
          </div>
        </div>
        <div class="trace-strip" id="traceStrip">
          <div class="trace-item"><strong>Step 0</strong><span>Waiting for weak seed.</span></div>
          <div class="trace-item"><strong>Step 1</strong><span>Waiting for repaired CAD.</span></div>
        </div>
        <div class="viewer-foot">
          <div class="metric"><span>build</span><strong id="buildMetric">--</strong></div>
          <div class="metric"><span>reward</span><strong id="rewardMetric">--</strong></div>
          <div class="metric"><span>editability</span><strong id="editMetric">--</strong></div>
          <div class="metric"><span>semantic</span><strong id="semanticMetric">--</strong></div>
        </div>
      </div>
    </section>

    <section class="repro-banner">
      <h2>Judge rerun links</h2>
      <p>The full CADForge SFT and GRPO runs were executed on a RunPod H200 as distinct production scripts. The Colab notebook is the public smoke path: it validates OpenEnv, loads the public dataset, runs the real CadQuery reward backend, and launches tiny SFT/GRPO checks with the same source files.</p>
      <div class="repro-links">
        <a class="repro-link" href="https://github.com/sanjuhs/open-env-meta-final-hackathon" target="_blank">GitHub repo</a>
        <a class="repro-link" href="https://colab.research.google.com/github/sanjuhs/open-env-meta-final-hackathon/blob/main/training/cadforge_openenv_training_colab.ipynb" target="_blank">Open Colab notebook</a>
        <a class="repro-link" href="https://gist.github.com/sanjuhs/10596f688e8b4560910a3b1b137bfeeb" target="_blank">Training scripts Gist</a>
        <a class="repro-link" href="https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence" target="_blank">HF logs + evidence</a>
      </div>
    </section>

    <section class="band">
      <h2>The environment fights back</h2>
      <p>CADForge is not a static benchmark. The first dense GRPO run exposed a reward flaw: the model could receive partial reward while still failing to build. The environment adapted. Buildability became the first gate, failed code became negative reward, and each failure type became a curriculum target.</p>
      <div class="grid">
        <div class="card"><h3>1. Observe failure</h3><p>SyntaxError, missing fixture, invented API, disconnected parts, clipped final union, weak semantic match.</p></div>
        <div class="card"><h3>2. Generate curriculum</h3><p>Failed trajectories become new repair tasks: fix one concrete CAD failure and improve the reward delta.</p></div>
        <div class="card"><h3>3. Train harder rollouts</h3><p>GRPO groups compare buildable vs broken candidates, giving the model clean advantage signals.</p></div>
      </div>
    </section>

    <section class="band results">
      <h2>Real training evidence</h2>
      <p>We ran seven distinct training experiments on RunPod H200. The important story is not just that loss went down; it is that the environment exposed reward hacking, then build-gated GRPO and adaptive repair made buildable CAD separate from broken code.</p>
      <table>
        <thead><tr><th>Run</th><th>What happened</th><th>Lesson</th></tr></thead>
        <tbody>
          <tr><td>1. Qwen3.5-2B SFT</td><td>train loss 1.4480 to 0.1658; eval loss 0.4477 to 0.2676</td><td>2B learned CadQuery grammar and trace format.</td></tr>
          <tr><td>2. Qwen3.5-2B dense GRPO</td><td>160 completions; 0.0% build rate; mean/best reward 0.3387 / 0.5303</td><td>Reward was learnable, but too hackable without a hard build gate.</td></tr>
          <tr><td>3. Qwen3.5-9B SFT</td><td>train loss 2.6020 to 0.1413; eval loss 0.3650 to 0.2398</td><td>9B learned syntax and structure faster than 2B.</td></tr>
          <tr><td>4. Qwen3.5-9B dense GRPO</td><td>160 completions; 0.0% build rate; mean/best reward 0.4355 / 0.6828</td><td>Bigger model got higher scalar reward while still failing buildability.</td></tr>
          <tr><td>5. Qwen3.5-9B strict GRPO</td><td>320 completions; 96 buildable; best CADForge score 0.9352</td><td>Buildability-first reward produced the first real breakthrough.</td></tr>
          <tr><td>6. Adaptive repair v1</td><td>120 repair completions; 0 buildable; clipped-output pattern exposed</td><td>The environment found a curriculum/completion-length bug.</td></tr>
          <tr><td>7. Adaptive repair final 8192</td><td>180 repair completions; 53 buildable; 0 clipped completions; best reward 0.882</td><td>Failure mining plus longer completions recovered buildable repairs.</td></tr>
        </tbody>
      </table>
      <div class="model-callout">
        <div>
          <strong>Best downloadable model adapter</strong>
          <p>Use the final Qwen3.5-9B adaptive-repair LoRA to test CADQuery generation and repair locally or on a GPU notebook.</p>
        </div>
        <a class="model-link" href="https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora" target="_blank">Download best model</a>
      </div>
      <p>Held-out eval after strict GRPO built 2 of 3 generated CadQuery files successfully. The remaining failed chair case clipped before the final assembly, which directly motivated the adaptive repair run.</p>
    </section>

    <section class="band">
      <h2>Reward hacking and reward design</h2>
      <p>CADForge started with dense rewards for code shape, semantic words, topology, contact, reference similarity, and editability. Training showed a classic reward-hacking pattern: models could earn positive-looking reward while still producing non-buildable CAD. The fix was to make buildability the first gate.</p>
      <div class="grid">
        <div class="card"><h3>What was hackable</h3><p>Dense reward gave partial credit for code-like text, named parts, and semantic hints even when CadQuery failed to export an STL.</p></div>
        <div class="card"><h3>What fixed it</h3><p>Strict GRPO makes failed builds negative. Dense topology, semantic, contact, reference, and editability scores unlock only after the CAD builds.</p></div>
        <div class="card"><h3>Step rewards</h3><p>Each action returns reward JSON: build, topology, contact, semantic parts, reference similarity, editability, efficiency, and verifier notes.</p></div>
      </div>
      <pre>{
  "build": 1.0,
  "topology": 0.82,
  "contact": 0.74,
  "semantic_parts": 0.61,
  "reference_similarity": 0.58,
  "editability": 0.80,
  "total": 0.86,
  "notes": ["candidate builds", "recognizable task parts", "clean fixture"]
}</pre>
    </section>

    <section class="band results">
      <h2>Space APIs</h2>
      <p>The Space is both a demo and an OpenEnv-style reward service. A model can submit CadQuery code, receive structured observations, and use those step rewards for SFT data generation, GRPO rollouts, or human-readable debugging.</p>
      <div class="api-list">
        <div class="api-row"><code>GET /healthz</code><span>Health check for the CADForge Space.</span></div>
        <div class="api-row"><code>POST /api/space/repair-loop</code><span>Runs the demo loop: weak seed, repaired CAD, CadQuery build, reward JSON, and STL artifact URLs.</span></div>
        <div class="api-row"><code>POST /api/space/demo</code><span>Scores a known buildable candidate and returns reward dimensions plus artifact paths.</span></div>
        <div class="api-row"><code>GET /api/space/loop-stl/{task_id}</code><span>Downloads the repaired STL from the most recent repair-loop run.</span></div>
        <div class="api-row"><code>GET /api/space/loop-stl/{task_id}/{step_id}</code><span>Downloads a specific weak-seed or repaired-step STL for visual comparison.</span></div>
        <div class="api-row"><code>OpenEnv step route</code><span>The OpenEnv server wraps complete CadQuery Python files as actions and returns observations with reward JSON and verifier notes.</span></div>
      </div>
    </section>

    <section class="band">
      <h2>Theme alignment</h2>
      <div class="grid">
        <div class="card"><h3>Long-horizon planning</h3><p>CAD is built through repeated code edits, reward observations, and repairs rather than one-shot text generation.</p></div>
        <div class="card"><h3>Professional world modeling</h3><p>The agent interacts with real CadQuery execution, STL export, mesh checks, reference metrics, and persistent state.</p></div>
        <div class="card"><h3>Self-improvement</h3><p>The curriculum adapts to model failures: build errors and weak semantics become the next tasks the model must learn to repair.</p></div>
      </div>
      <pre id="rewardJson">Reward JSON will appear here after the repair loop runs.</pre>
    </section>

    <footer class="footer">
      <strong>CADForge</strong> trains LLMs to generate parametric CAD that compiles, edits, exports, and improves under reward feedback.
    </footer>

    <script type="importmap">
      {
        "imports": {
          "three": "https://unpkg.com/three@0.181.2/build/three.module.js",
          "three/addons/": "https://unpkg.com/three@0.181.2/examples/jsm/"
        }
      }
    </script>
    <script type="module">
      import * as THREE from "three";
      import { OrbitControls } from "three/addons/controls/OrbitControls.js";
      import { STLLoader } from "three/addons/loaders/STLLoader.js";

      const viewer = document.querySelector("#viewer");
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xeff4f7);
        const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100000);
      camera.position.set(180, -220, 170);
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      viewer.appendChild(renderer.domElement);
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      scene.add(new THREE.HemisphereLight(0xffffff, 0x8aa0aa, 2.2));
      const key = new THREE.DirectionalLight(0xffffff, 2.6);
      key.position.set(180, -220, 260);
      scene.add(key);
      const grid = new THREE.GridHelper(260, 12, 0xb7c5cc, 0xd6e0e5);
      grid.rotation.x = Math.PI / 2;
      scene.add(grid);
      let mesh = null;
      let currentRun = 0;

      function resize() {
        const box = viewer.getBoundingClientRect();
        renderer.setSize(box.width, box.height);
        camera.aspect = box.width / Math.max(1, box.height);
        camera.updateProjectionMatrix();
      }
      window.addEventListener("resize", resize);
      resize();

      function frameObject(object) {
        const box = new THREE.Box3().setFromObject(object);
        const size = new THREE.Vector3();
        const center = new THREE.Vector3();
        box.getSize(size);
        box.getCenter(center);
        const maxDim = Math.max(size.x, size.y, size.z, 1);
        camera.near = Math.max(0.1, maxDim / 5000);
        camera.far = Math.max(5000, maxDim * 10);
        camera.position.set(center.x + maxDim * 1.25, center.y - maxDim * 1.55, center.z + maxDim * 1.05);
        camera.updateProjectionMatrix();
        controls.target.copy(center);
        controls.update();
      }

      async function runDemo() {
        const runId = ++currentRun;
        const taskId = document.querySelector("#taskSelect").value;
        clearViewer();
        document.querySelector("#buildMetric").textContent = "--";
        document.querySelector("#rewardMetric").textContent = "--";
        document.querySelector("#editMetric").textContent = "--";
        document.querySelector("#semanticMetric").textContent = "--";
        document.querySelector("#runDemo").disabled = true;
        document.querySelector("#viewerStatus").textContent = "Running weak seed, repair, CadQuery build, and reward...";
        document.querySelector("#traceStrip").innerHTML = `
          <div class="trace-item"><strong>Step 0</strong><span>Evaluating weak seed...</span></div>
          <div class="trace-item"><strong>Step 1</strong><span>Waiting for repaired CAD...</span></div>
        `;
        let payload = {};
        try {
          const response = await fetch("/api/space/repair-loop", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ task_id: taskId })
          });
          payload = await response.json();
          if (runId !== currentRun) return;
          if (!response.ok || !payload.ok) {
            document.querySelector("#viewerStatus").textContent = payload.error || "CadQuery build failed.";
            if (payload.steps) updateTrace(payload.steps);
            document.querySelector("#rewardJson").textContent = JSON.stringify(payload, null, 2);
            return;
          }
        } finally {
          if (runId === currentRun) document.querySelector("#runDemo").disabled = false;
        }
        document.querySelector("#viewerTitle").textContent = payload.label;
        document.querySelector("#viewerStatus").textContent = "Repair loop complete. Reward delta: " + Number(payload.delta_reward || 0).toFixed(3) + ".";
        updateTrace(payload.steps || []);
        document.querySelector("#buildMetric").textContent = Number(payload.final.reward.build || 0).toFixed(1);
        document.querySelector("#rewardMetric").textContent = Number(payload.final.reward.total || 0).toFixed(3);
        document.querySelector("#editMetric").textContent = Number(payload.final.reward.editability || 0).toFixed(3);
        document.querySelector("#semanticMetric").textContent = Number(payload.final.reward.semantic_parts || 0).toFixed(3);
        document.querySelector("#rewardJson").textContent = JSON.stringify(payload, null, 2);

        await renderMeshes(payload, taskId, runId);
      }

      function clearViewer() {
        if (mesh) {
          scene.remove(mesh);
          mesh.traverse((child) => {
            if (child.geometry) child.geometry.dispose();
            if (child.material) child.material.dispose();
          });
          mesh = null;
        }
      }

      async function renderMeshes(payload, taskId, runId) {
        clearViewer();
        const group = new THREE.Group();
        const loader = new STLLoader();
        const geometries = [];
        if (payload.seed && payload.seed.stl_url && payload.steps && payload.steps[0] && payload.steps[0].build > 0) {
          const seedGeometry = await loader.loadAsync(payload.seed.stl_url + "?t=" + Date.now());
          if (runId !== currentRun) return;
          seedGeometry.computeVertexNormals();
          seedGeometry.computeBoundingBox();
          geometries.push(seedGeometry);
          const seedMesh = new THREE.Mesh(
            seedGeometry,
            new THREE.MeshStandardMaterial({ color: 0xd65b5b, roughness: 0.72, metalness: 0.20, transparent: true, opacity: 0.64 })
          );
          group.add(seedMesh);
        }
        const finalGeometry = await loader.loadAsync(payload.final.stl_url + "?t=" + Date.now());
        if (runId !== currentRun) return;
        finalGeometry.computeVertexNormals();
        finalGeometry.computeBoundingBox();
        geometries.push(finalGeometry);
        const finalMesh = new THREE.Mesh(
          finalGeometry,
          new THREE.MeshStandardMaterial({ color: taskId.includes("stator") ? 0x2f80ed : 0x2a9d8f, roughness: 0.48, metalness: 0.50 })
        );
        group.add(finalMesh);
        const maxDim = Math.max(...geometries.map((geometry) => {
          const size = new THREE.Vector3();
          geometry.boundingBox.getSize(size);
          return Math.max(size.x, size.y, size.z, 1);
        }));
        group.children.forEach((child, index) => {
          child.geometry.center();
          child.position.x = group.children.length > 1 ? (index === 0 ? -maxDim * 0.68 : maxDim * 0.68) : 0;
        });
        mesh = group;
        scene.add(mesh);
        frameObject(mesh);
      }

      function updateTrace(steps) {
        document.querySelector("#traceStrip").innerHTML = steps.map((step, index) => `
          <div class="trace-item">
            <strong>Step ${index}: ${step.name || "candidate"}</strong>
            <span>build ${Number(step.build || 0).toFixed(1)} · reward ${Number(step.reward || 0).toFixed(3)} · ${step.summary || ""}</span>
          </div>
        `).join("");
      }

      document.querySelector("#runDemo").addEventListener("click", runDemo);
      document.querySelector("#taskSelect").addEventListener("change", runDemo);
      runDemo();
      renderer.setAnimationLoop(() => {
        controls.update();
        renderer.render(scene, camera);
      });
    </script>
  </body>
</html>
'''


def _safe_task_id(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in {"_", "-"}).strip() or "caster_wheel_fork"


def _artifact_dir(task_id: str) -> Path:
    return APP_ROOT / "runs" / "cadquery-env" / f"space-demo-{_safe_task_id(task_id)}" / "sample"


def _loop_artifact_dir(task_id: str, step_id: str) -> Path:
    return APP_ROOT / "runs" / "cadquery-env" / f"space-loop-{_safe_task_id(task_id)}" / _safe_task_id(step_id)


def _stl_path(artifact_dir: Path) -> Path:
    stl_path = artifact_dir / "candidate_normalized.stl"
    if not stl_path.exists():
        stl_path = artifact_dir / "candidate.stl"
    return stl_path


def _step_summary(result: dict, fallback: str) -> str:
    notes = result.get("notes")
    if isinstance(notes, list) and notes:
        return str(notes[0])[:140]
    error = result.get("error")
    if error:
        return str(error)[:140]
    return fallback


def _step_payload(name: str, result: dict, fallback: str) -> dict:
    reward = result.get("reward", {}) if isinstance(result.get("reward"), dict) else {}
    return {
        "name": name,
        "ok": bool(result.get("ok")),
        "build": float(reward.get("build", 0.0) or 0.0),
        "reward": float(reward.get("total", 0.0) or 0.0),
        "editability": float(reward.get("editability", 0.0) or 0.0),
        "semantic_parts": float(reward.get("semantic_parts", 0.0) or 0.0),
        "summary": _step_summary(result, fallback),
    }


@app.get("/", response_class=HTMLResponse)
@app.get("/web", response_class=HTMLResponse)
def space_home() -> HTMLResponse:
    return HTMLResponse(SPACE_HTML)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"ok": "true", "env": "cadforge_cadquery"}


@app.post("/api/space/demo")
async def run_space_demo(request: Request) -> JSONResponse:
    payload = await request.json()
    task_id = _safe_task_id(str(payload.get("task_id") or "caster_wheel_fork"))
    demo = DEMO_TASKS.get(task_id) or DEMO_TASKS["caster_wheel_fork"]
    task_spec = read_task_spec(task_id) or {"id": task_id, "prompt": demo["prompt"]}
    reference_root = APP_ROOT / "data" / "reference-metrics" / task_id
    result = evaluate_code(
        demo["code"],
        f"space-demo-{task_id}",
        "sample",
        task_prompt=str(task_spec.get("prompt") or demo["prompt"]),
        reference_root=reference_root,
        reward_mode="fast",
        task_spec=task_spec,
    )
    reward = result.get("reward", {})
    artifact_dir = Path(str(result.get("artifacts_dir") or _artifact_dir(task_id)))
    stl_path = _stl_path(artifact_dir)
    if not result.get("ok") or not stl_path.exists():
        return JSONResponse(
            {
                "ok": False,
                "task_id": task_id,
                "label": demo["label"],
                "error": result.get("error", "CadQuery build failed"),
                "notes": result.get("notes", []),
                "reward": reward,
            },
            status_code=500,
        )
    return JSONResponse(
        {
            "ok": True,
            "task_id": task_id,
            "label": demo["label"],
            "prompt": demo["prompt"],
            "reward": reward,
            "notes": result.get("notes", []),
            "elapsed_ms": result.get("elapsed_ms", 0),
            "stl_url": f"/api/space/stl/{task_id}",
            "artifacts_dir": result.get("artifacts_dir"),
        }
    )


@app.post("/api/space/repair-loop")
async def run_space_repair_loop(request: Request) -> JSONResponse:
    payload = await request.json()
    task_id = _safe_task_id(str(payload.get("task_id") or "caster_wheel_fork"))
    demo = DEMO_TASKS.get(task_id) or DEMO_TASKS["caster_wheel_fork"]
    task_spec = read_task_spec(task_id) or {"id": task_id, "prompt": demo["prompt"]}
    task_prompt = str(task_spec.get("prompt") or demo["prompt"])
    reference_root = APP_ROOT / "data" / "reference-metrics" / task_id
    broken = evaluate_code(
        demo["broken_code"],
        f"space-loop-{task_id}",
        "broken",
        task_prompt=task_prompt,
        reference_root=reference_root,
        reward_mode="fast",
        task_spec=task_spec,
    )
    repaired = evaluate_code(
        demo["code"],
        f"space-loop-{task_id}",
        "repaired",
        task_prompt=task_prompt,
        reference_root=reference_root,
        reward_mode="fast",
        task_spec=task_spec,
    )
    repaired_reward = repaired.get("reward", {}) if isinstance(repaired.get("reward"), dict) else {}
    broken_reward = broken.get("reward", {}) if isinstance(broken.get("reward"), dict) else {}
    artifact_dir = Path(str(repaired.get("artifacts_dir") or _loop_artifact_dir(task_id, "repaired")))
    stl_path = _stl_path(artifact_dir)
    steps = [
        _step_payload("weak seed", broken, "CADForge scores the weak first attempt before repair."),
        _step_payload("repaired CAD", repaired, "The repaired candidate is rebuilt and rescored."),
    ]
    if not repaired.get("ok") or not stl_path.exists():
        return JSONResponse(
            {
                "ok": False,
                "task_id": task_id,
                "label": demo["label"],
                "prompt": demo["prompt"],
                "steps": steps,
                "error": repaired.get("error", "Repaired CadQuery build failed"),
                "final": {"reward": repaired_reward},
            },
            status_code=500,
        )
    return JSONResponse(
        {
            "ok": True,
            "task_id": task_id,
            "label": demo["label"],
            "prompt": demo["prompt"],
            "delta_reward": float(repaired_reward.get("total", 0.0) or 0.0)
            - float(broken_reward.get("total", 0.0) or 0.0),
            "steps": steps,
            "seed": {
                "reward": broken_reward,
                "notes": broken.get("notes", []),
                "elapsed_ms": broken.get("elapsed_ms", 0),
                "stl_url": f"/api/space/loop-stl/{task_id}/broken",
                "artifacts_dir": broken.get("artifacts_dir"),
            },
            "final": {
                "reward": repaired_reward,
                "notes": repaired.get("notes", []),
                "elapsed_ms": repaired.get("elapsed_ms", 0),
                "stl_url": f"/api/space/loop-stl/{task_id}",
                "artifacts_dir": repaired.get("artifacts_dir"),
            },
        }
    )


@app.get("/api/space/stl/{task_id}")
def get_space_stl(task_id: str) -> FileResponse:
    safe_task = _safe_task_id(task_id)
    artifact_dir = _artifact_dir(safe_task)
    stl_path = _stl_path(artifact_dir)
    if not stl_path.exists():
        raise HTTPException(status_code=404, detail="Run the demo verifier first.")
    return FileResponse(stl_path, media_type="model/stl", filename=f"{safe_task}.stl")


@app.get("/api/space/loop-stl/{task_id}")
def get_space_loop_stl(task_id: str) -> FileResponse:
    safe_task = _safe_task_id(task_id)
    stl_path = _stl_path(_loop_artifact_dir(safe_task, "repaired"))
    if not stl_path.exists():
        raise HTTPException(status_code=404, detail="Run the repair loop first.")
    return FileResponse(stl_path, media_type="model/stl", filename=f"{safe_task}-repaired.stl")


@app.get("/api/space/loop-stl/{task_id}/{step_id}")
def get_space_loop_step_stl(task_id: str, step_id: str) -> FileResponse:
    safe_task = _safe_task_id(task_id)
    safe_step = _safe_task_id(step_id)
    stl_path = _stl_path(_loop_artifact_dir(safe_task, safe_step))
    if not stl_path.exists():
        raise HTTPException(status_code=404, detail="Run the repair loop first.")
    return FileResponse(stl_path, media_type="model/stl", filename=f"{safe_task}-{safe_step}.stl")


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.port == 8000:
        main()
    else:
        main(port=args.port)
