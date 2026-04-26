import "./styles.css";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLExporter } from "three/examples/jsm/exporters/STLExporter.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { renderScadToGroup } from "./scadRenderer.js";

const app = document.querySelector("#app");
const route = window.location.pathname;
const detailedBlogUrl =
  "https://huggingface.co/spaces/sanjuhs/cadforge-cadquery-openenv/blob/main/docs/detailed-blog/cadforge-detailed-blog.md";
const bestModelUrl = "https://huggingface.co/sanjuhs/qwen35-9b-cadforge-grpo-adaptive-repair-lora";
const trainingLogsUrl = "https://huggingface.co/datasets/sanjuhs/cadforge-training-evidence";
const trainingGistUrl = "https://gist.github.com/sanjuhs/10596f688e8b4560910a3b1b137bfeeb";
const isLandingPage = route === "/" || route === "/index.html";
const isCadQueryGeneratorPage = route === "/cadquery";
const isCadQueryRendererPage = route === "/cadquery-renderer";
const isCadQueryEnvPage = route === "/cadquery-env";
const isCadQueryPage = isCadQueryGeneratorPage || isCadQueryRendererPage || isCadQueryEnvPage;
const isOpenScadPage = route === "/openscad" || (!isLandingPage && !isCadQueryPage);

app.innerHTML = `
  <main class="landing ${isLandingPage ? "" : "hidden"}">
    <section>
      <p class="eyebrow">CADForge Experiment 2</p>
      <h1>CAD workbench</h1>
      <p class="intro">Choose the code-CAD path to render and inspect. OpenSCAD is the agent loop; CadQuery is the real Python CAD backend for parametric mechanical parts.</p>
      <div class="route-grid">
        <a class="route-card" href="/openscad">
          <span>OpenSCAD</span>
          <strong>Markus chair agent</strong>
          <small>GPT-5.4 generates SCAD, renders the supported CSG subset, and iterates with topology feedback.</small>
        </a>
        <a class="route-card" href="/cadquery">
          <span>CadQuery</span>
          <strong>Python CAD generator</strong>
          <small>GPT-5.4 writes CadQuery, the backend exports STL, and the viewer inspects the generated mesh.</small>
        </a>
        <a class="route-card" href="/cadquery-renderer">
          <span>CadQuery</span>
          <strong>Renderer test bench</strong>
          <small>Run known-good CadQuery code through the backend to verify Python, CadQuery, STL export, and frontend rendering.</small>
        </a>
        <a class="route-card" href="/cadquery-env">
          <span>RLVE</span>
          <strong>Reward environment</strong>
          <small>Generate, revise, render, and score Markus-chair CadQuery candidates against the ideal code and GLB reference.</small>
        </a>
        <a class="route-card" href="${detailedBlogUrl}" target="_blank" rel="noreferrer">
          <span>Submission</span>
          <strong>Detailed blog</strong>
          <small>Read the full hackathon story: frontier model failures, reward design, SFT/GRPO evidence, and self-improvement loops.</small>
        </a>
        <a class="route-card" href="${bestModelUrl}" target="_blank" rel="noreferrer">
          <span>Model</span>
          <strong>Best trained LoRA</strong>
          <small>Download the final Qwen3.5-9B adaptive-repair adapter for CadQuery generation and repair tests.</small>
        </a>
      </div>

      <div class="evidence-panel">
        <div class="section-head">
          <p class="eyebrow">RunPod H200 evidence</p>
          <h2>Seven training runs</h2>
          <p class="intro">We did not just run one fine-tune. CADForge exposed reward hacking, then strict build-gated GRPO and adaptive repair improved buildable CAD behavior.</p>
        </div>
        <div class="evidence-actions">
          <a href="${bestModelUrl}" target="_blank" rel="noreferrer">Download best model</a>
          <a href="${trainingLogsUrl}" target="_blank" rel="noreferrer">Training logs</a>
          <a href="${trainingGistUrl}" target="_blank" rel="noreferrer">Training scripts Gist</a>
        </div>
        <table class="run-table">
          <thead><tr><th>Run</th><th>Result</th><th>Takeaway</th></tr></thead>
          <tbody>
            <tr><td>1. Qwen3.5-2B SFT</td><td>loss 1.4480 -> 0.1658; eval 0.4477 -> 0.2676</td><td>learned CadQuery grammar</td></tr>
            <tr><td>2. Qwen3.5-2B dense GRPO</td><td>160 completions; 0.0% builds; mean/best 0.3387 / 0.5303</td><td>reward signal existed, but was hackable</td></tr>
            <tr><td>3. Qwen3.5-9B SFT</td><td>loss 2.6020 -> 0.1413; eval 0.3650 -> 0.2398</td><td>larger model learned structure faster</td></tr>
            <tr><td>4. Qwen3.5-9B dense GRPO</td><td>160 completions; 0.0% builds; mean/best 0.4355 / 0.6828</td><td>higher reward still did not mean buildable CAD</td></tr>
            <tr><td>5. Qwen3.5-9B strict GRPO</td><td>320 completions; 96 buildable; best CADForge score 0.9352</td><td>build gate created the breakthrough</td></tr>
            <tr><td>6. Adaptive repair v1</td><td>120 repairs; 0 buildable; clipped completions surfaced</td><td>environment found a curriculum bug</td></tr>
            <tr><td>7. Adaptive repair final 8192</td><td>180 repairs; 53 buildable; 0 clipped; best reward 0.882</td><td>failure mining recovered buildable repairs</td></tr>
          </tbody>
        </table>
      </div>

      <div class="evidence-grid">
        <section class="evidence-card">
          <h2>Reward hacking lesson</h2>
          <p>Dense reward alone was too forgiving: models earned partial credit for code-shaped text and semantic words while failing to export CAD. The fix was strict build gating: failed builds stay negative, and topology/contact/semantic/reference/editability rewards unlock only after CadQuery exports geometry.</p>
        </section>
        <section class="evidence-card">
          <h2>Step reward API</h2>
          <p>The environment acts like a standard tool/reward loop. Each CadQuery action returns build status, reward dimensions, verifier notes, artifact paths, and STL renders. Those observations become SFT rows, GRPO rollouts, or human debugging traces.</p>
        </section>
        <section class="evidence-card">
          <h2>Space endpoints</h2>
          <p><code>POST /api/space/repair-loop</code> runs weak seed -> repair -> reward. <code>POST /api/space/demo</code> scores a buildable candidate. <code>GET /api/space/loop-stl/{task_id}</code> returns generated STL artifacts for visual comparison.</p>
        </section>
      </div>
    </section>
  </main>

  <main class="shell ${isLandingPage ? "hidden" : ""}">
    <section class="panel controls">
      <nav class="subnav">
        <a href="/">Home</a>
        <a class="${isOpenScadPage ? "active" : ""}" href="/openscad">OpenSCAD</a>
        <a class="${isCadQueryGeneratorPage ? "active" : ""}" href="/cadquery">CadQuery</a>
        <a class="${isCadQueryRendererPage ? "active" : ""}" href="/cadquery-renderer">Renderer</a>
        <a class="${isCadQueryEnvPage ? "active" : ""}" href="/cadquery-env">Env</a>
        <a href="${detailedBlogUrl}" target="_blank" rel="noreferrer">Detailed Blog</a>
        <a href="${bestModelUrl}" target="_blank" rel="noreferrer">Best Model</a>
      </nav>
      <div>
        <p class="eyebrow">CADForge Experiment 2</p>
        <h1>${isCadQueryEnvPage ? "CadQuery reward environment" : isCadQueryRendererPage ? "CadQuery renderer test bench" : isCadQueryGeneratorPage ? "CadQuery generator" : "Markus chair CAD generator"}</h1>
        <p class="intro">${isCadQueryEnvPage ? "Generate or revise CadQuery in a REPL loop, render the model, and score it against the ideal Markus CadQuery model plus the GLB reference." : isCadQueryRendererPage ? "Verify the real Python CadQuery backend, STL export path, and frontend mesh viewer with known-good code before testing generated CAD." : isCadQueryGeneratorPage ? "Generate or edit real CadQuery scripts in the backend, export STL, and inspect the generated mechanical mesh." : "Generate editable SCAD code, render it as real CSG geometry, and inspect topology before comparing against the Markus chair reference."}</p>
      </div>

      <label class="${isCadQueryPage ? "hidden" : ""}" for="prompt">Design prompt</label>
      <textarea class="${isCadQueryPage ? "hidden" : ""}" id="prompt" spellcheck="false">Create an editable OpenSCAD model of an office chair similar to an IKEA Markus chair. It should have a seat, tall backrest, headrest-like upper section, armrests, a central support column or leg structure, and a five-star rolling base. Every structural part must touch or union into one coherent watertight object with no floating parts.</textarea>

      <button id="generate-scad" class="primary generate-only ${isCadQueryPage ? "hidden" : ""}">Generate</button>

      <section class="scad-lab ${isCadQueryPage ? "hidden" : ""}">
        <div class="scad-lab-head">
          <label for="scad-code">OpenSCAD code</label>
          <span>real CSG subset renderer</span>
        </div>
        <textarea id="scad-code" spellcheck="false">difference() {
  union() {
    cube([80, 55, 6]);
    translate([12, 10, 6]) cube([8, 8, 55]);
    translate([60, 10, 6]) cube([8, 8, 55]);
    translate([12, 38, 6]) cube([8, 8, 55]);
    translate([60, 38, 6]) cube([8, 8, 55]);
    translate([0, 42, 58]) cube([80, 8, 55]);
  }
  translate([20, 27, -1]) cylinder(h=8, r=4, $fn=32);
}</textarea>
        <div id="scad-output" class="scad-output">Supported now: cube, sphere, cylinder, translate, rotate, scale, union, difference, and intersection.</div>
      </section>

      <section class="scad-lab ${isCadQueryGeneratorPage ? "" : "hidden"}">
        <div class="scad-lab-head">
          <label for="cadquery-prompt">CadQuery prompt</label>
          <span>GPT-5.4 -> Python CadQuery -> STL</span>
        </div>
        <textarea id="cadquery-prompt" spellcheck="false">Design a simple 6061 aluminum wall-mounted J hook for a 120 N downward hanging load at the hook tip. It should have a filleted wall plate, four countersunk mounting holes, a curved J hook arm, and triangular gussets. Generate clean parametric CadQuery code.</textarea>
        <button id="generate-cadquery" class="primary generate-only">Generate</button>
      </section>

      <section class="scad-lab ${isCadQueryEnvPage ? "" : "hidden"}">
        <div class="scad-lab-head">
          <label for="cadquery-env-prompt">RLVE prompt</label>
          <span>code REPL + reward</span>
        </div>
        <textarea id="cadquery-env-prompt" spellcheck="false">Create an editable CadQuery model of an IKEA Markus-like office chair. It should have a seat, tall backrest, headrest-like upper cushion, armrests, central gas cylinder, five-star base, and caster proxies. Prefer clear functions and named dimensions.</textarea>
        <div class="env-row">
          <label for="cadquery-provider">Provider</label>
          <select id="cadquery-provider">
            <option value="openai">OpenAI</option>
            <option value="ollama">Ollama</option>
          </select>
          <label for="cadquery-model">Model</label>
          <input id="cadquery-model" value="gpt-5.4" />
        </div>
        <div class="button-row">
          <button id="env-generate-cadquery" class="primary">Generate</button>
          <button id="env-revise-cadquery">Revise</button>
          <button id="env-evaluate-cadquery">Evaluate</button>
          <button id="env-load-ideal">Load Ideal</button>
        </div>
        <div id="cadquery-reward-output" class="scad-output">No reward yet.</div>
      </section>

      <section class="scad-lab ${isCadQueryPage ? "" : "hidden"}">
        <div class="scad-lab-head">
          <label for="cadquery-code">CadQuery code</label>
          <span>edit then render real STL</span>
        </div>
        <textarea id="cadquery-code" spellcheck="false">Loading sample CadQuery code...</textarea>
        <div class="button-row">
          <button id="render-cadquery" class="primary">Render</button>
          <button id="test-cadquery-backend" class="${isCadQueryRendererPage ? "" : "hidden"}">Test Backend</button>
          <button id="load-cadquery-sample">Load Sample</button>
        </div>
        <div id="cadquery-output" class="scad-output">Backend will run the real CadQuery sample and return an STL mesh.</div>
      </section>

      <div id="status" class="status">Ready.</div>
      <div id="agent-steps" class="agent-steps"></div>

      <div class="metrics" id="metrics"></div>
      <pre id="json" class="json"></pre>
    </section>

    <section class="viewer-wrap">
      <div class="viewer-top">
        <div>
          <p class="eyebrow">3D Viewer</p>
          <h2 id="design-title">${isCadQueryPage ? "No CadQuery mesh loaded" : "No CAD design loaded"}</h2>
        </div>
        <div class="legend">
          <span><i class="swatch plate"></i>primitive/body</span>
          <span><i class="swatch rib"></i>structure</span>
          <span><i class="swatch boss"></i>shaft/bolt/load boss</span>
          <span><i class="swatch slot"></i>slots/bores</span>
          <span><i class="swatch decorative"></i>decorative CAD</span>
          <span><i class="swatch load"></i>load</span>
          <span><i class="swatch stress"></i>stress</span>
          <span><i class="swatch warning"></i>low-SF member</span>
        </div>
      </div>
      <div id="viewer"></div>
      <div id="view-captures" class="view-captures"></div>
    </section>
  </main>
`;

const viewer = document.querySelector("#viewer");
const promptInput = document.querySelector("#prompt");
const presetButtons = document.querySelectorAll("[data-preset]");
const systemPromptInput = document.querySelector("#system-prompt");
const generateButton = document.querySelector("#generate");
const benchmarkButton = document.querySelector("#benchmark");
const toolEpisodeButton = document.querySelector("#tool-episode");
const sampleButton = document.querySelector("#sample");
const exportButton = document.querySelector("#export");
const captureViewsButton = document.querySelector("#capture-views");
const scadCodeInput = document.querySelector("#scad-code");
const generateScadButton = document.querySelector("#generate-scad");
const iterateScadButton = document.querySelector("#iterate-scad");
const renderScadButton = document.querySelector("#render-scad");
const loadScadExampleButton = document.querySelector("#load-scad-example");
const scadOutputEl = document.querySelector("#scad-output");
const cadqueryPromptInput = document.querySelector("#cadquery-prompt");
const cadqueryEnvPromptInput = document.querySelector("#cadquery-env-prompt");
const cadqueryProviderSelect = document.querySelector("#cadquery-provider");
const cadqueryModelInput = document.querySelector("#cadquery-model");
const cadqueryCodeInput = document.querySelector("#cadquery-code");
const generateCadqueryButton = document.querySelector("#generate-cadquery");
const envGenerateCadqueryButton = document.querySelector("#env-generate-cadquery");
const envReviseCadqueryButton = document.querySelector("#env-revise-cadquery");
const envEvaluateCadqueryButton = document.querySelector("#env-evaluate-cadquery");
const envLoadIdealButton = document.querySelector("#env-load-ideal");
const renderCadqueryButton = document.querySelector("#render-cadquery");
const testCadqueryBackendButton = document.querySelector("#test-cadquery-backend");
const loadCadquerySampleButton = document.querySelector("#load-cadquery-sample");
const cadqueryOutputEl = document.querySelector("#cadquery-output");
const cadqueryRewardOutputEl = document.querySelector("#cadquery-reward-output");
const agentStepsEl = document.querySelector("#agent-steps");
const toolBudgetInput = document.querySelector("#tool-budget");
const toolBudgetValue = document.querySelector("#tool-budget-value");
const viewCapturesEl = document.querySelector("#view-captures");
const statusEl = document.querySelector("#status");
const renderStateSelect = document.querySelector("#render-state-select");
const renderStateNote = document.querySelector("#render-state-note");
const benchmarkResultsEl = document.querySelector("#benchmark-results");
const metricsEl = document.querySelector("#metrics");
const traceEl = document.querySelector("#toolcalls");
const agentLoopEl = document.querySelector("#agent-loop");
const iterationsEl = document.querySelector("#iterations");
const llmInputEl = document.querySelector("#llm-input");
const jsonEl = document.querySelector("#json");
const titleEl = document.querySelector("#design-title");
const tabButtons = document.querySelectorAll("[data-tab]");
const tabPanels = {
  loop: document.querySelector("#loop-panel"),
  tools: document.querySelector("#tools-panel"),
  iterations: document.querySelector("#iterations-panel"),
  llm: document.querySelector("#llm-panel"),
  json: document.querySelector("#json-panel")
};

let currentGroup = null;
let latestDesign = null;
let latestAnalysis = null;
let latestAgentRun = null;
let latestRenderStates = [];
let latestScadStats = null;

const promptPresets = {
  chair:
    "Build a simple four-legged chair as editable code-CAD. It must support a 700 N seated load, include a seat panel, four connected legs, lower crossbars, and a backrest, fit inside a 500 mm x 500 mm x 900 mm envelope, and avoid floating parts.",
  "advanced-chair":
    "Build an ergonomic curvy chair as editable code-CAD. It needs a curved seat, four connected splayed legs, crossbars, armrests, a curved backrest, and a headrest. It must withstand 1000 N on the seat and 100 N on the backrest while remaining one connected watertight CAD-like object.",
  truss:
    "Build a simple lightweight truss support as code-CAD. Use connected triangular load paths, two fixed mounting holes on the left, a load boss on the right, and enough ribs/cross-members to carry a 250 N downward load with safety factor above 2.0.",
  cantilever:
    "Design a lightweight 6061 aluminum cantilever bracket. It is fixed by two M5 bolts on the left side and must carry 120 N downward at the tip 90 mm from the fixed edge. Keep mass below 45 g and safety factor above 2.0.",
  "torque-clamp":
    "Design a compact 6061 aluminum clamp fixture that resists 120 Nm torque around a shaft proxy. Use a twin-bolt fixed root on the left, place the shaft/load boss near the free end, keep the load path clear, and maintain safety factor above 2.0 while minimizing mass.",
  hook:
    "Design a simple 6061 aluminum wall-mounted J hook for a 120 N downward hanging load at the hook tip. It should visibly look like a hook, with a compact wall mount and a curved hook arm, not a ribbed cantilever bracket.",
  "motor-stator":
    "Design a simple 12-slot axial motor stator concept. It should visibly look like a circular stator ring with radial teeth and a center shaft opening. Use steel and keep the structure compact.",
  table:
    "Design a small table with six legs. It should have a rectangular tabletop, six visible support legs, lower crossbar stretchers, and the capability to withstand 500 N of downward force.",
  "bike-fixture":
    "Design a compact 6061 aluminum bike accessory mounting fixture for a 120 N downward load. Use a clamp-like mount and a short supported arm, with safety factor above 2.0."
};

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf6f7f9);

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
camera.position.set(90, -130, 92);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
viewer.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(55, 0, 8);

scene.add(new THREE.HemisphereLight(0xffffff, 0x8792a2, 2.1));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
keyLight.position.set(90, -80, 140);
scene.add(keyLight);

const grid = new THREE.GridHelper(180, 18, 0xc9d1dc, 0xe2e7ee);
grid.rotation.x = Math.PI / 2;
grid.position.z = -2;
scene.add(grid);

function resize() {
  const rect = viewer.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height);
  camera.aspect = rect.width / Math.max(rect.height, 1);
  camera.updateProjectionMatrix();
}

window.addEventListener("resize", resize);
resize();

function setStatus(message, kind = "") {
  statusEl.textContent = message;
  statusEl.className = `status ${kind}`;
}

function metric(label, value, suffix = "") {
  return `<div class="metric"><span>${label}</span><strong>${value}${suffix}</strong></div>`;
}

function fitCameraToObject(object, options = {}) {
  resize();
  const box = new THREE.Box3().setFromObject(object);
  if (box.isEmpty()) return;

  const center = new THREE.Vector3();
  const sphere = new THREE.Sphere();
  box.getCenter(center);
  box.getBoundingSphere(sphere);

  const radius = Math.max(sphere.radius, 1);
  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * Math.max(camera.aspect, 0.1));
  const fitFov = Math.min(verticalFov, horizontalFov);
  const distance = (radius / Math.sin(fitFov / 2)) * (options.padding ?? 1.35);
  const direction = (options.direction || new THREE.Vector3(0.9, -1.25, 0.72)).normalize();

  camera.near = Math.max(radius / 10000, 0.01);
  camera.far = Math.max(distance + radius * 8, 1000);
  camera.updateProjectionMatrix();
  controls.minDistance = Math.max(radius * 0.03, 1);
  controls.maxDistance = Math.max(distance + radius * 10, 1000);
  controls.target.copy(center);
  camera.position.copy(center).addScaledVector(direction, distance);
  controls.update();
}

function renderMetrics(analysis) {
  const cadforge = analysis.cadforge || {};
  metricsEl.innerHTML = [
    metric("Score", analysis.score),
    metric("AST nodes", cadforge.ast_nodes ?? "n/a"),
    metric("Components", cadforge.connected_components ?? "n/a"),
    metric("Watertight", cadforge.watertight_proxy === undefined ? "n/a" : cadforge.watertight_proxy ? "yes" : "no"),
    metric("Editability", cadforge.editability_score ?? "n/a"),
    metric("Safety factor", analysis.safety_factor),
    metric("Stress", analysis.max_stress_mpa, " MPa"),
    metric("Strain", analysis.max_strain_microstrain, " uε"),
    metric("Deflection", analysis.tip_deflection_mm, " mm"),
    metric("Thermal rise", analysis.thermal_delta_c_proxy, " C"),
    metric("Mass", analysis.mass_g, " g"),
    metric("Verdict", analysis.verdict)
  ].join("");
}

function renderScadFromEditor() {
  const material = new THREE.MeshStandardMaterial({ color: 0x38a078, metalness: 0.12, roughness: 0.44 });
  const { group, stats } = renderScadToGroup(scadCodeInput.value, material);
  if (currentGroup) scene.remove(currentGroup);
  currentGroup = group;
  latestDesign = null;
  latestAnalysis = null;
  latestScadStats = stats;
  scene.add(group);
  const box = new THREE.Box3().setFromObject(group);
  const size = new THREE.Vector3();
  box.getSize(size);
  fitCameraToObject(group, { padding: 1.45 });
  titleEl.textContent = "Rendered OpenSCAD CSG";
  scadOutputEl.textContent = `Rendered ${Math.round(stats.triangles)} triangles from ${stats.root_nodes} root node(s).`;
  metricsEl.innerHTML = [
    metric("SCAD roots", stats.root_nodes),
    metric("Triangles", Math.round(stats.triangles)),
    metric("Components", stats.connected_components),
    metric("Floating", stats.floating_parts),
    metric("Boundary edges", stats.boundary_edges),
    metric("Watertight", stats.watertight ? "yes" : "no"),
    metric("Renderer", "OpenSCAD subset")
  ].join("");
  jsonEl.textContent = JSON.stringify({ scad_code: scadCodeInput.value, render_stats: stats }, null, 2);
  setStatus("Rendered SCAD code into the 3D viewer.", "ok");
  window.setTimeout(() => captureViews({ silent: true }), 80);
}

function arrayBufferFromBase64(value) {
  const binary = window.atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes.buffer;
}

function renderCadqueryStl(result) {
  if (result.repaired && result.code && cadqueryCodeInput) {
    cadqueryCodeInput.value = result.code;
  }
  const loader = new STLLoader();
  const geometry = loader.parse(arrayBufferFromBase64(result.stl_base64));
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();

  if (currentGroup) scene.remove(currentGroup);
  const material = new THREE.MeshStandardMaterial({ color: 0x7a8f9f, metalness: 0.32, roughness: 0.34 });
  const mesh = new THREE.Mesh(geometry, material);
  currentGroup = new THREE.Group();
  currentGroup.add(mesh);
  scene.add(currentGroup);

  const box = new THREE.Box3().setFromObject(currentGroup);
  const size = new THREE.Vector3();
  box.getSize(size);
  fitCameraToObject(currentGroup, { padding: 1.5 });

  const triangles = geometry.index ? geometry.index.count / 3 : geometry.attributes.position.count / 3;
  titleEl.textContent = result.name || "Rendered CadQuery STL";
  cadqueryOutputEl.textContent = result.repaired
    ? `Generated STL with ${Math.round(triangles)} triangles from real CadQuery. Repair applied: ${result.repair_note}`
    : `Generated STL with ${Math.round(triangles)} triangles from real CadQuery.`;
  const rewardMetrics = result.reward
    ? [
        metric("Reward", Number(result.reward.total).toFixed(3)),
        metric("Contact", Number(result.reward.contact || 0).toFixed(3)),
        metric("Similarity", Number(result.reward.reference_similarity || 0).toFixed(3)),
        metric("Semantic", Number(result.reward.semantic_parts || 0).toFixed(3))
      ]
    : [];
  metricsEl.innerHTML = [
    metric("Backend", "CadQuery"),
    metric("Triangles", Math.round(triangles)),
    metric("X size", size.x.toFixed(1), " mm"),
    metric("Y size", size.y.toFixed(1), " mm"),
    metric("Z size", size.z.toFixed(1), " mm"),
    metric("Features", result.cadquery_features?.length || 0),
    ...rewardMetrics
  ].join("");
  jsonEl.textContent = JSON.stringify({ ...result, stl_base64: `<${result.stl_base64.length} base64 chars>` }, null, 2);
  setStatus(`Rendered CadQuery STL in ${(result.elapsed_ms / 1000).toFixed(1)}s.`, "ok");
  window.setTimeout(() => captureViews({ silent: true }), 80);
}

function renderRewardSummary(result) {
  if (!cadqueryRewardOutputEl || !result.reward) return;
  const reward = result.reward;
  const notes = (result.notes || []).map((note) => `<li>${note}</li>`).join("");
  cadqueryRewardOutputEl.innerHTML = `
    <strong>Total ${Number(reward.total).toFixed(3)}</strong>
    <div class="reward-grid">
      <span>build ${Number(reward.build).toFixed(3)}</span>
      <span>topology ${Number(reward.topology).toFixed(3)}</span>
      <span>contact ${Number(reward.contact || 0).toFixed(3)}</span>
      <span>semantic ${Number(reward.semantic_parts).toFixed(3)}</span>
      <span>reference ${Number(reward.reference_similarity).toFixed(3)}</span>
      <span>silhouette ${Number(reward.silhouette).toFixed(3)}</span>
      <span>editability ${Number(reward.editability).toFixed(3)}</span>
    </div>
    <ul>${notes}</ul>
  `;
}

async function renderCadquerySample() {
  setStatus("Running fixed CadQuery sample and exporting STL...", "working");
  if (renderCadqueryButton) renderCadqueryButton.disabled = true;
  try {
    const response = await fetch("/api/cadquery/sample-hook", { method: "POST" });
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "CadQuery render failed.", "error");
      jsonEl.textContent = JSON.stringify(result, null, 2);
      return;
    }
    renderCadqueryStl(result);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "CadQuery render failed.", "error");
  } finally {
    if (renderCadqueryButton) renderCadqueryButton.disabled = false;
  }
}

async function testCadqueryBackend() {
  setStatus("Testing CadQuery backend with a known-good cube...", "working");
  if (testCadqueryBackendButton) testCadqueryBackendButton.disabled = true;
  if (renderCadqueryButton) renderCadqueryButton.disabled = true;
  try {
    const response = await fetch("/api/cadquery/health", { method: "POST" });
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "CadQuery backend test failed.", "error");
      cadqueryOutputEl.textContent = result.stderr || result.error || "CadQuery backend test failed.";
      jsonEl.textContent = JSON.stringify(result, null, 2);
      return false;
    }
    cadqueryCodeInput.value = result.code || cadqueryCodeInput.value;
    renderCadqueryStl(result);
    cadqueryOutputEl.textContent = `Backend OK: Python imported CadQuery, generated STL, and returned ${result.stl_bytes} bytes.`;
    return true;
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "CadQuery backend test failed.", "error");
    return false;
  } finally {
    if (testCadqueryBackendButton) testCadqueryBackendButton.disabled = false;
    if (renderCadqueryButton) renderCadqueryButton.disabled = false;
  }
}

async function loadCadquerySampleCode({ render = false } = {}) {
  setStatus("Loading CadQuery sample code...", "working");
  try {
    const response = await fetch("/api/cadquery/sample-code");
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "Could not load CadQuery sample.", "error");
      return;
    }
    cadqueryCodeInput.value = result.cadquery_code || "";
    cadqueryOutputEl.textContent = "Loaded the real heavy-duty hook CadQuery sample.";
    setStatus("Loaded CadQuery sample code.", "ok");
    if (render) await renderCadqueryCode();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Could not load CadQuery sample.", "error");
  }
}

async function renderCadqueryCode() {
  setStatus("Running CadQuery code and exporting STL...", "working");
  if (renderCadqueryButton) renderCadqueryButton.disabled = true;
  if (generateCadqueryButton) generateCadqueryButton.disabled = true;
  try {
    const response = await fetch("/api/cadquery/render-code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cadquery_code: cadqueryCodeInput.value })
    });
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "CadQuery render failed.", "error");
      jsonEl.textContent = JSON.stringify(result, null, 2);
      return false;
    }
    renderCadqueryStl(result);
    return true;
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "CadQuery render failed.", "error");
    return false;
  } finally {
    if (renderCadqueryButton) renderCadqueryButton.disabled = false;
    if (generateCadqueryButton) generateCadqueryButton.disabled = false;
  }
}

async function generateCadqueryCode() {
  setStatus("Asking GPT-5.4 to generate CadQuery code...", "working");
  if (generateCadqueryButton) generateCadqueryButton.disabled = true;
  if (renderCadqueryButton) renderCadqueryButton.disabled = true;
  try {
    const response = await fetch("/api/cadquery/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: cadqueryPromptInput.value })
    });
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "CadQuery generation failed.", "error");
      jsonEl.textContent = JSON.stringify(result, null, 2);
      return;
    }
    cadqueryCodeInput.value = result.cadquery_code || "";
    cadqueryOutputEl.textContent = result.rationale || "Generated CadQuery code.";
    jsonEl.textContent = JSON.stringify({ ...result, cadquery_code: "<shown in editor>" }, null, 2);
    const rendered = await renderCadqueryCode();
    if (!rendered) {
      cadqueryOutputEl.textContent = `${result.rationale || "Generated CadQuery code."} Render failed; edit the code or regenerate.`;
    }
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "CadQuery generation failed.", "error");
  } finally {
    if (generateCadqueryButton) generateCadqueryButton.disabled = false;
    if (renderCadqueryButton) renderCadqueryButton.disabled = false;
  }
}

async function evaluateCadqueryEnv({ rewardMode = "full" } = {}) {
  setStatus(`Evaluating CadQuery reward (${rewardMode})...`, "working");
  if (envEvaluateCadqueryButton) envEvaluateCadqueryButton.disabled = true;
  try {
    const response = await fetch("/api/cadquery/evaluate-code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cadquery_code: cadqueryCodeInput.value,
        task_prompt: cadqueryEnvPromptInput?.value || cadqueryPromptInput?.value || "",
        reward_mode: rewardMode,
        episode_id: "frontend",
        step_id: `step-${Date.now()}`
      })
    });
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "CadQuery evaluation failed.", "error");
      jsonEl.textContent = JSON.stringify(result, null, 2);
      return null;
    }
    renderRewardSummary(result);
    if (result.stl_base64) renderCadqueryStl({ ...result, name: "CadQuery RLVE candidate" });
    jsonEl.textContent = JSON.stringify({ ...result, stl_base64: result.stl_base64 ? `<${result.stl_base64.length} base64 chars>` : undefined }, null, 2);
    setStatus(`Reward ${Number(result.reward.total).toFixed(3)} computed.`, "ok");
    return result;
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "CadQuery evaluation failed.", "error");
    return null;
  } finally {
    if (envEvaluateCadqueryButton) envEvaluateCadqueryButton.disabled = false;
  }
}

async function runCadqueryReplStep({ revise = false } = {}) {
  setStatus(revise ? "Revising CadQuery with verifier context..." : "Generating CadQuery candidate...", "working");
  if (envGenerateCadqueryButton) envGenerateCadqueryButton.disabled = true;
  if (envReviseCadqueryButton) envReviseCadqueryButton.disabled = true;
  let reward = null;
  if (revise && cadqueryCodeInput.value.trim()) {
    reward = await evaluateCadqueryEnv({ rewardMode: "fast" });
  }
  try {
    const response = await fetch("/api/cadquery/repl-step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: cadqueryEnvPromptInput?.value || cadqueryPromptInput?.value || "",
        current_code: revise ? cadqueryCodeInput.value : "",
        provider: cadqueryProviderSelect?.value || "openai",
        model: cadqueryModelInput?.value || "",
        reward
      })
    });
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "CadQuery REPL step failed.", "error");
      jsonEl.textContent = JSON.stringify(result, null, 2);
      return;
    }
    cadqueryCodeInput.value = result.cadquery_code || "";
    cadqueryOutputEl.textContent = `${result.provider} ${result.model} returned a CadQuery candidate.`;
    jsonEl.textContent = JSON.stringify({ ...result, cadquery_code: "<shown in editor>" }, null, 2);
    await evaluateCadqueryEnv({ rewardMode: "full" });
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "CadQuery REPL step failed.", "error");
  } finally {
    if (envGenerateCadqueryButton) envGenerateCadqueryButton.disabled = false;
    if (envReviseCadqueryButton) envReviseCadqueryButton.disabled = false;
  }
}

async function loadIdealCadqueryCode() {
  setStatus("Loading ideal Markus CadQuery code...", "working");
  try {
    const response = await fetch("/api/cadquery/ideal-code");
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "Could not load ideal CadQuery code.", "error");
      return;
    }
    cadqueryCodeInput.value = result.cadquery_code || "";
    cadqueryOutputEl.textContent = "Loaded ideal Markus CadQuery reference.";
    await evaluateCadqueryEnv({ rewardMode: "full" });
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Could not load ideal CadQuery code.", "error");
  }
}

function makePlateShape(design) {
  const shape = new THREE.Shape();
  const length = design.base_length_mm;
  const halfWidth = design.base_width_mm / 2;
  shape.moveTo(0, -halfWidth);
  shape.lineTo(length, -halfWidth);
  shape.lineTo(length, halfWidth);
  shape.lineTo(0, halfWidth);
  shape.lineTo(0, -halfWidth);

  for (const hole of design.fixed_holes || []) {
    const path = new THREE.Path();
    path.absellipse(hole.x, hole.y, hole.radius, hole.radius, 0, Math.PI * 2, false, 0);
    shape.holes.push(path);
  }

  for (const feature of design.features || []) {
    if (feature.type === "lightening_hole") {
      const path = new THREE.Path();
      path.absellipse(feature.x, feature.y, feature.radius, feature.radius, 0, Math.PI * 2, false, 0);
      shape.holes.push(path);
    }
  }

  return shape;
}

function addBoxBetween(group, feature, material) {
  const x1 = feature.x;
  const y1 = feature.y;
  const x2 = feature.x2;
  const y2 = feature.y2;
  const length = Math.max(Math.hypot(x2 - x1, y2 - y1), 1);
  const width = Math.max(feature.width, 1);
  const height = Math.max(feature.height, 1);
  const geometry = new THREE.BoxGeometry(length, width, height);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set((x1 + x2) / 2, (y1 + y2) / 2, height / 2 + latestDesign.base_thickness_mm / 2);
  mesh.rotation.z = Math.atan2(y2 - y1, x2 - x1);
  group.add(mesh);
}

function vectorFromLoad(analysis) {
  const vector = analysis?.force_vector_n || analysis?.load_case?.vector_n || [0, 0, -1];
  const result = new THREE.Vector3(vector[0] || 0, vector[1] || 0, vector[2] || -1);
  return result.length() > 0 ? result.normalize() : new THREE.Vector3(0, 0, -1);
}

function loadPointFromAnalysis(design, analysis) {
  const point = analysis?.load_case?.load_point || [
    design.load_point_x_mm,
    design.load_point_y_mm,
    design.base_thickness_mm
  ];
  return new THREE.Vector3(
    Number(point[0] ?? design.load_point_x_mm),
    Number(point[1] ?? design.load_point_y_mm),
    Number(point[2] ?? design.base_thickness_mm)
  );
}

function visualLoadPoint(design, analysis) {
  const family = familyOf(design);
  if (family === "wall_hook") {
    const feature = (design.features || []).find((item) => item.type === "hook_curve");
    const wallHeight = Math.max(design.base_width_mm, 48);
    const reach = Math.max(feature?.x2 || design.base_length_mm, 54);
    return new THREE.Vector3(reach * 0.56, 0, wallHeight * 0.58 - 22);
  }
  if (family === "torque_clamp") return new THREE.Vector3(82, 0, 24);
  if (family === "motor_stator") return new THREE.Vector3(design.base_length_mm / 2, 0, Math.max(design.base_thickness_mm, 8) + 8);
  if (family === "chair") return new THREE.Vector3(design.base_length_mm / 2, 0, 54);
  if (family === "table") return new THREE.Vector3(design.base_length_mm / 2, 0, 58);
  if (family === "freeform_object") return new THREE.Vector3(design.load_point_x_mm || design.base_length_mm / 2, design.load_point_y_mm || 0, 28);
  return loadPointFromAnalysis(design, analysis);
}

function addCylinderBetween(group, start, end, radius, material) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  if (length <= 0.01) return;
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 24), material);
  mesh.position.copy(start).add(end).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
  group.add(mesh);
}

function addCurveTube(group, points, radius, material, segments = 32) {
  const curve = new THREE.CatmullRomCurve3(points);
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, segments, radius, 16, false), material);
  group.add(mesh);
  return mesh;
}

function addClosedCurveTube(group, points, radius, material, segments = 48) {
  const curve = new THREE.CatmullRomCurve3(points, true);
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, segments, radius, 16, true), material);
  group.add(mesh);
  return mesh;
}

function hasFeature(design, type) {
  return (design.features || []).some((feature) => feature.type === type);
}

function box(group, size, position, material) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(size.x, size.y, size.z), material);
  mesh.position.copy(position);
  group.add(mesh);
  return mesh;
}

function familyOf(design) {
  if (hasFeature(design, "hook_curve")) return "wall_hook";
  if (hasFeature(design, "stator_ring")) return "motor_stator";
  if (hasFeature(design, "tabletop")) return "table";
  if (hasFeature(design, "seat_panel")) return "chair";
  if (hasFeature(design, "clamp_jaw")) return "torque_clamp";
  if ((design.features || []).some((feature) => ["generic_panel", "support_tube", "curved_tube", "flat_foot", "armrest", "headrest"].includes(feature.type))) return "freeform_object";
  return "bracket";
}

function isCurvyChair(design) {
  const text = [
    design.title,
    design.rationale,
    ...(design.features || []).map((feature) => `${feature.note || ""} ${feature.radius || 0}`)
  ]
    .join(" ")
    .toLowerCase();
  return /curv|round|organic|sweep|arched|bent|flow/.test(text) || (design.features || []).some((feature) => feature.type.startsWith("chair_") && Number(feature.radius || 0) >= 6);
}

function ellipsePointsOnBack(cx, y, cz, rx, rz, rotation = 0, count = 28) {
  const points = [];
  for (let i = 0; i < count; i += 1) {
    const t = (Math.PI * 2 * i) / count;
    const x = Math.cos(t) * rx;
    const z = Math.sin(t) * rz;
    points.push(
      new THREE.Vector3(
        cx + x * Math.cos(rotation) - z * Math.sin(rotation),
        y,
        cz + x * Math.sin(rotation) + z * Math.cos(rotation)
      )
    );
  }
  return points;
}

function renderChairDecorations(group, design, materials, dims) {
  const decorative = (design.features || []).filter((feature) => feature.type === "decorative_curve");
  if (!decorative.length) return;
  const flowerRequested = decorative.some((feature) => /flower|petal|blossom|rose|lotus/i.test(feature.note || ""));
  const material = new THREE.MeshStandardMaterial({ color: 0x7aa0bd, metalness: 0.1, roughness: 0.38 });
  const centerX = dims.length / 2;
  const backPlaneY = dims.backY + 17.5;
  const centerZ = dims.seatZ + 38;

  if (flowerRequested) {
    const petalRadius = Math.max(1.6, decorative[0]?.radius || 3);
    const petalLength = Math.max(9, (decorative[1]?.width || 44) / 5);
    const petalWidth = Math.max(4, (decorative[1]?.height || 24) / 6);
    for (let i = 0; i < 6; i += 1) {
      const angle = (Math.PI * 2 * i) / 6;
      const petalCenter = new THREE.Vector3(centerX + Math.cos(angle) * 10, backPlaneY, centerZ + Math.sin(angle) * 10);
      addClosedCurveTube(group, ellipsePointsOnBack(petalCenter.x, backPlaneY, petalCenter.z, petalLength, petalWidth, angle), petalRadius * 0.32, material, 42);
    }
    const blossom = new THREE.Mesh(new THREE.SphereGeometry(Math.max(2.5, petalRadius * 0.62), 24, 16), material);
    blossom.position.set(centerX, backPlaneY, centerZ);
    group.add(blossom);
    addCurveTube(
      group,
      [
        new THREE.Vector3(centerX, backPlaneY, centerZ - 3),
        new THREE.Vector3(centerX - 4, backPlaneY, centerZ - 18),
        new THREE.Vector3(centerX - 2, backPlaneY, dims.seatZ + 10)
      ],
      Math.max(1.1, petalRadius * 0.22),
      materials.rib,
      24
    );
    return;
  }

  for (const [index, feature] of decorative.entries()) {
    const z = centerZ + (index - decorative.length / 2) * 8;
    addCurveTube(
      group,
      [
        new THREE.Vector3(centerX - feature.width / 2, backPlaneY, z),
        new THREE.Vector3(centerX, backPlaneY, z + feature.height / 3),
        new THREE.Vector3(centerX + feature.width / 2, backPlaneY, z)
      ],
      Math.max(1.2, feature.radius * 0.25),
      material,
      32
    );
  }
}

function featureZ(feature, fallback = 24) {
  return Number.isFinite(Number(feature.z)) ? Number(feature.z) : fallback;
}

function renderPrimitiveFeature(group, feature, materials, options = {}) {
  const structureMaterial = options.structureMaterial || materials.rib;
  const bodyMaterial = options.bodyMaterial || materials.plate;
  const decorativeMaterial =
    options.decorativeMaterial ||
    new THREE.MeshStandardMaterial({ color: 0xd58f22, metalness: 0.08, roughness: 0.42 });
  const tubeRadius = Math.max(Number(feature.radius || 0), Number(feature.width || 0) / 2, 2);
  const height = Math.max(Number(feature.height || 0), 4);
  const x = Number(feature.x || 0);
  const y = Number(feature.y || 0);
  const x2 = Number.isFinite(Number(feature.x2)) ? Number(feature.x2) : x;
  const y2 = Number.isFinite(Number(feature.y2)) ? Number(feature.y2) : y;

  if (feature.type === "tabletop" || feature.type === "generic_panel") {
    const panelLength = Math.max(Number(feature.width || 0), 24);
    const panelDepth = Math.max(options.panelDepth || latestDesign?.base_width_mm || 44, 18);
    const panelHeight = Math.max(Number(feature.height || 0), 4);
    const z = feature.type === "tabletop" ? 52 : featureZ(feature, panelHeight / 2);
    box(group, new THREE.Vector3(panelLength, panelDepth, panelHeight), new THREE.Vector3(x || panelLength / 2, y, z), bodyMaterial);
    return;
  }

  if (feature.type === "table_leg") {
    const legHeight = Math.max(height, 24);
    const radius = Math.max(Number(feature.radius || 0), Number(feature.width || 0) / 2, 2.4);
    addCylinderBetween(
      group,
      new THREE.Vector3(x, y, 2),
      new THREE.Vector3(x, y, legHeight),
      radius,
      structureMaterial
    );
    return;
  }

  if (feature.type === "support_tube") {
    const z = featureZ(feature, height || 20);
    addCylinderBetween(group, new THREE.Vector3(x, y, z), new THREE.Vector3(x2, y2, z), tubeRadius, structureMaterial);
    return;
  }

  if (feature.type === "curved_tube") {
    const z = featureZ(feature, height || 24);
    const mid = new THREE.Vector3((x + x2) / 2, (y + y2) / 2, z + Math.max(Number(feature.radius || 0) * 2, 12));
    addCurveTube(group, [new THREE.Vector3(x, y, z), mid, new THREE.Vector3(x2, y2, z)], tubeRadius, decorativeMaterial, 42);
    return;
  }

  if (feature.type === "flat_foot") {
    const footLength = Math.max(Number(feature.width || 0), 16);
    const footDepth = Math.max(Number(feature.radius || 0) * 2.4, 8);
    const footHeight = Math.max(Number(feature.height || 0), 2.5);
    const mesh = box(group, new THREE.Vector3(footLength, footDepth, footHeight), new THREE.Vector3(x, y, footHeight / 2), decorativeMaterial);
    mesh.rotation.z = Math.atan2(y2 - y, x2 - x || 1);
    return;
  }
}

function renderChairExtras(group, design, materials, dims) {
  const decorativeMaterial = new THREE.MeshStandardMaterial({ color: 0xd58f22, metalness: 0.08, roughness: 0.42 });
  const leftX = 10;
  const rightX = dims.length - 10;
  const frontY = -dims.width / 2 + 7;
  const backY = dims.backY + 6;
  const seatTop = dims.seatZ + 5;

  for (const feature of design.features || []) {
    if (feature.type === "armrest") {
      const sideX = feature.x < dims.length / 2 ? leftX - 8 : rightX + 8;
      addCurveTube(
        group,
        [
          new THREE.Vector3(sideX, frontY, seatTop + 2),
          new THREE.Vector3(sideX, 0, seatTop + 18),
          new THREE.Vector3(sideX, backY, seatTop + 16)
        ],
        Math.max(Number(feature.width || 0) / 2, 3),
        decorativeMaterial,
        44
      );
    }
    if (feature.type === "headrest") {
      addCurveTube(
        group,
        [
          new THREE.Vector3(dims.length * 0.22, dims.backY + 19, dims.seatZ + 72),
          new THREE.Vector3(dims.length * 0.5, dims.backY + 25, dims.seatZ + 78),
          new THREE.Vector3(dims.length * 0.78, dims.backY + 19, dims.seatZ + 72)
        ],
        Math.max(Number(feature.radius || 0) * 0.42, 3.2),
        decorativeMaterial,
        42
      );
    }
    if (feature.type === "flat_foot") {
      renderPrimitiveFeature(group, feature, materials, { decorativeMaterial });
    }
    if (feature.type === "support_tube" || feature.type === "curved_tube") {
      renderPrimitiveFeature(group, feature, materials, { decorativeMaterial });
    }
  }
}

function renderTableFamily(group, design, materials) {
  const decorativeMaterial = new THREE.MeshStandardMaterial({ color: 0xd58f22, metalness: 0.08, roughness: 0.42 });
  const features = design.features || [];
  const tabletop = features.find((feature) => feature.type === "tabletop") || {
    type: "tabletop",
    x: design.base_length_mm / 2,
    y: 0,
    width: design.base_length_mm,
    height: design.base_thickness_mm
  };
  renderPrimitiveFeature(group, tabletop, materials, { panelDepth: design.base_width_mm, decorativeMaterial });

  const legs = features.filter((feature) => feature.type === "table_leg");
  const fallbackLegs = [
    { type: "table_leg", x: 10, y: -28, width: 6, height: 48, radius: 3 },
    { type: "table_leg", x: 50, y: -28, width: 6, height: 48, radius: 3 },
    { type: "table_leg", x: 90, y: -28, width: 6, height: 48, radius: 3 },
    { type: "table_leg", x: 10, y: 28, width: 6, height: 48, radius: 3 },
    { type: "table_leg", x: 50, y: 28, width: 6, height: 48, radius: 3 },
    { type: "table_leg", x: 90, y: 28, width: 6, height: 48, radius: 3 }
  ];
  for (const leg of legs.length ? legs : fallbackLegs.slice(0, 4)) {
    renderPrimitiveFeature(group, leg, materials, { decorativeMaterial });
  }
  for (const feature of features.filter((item) => ["support_tube", "curved_tube", "flat_foot", "generic_panel"].includes(item.type))) {
    renderPrimitiveFeature(group, feature, materials, { decorativeMaterial });
  }
}

function renderFreeformFamily(group, design, materials) {
  const decorativeMaterial = new THREE.MeshStandardMaterial({ color: 0xd58f22, metalness: 0.08, roughness: 0.42 });
  for (const feature of design.features || []) {
    renderPrimitiveFeature(group, feature, materials, { panelDepth: design.base_width_mm, decorativeMaterial });
  }
}

function addArcTube(group, center, radius, startAngle, endAngle, tubeRadius, material) {
  const points = [];
  const segments = 36;
  for (let i = 0; i <= segments; i += 1) {
    const t = startAngle + ((endAngle - startAngle) * i) / segments;
    points.push(new THREE.Vector3(center.x, center.y + Math.cos(t) * radius, center.z + Math.sin(t) * radius));
  }
  const curve = new THREE.CatmullRomCurve3(points);
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, segments, tubeRadius, 16, false), material);
  group.add(mesh);
  return mesh;
}

function makeAnnulusGeometry(outerRadius, innerRadius, depth) {
  const shape = new THREE.Shape();
  shape.absarc(0, 0, outerRadius, 0, Math.PI * 2, false);
  const hole = new THREE.Path();
  hole.absarc(0, 0, innerRadius, 0, Math.PI * 2, true);
  shape.holes.push(hole);
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: true,
    bevelThickness: 0.25,
    bevelSize: 0.25,
    bevelSegments: 1
  });
  geometry.center();
  return geometry;
}

function renderHookFamily(group, design, materials) {
  const wallHeight = Math.max(design.base_width_mm, 48);
  const wallWidth = Math.max(design.base_width_mm * 0.42, 24);
  const wallThickness = Math.max(design.base_thickness_mm, 6);
  box(
    group,
    new THREE.Vector3(wallThickness, wallWidth, wallHeight),
    new THREE.Vector3(0, 0, wallHeight / 2),
    materials.plate
  );

  for (const hole of design.fixed_holes || []) {
    const z = wallHeight / 2 + hole.y;
    const marker = new THREE.Mesh(
      new THREE.CylinderGeometry(hole.radius, hole.radius, wallThickness + 0.8, 32),
      new THREE.MeshStandardMaterial({ color: 0xd9fff0, roughness: 0.35 })
    );
    marker.rotation.z = Math.PI / 2;
    marker.position.set(-0.2, 0, z);
    group.add(marker);
  }

  const feature = (design.features || []).find((item) => item.type === "hook_curve");
  const tubeRadius = Math.max(feature?.width || 8, 3) / 2;
  const rootZ = wallHeight * 0.58;
  const reach = Math.max(feature?.x2 || design.base_length_mm, 54);
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(wallThickness / 2, 0, rootZ),
    new THREE.Vector3(reach * 0.45, 0, rootZ),
    new THREE.Vector3(reach * 0.78, 0, rootZ - 8),
    new THREE.Vector3(reach * 0.86, 0, rootZ - 25),
    new THREE.Vector3(reach * 0.66, 0, rootZ - 33),
    new THREE.Vector3(reach * 0.52, 0, rootZ - 21)
  ]);
  const hook = new THREE.Mesh(new THREE.TubeGeometry(curve, 52, tubeRadius, 18, false), materials.rib);
  group.add(hook);

  const root = new THREE.Mesh(new THREE.SphereGeometry(tubeRadius * 1.45, 28, 18), materials.boss);
  root.position.set(wallThickness / 2 + 1, 0, rootZ);
  group.add(root);
}

function renderClampFamily(group, design, materials) {
  const rootHeight = 30;
  box(group, new THREE.Vector3(18, design.base_width_mm, rootHeight), new THREE.Vector3(9, 0, rootHeight / 2), materials.plate);
  for (const hole of design.fixed_holes || []) {
    const marker = new THREE.Mesh(
      new THREE.CylinderGeometry(hole.radius, hole.radius, 19, 28),
      new THREE.MeshStandardMaterial({ color: 0xd9fff0, roughness: 0.35 })
    );
    marker.rotation.z = Math.PI / 2;
    marker.position.set(9, hole.y, rootHeight / 2);
    group.add(marker);
  }

  const center = new THREE.Vector3(62, 0, 24);
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(10, 10, 66, 48), materials.boss);
  shaft.rotation.z = Math.PI / 2;
  shaft.position.copy(center);
  group.add(shaft);

  addArcTube(group, center, 20, -Math.PI * 0.76, Math.PI * 0.76, 4.6, materials.rib);
  addArcTube(group, center, 20, Math.PI * 1.24, Math.PI * 2.76, 4.6, materials.rib);
  box(group, new THREE.Vector3(68, 8, 12), new THREE.Vector3(46, -22, 24), materials.rib);
  box(group, new THREE.Vector3(68, 8, 12), new THREE.Vector3(46, 22, 24), materials.rib);
  box(group, new THREE.Vector3(28, 8, 12), new THREE.Vector3(20, -22, 24), materials.rib);
  box(group, new THREE.Vector3(28, 8, 12), new THREE.Vector3(20, 22, 24), materials.rib);
  box(group, new THREE.Vector3(12, 52, 8), new THREE.Vector3(86, 0, 24), materials.plate);
  box(group, new THREE.Vector3(20, 8, 8), new THREE.Vector3(70, -30, 24), materials.plate);
  box(group, new THREE.Vector3(20, 8, 8), new THREE.Vector3(70, 30, 24), materials.plate);
  for (const y of [-24, 24]) {
    const bolt = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, 16, 24), materials.boss);
    bolt.rotation.z = Math.PI / 2;
    bolt.position.set(82, y, 24);
    group.add(bolt);
  }
}

function renderStatorFamily(group, design, materials) {
  const ring = (design.features || []).find((feature) => feature.type === "stator_ring");
  const tooth = (design.features || []).find((feature) => feature.type === "stator_tooth");
  const centerX = ring?.x || design.base_length_mm / 2;
  const centerY = ring?.y || 0;
  const outerRadius = (ring?.radius || 34) + Math.max(ring?.width || 14, 8);
  const innerRadius = Math.max(tooth?.radius || 17, 12);
  const height = Math.max(ring?.height || design.base_thickness_mm, 6);
  const ringMesh = new THREE.Mesh(makeAnnulusGeometry(outerRadius, innerRadius, height), materials.plate);
  ringMesh.position.set(centerX, centerY, height / 2);
  group.add(ringMesh);

  const toothCount = 12;
  for (let i = 0; i < toothCount; i += 1) {
    const angle = (Math.PI * 2 * i) / toothCount;
    const radial = innerRadius + (tooth?.height || 18) / 2;
    const toothMesh = new THREE.Mesh(
      new THREE.BoxGeometry(tooth?.height || 18, tooth?.width || 8, height + 2),
      materials.rib
    );
    toothMesh.position.set(centerX + Math.cos(angle) * radial, centerY + Math.sin(angle) * radial, height / 2);
    toothMesh.rotation.z = angle;
    group.add(toothMesh);

    const slot = new THREE.Mesh(
      new THREE.BoxGeometry(outerRadius - innerRadius - 8, Math.max((tooth?.width || 8) * 0.55, 3), height + 2.4),
      new THREE.MeshStandardMaterial({ color: 0x24313c, transparent: true, opacity: 0.28, roughness: 0.6 })
    );
    slot.position.set(centerX + Math.cos(angle + Math.PI / toothCount) * (innerRadius + (outerRadius - innerRadius) / 2), centerY + Math.sin(angle + Math.PI / toothCount) * (innerRadius + (outerRadius - innerRadius) / 2), height / 2);
    slot.rotation.z = angle + Math.PI / toothCount;
    group.add(slot);
  }

  const bore = new THREE.Mesh(
    new THREE.CylinderGeometry(innerRadius * 0.88, innerRadius * 0.88, height + 2, 64),
    new THREE.MeshStandardMaterial({ color: 0xf2f7fb, roughness: 0.5 })
  );
  bore.rotation.x = Math.PI / 2;
  bore.position.set(centerX, centerY, height / 2);
  group.add(bore);
}

function renderChairFamily(group, design, materials) {
  const length = Math.max(design.base_length_mm || 90, 72);
  const width = Math.max(design.base_width_mm || 70, 54);
  const thickness = Math.max(design.base_thickness_mm || 6, 5);
  const seatZ = 46;
  const legSize = 5.5;
  const frontY = -width / 2 + 9;
  const backY = width / 2 - 9;
  const leftX = 12;
  const rightX = length - 12;
  const curvy = isCurvyChair(design);

  box(group, new THREE.Vector3(length, width, thickness), new THREE.Vector3(length / 2, 0, seatZ), materials.plate);

  if (curvy) {
    const legRadius = Math.max(2.8, ((design.features || []).find((feature) => feature.type === "chair_leg")?.width || 7) / 2);
    const railRadius = 2.6;
    const seatTop = seatZ + thickness / 2 + 0.5;
    const seatBottom = seatZ - thickness / 2;
    const footZ = 2;
    const legData = [
      { top: new THREE.Vector3(leftX, frontY, seatBottom), foot: new THREE.Vector3(2, frontY - 12, footZ), bow: new THREE.Vector3(-5, -7, 22) },
      { top: new THREE.Vector3(rightX, frontY, seatBottom), foot: new THREE.Vector3(length - 2, frontY - 12, footZ), bow: new THREE.Vector3(5, -7, 22) },
      { top: new THREE.Vector3(leftX, backY, seatBottom), foot: new THREE.Vector3(2, backY + 13, footZ), bow: new THREE.Vector3(-6, 9, 24) },
      { top: new THREE.Vector3(rightX, backY, seatBottom), foot: new THREE.Vector3(length - 2, backY + 13, footZ), bow: new THREE.Vector3(6, 9, 24) }
    ];

    for (const leg of legData) {
      const mid = new THREE.Vector3().copy(leg.top).add(leg.foot).multiplyScalar(0.5).add(leg.bow);
      addCurveTube(group, [leg.top, mid, leg.foot], legRadius, materials.rib, 36);
    }

    addCurveTube(
      group,
      [
        new THREE.Vector3(leftX - 4, frontY - 2, seatTop),
        new THREE.Vector3(length / 2, frontY - 8, seatTop + 1.2),
        new THREE.Vector3(rightX + 4, frontY - 2, seatTop)
      ],
      railRadius,
      materials.rib,
      36
    );
    addCurveTube(group, [new THREE.Vector3(leftX, frontY, seatTop), new THREE.Vector3(leftX - 4, 0, seatTop + 1.4), new THREE.Vector3(leftX, backY, seatTop)], railRadius, materials.rib, 34);
    addCurveTube(group, [new THREE.Vector3(rightX, frontY, seatTop), new THREE.Vector3(rightX + 4, 0, seatTop + 1.4), new THREE.Vector3(rightX, backY, seatTop)], railRadius, materials.rib, 34);

    const lowZ = 20;
    addCurveTube(group, [new THREE.Vector3(4, frontY - 10, lowZ), new THREE.Vector3(length / 2, frontY - 14, lowZ + 2), new THREE.Vector3(length - 4, frontY - 10, lowZ)], railRadius, materials.rib, 34);
    addCurveTube(group, [new THREE.Vector3(4, backY + 11, lowZ), new THREE.Vector3(length / 2, backY + 15, lowZ + 2), new THREE.Vector3(length - 4, backY + 11, lowZ)], railRadius, materials.rib, 34);
    addCurveTube(group, [new THREE.Vector3(4, frontY - 10, lowZ), new THREE.Vector3(0, 0, lowZ + 2), new THREE.Vector3(4, backY + 11, lowZ)], railRadius, materials.rib, 34);
    addCurveTube(group, [new THREE.Vector3(length - 4, frontY - 10, lowZ), new THREE.Vector3(length, 0, lowZ + 2), new THREE.Vector3(length - 4, backY + 11, lowZ)], railRadius, materials.rib, 34);

    const postTopZ = seatZ + 58;
    addCurveTube(group, [new THREE.Vector3(leftX, backY, seatTop), new THREE.Vector3(leftX - 5, backY + 9, seatZ + 72 / 2), new THREE.Vector3(leftX - 2, backY + 16, postTopZ)], legRadius, materials.rib, 42);
    addCurveTube(group, [new THREE.Vector3(rightX, backY, seatTop), new THREE.Vector3(rightX + 5, backY + 9, seatZ + 72 / 2), new THREE.Vector3(rightX + 2, backY + 16, postTopZ)], legRadius, materials.rib, 42);

    for (const z of [seatZ + 24, seatZ + 38, seatZ + 52]) {
      addCurveTube(
        group,
        [
          new THREE.Vector3(leftX - 2, backY + 14, z),
          new THREE.Vector3(length / 2, backY + 21, z + 3),
          new THREE.Vector3(rightX + 2, backY + 14, z)
        ],
        z === seatZ + 52 ? 3.5 : 3,
        z === seatZ + 38 ? materials.plate : materials.rib,
        42
      );
    }
    renderChairExtras(group, design, materials, { length, width, seatZ, backY });
    renderChairDecorations(group, design, materials, { length, width, seatZ, backY });
    return;
  }

  const legHeight = seatZ - thickness / 2;

  for (const [x, y] of [
    [leftX, frontY],
    [rightX, frontY],
    [leftX, backY],
    [rightX, backY]
  ]) {
    box(group, new THREE.Vector3(legSize, legSize, legHeight), new THREE.Vector3(x, y, legHeight / 2), materials.rib);
  }

  const backPostHeight = 54;
  const backPostCenterZ = seatZ + thickness / 2 + backPostHeight / 2;
  box(group, new THREE.Vector3(legSize, legSize, backPostHeight), new THREE.Vector3(leftX, backY, backPostCenterZ), materials.rib);
  box(group, new THREE.Vector3(legSize, legSize, backPostHeight), new THREE.Vector3(rightX, backY, backPostCenterZ), materials.rib);
  box(group, new THREE.Vector3(length - 18, 5, 30), new THREE.Vector3(length / 2, backY + 1, seatZ + 38), materials.plate);

  box(group, new THREE.Vector3(length - 18, 4, 4), new THREE.Vector3(length / 2, frontY, 22), materials.rib);
  box(group, new THREE.Vector3(length - 18, 4, 4), new THREE.Vector3(length / 2, backY, 22), materials.rib);
  box(group, new THREE.Vector3(4, width - 18, 4), new THREE.Vector3(leftX, 0, 22), materials.rib);
  box(group, new THREE.Vector3(4, width - 18, 4), new THREE.Vector3(rightX, 0, 22), materials.rib);
  renderChairExtras(group, design, materials, { length, width, seatZ, backY });
  renderChairDecorations(group, design, materials, { length, width, seatZ, backY });
}

function addLoadArrow(group, design) {
  const red = new THREE.MeshStandardMaterial({ color: 0xdd3b3b, roughness: 0.45 });
  const loadPoint = visualLoadPoint(design, latestAnalysis);
  const direction = vectorFromLoad(latestAnalysis);
  const arrowLength = Math.max(22, Math.min(46, design.base_length_mm * 0.32));
  const coneHeight = Math.max(8, Math.min(13, arrowLength * 0.28));
  const shaftStart = loadPoint.clone().sub(direction.clone().multiplyScalar(arrowLength));
  const coneBase = loadPoint.clone().sub(direction.clone().multiplyScalar(coneHeight));
  addCylinderBetween(group, shaftStart, coneBase, 1.15, red);

  const cone = new THREE.Mesh(new THREE.ConeGeometry(4.5, coneHeight, 28), red);
  cone.position.copy(loadPoint).sub(direction.clone().multiplyScalar(coneHeight / 2));
  cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
  group.add(cone);

  const contact = new THREE.Mesh(
    new THREE.SphereGeometry(2.5, 20, 14),
    new THREE.MeshStandardMaterial({ color: 0x9f1f1f, emissive: 0x2c0505, roughness: 0.35 })
  );
  contact.position.copy(loadPoint);
  group.add(contact);
}

function severityColor(severity) {
  const s = Math.max(0, Math.min(1, severity));
  return new THREE.Color().setHSL(0.34 * (1 - s), 0.85, 0.5);
}

function addAnalysisOverlays(group, design, analysis) {
  const stressMaterial = new THREE.MeshStandardMaterial({ color: 0xdf4a35, emissive: 0x3b0704, roughness: 0.35 });
  const family = familyOf(design);
  if (family !== "bracket") {
    const stressPoints = family === "chair"
      ? [
          new THREE.Vector3(14, 24, 48),
          new THREE.Vector3(design.base_length_mm - 14, 24, 48),
          visualLoadPoint(design, analysis)
        ]
      : [
          new THREE.Vector3(Math.max(12, design.base_length_mm * 0.18), 0, Math.max(design.base_thickness_mm, 8) + 6),
          visualLoadPoint(design, analysis)
        ];
    stressPoints.forEach((point, index) => {
      const marker = new THREE.Mesh(new THREE.SphereGeometry(index === 0 ? 4 : 3, 24, 16), stressMaterial.clone());
      marker.material.color = severityColor(index === 0 ? 0.72 : 0.42);
      marker.position.copy(point);
      group.add(marker);
    });
    return;
  }

  for (const region of analysis.stress_regions || []) {
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(2.5 + 5 * Math.max(region.severity, 0.05), 24, 16),
      stressMaterial.clone()
    );
    marker.material.color = severityColor(region.severity);
    marker.position.set(region.x, region.y, region.z ?? design.base_thickness_mm + 6);
    group.add(marker);
  }

  const deflection = Math.max(analysis.tip_deflection_mm || 0, 0.01);
  const lineMaterial = new THREE.LineBasicMaterial({ color: 0x7b5fd6, linewidth: 2 });
  const points = [
    new THREE.Vector3(0, design.load_point_y_mm, design.base_thickness_mm + 1),
    new THREE.Vector3(design.load_point_x_mm / 2, design.load_point_y_mm, design.base_thickness_mm + 1 - deflection * 6),
    new THREE.Vector3(design.load_point_x_mm, design.load_point_y_mm, design.base_thickness_mm + 1 - deflection * 12)
  ];
  group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), lineMaterial));

  const heatSeverity = Math.max(0, Math.min(1, (analysis.thermal_delta_c_proxy || 0) / 45));
  const heatMaterial = new THREE.MeshStandardMaterial({
    color: severityColor(heatSeverity),
    transparent: true,
    opacity: 0.32,
    roughness: 0.8
  });
  const heatPad = new THREE.Mesh(
    new THREE.BoxGeometry(design.base_length_mm * 0.75, design.base_width_mm * 0.65, 0.5),
    heatMaterial
  );
  heatPad.position.set(design.base_length_mm * 0.55, 0, design.base_thickness_mm + 0.35);
  group.add(heatPad);
}

function renderDesign(design, analysis) {
  latestDesign = design;
  latestAnalysis = analysis;
  if (currentGroup) scene.remove(currentGroup);

  const group = new THREE.Group();
  const plateMaterial = new THREE.MeshStandardMaterial({ color: 0x8ca3b7, metalness: 0.2, roughness: 0.48 });
  const ribMaterial = new THREE.MeshStandardMaterial({ color: analysis.safety_factor >= 2 ? 0x23a36f : 0xd88b25, metalness: 0.1, roughness: 0.5 });
  const bossMaterial = new THREE.MeshStandardMaterial({ color: 0x4b6f9f, metalness: 0.1, roughness: 0.45 });
  const familyMaterials = { plate: plateMaterial, rib: ribMaterial, boss: bossMaterial };
  const family = familyOf(design);

  if (family === "wall_hook") {
    renderHookFamily(group, design, familyMaterials);
  } else if (family === "motor_stator") {
    renderStatorFamily(group, design, familyMaterials);
  } else if (family === "chair") {
    renderChairFamily(group, design, familyMaterials);
  } else if (family === "table") {
    renderTableFamily(group, design, familyMaterials);
  } else if (family === "freeform_object") {
    renderFreeformFamily(group, design, familyMaterials);
  } else if (family === "torque_clamp") {
    renderClampFamily(group, design, familyMaterials);
  } else {

    const plateGeometry = new THREE.ExtrudeGeometry(makePlateShape(design), {
      depth: Math.max(design.base_thickness_mm, 1),
      bevelEnabled: true,
      bevelThickness: 0.4,
      bevelSize: 0.4,
      bevelSegments: 2
    });
    plateGeometry.center();
    const plate = new THREE.Mesh(plateGeometry, plateMaterial);
    plate.position.set(design.base_length_mm / 2, 0, design.base_thickness_mm / 2);
    group.add(plate);

    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(plateGeometry),
      new THREE.LineBasicMaterial({ color: 0x2f3a45, transparent: true, opacity: 0.35 })
    );
    edges.position.copy(plate.position);
    group.add(edges);

    for (const feature of design.features || []) {
      if (feature.type === "rib") addBoxBetween(group, feature, ribMaterial);
      if (feature.type === "boss") {
        const boss = new THREE.Mesh(
          new THREE.CylinderGeometry(Math.max(feature.radius, 1), Math.max(feature.radius, 1), Math.max(feature.height, 1), 40),
          bossMaterial
        );
        boss.position.set(feature.x, feature.y, design.base_thickness_mm + feature.height / 2);
        group.add(boss);
      }
      if (feature.type === "fillet_marker") {
        const marker = new THREE.Mesh(new THREE.SphereGeometry(Math.max(feature.radius, 1), 16, 12), bossMaterial);
        marker.position.set(feature.x, feature.y, design.base_thickness_mm + Math.max(feature.radius, 1));
        group.add(marker);
      }
    }
  }

  addLoadArrow(group, design);
  addAnalysisOverlays(group, design, analysis);
  scene.add(group);
  currentGroup = group;

  const centerX = design.base_length_mm / 2;
  if (family === "chair") {
    controls.target.set(centerX, 0, 48);
    camera.position.set(centerX, -165, 64);
  } else if (family === "table") {
    controls.target.set(centerX, 0, 32);
    camera.position.set(centerX + 55, -145, 82);
  } else if (family === "freeform_object") {
    controls.target.set(centerX, 0, 28);
    camera.position.set(centerX + 65, -130, 82);
  } else if (family === "motor_stator") {
    controls.target.set(centerX, 0, 6);
    camera.position.set(centerX + 10, -135, 105);
  } else if (family === "wall_hook") {
    controls.target.set(34, 0, 28);
    camera.position.set(76, -112, 70);
  } else {
    controls.target.set(centerX, 0, 18);
    camera.position.set(centerX + 70, -135, 90);
  }
  fitCameraToObject(group, {
    padding: family === "chair" || family === "table" ? 1.55 : 1.35
  });
  titleEl.textContent = design.title;
  renderMetrics(analysis);
  jsonEl.textContent = JSON.stringify({ design, analysis }, null, 2);
  window.setTimeout(() => captureViews({ silent: true }), 80);
}

function cameraPoseForView(view, design = latestDesign) {
  const family = design ? familyOf(design) : "bracket";
  let centerX = design?.base_length_mm ? design.base_length_mm / 2 : 50;
  let targetZ = family === "chair" ? 56 : family === "motor_stator" ? 6 : family === "table" ? 34 : family === "freeform_object" ? 30 : 22;
  let target = new THREE.Vector3(centerX, 0, targetZ);
  let distance = family === "chair" ? 155 : family === "table" ? 145 : 130;

  if (!design && currentGroup) {
    const box = new THREE.Box3().setFromObject(currentGroup);
    const size = new THREE.Vector3();
    const sphere = new THREE.Sphere();
    box.getSize(size);
    box.getCenter(target);
    box.getBoundingSphere(sphere);
    centerX = target.x;
    targetZ = target.z;
    distance = Math.max(sphere.radius * 3.3, Math.max(size.x, size.y, size.z, 80) * 1.55);
  }

  const poses = {
    isometric: family === "chair" || family === "table"
      ? new THREE.Vector3(centerX + distance * 0.26, -distance, targetZ + distance * 0.22)
      : new THREE.Vector3(centerX + distance * 0.55, -distance, targetZ + distance * 0.62),
    front: new THREE.Vector3(centerX, -distance, targetZ + 8),
    back: new THREE.Vector3(centerX, distance, targetZ + 8),
    left: new THREE.Vector3(centerX - distance, 0, targetZ + 8),
    right: new THREE.Vector3(centerX + distance, 0, targetZ + 8),
    top: new THREE.Vector3(centerX, 0, targetZ + distance),
    bottom: new THREE.Vector3(centerX, 0, targetZ - distance)
  };
  return { position: poses[view] || poses.isometric, target };
}

function setCameraView(view) {
  if (!currentGroup) return;
  const pose = cameraPoseForView(view, latestDesign);
  camera.position.copy(pose.position);
  controls.target.copy(pose.target);
  controls.update();
  renderer.render(scene, camera);
}

function captureViews(options = {}) {
  if (!currentGroup) return;
  const originalPosition = camera.position.clone();
  const originalTarget = controls.target.clone();
  const views = ["isometric", "front", "back", "left", "right", "top", "bottom"];
  const captures = views.map((view) => {
    setCameraView(view);
    return { view, url: renderer.domElement.toDataURL("image/png") };
  });
  camera.position.copy(originalPosition);
  controls.target.copy(originalTarget);
  controls.update();
  viewCapturesEl.innerHTML = captures
    .map(
      (capture) => `
        <figure>
          <img src="${capture.url}" alt="${capture.view} view of current CAD render" />
          <figcaption>${capture.view}</figcaption>
        </figure>
      `
    )
    .join("");
  if (!options.silent) setStatus("Captured isometric, front, back, left, right, top, and bottom debug views.", "ok");
}

function populateRenderStates(trace = [], finalDesign = latestDesign, finalAnalysis = latestAnalysis) {
  latestRenderStates = (trace || [])
    .filter((step) => step.content?.design_snapshot)
    .map((step, index) => ({
      label: `${index + 1}. after ${step.name}`,
      design: step.content.design_snapshot
    }));

  if (finalDesign) {
    latestRenderStates.push({ label: `Final committed design (${trace?.length || "current"} tool calls)`, design: finalDesign });
  }

  renderStateSelect.innerHTML = latestRenderStates.length
    ? latestRenderStates.map((state, index) => `<option value="${index}">${escapeHtml(state.label)}</option>`).join("")
    : `<option>No run loaded</option>`;
  renderStateSelect.disabled = latestRenderStates.length === 0;
  if (latestRenderStates.length) {
    renderStateSelect.value = String(latestRenderStates.length - 1);
    renderStateNote.textContent = "Viewer is rendering the latest committed design.";
  } else {
    renderStateNote.textContent = "Viewer is rendering the local sample.";
  }
  renderStateSelect.onchange = () => {
    const selected = latestRenderStates[Number(renderStateSelect.value)];
    if (!selected) return;
    renderDesign(selected.design, finalAnalysis || latestAnalysis);
    renderStateNote.textContent = selected.label.includes("Final")
      ? "Viewer is rendering the latest committed design."
      : `Viewer is rendering an intermediate snapshot: ${selected.label}.`;
  };
}

function renderBenchmarkResults(result) {
  if (!result?.results?.length) {
    benchmarkResultsEl.innerHTML = "";
    return;
  }

  benchmarkResultsEl.innerHTML = result.results
    .map((item) => {
      if (item.error) {
        return `
          <div class="benchmark-card error-card">
            <div>
              <span>${item.model}</span>
              <strong>error</strong>
            </div>
            <p>${item.error}</p>
          </div>
        `;
      }
      const best = item.best;
      const trace = item.trace.map((step) => `${step.iteration}: ${step.analysis.score}`).join(" → ");
      return `
        <div class="benchmark-card">
          <div>
            <span>${item.model}</span>
            <strong>${best.analysis.score}</strong>
          </div>
          <p>${best.design.title}</p>
          <small>scores ${trace}</small>
        </div>
      `;
    })
    .join("");
}

function markusFeedback(stats = {}, scadCode = "") {
  const code = scadCode.toLowerCase();
  const dimensions = stats.dimensions || {};
  const width = Number(dimensions.x || 0);
  const depth = Number(dimensions.y || 0);
  const height = Number(dimensions.z || 0);
  const components = Number(stats.connected_components || 0);
  const floating = Number(stats.floating_parts || Math.max(0, components - 1));
  const boundary = Number(stats.boundary_edges || 0);
  const nonManifold = Number(stats.non_manifold_edges || 0);
  const checks = [
    { name: "compile/render", pass: !stats.compile_error },
    { name: "single connected body", pass: components === 1 && floating === 0 },
    { name: "watertight topology", pass: stats.watertight === true && boundary === 0 && nonManifold === 0 },
    { name: "chair proportions", pass: height > Math.max(width, Math.abs(depth)) * 0.9 && height > 80 },
    { name: "seat/back structure", pass: code.includes("back") || code.includes("backrest") || height > 120 },
    { name: "armrests", pass: code.includes("armrest") || code.includes("arm rest") },
    { name: "central column", pass: code.includes("column") || code.includes("cylinder") },
    { name: "five-star base", pass: code.includes("spoke") || code.includes("star") || (code.match(/rotate\(/g) || []).length >= 4 },
    { name: "casters or feet", pass: code.includes("caster") || code.includes("wheel") || code.includes("foot") }
  ];
  const passed = checks.filter((check) => check.pass).length;
  const markus_score = Math.round((passed / checks.length) * 100);
  const missing = checks.filter((check) => !check.pass).map((check) => check.name);
  const should_stop = markus_score >= 78 && components === 1 && floating === 0 && !stats.compile_error;
  return {
    target: "IKEA Markus-like office chair heuristic, not full GLB distance",
    markus_score,
    should_stop,
    missing,
    topology: {
      connected_components: components,
      floating_parts: floating,
      boundary_edges: boundary,
      non_manifold_edges: nonManifold,
      watertight: stats.watertight === true
    },
    dimensions_mm: { width_x: width, depth_y: depth, height_z: height }
  };
}

function renderAgentSteps(steps = []) {
  if (!agentStepsEl) return;
  if (!steps.length) {
    agentStepsEl.innerHTML = "";
    return;
  }
  agentStepsEl.innerHTML = `
    <h3>Agent tool loop</h3>
    ${steps
      .map((step) => {
        const feedback = step.feedback || {};
        const stats = step.render_stats || {};
        return `
          <details class="agent-step" ${step.step === steps.length ? "open" : ""}>
            <summary>
              <span>Step ${step.step}</span>
              <strong>${feedback.markus_score ?? "?"}/100</strong>
            </summary>
            <p>${escapeHtml(step.rationale || step.error || "")}</p>
            <dl>
              <div><dt>tool</dt><dd>${escapeHtml(step.tool || "")}</dd></div>
              <div><dt>model</dt><dd>${escapeHtml(step.model || "")}</dd></div>
              <div><dt>components</dt><dd>${escapeHtml(String(stats.connected_components ?? "n/a"))}</dd></div>
              <div><dt>floating</dt><dd>${escapeHtml(String(stats.floating_parts ?? "n/a"))}</dd></div>
              <div><dt>watertight</dt><dd>${escapeHtml(String(stats.watertight ?? "n/a"))}</dd></div>
            </dl>
            ${feedback.missing?.length ? `<small>Missing: ${escapeHtml(feedback.missing.join(", "))}</small>` : "<small>Verifier says the current candidate is close enough for this scoped loop.</small>"}
          </details>
        `;
      })
      .join("")}
  `;
}

function renderTrace(trace) {
  if (!trace?.length) {
    traceEl.innerHTML = "";
    return;
  }

  traceEl.innerHTML = trace
    .map((step, index) => {
      const content =
        typeof step.content === "string"
          ? step.content
          : JSON.stringify(step.content, (key, value) => {
              if (value?.method && value?.element_results) {
                return {
                  method: value.method,
                  node_count: value.nodes?.length,
                  element_count: value.elements?.length || value.tets?.length,
                  max_stress_mpa: value.max_stress_mpa,
                  tip_deflection_mm: value.tip_deflection_mm || value.load_point_deflection_mm,
                  safety_factor: value.safety_factor,
                  mass_g: value.mass_g,
                  score: value.score,
                  force_vector_n: value.force_vector_n,
                  load_case: value.load_case,
                  top_elements: value.element_results.slice(0, 5)
                };
              }
              return value;
            }, 2);
      return `
        <details class="trace-step" ${index >= trace.length - 2 ? "open" : ""}>
          <summary>${index + 1}. ${step.role}${step.name ? ` / ${step.name}` : ""}</summary>
          <pre>${escapeHtml(content)}</pre>
        </details>
      `;
    })
    .join("");
}

function setActiveTab(name) {
  tabButtons.forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
  Object.entries(tabPanels).forEach(([key, panel]) => panel.classList.toggle("active", key === name));
}

function feedbackSummary(analysis) {
  if (!analysis) return {};
  return {
    score: analysis.score,
    mass_g: analysis.mass_g,
    max_stress_mpa: analysis.max_stress_mpa,
    max_strain_microstrain: analysis.max_strain_microstrain,
    safety_factor: analysis.safety_factor,
    tip_deflection_mm: analysis.tip_deflection_mm,
    thermal_delta_c_proxy: analysis.thermal_delta_c_proxy,
    load_case: analysis.load_case,
    stress_regions: analysis.stress_regions
  };
}

function llmMessagesFromTrace(trace = []) {
  return {
    system: trace.find((step) => step.role === "system")?.content || "",
    user: trace.find((step) => step.role === "user")?.content || ""
  };
}

function renderAgentLoop(run) {
  if (!run) {
    const empty = `<p class="empty-note">Run Generate Agent Loop or Run Tool Episode to inspect the CADForge loop.</p>`;
    agentLoopEl.innerHTML = empty;
    iterationsEl.innerHTML = empty;
    llmInputEl.innerHTML = empty;
    return;
  }

  if (run.type === "tool_episode") {
    const steps = run.trace || [];
    agentLoopEl.innerHTML = `
      <div class="loop-strip">
        <span>Prompt</span><span>CSG family</span><span>AST/CAD actions</span><span>Geometry validation</span><span>Structural check</span><span>Commit</span>
      </div>
      <h3>CADForge Tool Episode</h3>
      <div class="iteration-grid tool-grid">
        ${steps
          .map(
            (step, index) => `
              <div class="iteration-card">
                <span>Tool ${index + 1}</span>
                <strong>${escapeHtml(step.name || "tool")}</strong>
                <small>${escapeHtml(step.content?.result?.message || step.content?.result?.added_feature || step.content?.result?.engine || step.content?.result?.verdict || "state updated")}</small>
              </div>
            `
          )
          .join("")}
      </div>
    `;
    iterationsEl.innerHTML = `
      <h3>Design State After Each Tool</h3>
      ${steps
        .map(
          (step, index) => `
            <details class="trace-step" ${index >= run.trace.length - 2 ? "open" : ""}>
              <summary>${index + 1}. ${escapeHtml(step.name)} ${step.content?.design_snapshot?.features ? `(${step.content.design_snapshot.features.length} features)` : ""}</summary>
              <pre>${escapeHtml(JSON.stringify(step.content?.design_snapshot || step.content, null, 2))}</pre>
            </details>
          `
        )
        .join("")}
    `;
    const cadStep = steps.find((step) => step.name === "export_cadquery");
    const planner = run.planner || {};
    const plannerRounds = planner.rounds || [];
    const toolContexts = steps.map((step, index) => ({
      step: index + 1,
      tool: step.name,
      round: step.content?.round || null,
      note: plannerRounds.length
        ? "Sequential executor context inside a receding-horizon planner round."
        : "Sequential executor context. This is not a separate GPT call in the current implementation.",
      tool_input: step.content?.params || {},
      compact_observation_for_next_step: step.content?.result || null
    }));
    llmInputEl.innerHTML = `
      <p class="empty-note">${plannerRounds.length ? `Current architecture: ${plannerRounds.length} planner/replanner calls. Each call observes the current CAD/simulation state, proposes the next actions, then the environment executes the expanded tools.` : "Current architecture: one actual GPT planning call creates the high-level CAD plan, then the environment expands and executes the tool calls sequentially."}</p>
      ${plannerRounds.length
        ? plannerRounds
            .map(
              (round) => `
                <details class="trace-step" ${round.round === 1 ? "open" : ""}>
                  <summary>Actual LLM call ${round.round}: ${escapeHtml(round.kind || "planner")} via ${escapeHtml(round.source || "unknown")}</summary>
                  <pre>${escapeHtml(
                    JSON.stringify(
                      {
                        round: round.round,
                        source: round.source,
                        model: round.model,
                        system: round.system,
                        user: round.user,
                        planner_error: round.error || null,
                        observation: round.observation || null,
                        model_plan: round.plan || null
                      },
                      null,
                      2
                    )
                  )}</pre>
                </details>
              `
            )
            .join("")
        : `<details class="trace-step" open>
        <summary>Actual LLM call: ${planner.source === "openai_tool_planner" ? `GPT tool-planner input to ${escapeHtml(planner.model || "model")}` : "local fallback planner"}</summary>
        <pre>${escapeHtml(
          JSON.stringify(
            {
              user_prompt: run.prompt || promptInput.value,
              source: planner.source || "unknown",
              system: planner.system || "Local deterministic planner was used.",
              user: planner.user || run.prompt || promptInput.value,
              planner_error: planner.error || null,
              model_plan: planner.plan || null,
              selected_family: steps[0]?.content?.params?.family || "unknown",
              available_tools: ["create_design_family", "set_material", "add_feature", "set_load", "export_cadquery", "run_fea", "commit_design"],
              cadquery_export: cadStep?.content?.result || null
            },
            null,
            2
          )
        )}</pre>
      </details>`}
      <details class="trace-step">
        <summary>Sequential tool contexts (${steps.length} executed tools)</summary>
        <pre>${escapeHtml(JSON.stringify(toolContexts, null, 2))}</pre>
      </details>
    `;
    return;
  }

  const iterations = run.iterations || [];
  agentLoopEl.innerHTML = `
    <div class="loop-strip">
      <span>Prompt</span><span>LLM code-CAD JSON</span><span>CADForge verifier</span><span>Feedback summary</span><span>Next iteration</span>
    </div>
    <h3>CADForge Iterations</h3>
  `;
  iterationsEl.innerHTML = `
    <h3>Iteration Scores</h3>
    <div class="iteration-grid">
      ${iterations
        .map(
          (iteration) => `
            <div class="iteration-card">
              <span>Iteration ${iteration.iteration}</span>
              <strong>${iteration.analysis?.score ?? "n/a"}</strong>
              <small>${escapeHtml(iteration.design?.title || "Untitled design")}</small>
            </div>
          `
        )
        .join("")}
    </div>
  `;
  llmInputEl.innerHTML = `
    <h3>LLM Inputs</h3>
    ${iterations
      .map((iteration) => {
        const messages = llmMessagesFromTrace(iteration.trace);
        return `
          <details class="trace-step">
            <summary>Iteration ${iteration.iteration} input to ${escapeHtml(iteration.model || run.model || "model")}</summary>
            <pre>${escapeHtml(
              JSON.stringify(
                {
                  system: messages.system,
                  user: messages.user,
                  feedback_summary_sent_next_time: feedbackSummary(iteration.analysis)
                },
                null,
                2
              )
            )}</pre>
          </details>
        `;
      })
      .join("")}
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function loadSample() {
  setStatus("Loading local sample...");
  const response = await fetch("/api/sample");
  const result = await response.json();
  renderDesign(result.design, result.analysis);
  latestAgentRun = null;
  renderAgentLoop(latestAgentRun);
  renderTrace([]);
  populateRenderStates([], result.design, result.analysis);
  setStatus("Loaded local sample.", "ok");
}

async function generateDesign() {
  setStatus(`Running receding-horizon CAD agent with ${toolBudgetInput.value} tool calls...`, "working");
  benchmarkResultsEl.innerHTML = "";
  generateButton.disabled = true;
  try {
    const response = await fetch("/api/receding-agent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: promptInput.value, target_tool_calls: Number(toolBudgetInput.value) })
    });
    const result = await response.json();
    if (!response.ok) {
      if (result.design && result.analysis) renderDesign(result.design, result.analysis);
      setStatus(result.error || "Agent generation failed.", "error");
      return;
    }
    renderDesign(result.design, result.analysis);
    renderTrace(result.trace);
    latestAgentRun = { type: "tool_episode", prompt: promptInput.value, trace: result.trace, planner: result.planner };
    renderAgentLoop(latestAgentRun);
    populateRenderStates(result.trace, result.design, result.analysis);
    setActiveTab("loop");
    const plannerLabel = result.planner?.source === "receding_horizon" ? `${result.planner.rounds?.length || 1} planner calls` : "single planner";
    setStatus(`Agent loop complete: ${result.trace.length} tool calls, ${plannerLabel}, score ${result.analysis.score}.`, "ok");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Agent generation failed.", "error");
  } finally {
    generateButton.disabled = false;
  }
}

async function benchmarkDesigns() {
  setStatus("Running GPT-5.4 iterative benchmark...", "working");
  benchmarkButton.disabled = true;
  generateButton.disabled = true;
  benchmarkResultsEl.innerHTML = "";
  try {
    const response = await fetch("/api/benchmark", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: promptInput.value,
        system_prompt: systemPromptInput.value,
        models: ["gpt-5.4"],
        iterations: 3
      })
    });
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "Benchmark failed.", "error");
      return;
    }

    renderBenchmarkResults(result);
    const validResults = result.results.filter((item) => item.best);
    if (!validResults.length) {
      setStatus("Benchmark finished, but no model produced a valid design.", "error");
      return;
    }

    const winner = validResults
      .map((item) => item.best)
      .sort((a, b) => b.analysis.score - a.analysis.score)[0];
    renderDesign(winner.design, winner.analysis);
    renderTrace(winner.trace);
    const winningResult = validResults.find((item) => item.best === winner) || validResults[0];
    latestAgentRun = {
      type: "llm_benchmark",
      model: winningResult.model,
      iterations: winningResult.trace
    };
    renderAgentLoop(latestAgentRun);
    populateRenderStates(winner.trace || [], winner.design, winner.analysis);
    setActiveTab("iterations");
    setStatus(`Benchmark complete in ${(result.elapsed_ms / 1000).toFixed(1)}s. Rendering best design from ${winner.model}.`, "ok");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Benchmark failed.", "error");
  } finally {
    benchmarkButton.disabled = false;
    generateButton.disabled = false;
  }
}

async function runToolEpisode() {
  setStatus("Running Python tool episode...", "working");
  toolEpisodeButton.disabled = true;
  benchmarkResultsEl.innerHTML = "";
  try {
    const response = await fetch("/api/tool-episode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: promptInput.value, target_tool_calls: Number(toolBudgetInput.value) })
    });
    const result = await response.json();
    if (!response.ok) {
      setStatus(result.error || "Tool episode failed.", "error");
      return;
    }
    renderDesign(result.design, result.analysis);
    renderTrace(result.trace);
    latestAgentRun = { type: "tool_episode", prompt: promptInput.value, trace: result.trace, planner: result.planner };
    renderAgentLoop(latestAgentRun);
    populateRenderStates(result.trace, result.design, result.analysis);
    setActiveTab("loop");
    const plannerLabel = result.planner?.source === "openai_tool_planner" ? `planned by ${result.planner.model}` : "local fallback planner";
    setStatus(`Tool episode complete: ${result.trace.length} actions, ${plannerLabel}, score ${result.analysis.score}.`, "ok");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Tool episode failed.", "error");
  } finally {
    toolEpisodeButton.disabled = false;
  }
}

async function callScadAgentTool(endpoint, payload) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "SCAD generation failed.");
  }
  return result;
}

async function generateScad(iterate = false) {
  const button = iterate ? iterateScadButton : generateScadButton;
  const maxSteps = iterate ? 1 : 5;
  const agentSteps = [];
  setStatus(iterate ? "Asking model to revise the SCAD code..." : "Running multi-step SCAD agent against the Markus chair target...", "working");
  if (button) button.disabled = true;
  renderAgentSteps(agentSteps);
  try {
    for (let step = 1; step <= maxSteps; step += 1) {
      const isInitial = step === 1 && !iterate;
      const endpoint = isInitial ? "/api/scad-generate" : "/api/scad-iterate";
      const tool = isInitial ? "generate_scad_candidate" : "iterate_scad_with_render_feedback";
      setStatus(`Tool ${step}/${maxSteps}: ${tool}`, "working");
      const result = await callScadAgentTool(endpoint, {
        prompt: promptInput.value,
        scad_code: scadCodeInput.value,
        render_stats: latestScadStats
      });
      scadCodeInput.value = result.scad_code || "";
      scadOutputEl.textContent = result.rationale || "Generated SCAD code.";

      let feedback;
      try {
        renderScadFromEditor();
        feedback = markusFeedback(latestScadStats, scadCodeInput.value);
      } catch (renderError) {
        latestScadStats = {
          compile_error: renderError instanceof Error ? renderError.message : "SCAD render failed.",
          connected_components: 0,
          floating_parts: 999,
          boundary_edges: 999,
          non_manifold_edges: 999,
          watertight: false
        };
        feedback = markusFeedback(latestScadStats, scadCodeInput.value);
        setStatus(latestScadStats.compile_error, "error");
      }

      agentSteps.push({
        step,
        tool,
        source: result.source,
        model: result.model,
        rationale: result.rationale,
        render_stats: latestScadStats,
        feedback
      });
      renderAgentSteps(agentSteps);
      jsonEl.textContent = JSON.stringify({ latest_result: result, agent_steps: agentSteps }, null, 2);

      if (feedback.should_stop) {
        setStatus(`Stopped after ${step} tool calls: Markus heuristic ${feedback.markus_score}/100 with connected topology.`, "ok");
        return;
      }
    }
    const finalFeedback = agentSteps[agentSteps.length - 1]?.feedback;
    setStatus(`Completed ${agentSteps.length} tool calls. Markus heuristic ${finalFeedback?.markus_score ?? "?"}/100.`, "ok");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "SCAD generation failed.", "error");
    agentSteps.push({
      step: agentSteps.length + 1,
      tool: "agent_error",
      error: error instanceof Error ? error.message : "SCAD generation failed.",
      render_stats: latestScadStats || {},
      feedback: markusFeedback(latestScadStats || {}, scadCodeInput.value)
    });
    renderAgentSteps(agentSteps);
  } finally {
    if (button) button.disabled = false;
  }
}

function exportStl() {
  if (!currentGroup) {
    setStatus("Load or generate a design first.", "error");
    return;
  }
  const exporter = new STLExporter();
  const stl = exporter.parse(currentGroup);
  const blob = new Blob([stl], { type: "model/stl" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "cadforge-design.stl";
  link.click();
  URL.revokeObjectURL(url);
  setStatus("Exported STL from the rendered mesh.", "ok");
}

if (generateButton) generateButton.addEventListener("click", generateDesign);
if (benchmarkButton) benchmarkButton.addEventListener("click", benchmarkDesigns);
if (toolEpisodeButton) toolEpisodeButton.addEventListener("click", runToolEpisode);
if (sampleButton) sampleButton.addEventListener("click", loadSample);
if (exportButton) exportButton.addEventListener("click", exportStl);
if (captureViewsButton) captureViewsButton.addEventListener("click", () => captureViews());
if (generateScadButton) generateScadButton.addEventListener("click", () => generateScad(false));
if (generateCadqueryButton) generateCadqueryButton.addEventListener("click", generateCadqueryCode);
if (envGenerateCadqueryButton) envGenerateCadqueryButton.addEventListener("click", () => runCadqueryReplStep({ revise: false }));
if (envReviseCadqueryButton) envReviseCadqueryButton.addEventListener("click", () => runCadqueryReplStep({ revise: true }));
if (envEvaluateCadqueryButton) envEvaluateCadqueryButton.addEventListener("click", () => evaluateCadqueryEnv({ rewardMode: "full" }));
if (envLoadIdealButton) envLoadIdealButton.addEventListener("click", loadIdealCadqueryCode);
if (renderCadqueryButton) renderCadqueryButton.addEventListener("click", renderCadqueryCode);
if (testCadqueryBackendButton) testCadqueryBackendButton.addEventListener("click", testCadqueryBackend);
if (loadCadquerySampleButton) loadCadquerySampleButton.addEventListener("click", () => loadCadquerySampleCode({ render: false }));
if (iterateScadButton) iterateScadButton.addEventListener("click", () => generateScad(true));
if (renderScadButton) renderScadButton.addEventListener("click", () => {
  try {
    renderScadFromEditor();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "SCAD render failed.", "error");
  }
});
if (loadScadExampleButton) loadScadExampleButton.addEventListener("click", () => {
  scadCodeInput.value = `difference() {
  union() {
    cube([90, 60, 7]);
    translate([10, 10, 7]) cylinder(h=58, r=5, $fn=32);
    translate([75, 10, 7]) cylinder(h=58, r=5, $fn=32);
    translate([10, 45, 7]) cylinder(h=58, r=5, $fn=32);
    translate([75, 45, 7]) cylinder(h=58, r=5, $fn=32);
    translate([0, 47, 60]) cube([90, 9, 58]);
    translate([5, 8, 32]) cube([80, 6, 6]);
    translate([5, 46, 32]) cube([80, 6, 6]);
  }
  translate([25, 30, -1]) cylinder(h=10, r=5, $fn=32);
}`;
  renderScadFromEditor();
});
if (toolBudgetInput && toolBudgetValue) toolBudgetInput.addEventListener("input", () => {
  toolBudgetValue.textContent = toolBudgetInput.value;
});
presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    promptInput.value = promptPresets[button.dataset.preset] || promptInput.value;
    setStatus(`Loaded ${button.textContent} prompt.`, "ok");
  });
});
tabButtons.forEach((button) => button.addEventListener("click", () => setActiveTab(button.dataset.tab)));

function animate() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

animate();
if (isOpenScadPage) {
  try {
    renderScadFromEditor();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "SCAD render failed.", "error");
  }
}

if (isCadQueryRendererPage) {
  testCadqueryBackend();
} else if (isCadQueryEnvPage) {
  loadIdealCadqueryCode();
} else if (isCadQueryGeneratorPage) {
  loadCadquerySampleCode({ render: true });
}

if (systemPromptInput) {
  fetch("/api/system-prompt")
    .then((response) => response.json())
    .then((result) => {
      systemPromptInput.value = result.system_prompt || "";
    })
    .catch(() => {
      systemPromptInput.value = "";
    });
}
