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
        "code": r'''
import cadquery as cq

slot_count = 12
outer_radius = 60.0
inner_radius = 24.0
shaft_radius = 11.0
thickness = 8.0
tooth_length = 24.0
tooth_width = 10.0

ring = cq.Workplane("XY").circle(outer_radius).extrude(thickness).cut(
    cq.Workplane("XY").circle(inner_radius).extrude(thickness + 2).translate((0, 0, -1))
)

teeth = None
for index in range(slot_count):
    angle = 360.0 * index / slot_count
    tooth = (
        cq.Workplane("XY")
        .center(inner_radius + tooth_length / 2, 0)
        .rect(tooth_length, tooth_width)
        .extrude(thickness)
        .rotate((0, 0, 0), (0, 0, 1), angle)
    )
    teeth = tooth if teeth is None else teeth.union(tooth)

shaft_hole = cq.Workplane("XY").circle(shaft_radius).extrude(thickness + 2).translate((0, 0, -1))
fixture = ring.union(teeth).cut(shaft_hole).clean()
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
      #viewer { min-height: 410px; background: #eff4f7; }
      .viewer-foot {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1px;
        background: rgba(255,255,255,0.18);
      }
      .metric { background: rgba(9, 33, 45, 0.82); padding: 12px; }
      .metric span { display: block; color: #aee1ef; font-size: 12px; font-weight: 800; text-transform: uppercase; }
      .metric strong { display: block; margin-top: 4px; font-size: 22px; }
      .band { padding: 36px 34px; }
      .band h2 { font-size: 34px; margin: 0 0 12px; color: #142532; }
      .band p { color: #526170; line-height: 1.55; }
      .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }
      .card {
        border: 1px solid #dbe4ea;
        border-radius: 8px;
        background: #fff;
        padding: 18px;
      }
      .card h3 { margin: 0 0 8px; color: #17202a; }
      .card p { margin: 0; }
      .results { background: #ffffff; border-top: 1px solid #dde5eb; border-bottom: 1px solid #dde5eb; }
      table { width: 100%; border-collapse: collapse; margin-top: 18px; background: #fff; border: 1px solid #dbe4ea; border-radius: 8px; overflow: hidden; }
      th, td { padding: 12px 14px; border-bottom: 1px solid #edf1f4; text-align: left; }
      th { color: #35566b; font-size: 13px; text-transform: uppercase; }
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
        .viewer-foot { grid-template-columns: repeat(2, minmax(0, 1fr)); }
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
          <a class="button" href="https://github.com/sanjuhs/open-env-meta-final-hackathon" target="_blank">Training code</a>
        </div>
      </div>
      <div class="viewer-panel" id="demo">
        <div class="viewer-head">
          <div>
            <h2 id="viewerTitle">Buildable CAD preview</h2>
            <p id="viewerStatus">Choose a task and score it through the same CadQuery reward backend used for GRPO.</p>
          </div>
          <div class="demo-controls">
            <select id="taskSelect">
              <option value="caster_wheel_fork">Caster wheel fork</option>
              <option value="axial_motor_stator_12_slot">12-slot motor stator</option>
            </select>
            <button class="light-button" id="runDemo">Run verifier</button>
          </div>
        </div>
        <div id="viewer"></div>
        <div class="viewer-foot">
          <div class="metric"><span>build</span><strong id="buildMetric">--</strong></div>
          <div class="metric"><span>reward</span><strong id="rewardMetric">--</strong></div>
          <div class="metric"><span>editability</span><strong id="editMetric">--</strong></div>
          <div class="metric"><span>semantic</span><strong id="semanticMetric">--</strong></div>
        </div>
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
      <p>The final strict run trained from the 9B SFT checkpoint on a RunPod H200 with TRL GRPO and real CADForge reward calls.</p>
      <table>
        <thead><tr><th>Run</th><th>Result</th></tr></thead>
        <tbody>
          <tr><td>Qwen3.5-2B SFT</td><td>train loss 1.4480 to 0.1658, eval loss 0.4477 to 0.2676</td></tr>
          <tr><td>Qwen3.5-9B SFT</td><td>train loss 2.6020 to 0.1413, eval loss 0.3650 to 0.2398</td></tr>
          <tr><td>Qwen3.5-9B strict GRPO</td><td>320 completions, 96 buildable, best CADForge score 0.9352</td></tr>
          <tr><td>Held-out eval</td><td>2 of 3 generated CADQuery files built successfully</td></tr>
        </tbody>
      </table>
    </section>

    <section class="band">
      <h2>Theme alignment</h2>
      <div class="grid">
        <div class="card"><h3>Long-horizon planning</h3><p>CAD is built through repeated code edits, reward observations, and repairs rather than one-shot text generation.</p></div>
        <div class="card"><h3>Professional world modeling</h3><p>The agent interacts with real CadQuery execution, STL export, mesh checks, reference metrics, and persistent state.</p></div>
        <div class="card"><h3>Self-improvement</h3><p>The curriculum adapts to model failures: build errors and weak semantics become the next tasks the model must learn to repair.</p></div>
      </div>
      <pre id="rewardJson">Reward JSON will appear here after the verifier runs.</pre>
    </section>

    <footer class="footer">
      <strong>CADForge</strong> trains LLMs to generate parametric CAD that compiles, edits, exports, and improves under reward feedback.
    </footer>

    <script type="module">
      import * as THREE from "https://unpkg.com/three@0.181.2/build/three.module.js";
      import { OrbitControls } from "https://unpkg.com/three@0.181.2/examples/jsm/controls/OrbitControls.js";
      import { STLLoader } from "https://unpkg.com/three@0.181.2/examples/jsm/loaders/STLLoader.js";

      const viewer = document.querySelector("#viewer");
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xeff4f7);
      const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000);
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
        camera.position.set(center.x + maxDim * 1.25, center.y - maxDim * 1.55, center.z + maxDim * 1.05);
        controls.target.copy(center);
        controls.update();
      }

      async function runDemo() {
        const taskId = document.querySelector("#taskSelect").value;
        document.querySelector("#viewerStatus").textContent = "Running CadQuery build and reward...";
        const response = await fetch("/api/space/demo", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ task_id: taskId })
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          document.querySelector("#viewerStatus").textContent = payload.error || "CadQuery build failed.";
          document.querySelector("#rewardJson").textContent = JSON.stringify(payload, null, 2);
          return;
        }
        document.querySelector("#viewerTitle").textContent = payload.label;
        document.querySelector("#viewerStatus").textContent = "Built and scored by CADForge in " + payload.elapsed_ms + " ms.";
        document.querySelector("#buildMetric").textContent = Number(payload.reward.build || 0).toFixed(1);
        document.querySelector("#rewardMetric").textContent = Number(payload.reward.total || 0).toFixed(3);
        document.querySelector("#editMetric").textContent = Number(payload.reward.editability || 0).toFixed(3);
        document.querySelector("#semanticMetric").textContent = Number(payload.reward.semantic_parts || 0).toFixed(3);
        document.querySelector("#rewardJson").textContent = JSON.stringify(payload, null, 2);

        const geometry = await new STLLoader().loadAsync(payload.stl_url + "?t=" + Date.now());
        geometry.computeVertexNormals();
        if (mesh) scene.remove(mesh);
        mesh = new THREE.Mesh(
          geometry,
          new THREE.MeshStandardMaterial({ color: taskId.includes("stator") ? 0x7f8c8d : 0x3c8dbc, roughness: 0.58, metalness: 0.45 })
        );
        scene.add(mesh);
        frameObject(mesh);
      }

      document.querySelector("#runDemo").addEventListener("click", runDemo);
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
    stl_path = artifact_dir / "candidate_normalized.stl"
    if not stl_path.exists():
        stl_path = artifact_dir / "candidate.stl"
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


@app.get("/api/space/stl/{task_id}")
def get_space_stl(task_id: str) -> FileResponse:
    safe_task = _safe_task_id(task_id)
    artifact_dir = _artifact_dir(safe_task)
    stl_path = artifact_dir / "candidate_normalized.stl"
    if not stl_path.exists():
        stl_path = artifact_dir / "candidate.stl"
    if not stl_path.exists():
        raise HTTPException(status_code=404, detail="Run the demo verifier first.")
    return FileResponse(stl_path, media_type="model/stl", filename=f"{safe_task}.stl")


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
