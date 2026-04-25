import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { spawnSync } from "node:child_process";
import OpenAI from "openai";
import { zodTextFormat } from "openai/helpers/zod";
import { z } from "zod";

function loadEnv() {
  dotenv.config({ path: "../.env" });
  dotenv.config({ path: ".env" });
}

loadEnv();

const app = express();
const port = Number(process.env.PORT || 8787);
const pythonBin =
  process.env.PYTHON_SIM_BIN ||
  "/Users/sanju/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";

app.use(cors());
app.use(express.json({ limit: "1mb" }));

const FeatureSchema = z.object({
  type: z.enum([
    "rib",
    "lightening_hole",
    "boss",
    "fillet_marker",
    "hook_curve",
    "clamp_jaw",
    "stator_ring",
    "stator_tooth",
    "seat_panel",
    "chair_leg",
    "chair_back",
    "chair_crossbar",
    "decorative_curve",
    "generic_panel",
    "support_tube",
    "curved_tube",
    "flat_foot",
    "armrest",
    "headrest",
    "tabletop",
    "table_leg"
  ]),
  x: z.number(),
  y: z.number(),
  x2: z.number(),
  y2: z.number(),
  width: z.number(),
  height: z.number(),
  radius: z.number(),
  note: z.string()
});

const ToolActionParamSchema = z
  .object({
    family: z.string().optional(),
    material: z.string().optional(),
    type: z.string().optional(),
    x: z.number().optional(),
    y: z.number().optional(),
    x2: z.number().optional(),
    y2: z.number().optional(),
    width: z.number().optional(),
    height: z.number().optional(),
    radius: z.number().optional(),
    note: z.string().optional(),
    point_mm: z.array(z.number()).optional(),
    vector_n: z.array(z.number()).optional(),
    length_mm: z.number().optional(),
    width_mm: z.number().optional(),
    thickness_mm: z.number().optional(),
    start: z.array(z.number()).optional(),
    end: z.array(z.number()).optional(),
    id: z.string().optional()
  })
  .passthrough();

const ToolActionSchema = z.object({
  tool: z.enum([
    "create_design_family",
    "set_material",
    "set_envelope",
    "add_feature",
    "add_mount_hole",
    "add_rib",
    "add_lightening_hole",
    "set_load",
    "observe_design",
    "measure_clearance",
    "check_constraints",
    "visual_snapshot",
    "critique_geometry",
    "export_cadquery",
    "run_fea",
    "commit_design"
  ]),
  params: ToolActionParamSchema
});

const ToolPlanSchema = z.object({
  family: z.enum(["ribbed_cantilever_bracket", "wall_hook", "torque_clamp", "motor_stator", "chair", "bike_fixture", "table", "freeform_object"]),
  rationale: z.string(),
  actions: z.array(ToolActionSchema).min(5).max(20)
});

const DesignSchema = z.object({
  title: z.string(),
  rationale: z.string(),
  material: z.enum(["aluminum_6061", "aluminum_7075", "pla", "petg", "steel_1018"]),
  load_newtons: z.number(),
  load_point_x_mm: z.number(),
  load_point_y_mm: z.number(),
  base_length_mm: z.number(),
  base_width_mm: z.number(),
  base_thickness_mm: z.number(),
  fixed_holes: z.array(
    z.object({
      x: z.number(),
      y: z.number(),
      radius: z.number()
    })
  ),
  features: z.array(FeatureSchema),
  expected_failure_mode: z.string(),
  action_plan: z.array(z.string())
});

const materials = {
  aluminum_6061: { densityGcm3: 2.7, yieldMpa: 276, youngMpa: 69000, thermalWmK: 167 },
  aluminum_7075: { densityGcm3: 2.81, yieldMpa: 503, youngMpa: 71700, thermalWmK: 130 },
  pla: { densityGcm3: 1.24, yieldMpa: 55, youngMpa: 3500, thermalWmK: 0.13 },
  petg: { densityGcm3: 1.27, yieldMpa: 50, youngMpa: 2100, thermalWmK: 0.2 },
  steel_1018: { densityGcm3: 7.87, yieldMpa: 370, youngMpa: 200000, thermalWmK: 51 }
};

const allowedToolNames = new Set([
  "create_design_family",
  "set_material",
  "set_envelope",
  "add_feature",
  "add_mount_hole",
  "add_rib",
  "add_lightening_hole",
  "set_load",
  "observe_design",
  "measure_clearance",
  "check_constraints",
  "visual_snapshot",
  "critique_geometry",
  "export_cadquery",
  "run_fea",
  "commit_design"
]);

const allowedFamilies = new Set(["ribbed_cantilever_bracket", "wall_hook", "torque_clamp", "motor_stator", "chair", "bike_fixture", "table", "freeform_object"]);
const allowedFeatureTypes = new Set([
  "rib",
  "lightening_hole",
  "boss",
  "fillet_marker",
  "hook_curve",
  "clamp_jaw",
  "stator_ring",
  "stator_tooth",
  "seat_panel",
  "chair_leg",
  "chair_back",
  "chair_crossbar",
  "decorative_curve",
  "generic_panel",
  "support_tube",
  "curved_tube",
  "flat_foot",
  "armrest",
  "headrest",
  "tabletop",
  "table_leg"
]);
const materialAliases = {
  aluminum: "aluminum_6061",
  "6061": "aluminum_6061",
  "6061 aluminum": "aluminum_6061",
  aluminium: "aluminum_6061",
  steel: "steel_1018",
  mild_steel: "steel_1018",
  mildsteel: "steel_1018",
  plastic: "pla"
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function distance(x1, y1, x2, y2) {
  return Math.hypot(x2 - x1, y2 - y1);
}

function solveLinearSystem(matrix, vector) {
  const n = vector.length;
  const a = matrix.map((row, i) => [...row, vector[i]]);

  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < n; row += 1) {
      if (Math.abs(a[row][col]) > Math.abs(a[pivot][col])) pivot = row;
    }
    if (Math.abs(a[pivot][col]) < 1e-9) {
      throw new Error("FEA stiffness matrix is singular; the design is under-constrained.");
    }
    [a[col], a[pivot]] = [a[pivot], a[col]];

    const divisor = a[col][col];
    for (let j = col; j <= n; j += 1) a[col][j] /= divisor;

    for (let row = 0; row < n; row += 1) {
      if (row === col) continue;
      const factor = a[row][col];
      for (let j = col; j <= n; j += 1) a[row][j] -= factor * a[col][j];
    }
  }

  return a.map((row) => row[n]);
}

function matMul(a, b) {
  return a.map((row) => b[0].map((_, col) => row.reduce((sum, value, i) => sum + value * b[i][col], 0)));
}

function transpose(matrix) {
  return matrix[0].map((_, col) => matrix.map((row) => row[col]));
}

function frameElementStiffness(E, A, I, L, c, s) {
  const EA_L = (E * A) / L;
  const EI = E * I;
  const L2 = L * L;
  const L3 = L2 * L;
  const k = [
    [EA_L, 0, 0, -EA_L, 0, 0],
    [0, (12 * EI) / L3, (6 * EI) / L2, 0, (-12 * EI) / L3, (6 * EI) / L2],
    [0, (6 * EI) / L2, (4 * EI) / L, 0, (-6 * EI) / L2, (2 * EI) / L],
    [-EA_L, 0, 0, EA_L, 0, 0],
    [0, (-12 * EI) / L3, (-6 * EI) / L2, 0, (12 * EI) / L3, (-6 * EI) / L2],
    [0, (6 * EI) / L2, (2 * EI) / L, 0, (-6 * EI) / L2, (4 * EI) / L]
  ];

  const t = [
    [c, s, 0, 0, 0, 0],
    [-s, c, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0],
    [0, 0, 0, c, s, 0],
    [0, 0, 0, -s, c, 0],
    [0, 0, 0, 0, 0, 1]
  ];

  return matMul(transpose(t), matMul(k, t));
}

function frameLocalStiffness(E, A, I, L) {
  const EA_L = (E * A) / L;
  const EI = E * I;
  const L2 = L * L;
  const L3 = L2 * L;
  return [
    [EA_L, 0, 0, -EA_L, 0, 0],
    [0, (12 * EI) / L3, (6 * EI) / L2, 0, (-12 * EI) / L3, (6 * EI) / L2],
    [0, (6 * EI) / L2, (4 * EI) / L, 0, (-6 * EI) / L2, (2 * EI) / L],
    [-EA_L, 0, 0, EA_L, 0, 0],
    [0, (-12 * EI) / L3, (-6 * EI) / L2, 0, (12 * EI) / L3, (-6 * EI) / L2],
    [0, (6 * EI) / L2, (2 * EI) / L, 0, (-6 * EI) / L2, (4 * EI) / L]
  ];
}

function buildFrameModel(design, material, volumeAdjustments) {
  const length = clamp(design.base_length_mm, 30, 240);
  const width = clamp(design.base_width_mm, 10, 120);
  const thickness = clamp(design.base_thickness_mm, 1, 30);
  const loadX = clamp(Math.abs(design.load_point_x_mm), 5, length);
  const loadZ = thickness / 2;
  const nodeMap = new Map();
  const nodes = [];
  const elements = [];

  function node(x, z, label) {
    const key = `${x.toFixed(3)}:${z.toFixed(3)}`;
    if (nodeMap.has(key)) return nodeMap.get(key);
    const id = nodes.length;
    nodes.push({ id, x, z, label });
    nodeMap.set(key, id);
    return id;
  }

  const stations = new Set([0, loadX, length]);
  for (const feature of design.features || []) {
    stations.add(clamp(feature.x, 0, length));
    if (feature.type === "rib") stations.add(clamp(feature.x2, 0, length));
  }
  const xs = [...stations].sort((a, b) => a - b);

  const holeArea = (design.fixed_holes || []).reduce((sum, hole) => sum + Math.PI * Math.pow(clamp(hole.radius, 1, 10), 2), 0);
  const lighteningArea = (design.features || [])
    .filter((feature) => feature.type === "lightening_hole")
    .reduce((sum, feature) => sum + Math.PI * Math.pow(clamp(feature.radius, 1, width / 3), 2), 0);
  const areaReduction = clamp((holeArea + lighteningArea) / Math.max(length * width, 1), 0, 0.55);
  const baseArea = Math.max(width * thickness * (1 - areaReduction), width * thickness * 0.35);
  const baseI = Math.max((width * Math.pow(thickness, 3)) / 12 * Math.pow(1 - areaReduction, 1.8), (width * Math.pow(thickness, 3)) / 12 * 0.2);

  for (let i = 0; i < xs.length - 1; i += 1) {
    const n1 = node(xs[i], thickness / 2, "base");
    const n2 = node(xs[i + 1], thickness / 2, "base");
    if (Math.abs(xs[i + 1] - xs[i]) > 0.5) {
      elements.push({ n1, n2, A: baseArea, I: baseI, c: thickness / 2, label: "base plate beam" });
    }
  }

  for (const feature of design.features || []) {
    if (feature.type !== "rib") continue;
    const x1 = clamp(feature.x, 0, length);
    const x2 = clamp(feature.x2, 0, length);
    const ribHeight = clamp(feature.height, 1, 60);
    const ribWidth = clamp(feature.width, 1, 20);
    const z1 = thickness / 2;
    const z2 = thickness / 2 + ribHeight;
    const n1 = node(x1, z1, feature.note || "rib foot");
    const n2 = node(x2, z2, feature.note || "rib crown");
    const A = Math.max(ribWidth * ribHeight, 1);
    const I = Math.max((ribWidth * Math.pow(ribHeight, 3)) / 12, 1);
    elements.push({ n1, n2, A, I, c: ribHeight / 2, label: feature.note || "rib frame element" });
  }

  for (const feature of design.features || []) {
    if (feature.type !== "boss") continue;
    const x = clamp(feature.x, 0, length);
    const height = clamp(feature.height, 1, 40);
    const radius = clamp(feature.radius, 1, 20);
    const n1 = node(x, thickness / 2, "boss base");
    const n2 = node(x, thickness / 2 + height, "boss top");
    const A = Math.PI * radius * radius;
    const I = (Math.PI * Math.pow(radius, 4)) / 4;
    elements.push({ n1, n2, A, I, c: radius, label: feature.note || "load boss" });
  }

  const fixedNode = node(0, thickness / 2, "fixed edge");
  const loadNode = node(loadX, loadZ, "load point");

  return {
    nodes,
    elements,
    fixedNode,
    loadNode,
    load: Math.abs(design.load_newtons),
    material,
    volumeAdjustments,
    length,
    width,
    thickness
  };
}

function runFrameFea(design, material, volumeAdjustments) {
  const model = buildFrameModel(design, material, volumeAdjustments);
  const dofCount = model.nodes.length * 3;
  const K = Array.from({ length: dofCount }, () => Array(dofCount).fill(0));
  const F = Array(dofCount).fill(0);

  for (const element of model.elements) {
    const n1 = model.nodes[element.n1];
    const n2 = model.nodes[element.n2];
    const dx = n2.x - n1.x;
    const dz = n2.z - n1.z;
    const L = Math.max(Math.hypot(dx, dz), 1e-6);
    const c = dx / L;
    const s = dz / L;
    const kg = frameElementStiffness(material.youngMpa, element.A, element.I, L, c, s);
    const dofs = [element.n1 * 3, element.n1 * 3 + 1, element.n1 * 3 + 2, element.n2 * 3, element.n2 * 3 + 1, element.n2 * 3 + 2];
    for (let i = 0; i < 6; i += 1) {
      for (let j = 0; j < 6; j += 1) K[dofs[i]][dofs[j]] += kg[i][j];
    }
  }

  F[model.loadNode * 3 + 1] = -model.load;

  const fixedDofs = new Set([model.fixedNode * 3, model.fixedNode * 3 + 1, model.fixedNode * 3 + 2]);
  const freeDofs = Array.from({ length: dofCount }, (_, i) => i).filter((i) => !fixedDofs.has(i));
  const Kff = freeDofs.map((row) => freeDofs.map((col) => K[row][col]));
  const Ff = freeDofs.map((row) => F[row]);
  const Uf = solveLinearSystem(Kff, Ff);
  const U = Array(dofCount).fill(0);
  freeDofs.forEach((dof, index) => {
    U[dof] = Uf[index];
  });

  let maxStress = 0;
  let maxStrain = 0;
  const elementResults = [];
  for (const element of model.elements) {
    const n1 = model.nodes[element.n1];
    const n2 = model.nodes[element.n2];
    const dx = n2.x - n1.x;
    const dz = n2.z - n1.z;
    const L = Math.max(Math.hypot(dx, dz), 1e-6);
    const c = dx / L;
    const s = dz / L;
    const t = [
      [c, s, 0, 0, 0, 0],
      [-s, c, 0, 0, 0, 0],
      [0, 0, 1, 0, 0, 0],
      [0, 0, 0, c, s, 0],
      [0, 0, 0, -s, c, 0],
      [0, 0, 0, 0, 0, 1]
    ];
    const dofs = [element.n1 * 3, element.n1 * 3 + 1, element.n1 * 3 + 2, element.n2 * 3, element.n2 * 3 + 1, element.n2 * 3 + 2];
    const ug = dofs.map((dof) => [U[dof]]);
    const ul = matMul(t, ug).map((row) => row[0]);
    const fl = matMul(frameLocalStiffness(material.youngMpa, element.A, element.I, L), ul.map((value) => [value])).map((row) => row[0]);
    const axialStress = Math.max(Math.abs(fl[0]), Math.abs(fl[3])) / Math.max(element.A, 1);
    const bendingStress = Math.max(Math.abs(fl[2]), Math.abs(fl[5])) * element.c / Math.max(element.I, 1);
    const stress = axialStress + bendingStress;
    const strain = stress / material.youngMpa;
    maxStress = Math.max(maxStress, stress);
    maxStrain = Math.max(maxStrain, strain);
    elementResults.push({
      label: element.label,
      n1: element.n1,
      n2: element.n2,
      stress_mpa: Number(stress.toFixed(3)),
      strain_microstrain: Number((strain * 1_000_000).toFixed(1)),
      utilization: Number(clamp(stress / material.yieldMpa, 0, 1).toFixed(3))
    });
  }

  const displacements = model.nodes.map((node) => ({
    id: node.id,
    x: Number(node.x.toFixed(3)),
    z: Number(node.z.toFixed(3)),
    ux_mm: Number(U[node.id * 3].toFixed(6)),
    uz_mm: Number(U[node.id * 3 + 1].toFixed(6)),
    rotation_rad: Number(U[node.id * 3 + 2].toFixed(6)),
    magnitude_mm: Number(Math.hypot(U[node.id * 3], U[node.id * 3 + 1]).toFixed(6))
  }));
  const loadDisp = displacements[model.loadNode];

  return {
    method: "2D Euler-Bernoulli frame FEA",
    nodes: model.nodes,
    elements: model.elements,
    element_results: elementResults,
    displacements,
    max_stress_mpa: maxStress,
    max_strain: maxStrain,
    load_point_deflection_mm: Math.abs(loadDisp?.uz_mm || 0),
    force_vector_n: [0, 0, -Number(model.load.toFixed(2))]
  };
}

function invertMatrix(matrix) {
  const n = matrix.length;
  const a = matrix.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < n; row += 1) {
      if (Math.abs(a[row][col]) > Math.abs(a[pivot][col])) pivot = row;
    }
    if (Math.abs(a[pivot][col]) < 1e-12) throw new Error("Matrix is singular.");
    [a[col], a[pivot]] = [a[pivot], a[col]];
    const divisor = a[col][col];
    for (let j = 0; j < 2 * n; j += 1) a[col][j] /= divisor;
    for (let row = 0; row < n; row += 1) {
      if (row === col) continue;
      const factor = a[row][col];
      for (let j = 0; j < 2 * n; j += 1) a[row][j] -= factor * a[col][j];
    }
  }
  return a.map((row) => row.slice(n));
}

function determinant4(matrix) {
  const m = matrix.map((row) => [...row]);
  let det = 1;
  for (let col = 0; col < 4; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < 4; row += 1) {
      if (Math.abs(m[row][col]) > Math.abs(m[pivot][col])) pivot = row;
    }
    if (Math.abs(m[pivot][col]) < 1e-12) return 0;
    if (pivot !== col) {
      [m[col], m[pivot]] = [m[pivot], m[col]];
      det *= -1;
    }
    det *= m[col][col];
    const divisor = m[col][col];
    for (let row = col + 1; row < 4; row += 1) {
      const factor = m[row][col] / divisor;
      for (let j = col; j < 4; j += 1) m[row][j] -= factor * m[col][j];
    }
  }
  return det;
}

function isotropicElasticityMatrix(E, nu = 0.33) {
  const lambda = (E * nu) / ((1 + nu) * (1 - 2 * nu));
  const mu = E / (2 * (1 + nu));
  return [
    [lambda + 2 * mu, lambda, lambda, 0, 0, 0],
    [lambda, lambda + 2 * mu, lambda, 0, 0, 0],
    [lambda, lambda, lambda + 2 * mu, 0, 0, 0],
    [0, 0, 0, mu, 0, 0],
    [0, 0, 0, 0, mu, 0],
    [0, 0, 0, 0, 0, mu]
  ];
}

function tetraElementStiffness(points, material) {
  const m = points.map((p) => [1, p.x, p.y, p.z]);
  const det = determinant4(m);
  const volume = Math.abs(det) / 6;
  if (volume < 1e-8) return null;
  const inv = invertMatrix(m);
  const b = [];
  const c = [];
  const d = [];
  for (let i = 0; i < 4; i += 1) {
    b.push(inv[1][i]);
    c.push(inv[2][i]);
    d.push(inv[3][i]);
  }

  const B = Array.from({ length: 6 }, () => Array(12).fill(0));
  for (let i = 0; i < 4; i += 1) {
    const col = 3 * i;
    B[0][col] = b[i];
    B[1][col + 1] = c[i];
    B[2][col + 2] = d[i];
    B[3][col] = c[i];
    B[3][col + 1] = b[i];
    B[4][col + 1] = d[i];
    B[4][col + 2] = c[i];
    B[5][col] = d[i];
    B[5][col + 2] = b[i];
  }

  const D = isotropicElasticityMatrix(material.youngMpa);
  const Ke = matMul(transpose(B), matMul(D, B)).map((row) => row.map((value) => value * volume));
  return { Ke, B, D, volume };
}

function inferLoadCase(prompt, design) {
  const text = String(prompt || "").toLowerCase();
  let loadPointX = clamp(Math.abs(design.load_point_x_mm), 5, design.base_length_mm);
  let loadPointY = clamp(design.load_point_y_mm || 0, -design.base_width_mm / 2, design.base_width_mm / 2);
  let loadPointZ = design.base_thickness_mm;
  const bosses = (design.features || []).filter((feature) => feature.type === "boss");
  if (bosses.length) {
    const nearestBoss = bosses
      .slice()
      .sort((a, b) => distance(a.x, a.y, loadPointX, loadPointY) - distance(b.x, b.y, loadPointX, loadPointY))[0];
    loadPointX = nearestBoss.x;
    loadPointY = nearestBoss.y;
    loadPointZ = design.base_thickness_mm + Math.max(nearestBoss.height, 1);
  }
  const staticFactor = text.includes("impact") ? 3 : text.includes("cyclic") || text.includes("fatigue") ? 1.5 : 1;
  const torqueMatch = text.match(/(\d+(?:\.\d+)?)\s*(?:n\s*[-*]?\s*m|nm|newton\s*meter)/i);
  if (torqueMatch) {
    const torqueNm = Number(torqueMatch[1]);
    const equivalentForce = (torqueNm * 1000) / Math.max(loadPointX, 1);
    return {
      type: "torque_as_force_couple_proxy",
      effective_load_n: equivalentForce * staticFactor,
      nominal_load_n: equivalentForce,
      factor: staticFactor,
      load_point: [loadPointX, loadPointY, loadPointZ],
      vector_n: [0, 0, -Number((equivalentForce * staticFactor).toFixed(2))],
      note: `${torqueNm} Nm converted to equivalent tip force using lever arm ${loadPointX} mm.`
    };
  }

  return {
    type: text.includes("chair") ? "distributed_downward_proxy" : "cantilever_tip_load",
    effective_load_n: Math.abs(design.load_newtons) * staticFactor,
    nominal_load_n: Math.abs(design.load_newtons),
    factor: staticFactor,
    load_point: [loadPointX, loadPointY, loadPointZ],
    vector_n: [0, 0, -Number((Math.abs(design.load_newtons) * staticFactor).toFixed(2))],
    note: "Defaulted to fixed left face and downward load at the free tip/load boss."
  };
}

function pointInFeatureVolume(point, design) {
  const { x, y, z } = point;
  const length = design.base_length_mm;
  const halfWidth = design.base_width_mm / 2;
  const thickness = design.base_thickness_mm;
  let solid = x >= 0 && x <= length && y >= -halfWidth && y <= halfWidth && z >= 0 && z <= thickness;

  if (solid && z <= thickness) {
    for (const hole of design.fixed_holes || []) {
      if (Math.hypot(x - hole.x, y - hole.y) < hole.radius) solid = false;
    }
    for (const feature of design.features || []) {
      if (feature.type === "lightening_hole" && Math.hypot(x - feature.x, y - feature.y) < feature.radius) solid = false;
    }
  }

  for (const feature of design.features || []) {
    if (feature.type === "boss") {
      const radius = clamp(feature.radius, 1, 20);
      const height = clamp(feature.height, 1, 40);
      if (Math.hypot(x - feature.x, y - feature.y) <= radius && z >= thickness && z <= thickness + height) solid = true;
    }

    if (feature.type === "rib") {
      const ax = feature.x;
      const ay = feature.y;
      const bx = feature.x2;
      const by = feature.y2;
      const vx = bx - ax;
      const vy = by - ay;
      const len2 = Math.max(vx * vx + vy * vy, 1);
      const t = clamp(((x - ax) * vx + (y - ay) * vy) / len2, 0, 1);
      const px = ax + t * vx;
      const py = ay + t * vy;
      const ribHeight = clamp(feature.height, 1, 60);
      const ribTop = thickness + ribHeight;
      if (Math.hypot(x - px, y - py) <= Math.max(feature.width, 1) / 2 && z >= thickness && z <= ribTop) solid = true;
    }
  }

  return solid;
}

function buildSolidMesh(design) {
  const length = clamp(design.base_length_mm, 30, 240);
  const width = clamp(design.base_width_mm, 10, 120);
  const thickness = clamp(design.base_thickness_mm, 1, 30);
  const maxFeatureHeight = (design.features || []).reduce((max, feature) => {
    if (feature.type === "rib" || feature.type === "boss") return Math.max(max, feature.height || 0);
    return max;
  }, 0);
  const height = Math.max(thickness + maxFeatureHeight, thickness * 2);
  const nx = 7;
  const ny = 5;
  const nz = 5;
  const nodes = [];
  const nodeId = new Map();
  const tets = [];

  function gridPoint(i, j, k) {
    return {
      x: (length * i) / nx,
      y: -width / 2 + (width * j) / ny,
      z: (height * k) / nz
    };
  }

  function addNode(i, j, k) {
    const key = `${i}:${j}:${k}`;
    if (nodeId.has(key)) return nodeId.get(key);
    const id = nodes.length;
    const point = gridPoint(i, j, k);
    nodes.push({ id, ...point });
    nodeId.set(key, id);
    return id;
  }

  const tetPattern = [
    [0, 1, 3, 7],
    [0, 3, 2, 7],
    [0, 2, 6, 7],
    [0, 6, 4, 7],
    [0, 4, 5, 7],
    [0, 5, 1, 7]
  ];

  for (let i = 0; i < nx; i += 1) {
    for (let j = 0; j < ny; j += 1) {
      for (let k = 0; k < nz; k += 1) {
        const center = {
          x: (gridPoint(i, j, k).x + gridPoint(i + 1, j, k).x) / 2,
          y: (gridPoint(i, j, k).y + gridPoint(i, j + 1, k).y) / 2,
          z: (gridPoint(i, j, k).z + gridPoint(i, j, k + 1).z) / 2
        };
        if (!pointInFeatureVolume(center, design)) continue;
        const corners = [
          addNode(i, j, k),
          addNode(i + 1, j, k),
          addNode(i, j + 1, k),
          addNode(i + 1, j + 1, k),
          addNode(i, j, k + 1),
          addNode(i + 1, j, k + 1),
          addNode(i, j + 1, k + 1),
          addNode(i + 1, j + 1, k + 1)
        ];
        for (const tet of tetPattern) tets.push(tet.map((idx) => corners[idx]));
      }
    }
  }

  return { nodes, tets, length, width, height };
}

function vonMisesFromStress(stress) {
  const [sx, sy, sz, txy, tyz, txz] = stress;
  return Math.sqrt(
    0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) +
      3 * (txy ** 2 + tyz ** 2 + txz ** 2)
  );
}

function runSolidTetraFea(design, material, loadCase) {
  const mesh = buildSolidMesh(design);
  if (mesh.nodes.length < 8 || mesh.tets.length < 6) throw new Error("3D mesh has too few solid elements.");
  const dofCount = mesh.nodes.length * 3;
  const K = Array.from({ length: dofCount }, () => Array(dofCount).fill(0));
  const F = Array(dofCount).fill(0);
  const elementData = [];

  for (const tet of mesh.tets) {
    const points = tet.map((id) => mesh.nodes[id]);
    const elem = tetraElementStiffness(points, material);
    if (!elem) continue;
    const dofs = tet.flatMap((id) => [id * 3, id * 3 + 1, id * 3 + 2]);
    for (let i = 0; i < 12; i += 1) {
      for (let j = 0; j < 12; j += 1) K[dofs[i]][dofs[j]] += elem.Ke[i][j];
    }
    elementData.push({ tet, ...elem });
  }

  const [loadX, loadY, loadZ] = loadCase.load_point;
  const candidates = mesh.nodes
    .map((node) => ({
      id: node.id,
      distance: Math.hypot((node.x - loadX) / mesh.length, (node.y - loadY) / mesh.width, (node.z - loadZ) / Math.max(mesh.height, 1))
    }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, 6);
  const loadPerNode = loadCase.effective_load_n / Math.max(candidates.length, 1);
  for (const candidate of candidates) F[candidate.id * 3 + 2] -= loadPerNode;

  const fixedNodes = mesh.nodes.filter((node) => node.x <= mesh.length * 0.001);
  const fixedDofs = new Set(fixedNodes.flatMap((node) => [node.id * 3, node.id * 3 + 1, node.id * 3 + 2]));
  const freeDofs = Array.from({ length: dofCount }, (_, i) => i).filter((i) => !fixedDofs.has(i));
  const Kff = freeDofs.map((row) => freeDofs.map((col) => K[row][col]));
  const Ff = freeDofs.map((row) => F[row]);
  const Uf = solveLinearSystem(Kff, Ff);
  const U = Array(dofCount).fill(0);
  freeDofs.forEach((dof, index) => {
    U[dof] = Uf[index];
  });

  const D = isotropicElasticityMatrix(material.youngMpa);
  const elementResults = [];
  let maxVonMises = 0;
  let maxStrain = 0;
  for (const elem of elementData) {
    const dofs = elem.tet.flatMap((id) => [id * 3, id * 3 + 1, id * 3 + 2]);
    const ue = dofs.map((dof) => [U[dof]]);
    const strain = matMul(elem.B, ue).map((row) => row[0]);
    const stress = matMul(D, strain.map((value) => [value])).map((row) => row[0]);
    const vm = vonMisesFromStress(stress);
    const strainMag = Math.hypot(...strain);
    maxVonMises = Math.max(maxVonMises, vm);
    maxStrain = Math.max(maxStrain, strainMag);
    const centroid = elem.tet.reduce(
      (sum, id) => {
        const node = mesh.nodes[id];
        return { x: sum.x + node.x / 4, y: sum.y + node.y / 4, z: sum.z + node.z / 4 };
      },
      { x: 0, y: 0, z: 0 }
    );
    elementResults.push({
      centroid,
      von_mises_mpa: Number(vm.toFixed(3)),
      strain_microstrain: Number((strainMag * 1_000_000).toFixed(1)),
      utilization: Number(clamp(vm / material.yieldMpa, 0, 1).toFixed(3))
    });
  }

  const displacements = mesh.nodes.map((node) => {
    const ux = U[node.id * 3];
    const uy = U[node.id * 3 + 1];
    const uz = U[node.id * 3 + 2];
    return {
      id: node.id,
      x: Number(node.x.toFixed(3)),
      y: Number(node.y.toFixed(3)),
      z: Number(node.z.toFixed(3)),
      ux_mm: Number(ux.toFixed(6)),
      uy_mm: Number(uy.toFixed(6)),
      uz_mm: Number(uz.toFixed(6)),
      magnitude_mm: Number(Math.hypot(ux, uy, uz).toFixed(6))
    };
  });
  const maxDisplacement = displacements.reduce((max, node) => Math.max(max, node.magnitude_mm), 0);
  const loadNodeDeflection = candidates.reduce((sum, candidate) => sum + Math.abs(U[candidate.id * 3 + 2]) / candidates.length, 0);

  return {
    method: "3D linear tetrahedral elasticity",
    nodes: mesh.nodes,
    tets: mesh.tets,
    element_results: elementResults,
    displacements,
    max_stress_mpa: maxVonMises,
    max_strain: maxStrain,
    load_point_deflection_mm: loadNodeDeflection,
    max_displacement_mm: maxDisplacement,
    force_vector_n: loadCase.vector_n,
    fixed_node_count: fixedNodes.length,
    loaded_node_count: candidates.length,
    load_case: loadCase
  };
}

function simulateDesignFallback(design, prompt = "") {
  const material = materials[design.material] || materials.aluminum_6061;
  const length = clamp(design.base_length_mm, 30, 240);
  const width = clamp(design.base_width_mm, 10, 120);
  const thickness = clamp(design.base_thickness_mm, 1, 30);
  const load = clamp(Math.abs(design.load_newtons), 1, 2000);
  const lever = clamp(Math.abs(design.load_point_x_mm), 5, length);
  const baseVolumeMm3 = length * width * thickness;

  let addedVolumeMm3 = 0;
  let removedVolumeMm3 = 0;
  let secondMoment = (width * Math.pow(thickness, 3)) / 12;
  let sectionModulus = (width * Math.pow(thickness, 2)) / 6;
  let usefulRibs = 0;

  for (const feature of design.features) {
    if (feature.type === "lightening_hole") {
      const radius = clamp(feature.radius, 1, width / 3);
      removedVolumeMm3 += Math.PI * radius * radius * thickness;
    }

    if (feature.type === "boss") {
      const radius = clamp(feature.radius, 1, 20);
      const height = clamp(feature.height, 1, 40);
      addedVolumeMm3 += Math.PI * radius * radius * height;
    }

    if (feature.type === "rib") {
      const ribLength = clamp(distance(feature.x, feature.y, feature.x2, feature.y2), 5, length * 1.4);
      const ribWidth = clamp(feature.width, 1, 20);
      const ribHeight = clamp(feature.height, 1, 60);
      const alignment = Math.abs(feature.x2 - feature.x) / Math.max(ribLength, 1);
      const effectiveness = 0.25 + 0.75 * alignment;
      addedVolumeMm3 += ribLength * ribWidth * ribHeight * 0.85;
      secondMoment += effectiveness * ribWidth * Math.pow(thickness + ribHeight, 3) / 12;
      sectionModulus += effectiveness * ribWidth * Math.pow(thickness + ribHeight, 2) / 6;
      usefulRibs += effectiveness;
    }
  }

  for (const hole of design.fixed_holes) {
    const radius = clamp(hole.radius, 1, 10);
    removedVolumeMm3 += Math.PI * radius * radius * thickness;
  }

  const volumeMm3 = Math.max(baseVolumeMm3 + addedVolumeMm3 - removedVolumeMm3, baseVolumeMm3 * 0.2);
  const massG = volumeMm3 * material.densityGcm3 / 1000;
  const momentNmm = load * lever;
  const loadCase = inferLoadCase(prompt, design);
  let fea;
  try {
    fea = runSolidTetraFea(design, material, loadCase);
  } catch (error) {
    fea = runFrameFea(design, material, { addedVolumeMm3, removedVolumeMm3 });
    fea.method = `${fea.method} fallback after 3D solve failed: ${error instanceof Error ? error.message : "unknown error"}`;
    fea.load_case = loadCase;
  }
  const stressMpa = fea.max_stress_mpa;
  const safetyFactor = material.yieldMpa / Math.max(stressMpa, 0.01);
  const strain = fea.max_strain;
  const microstrain = strain * 1_000_000;
  const deflectionMm = fea.load_point_deflection_mm;
  const surfaceAreaMm2 = 2 * (length * width + length * thickness + width * thickness) + addedVolumeMm3 / Math.max(thickness, 1);
  const thermalRiseC = (8 * lever) / Math.max(material.thermalWmK * surfaceAreaMm2 * 0.001, 0.001);
  const manufacturability = clamp(1 - invalidGeometryPenalty(design) - Math.max(0, usefulRibs - 8) * 0.02, 0, 1);
  const safetyScore = clamp((safetyFactor - 0.8) / 2.2, 0, 1);
  const stiffnessScore = clamp(1 - deflectionMm / 8, 0, 1);
  const massScore = clamp(1 - massG / 90, 0, 1);
  const thermalScore = clamp(1 - thermalRiseC / 45, 0, 1);
  const score = clamp(0.38 * safetyScore + 0.28 * stiffnessScore + 0.2 * massScore + 0.14 * manufacturability, 0, 1);

  return {
    mass_g: Number(massG.toFixed(2)),
    max_stress_mpa: Number(stressMpa.toFixed(2)),
    max_strain_microstrain: Number(microstrain.toFixed(1)),
    safety_factor: Number(safetyFactor.toFixed(2)),
    tip_deflection_mm: Number(deflectionMm.toFixed(3)),
    thermal_delta_c_proxy: Number(thermalRiseC.toFixed(2)),
    thermal_score: Number(thermalScore.toFixed(3)),
    manufacturability: Number(manufacturability.toFixed(3)),
    score: Number(score.toFixed(3)),
    force_vector_n: fea.force_vector_n,
    load_case: loadCase,
    stress_regions: fea.element_results
      .slice()
      .sort((a, b) => b.utilization - a.utilization)
      .slice(0, 4)
      .map((element) => {
        const n1 = element.centroid || fea.nodes[element.n1];
        const n2 = element.centroid || fea.nodes[element.n2];
        return {
          label: element.label || "3D tetra element",
          x: Number((((n1.x || 0) + (n2.x || 0)) / 2).toFixed(1)),
          y: Number((((n1.y || 0) + (n2.y || 0)) / 2).toFixed(1)),
          severity: element.utilization
        };
      }),
    deformation_regions: [
      { label: "free tip deflection", x: Number(lever.toFixed(1)), y: Number(design.load_point_y_mm.toFixed(1)), deflection_mm: Number(deflectionMm.toFixed(3)) }
    ],
    fea,
    verdict: score > 0.72 && safetyFactor >= 1.8 ? "promising" : "needs iteration",
    caveat: "Coarse 3D linear tetrahedral FEA for rapid design iteration. Use a finer production mesh before certifying a real part."
  };
}

function runPythonTool(command, payload) {
  const result = spawnSync(pythonBin, ["-m", "mechforge.cli", command], {
    cwd: process.cwd(),
    input: JSON.stringify(payload),
    encoding: "utf8",
    env: {
      ...process.env,
      XDG_CACHE_HOME: process.env.XDG_CACHE_HOME || ".cache",
      EZDXF_CACHE_DIR: process.env.EZDXF_CACHE_DIR || ".cache/ezdxf",
      PYTHONPATH: "python_tools"
    },
    maxBuffer: 20 * 1024 * 1024
  });

  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || `Python tool ${command} failed.`);
  }

  return JSON.parse(result.stdout);
}

function simulateDesign(design, prompt = "") {
  let result;
  try {
    result = runPythonTool("simulate", { design, prompt });
  } catch (error) {
    const fallback = simulateDesignFallback(design, prompt);
    fallback.caveat = `Python solver failed; used JS fallback. ${error instanceof Error ? error.message : "Unknown Python tool error"}`;
    return fallback;
  }

  return result.analysis;
}

function familyFromPrompt(prompt = "") {
  const text = String(prompt).toLowerCase();
  if (text.includes("table") || text.includes("desk") || text.includes("bench")) return "table";
  if (text.includes("stator") || text.includes("motor")) return "motor_stator";
  if (text.includes("chair") || text.includes("seat")) return "chair";
  if (text.includes("hook") || text.includes("hanging")) return "wall_hook";
  if (text.includes("clamp") || text.includes("shaft") || text.includes("torque") || text.includes("120 nm")) return "torque_clamp";
  return "freeform_object";
}

function wantsCurvyChair(prompt = "") {
  const text = String(prompt || "").toLowerCase();
  return (text.includes("chair") || text.includes("seat")) && /(\bcurv|round|organic|sweep|arched|bent|\bflow\b|flowing)/.test(text);
}

function wantsFlowerBackrest(prompt = "") {
  const text = String(prompt || "").toLowerCase();
  return (text.includes("chair") || text.includes("backrest")) && /(flower|floral|petal|blossom|rose|lotus)/.test(text);
}

function wantsAdvancedChair(prompt = "") {
  const text = String(prompt || "").toLowerCase();
  return text.includes("chair") && /(armrest|arm rest|handle|headrest|head rest|flat feet|flat foot|ergonomic|advanced)/.test(text);
}

function loadFromPrompt(prompt = "", fallback = 120) {
  const text = String(prompt || "").toLowerCase();
  const match = text.match(/(\d+(?:\.\d+)?)\s*n(?!\s*[-*]?\s*m|m)/i);
  if (match) return Number(match[1]);
  const torqueLike = text.match(/(\d+(?:\.\d+)?)\s*(?:n\s*[-*]?\s*m|nm)\b/i);
  return torqueLike ? Number(torqueLike[1]) : fallback;
}

function actionsForFamily(family, prompt = "") {
  const torqueVector = String(prompt).toLowerCase().match(/120\s*(?:n\s*[-*]?\s*m|nm)/) ? [0, 0, -1333.33] : [0, 0, -120];
  const curvyChair = wantsCurvyChair(prompt);
  const flowerBackrest = wantsFlowerBackrest(prompt);
  const base = [{ tool: "create_design_family", params: { family } }];
  if (family === "wall_hook") {
    return [
      { tool: "create_design_family", params: { family: "blank_wall_hook" } },
      { tool: "set_material", params: { material: "aluminum_6061" } },
      { tool: "add_feature", params: { type: "hook_curve", x: 12, y: 0, x2: 68, y2: 0, width: 8, height: 34, radius: 10, note: "round J hook tube" } },
      { tool: "add_feature", params: { type: "boss", x: 62, y: 0, height: 1, radius: 4, note: "hook lip/load contact proxy" } },
      { tool: "set_load", params: { point_mm: [62, 0, 7], vector_n: [0, 0, -120] } },
      { tool: "export_cadquery", params: {} },
      { tool: "run_fea", params: {} },
      { tool: "commit_design", params: {} }
    ];
  }
  if (family === "torque_clamp") {
    return [
      { tool: "create_design_family", params: { family: "blank_torque_clamp" } },
      { tool: "set_material", params: { material: "aluminum_6061" } },
      { tool: "add_feature", params: { type: "clamp_jaw", x: 34, y: -18, x2: 78, y2: -18, width: 10, height: 18, radius: 9, note: "lower clamp jaw" } },
      { tool: "add_feature", params: { type: "clamp_jaw", x: 34, y: 18, x2: 78, y2: 18, width: 10, height: 18, radius: 9, note: "upper clamp jaw" } },
      { tool: "add_feature", params: { type: "boss", x: 66, y: 0, height: 12, radius: 12, note: "shaft torque proxy" } },
      { tool: "set_load", params: { point_mm: [68, 0, 20], vector_n: torqueVector } },
      { tool: "export_cadquery", params: {} },
      { tool: "run_fea", params: {} },
      { tool: "commit_design", params: {} }
    ];
  }
  if (family === "motor_stator") {
    return [
      { tool: "create_design_family", params: { family: "blank_motor_stator" } },
      { tool: "set_material", params: { material: "steel_1018" } },
      { tool: "add_feature", params: { type: "stator_ring", x: 48, y: 0, width: 14, height: 8, radius: 34, note: "lamination ring" } },
      { tool: "add_feature", params: { type: "stator_tooth", x: 48, y: 0, width: 9, height: 18, radius: 12, note: "12 radial teeth" } },
      { tool: "add_feature", params: { type: "boss", x: 48, y: 0, height: 8, radius: 6, note: "center shaft/load proxy" } },
      { tool: "set_load", params: { point_mm: [48, 0, 12], vector_n: [0, 0, -80] } },
      { tool: "export_cadquery", params: {} },
      { tool: "run_fea", params: {} },
      { tool: "commit_design", params: {} }
    ];
  }
  if (family === "chair") {
    const chairLoad = loadFromPrompt(prompt, 700);
    return [
      { tool: "create_design_family", params: { family: "blank_chair" } },
      { tool: "set_material", params: { material: "aluminum_6061" } },
      { tool: "add_feature", params: { type: "seat_panel", x: 45, y: 0, width: 90, height: 6, radius: curvyChair ? 14 : 0, note: curvyChair ? "curved rounded waterfall seat panel" : "seat panel" } },
      { tool: "add_feature", params: { type: "chair_leg", x: 14, y: -24, x2: curvyChair ? 2 : 6, y2: curvyChair ? -36 : -32, width: curvyChair ? 7 : 6, height: 55, radius: curvyChair ? 10 : 0, note: curvyChair ? "curved splayed tubular front left leg" : "front left leg" } },
      { tool: "add_feature", params: { type: "chair_leg", x: 76, y: -24, x2: curvyChair ? 88 : 84, y2: curvyChair ? -36 : -32, width: curvyChair ? 7 : 6, height: 55, radius: curvyChair ? 10 : 0, note: curvyChair ? "curved splayed tubular front right leg" : "front right leg" } },
      { tool: "add_feature", params: { type: "chair_leg", x: 14, y: 24, x2: curvyChair ? 2 : 6, y2: curvyChair ? 38 : 32, width: curvyChair ? 7 : 6, height: 55, radius: curvyChair ? 12 : 0, note: curvyChair ? "curved rear left leg continuing into back post" : "rear left leg" } },
      { tool: "add_feature", params: { type: "chair_leg", x: 76, y: 24, x2: curvyChair ? 88 : 84, y2: curvyChair ? 38 : 32, width: curvyChair ? 7 : 6, height: 55, radius: curvyChair ? 12 : 0, note: curvyChair ? "curved rear right leg continuing into back post" : "rear right leg" } },
      { tool: "add_feature", params: { type: "chair_back", x: 45, y: curvyChair ? 35 : 31, width: 84, height: curvyChair ? 52 : 44, radius: curvyChair ? 18 : 0, note: curvyChair ? "curved arched backrest with rounded top rail" : "upright backrest panel" } },
      { tool: "add_feature", params: { type: "chair_crossbar", x: 45, y: -30, width: 84, height: 4, radius: curvyChair ? 8 : 0, note: curvyChair ? "curved front leg crossbar" : "front leg crossbar" } },
      ...(curvyChair
        ? [
            { tool: "add_feature", params: { type: "chair_crossbar", x: 45, y: 30, width: 84, height: 4, radius: 8, note: "curved rear leg crossbar" } },
            { tool: "add_feature", params: { type: "chair_crossbar", x: 12, y: 0, width: 52, height: 4, radius: 8, note: "curved left side crossbar" } },
            { tool: "add_feature", params: { type: "chair_crossbar", x: 78, y: 0, width: 52, height: 4, radius: 8, note: "curved right side crossbar" } }
          ]
        : []),
      ...(flowerBackrest
        ? [
            { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, width: 30, height: 30, radius: 8, note: "flower backrest center blossom" } },
            { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, x2: 45, y2: 42, width: 48, height: 24, radius: 6, note: "six petal flower pattern on backrest" } },
            { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, x2: 45, y2: 42, width: 18, height: 36, radius: 4, note: "flower stem and leaf curves on backrest" } }
          ]
        : []),
      { tool: "set_load", params: { point_mm: [45, 0, 6], vector_n: [0, 0, -chairLoad] } },
      { tool: "export_cadquery", params: {} },
      { tool: "run_fea", params: {} },
      { tool: "commit_design", params: {} }
    ];
  }
  if (family === "table") {
    const tableLoad = loadFromPrompt(prompt, 500);
    const sixLegs = /six|6/.test(String(prompt).toLowerCase());
    const legXs = sixLegs ? [10, 50, 90, 10, 50, 90] : [12, 88, 12, 88];
    const legYs = sixLegs ? [-28, -28, -28, 28, 28, 28] : [-28, -28, 28, 28];
    const legActions = legXs.map((x, index) => ({
      tool: "add_feature",
      params: {
        type: "table_leg",
        x,
        y: legYs[index],
        x2: x,
        y2: legYs[index],
        width: 6,
        height: 48,
        radius: 3,
        note: `${sixLegs ? "six-leg " : ""}table support leg ${index + 1}`
      }
    }));
    return [
      { tool: "create_design_family", params: { family: "blank_table" } },
      { tool: "set_material", params: { material: "aluminum_6061" } },
      { tool: "add_feature", params: { type: "tabletop", x: 50, y: 0, width: 100, height: 6, radius: 4, note: "rectangular small tabletop panel" } },
      ...legActions,
      { tool: "add_feature", params: { type: "support_tube", x: 10, y: -28, x2: 90, y2: -28, width: 4, height: 22, radius: 3, note: "front lower table stretcher" } },
      { tool: "add_feature", params: { type: "support_tube", x: 10, y: 28, x2: 90, y2: 28, width: 4, height: 22, radius: 3, note: "rear lower table stretcher" } },
      { tool: "set_load", params: { point_mm: [50, 0, 6], vector_n: [0, 0, -tableLoad] } },
      { tool: "export_cadquery", params: {} },
      { tool: "run_fea", params: {} },
      { tool: "commit_design", params: {} }
    ];
  }
  return [
    { tool: "create_design_family", params: { family: "blank_freeform_object" } },
    { tool: "set_material", params: { material: "aluminum_6061" } },
    { tool: "set_envelope", params: { length_mm: 100, width_mm: 70, thickness_mm: 6 } },
    { tool: "add_feature", params: { type: "generic_panel", x: 50, y: 0, width: 80, height: 6, radius: 3, note: "primary body panel inferred from prompt" } },
    { tool: "add_feature", params: { type: "support_tube", x: 15, y: -20, x2: 85, y2: -20, width: 5, height: 20, radius: 3, note: "generic structural support tube" } },
    { tool: "set_load", params: { point_mm: [50, 0, 6], vector_n: [0, 0, -loadFromPrompt(prompt, 120)] } },
    { tool: "export_cadquery", params: {} },
    { tool: "run_fea", params: {} },
    { tool: "commit_design", params: {} }
  ];
}

function toolPlannerSystemPrompt() {
  return [
    "You are a CAD construction planner for MechForge.",
    "Turn the user prompt into a sequence of small tool calls. Do not one-shot a full CAD object.",
    "Start with create_design_family using a blank family when available: blank_wall_hook, blank_torque_clamp, blank_motor_stator, blank_chair, blank_table, blank_freeform_object, or ribbed_cantilever_bracket.",
    "Then set material, add visible features one at a time, set the load at the actual visual contact point, export CadQuery, run FEA, and commit.",
    "Avoid object templates when the prompt asks for a new object. Compose it from primitive CAD features: generic_panel, support_tube, curved_tube, decorative_curve, flat_foot, tabletop, table_leg, armrest, headrest, and family-specific features only when they fit.",
    "For chairs, create a full chair: seat_panel, four chair_leg features, chair_back, and chair_crossbar.",
    "For advanced chairs, use armrest, headrest, flat_foot, curved_tube, and support_tube features instead of only the basic chair parts.",
    "For tables, use tabletop plus the requested number of table_leg features and support_tube stretchers. Do not render a table as a chair.",
    "If the user asks for a curvy, rounded, organic, arched, bent, flowing, or sweeping chair, preserve that style in radius and note fields: use nonzero radius values and notes like curved tubular leg, curved seat, arched backrest, curved crossbar.",
    "Use decorative_curve for semantic visual requirements such as flower, logo, lattice, engraving, petal, or ornamental backrest patterns. Decorative curves do not replace load-bearing structure.",
    "For stators, create stator_ring and stator_tooth; it should be a flat toothed stator, not a donut placeholder.",
    "For clamps, create clamp_jaw features around a shaft/boss.",
    "For hooks, create hook_curve and a boss/load contact at the hook tip.",
    "Use only the available tool names and feature types. The executor will expand your high-level plan into 50-300 observe/measure/check/build tool calls."
  ].join("\n");
}

function clampToolBudget(value) {
  return clamp(Number(value) || 72, 50, 300);
}

function microAction(tool, params = {}) {
  return { tool, params };
}

function applyPromptStyleToActions(actions, prompt, family) {
  if (family !== "chair") return actions;
  const curvy = wantsCurvyChair(prompt);
  const flower = wantsFlowerBackrest(prompt);
  const advanced = wantsAdvancedChair(prompt);
  let chairLegOrdinal = 0;
  let crossbarOrdinal = 0;
  const styled = actions.map((action) => {
    if (action.tool === "set_load") {
      const load = loadFromPrompt(prompt, 0);
      if (load > 0) {
        const params = { ...(action.params || {}) };
        params.vector_n = [0, 0, -load];
        params.point_mm = params.point_mm || [45, 0, 6];
        return { ...action, params };
      }
    }
    if (action.tool !== "add_feature") return action;
    const params = { ...(action.params || {}) };
    if (curvy && params.type === "seat_panel") {
      params.radius = Math.max(Number(params.radius || 0), 14);
      params.note = String(params.note || "").includes("curv") ? params.note : `curved rounded waterfall ${params.note || "seat panel"}`;
    }
    if (curvy && params.type === "chair_leg") {
      chairLegOrdinal += 1;
      params.radius = Math.max(Number(params.radius || 0), chairLegOrdinal >= 3 ? 12 : 10);
      params.width = Math.max(Number(params.width || 0), 7);
      params.note = String(params.note || "").includes("curv") ? params.note : `curved splayed tubular ${params.note || "chair leg"}`;
      if (chairLegOrdinal === 1) Object.assign(params, { x2: 2, y2: -36 });
      if (chairLegOrdinal === 2) Object.assign(params, { x2: 88, y2: -36 });
      if (chairLegOrdinal === 3) Object.assign(params, { x2: 2, y2: 38 });
      if (chairLegOrdinal === 4) Object.assign(params, { x2: 88, y2: 38 });
    }
    if (params.type === "chair_back") {
      params.radius = Math.max(Number(params.radius || 0), curvy ? 18 : 8);
      params.height = Math.max(Number(params.height || 0), curvy ? 52 : 48);
      params.y = Number.isFinite(Number(params.y)) ? Math.max(Number(params.y), 35) : 35;
      if (curvy) params.note = String(params.note || "").includes("curv") ? params.note : `curved arched ${params.note || "backrest"}`;
      if (flower && !String(params.note || "").includes("flower")) params.note = `${params.note || "backrest"} with flower pattern support`;
    }
    if (curvy && params.type === "chair_crossbar") {
      crossbarOrdinal += 1;
      params.radius = Math.max(Number(params.radius || 0), 8);
      params.note = String(params.note || "").includes("curv") ? params.note : `curved ${params.note || "crossbar"}`;
      if (crossbarOrdinal === 2 && !Number(params.y)) params.y = 30;
    }
    return { ...action, params };
  });
  if (flower && !styled.some((action) => action.tool === "add_feature" && action.params?.type === "decorative_curve")) {
    const finalIndex = styled.findIndex((action) => ["set_load", "export_cadquery", "run_fea", "commit_design"].includes(action.tool));
    const insertAt = finalIndex >= 0 ? finalIndex : styled.length;
    styled.splice(
      insertAt,
      0,
      { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, width: 30, height: 30, radius: 8, note: "flower backrest center blossom" } },
      { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, width: 48, height: 24, radius: 6, note: "six petal flower pattern on backrest" } },
      { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, width: 18, height: 36, radius: 4, note: "flower stem and leaf curves on backrest" } }
    );
  }
  if (advanced) {
    const finalIndex = styled.findIndex((action) => ["set_load", "export_cadquery", "run_fea", "commit_design"].includes(action.tool));
    const insertAt = finalIndex >= 0 ? finalIndex : styled.length;
    const additions = [];
    if (!styled.some((action) => action.tool === "add_feature" && action.params?.type === "armrest")) {
      additions.push(
        { tool: "add_feature", params: { type: "armrest", x: 7, y: -2, x2: 7, y2: 31, width: 7, height: 54, radius: 10, note: "left curved ergonomic armrest handle" } },
        { tool: "add_feature", params: { type: "armrest", x: 83, y: -2, x2: 83, y2: 31, width: 7, height: 54, radius: 10, note: "right curved ergonomic armrest handle" } }
      );
    }
    if (!styled.some((action) => action.tool === "add_feature" && action.params?.type === "headrest")) {
      additions.push({ tool: "add_feature", params: { type: "headrest", x: 45, y: 45, width: 56, height: 18, radius: 9, note: "separate curved headrest above backrest" } });
    }
    if (!styled.some((action) => action.tool === "add_feature" && action.params?.type === "flat_foot")) {
      additions.push(
        { tool: "add_feature", params: { type: "flat_foot", x: 4, y: -38, width: 24, height: 3, radius: 5, note: "front left flat foot pad" } },
        { tool: "add_feature", params: { type: "flat_foot", x: 86, y: -38, width: 24, height: 3, radius: 5, note: "front right flat foot pad" } },
        { tool: "add_feature", params: { type: "flat_foot", x: 4, y: 40, width: 24, height: 3, radius: 5, note: "rear left flat foot pad" } },
        { tool: "add_feature", params: { type: "flat_foot", x: 86, y: 40, width: 24, height: 3, radius: 5, note: "rear right flat foot pad" } }
      );
    }
    styled.splice(insertAt, 0, ...additions);
  }
  return styled;
}

function expandLongHorizonActions(actions, targetToolCalls = 72) {
  const target = clampToolBudget(targetToolCalls);
  const expanded = [];
  const preCommit = [];
  const finalActions = [];
  for (const action of actions) {
    if (["export_cadquery", "run_fea", "commit_design"].includes(action.tool)) finalActions.push(action);
    else preCommit.push(action);
  }

  for (const [index, action] of preCommit.entries()) {
    expanded.push(microAction("observe_design", { phase: "before", next_tool: action.tool, step_index: index + 1 }));
    if (["add_feature", "add_rib", "add_lightening_hole", "add_mount_hole"].includes(action.tool)) {
      expanded.push(microAction("check_constraints", { phase: "pre_feature", feature_type: action.params?.type || action.tool }));
    }
    expanded.push(action);
    if (["create_design_family", "set_material", "set_envelope", "add_feature", "add_rib", "add_lightening_hole", "add_mount_hole", "set_load"].includes(action.tool)) {
      expanded.push(microAction("measure_clearance", { phase: "after", previous_tool: action.tool }));
      expanded.push(microAction("critique_geometry", { phase: "after", previous_tool: action.tool }));
    }
    if (["add_feature", "set_load"].includes(action.tool)) {
      expanded.push(microAction("visual_snapshot", { view: "isometric", phase: "after", previous_tool: action.tool }));
    }
  }

  const viewCycle = ["isometric", "front", "right", "top"];
  let repairIndex = 0;
  while (expanded.length + finalActions.length < target) {
    const view = viewCycle[repairIndex % viewCycle.length];
    const phase = `polish_${repairIndex + 1}`;
    expanded.push(microAction("observe_design", { phase }));
    if (expanded.length + finalActions.length >= target) break;
    expanded.push(microAction("visual_snapshot", { phase, view }));
    if (expanded.length + finalActions.length >= target) break;
    expanded.push(microAction("check_constraints", { phase, view }));
    if (expanded.length + finalActions.length >= target) break;
    expanded.push(microAction("measure_clearance", { phase, view }));
    if (expanded.length + finalActions.length >= target) break;
    expanded.push(microAction("critique_geometry", { phase, view }));
    repairIndex += 1;
  }

  const requiredFinals = finalActions.length ? finalActions : [microAction("export_cadquery"), microAction("run_fea"), microAction("commit_design")];
  const editableBudget = Math.max(0, target - requiredFinals.length);
  const requiredOperationSet = new Set(preCommit);
  let remainingRequiredOperations = expanded.filter((action) => requiredOperationSet.has(action)).length;
  const selected = [];

  for (const action of expanded) {
    const isRequiredOperation = requiredOperationSet.has(action);
    if (isRequiredOperation) {
      selected.push(action);
      remainingRequiredOperations -= 1;
    } else if (editableBudget - selected.length - remainingRequiredOperations > 0) {
      selected.push(action);
    }
    if (selected.length >= editableBudget) break;
  }

  return [...selected, ...requiredFinals];
}

function expandActionChunk(actions, targetCount, round = 1) {
  const expanded = [];
  for (const [index, action] of actions.entries()) {
    expanded.push(microAction("observe_design", { phase: `round_${round}_before`, next_tool: action.tool, step_index: index + 1 }));
    if (["add_feature", "add_rib", "add_lightening_hole", "add_mount_hole"].includes(action.tool)) {
      expanded.push(microAction("check_constraints", { phase: `round_${round}_pre_feature`, feature_type: action.params?.type || action.tool }));
    }
    expanded.push(action);
    if (["create_design_family", "set_material", "set_envelope", "add_feature", "add_rib", "add_lightening_hole", "add_mount_hole", "set_load"].includes(action.tool)) {
      expanded.push(microAction("measure_clearance", { phase: `round_${round}_after`, previous_tool: action.tool }));
      expanded.push(microAction("critique_geometry", { phase: `round_${round}_after`, previous_tool: action.tool }));
    }
    if (["add_feature", "set_load"].includes(action.tool)) {
      expanded.push(microAction("visual_snapshot", { view: "isometric", phase: `round_${round}_after`, previous_tool: action.tool }));
    }
  }

  const viewCycle = ["isometric", "front", "right", "top"];
  let polishIndex = 0;
  while (expanded.length < targetCount) {
    const view = viewCycle[polishIndex % viewCycle.length];
    const phase = `round_${round}_reassess_${polishIndex + 1}`;
    expanded.push(microAction("observe_design", { phase, view }));
    if (expanded.length >= targetCount) break;
    expanded.push(microAction("visual_snapshot", { phase, view }));
    if (expanded.length >= targetCount) break;
    expanded.push(microAction("check_constraints", { phase, view }));
    if (expanded.length >= targetCount) break;
    expanded.push(microAction("critique_geometry", { phase, view }));
    polishIndex += 1;
  }

  const required = new Set(actions);
  let remainingRequired = expanded.filter((action) => required.has(action)).length;
  const selected = [];
  for (const action of expanded) {
    const isRequired = required.has(action);
    if (isRequired) {
      selected.push(action);
      remainingRequired -= 1;
    } else if (targetCount - selected.length - remainingRequired > 0) {
      selected.push(action);
    }
    if (selected.length >= targetCount) break;
  }
  return selected;
}

function normalizePlannedActions(plan, prompt = "") {
  const fallbackFamily = familyFromPrompt(prompt);
  const family = plan?.family || fallbackFamily;
  const featureCounts = {};
  let featureSequence = 0;
  const actions = Array.isArray(plan?.actions)
    ? plan.actions.map((action) => {
        const params = { ...(action.params || {}) };
        let ordinal = 0;
        let sequence = 0;
        if (action.tool === "add_feature") {
          featureSequence += 1;
          sequence = featureSequence;
          params.type = inferFeatureType(params, family, sequence);
          ordinal = featureCounts[params.type] = (featureCounts[params.type] || 0) + 1;
        }
        return { tool: action.tool, params: sanitizeActionParams(action.tool, params, family, ordinal, sequence) };
      })
    : [];
  if (!actions.length || actions[0].tool !== "create_design_family") {
    return actionsForFamily(fallbackFamily, prompt);
  }
  if (actions[0].params?.family && !String(actions[0].params.family).startsWith("blank_") && family !== "ribbed_cantilever_bracket") {
    actions[0].params.family = `blank_${family}`;
  }
  if (!actions.some((action) => action.tool === "export_cadquery")) actions.push({ tool: "export_cadquery", params: {} });
  if (!actions.some((action) => action.tool === "run_fea")) actions.push({ tool: "run_fea", params: {} });
  if (!actions.some((action) => action.tool === "commit_design")) actions.push({ tool: "commit_design", params: {} });
  return applyPromptStyleToActions(actions, prompt, family);
}

function featureDefaults(family, type, ordinal = 1) {
  if (family === "chair") {
    const legDefaults = [
      { x: 14, y: -24, x2: 8, y2: -28, width: 6, height: 48, radius: 0, note: "front left leg" },
      { x: 76, y: -24, x2: 82, y2: -28, width: 6, height: 48, radius: 0, note: "front right leg" },
      { x: 14, y: 24, x2: 8, y2: 30, width: 6, height: 48, radius: 0, note: "rear left leg" },
      { x: 76, y: 24, x2: 82, y2: 30, width: 6, height: 48, radius: 0, note: "rear right leg" }
    ];
    const crossbars = [
      { x: 45, y: -30, x2: 45, y2: -30, width: 84, height: 4, radius: 0, note: "front leg crossbar" },
      { x: 45, y: 30, x2: 45, y2: 30, width: 84, height: 4, radius: 0, note: "rear leg crossbar" }
    ];
    if (type === "seat_panel") return { x: 45, y: 0, x2: 45, y2: 0, width: 90, height: 6, radius: 0, note: "seat panel" };
    if (type === "chair_leg") return legDefaults[Math.min(Math.max(ordinal - 1, 0), legDefaults.length - 1)];
    if (type === "chair_back") return { x: 45, y: 31, x2: 45, y2: 31, width: 84, height: 44, radius: 0, note: "upright backrest panel" };
    if (type === "chair_crossbar") return crossbars[Math.min(Math.max(ordinal - 1, 0), crossbars.length - 1)];
    if (type === "decorative_curve") return { x: 45, y: 42, x2: 45, y2: 42, width: 34, height: 26, radius: 6, note: "decorative backrest curve" };
    if (type === "armrest") return { x: ordinal === 1 ? 8 : 82, y: 0, x2: ordinal === 1 ? 8 : 82, y2: 30, width: 7, height: 54, radius: 10, note: ordinal === 1 ? "left ergonomic armrest handle" : "right ergonomic armrest handle" };
    if (type === "headrest") return { x: 45, y: 42, x2: 45, y2: 42, width: 52, height: 18, radius: 8, note: "separate curved headrest above backrest" };
    if (type === "flat_foot") return { x: ordinal % 2 ? 10 : 80, y: ordinal <= 2 ? -34 : 34, x2: 0, y2: 0, width: 18, height: 3, radius: 4, note: "flat anti-tip foot pad" };
  }
  if (family === "table") {
    if (type === "tabletop") return { x: 50, y: 0, x2: 50, y2: 0, width: 100, height: 6, radius: 4, note: "small tabletop panel" };
    if (type === "table_leg") {
      const legs = [
        { x: 10, y: -28 }, { x: 50, y: -28 }, { x: 90, y: -28 },
        { x: 10, y: 28 }, { x: 50, y: 28 }, { x: 90, y: 28 }
      ];
      const pos = legs[Math.min(Math.max(ordinal - 1, 0), legs.length - 1)];
      return { ...pos, x2: pos.x, y2: pos.y, width: 6, height: 48, radius: 3, note: `table support leg ${ordinal}` };
    }
    if (type === "support_tube") return { x: 10, y: ordinal % 2 ? -28 : 28, x2: 90, y2: ordinal % 2 ? -28 : 28, width: 4, height: 22, radius: 3, note: "table stretcher support tube" };
  }
  if (family === "torque_clamp") {
    const jaws = [
      { x: 28, y: -18, x2: 84, y2: -18, width: 10, height: 18, radius: 9, note: "lower split clamp jaw" },
      { x: 28, y: 18, x2: 84, y2: 18, width: 10, height: 18, radius: 9, note: "upper split clamp jaw" }
    ];
    if (type === "clamp_jaw") return jaws[Math.min(Math.max(ordinal - 1, 0), jaws.length - 1)];
    if (type === "boss") return { x: 66, y: 0, x2: 66, y2: 0, width: 0, height: 12, radius: 12, note: "shaft torque proxy" };
  }
  if (family === "motor_stator") {
    if (type === "stator_ring") return { x: 48, y: 0, x2: 48, y2: 0, width: 14, height: 8, radius: 34, note: "lamination ring" };
    if (type === "stator_tooth") return { x: 48, y: 0, x2: 48, y2: 0, width: 9, height: 18, radius: 12, note: "12 radial teeth" };
    if (type === "boss") return { x: 48, y: 0, x2: 48, y2: 0, width: 0, height: 8, radius: 6, note: "center shaft proxy" };
  }
  if (family === "wall_hook") {
    if (type === "hook_curve") return { x: 12, y: 0, x2: 68, y2: 0, width: 8, height: 34, radius: 10, note: "round J hook tube" };
    if (type === "boss") return { x: 62, y: 0, x2: 62, y2: 0, width: 0, height: 1, radius: 4, note: "hook lip/load contact proxy" };
  }
  if (type === "boss") return { x: 90, y: 0, x2: 90, y2: 0, width: 0, height: 7, radius: 6, note: "load application boss" };
  if (type === "rib") return { x: 16, y: -14, x2: 88, y2: -4, width: 5, height: 18, radius: 0, note: "diagonal rib" };
  if (type === "generic_panel") return { x: 50, y: 0, x2: 50, y2: 0, width: 80, height: 6, radius: 3, note: "generic body panel" };
  if (type === "support_tube" || type === "curved_tube") return { x: 15, y: -20, x2: 85, y2: 20, width: 5, height: 22, radius: 4, note: "generic support tube" };
  if (type === "flat_foot") return { x: 10, y: -25, x2: 0, y2: 0, width: 18, height: 3, radius: 4, note: "flat foot pad" };
  return { x: 0, y: 0, x2: 0, y2: 0, width: 1, height: 1, radius: 0, note: type };
}

function inferFeatureType(params, family, sequence = 1) {
  const direct = params.type || params.feature_type;
  if (
    allowedFeatureTypes.has(direct) &&
    [
      "decorative_curve",
      "armrest",
      "headrest",
      "flat_foot",
      "generic_panel",
      "support_tube",
      "curved_tube",
      "tabletop",
      "table_leg"
    ].includes(direct)
  ) {
    return direct;
  }
  if (family === "chair") {
    if (sequence === 1) return "seat_panel";
    if (sequence >= 2 && sequence <= 5) return "chair_leg";
    if (sequence === 6) return "chair_back";
  }
  if (allowedFeatureTypes.has(direct)) return direct;
  const hint = [params.type, params.feature_type, params.part, params.name, params.note, params.id, params.description]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  if (family === "chair") {
    if (hint.includes("flower") || hint.includes("petal") || hint.includes("decor") || hint.includes("ornament") || hint.includes("pattern") || hint.includes("logo")) return "decorative_curve";
    if (hint.includes("arm")) return "armrest";
    if (hint.includes("head")) return "headrest";
    if (hint.includes("foot") || hint.includes("feet")) return "flat_foot";
    if (hint.includes("seat")) return "seat_panel";
    if (hint.includes("leg") || hint.includes("post")) return "chair_leg";
    if (hint.includes("back")) return "chair_back";
    if (hint.includes("bar") || hint.includes("brace") || hint.includes("rail")) return "chair_crossbar";
    return "chair_crossbar";
  }
  if (family === "table") {
    if (hint.includes("top") || hint.includes("surface") || sequence === 1) return "tabletop";
    if (hint.includes("leg") || hint.includes("post")) return "table_leg";
    if (hint.includes("foot") || hint.includes("feet")) return "flat_foot";
    if (hint.includes("curve") || hint.includes("curvy")) return "curved_tube";
    return "support_tube";
  }
  if (family === "torque_clamp") {
    if (hint.includes("boss") || hint.includes("shaft")) return "boss";
    return "clamp_jaw";
  }
  if (family === "motor_stator") {
    if (hint.includes("ring")) return "stator_ring";
    if (hint.includes("boss") || hint.includes("shaft") || hint.includes("bore")) return "boss";
    return "stator_tooth";
  }
  if (family === "wall_hook") {
    if (hint.includes("boss") || hint.includes("tip") || hint.includes("load")) return "boss";
    return "hook_curve";
  }
  if (hint.includes("hole")) return "lightening_hole";
  if (hint.includes("boss")) return "boss";
  if (hint.includes("panel") || hint.includes("body") || hint.includes("blade") || hint.includes("surface")) return "generic_panel";
  if (hint.includes("curve") || hint.includes("arc") || hint.includes("handle")) return "curved_tube";
  if (hint.includes("foot") || hint.includes("feet")) return "flat_foot";
  return "support_tube";
}

function sanitizeNumber(value, fallback, allowZero = true) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  if (!allowZero && number === 0) return fallback;
  return number;
}

function sanitizeActionParams(tool, params, family, ordinal = 1, sequence = 1) {
  const clean = { ...params };
  if (tool === "set_material") {
    const raw = String(clean.material || "").toLowerCase();
    clean.material = materials[raw] ? raw : materialAliases[raw] || (family === "motor_stator" ? "steel_1018" : "aluminum_6061");
  }
  if (tool === "create_design_family") {
    const rawFamily = String(clean.family || family || "ribbed_cantilever_bracket");
    const baseFamily = rawFamily.startsWith("blank_") ? rawFamily.slice(6) : rawFamily;
    clean.family = allowedFamilies.has(baseFamily) && baseFamily !== "ribbed_cantilever_bracket" ? `blank_${baseFamily}` : "ribbed_cantilever_bracket";
  }
  if (tool === "add_feature" && !allowedFeatureTypes.has(clean.type)) {
    clean.type = inferFeatureType(clean, family, sequence);
  }
  if (tool === "add_feature") {
    const defaults = featureDefaults(family, clean.type, ordinal);
    const needsGeometryDefault =
      !Number.isFinite(Number(clean.x)) ||
      !Number.isFinite(Number(clean.width)) ||
      !Number.isFinite(Number(clean.height)) ||
      (Number(clean.x) === 0 && Number(clean.y) === 0 && Number(clean.x2 || 0) === 0 && Number(clean.y2 || 0) === 0 && Number(clean.width || 0) === 0 && Number(clean.height || 0) === 0);
    if (needsGeometryDefault) {
      Object.assign(clean, { ...defaults, note: clean.note || defaults.note });
    } else {
      clean.x = sanitizeNumber(clean.x, defaults.x, true);
      clean.y = sanitizeNumber(clean.y, defaults.y, true);
      clean.x2 = sanitizeNumber(clean.x2, defaults.x2, true);
      clean.y2 = sanitizeNumber(clean.y2, defaults.y2, true);
      clean.width = sanitizeNumber(clean.width, defaults.width, false);
      clean.height = sanitizeNumber(clean.height, defaults.height, false);
      clean.radius = sanitizeNumber(clean.radius, defaults.radius, true);
      clean.note = clean.note || defaults.note;
    }
  }
  return clean;
}

function sanitizeModelPlan(rawPlan, prompt = "") {
  const promptFamily = familyFromPrompt(prompt);
  const family = promptFamily !== "freeform_object"
    ? promptFamily
    : allowedFamilies.has(rawPlan?.family)
      ? rawPlan.family
      : promptFamily;
  const actions = (Array.isArray(rawPlan?.actions) ? rawPlan.actions : [])
    .filter((action) => allowedToolNames.has(action?.tool))
    .map((action) => ({ tool: action.tool, params: action.params && typeof action.params === "object" ? action.params : {} }));
  const normalizedActions = normalizePlannedActions({ family, actions }, prompt);
  if (!normalizedActions.length) {
    throw new Error("Planner returned no executable tool actions.");
  }
  return {
    family,
    rationale: typeof rawPlan?.rationale === "string" ? rawPlan.rationale : "Model-planned CAD tool sequence.",
    actions: normalizedActions,
    raw_action_count: Array.isArray(rawPlan?.actions) ? rawPlan.actions.length : 0,
    executable_action_count: normalizedActions.length
  };
}

async function planToolActionsWithModel(prompt = "") {
  loadEnv();
  const model = process.env.MODEL_NAME || "gpt-5.4";
  const systemPrompt = toolPlannerSystemPrompt();
  const userMessage = [
    prompt,
    "",
    "Return a tool plan. The environment will execute each tool call sequentially and show the trace."
  ].join("\n");
  if (!process.env.OPENAI_API_KEY) {
    return {
      source: "deterministic_fallback",
      model,
      system: systemPrompt,
      user: userMessage,
      plan: { family: familyFromPrompt(prompt), rationale: "OPENAI_API_KEY missing; used local family template.", actions: actionsForFamily(familyFromPrompt(prompt), prompt) }
    };
  }

  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const response = await client.responses.create({
    model,
    input: [
      { role: "system", content: systemPrompt },
      {
        role: "user",
        content: [
          userMessage,
          "",
          "Return valid JSON only with this shape:",
          '{"family":"chair","rationale":"...","actions":[{"tool":"create_design_family","params":{"family":"blank_chair"}}]}'
        ].join("\n")
      }
    ]
  });
  const rawText = response.output_text || "";
  const parsedJson = JSON.parse(rawText);
  const parsedPlan = sanitizeModelPlan(parsedJson, prompt);
  return {
    source: "openai_tool_planner",
    model,
    system: systemPrompt,
    user: userMessage,
    plan: {
      ...parsedPlan,
      actions: normalizePlannedActions(parsedPlan, prompt)
    }
  };
}

function compactDesignObservation(design, analysis = null, prompt = "") {
  const features = design?.features || [];
  const featureTypes = features.reduce((acc, feature) => {
    acc[feature.type] = (acc[feature.type] || 0) + 1;
    return acc;
  }, {});
  const notes = features.map((feature) => feature.note).filter(Boolean).slice(-10);
  return {
    prompt,
    title: design?.title,
    material: design?.material,
    load_newtons: design?.load_newtons,
    dimensions_mm: design
      ? { length: design.base_length_mm, width: design.base_width_mm, thickness: design.base_thickness_mm }
      : null,
    feature_count: features.length,
    feature_types: featureTypes,
    recent_feature_notes: notes,
    analysis: analysis
      ? {
          score: analysis.score,
          safety_factor: analysis.safety_factor,
          max_stress_mpa: analysis.max_stress_mpa,
          max_displacement_mm: analysis.max_displacement_mm,
          mass_g: analysis.mass_g,
          verdict: analysis.verdict
        }
      : null,
    semantic_requirements: {
      flower_backrest: wantsFlowerBackrest(prompt),
      curvy_chair: wantsCurvyChair(prompt)
    }
  };
}

function sanitizeContinuationActions(rawPlan, prompt, currentDesign) {
  const family = familyFromPrompt(prompt);
  const existingCounts = {};
  for (const feature of currentDesign?.features || []) {
    existingCounts[feature.type] = (existingCounts[feature.type] || 0) + 1;
  }
  let featureSequence = (currentDesign?.features || []).length;
  const actions = (Array.isArray(rawPlan?.actions) ? rawPlan.actions : [])
    .filter((action) => allowedToolNames.has(action?.tool))
    .filter((action) => !["create_design_family", "export_cadquery", "run_fea", "commit_design"].includes(action.tool))
    .map((action) => {
      const params = action.params && typeof action.params === "object" ? { ...action.params } : {};
      let ordinal = 0;
      let sequence = 0;
      if (action.tool === "add_feature") {
        featureSequence += 1;
        sequence = featureSequence;
        params.type = inferFeatureType(params, family, sequence);
        ordinal = existingCounts[params.type] = (existingCounts[params.type] || 0) + 1;
      }
      return { tool: action.tool, params: sanitizeActionParams(action.tool, params, family, ordinal, sequence) };
    });
  return applyPromptStyleToActions(actions, prompt, family);
}

async function planContinuationWithModel(prompt, currentDesign, currentAnalysis, round, maxRounds) {
  loadEnv();
  const model = process.env.MODEL_NAME || "gpt-5.4";
  const systemPrompt = [
    toolPlannerSystemPrompt(),
    "",
    "You are now replanning from an existing CAD state.",
    "Return only the next few repair/improvement tool calls. Do not recreate the design family. Do not export, run FEA, or commit; the environment handles those.",
    "Prefer semantic repairs first: if the prompt asks for a flower backrest and the current state lacks decorative_curve flower/petal features, add them.",
    "Use structural repairs if safety factor is low or the chair is missing legs/back/crossbars."
  ].join("\n");
  const observation = compactDesignObservation(currentDesign, currentAnalysis, prompt);
  const userMessage = [
    `Round ${round} of ${maxRounds}.`,
    "Current CAD/environment observation:",
    JSON.stringify(observation, null, 2),
    "",
    "Return valid JSON only with this shape:",
    '{"family":"chair","rationale":"...","actions":[{"tool":"add_feature","params":{"type":"decorative_curve","x":45,"y":42,"width":30,"height":30,"radius":8,"note":"flower petal curve"}}]}'
  ].join("\n");

  if (!process.env.OPENAI_API_KEY) {
    return {
      source: "deterministic_continuation_fallback",
      model,
      system: systemPrompt,
      user: userMessage,
      plan: { family: familyFromPrompt(prompt), rationale: "OPENAI_API_KEY missing; used local continuation repair.", actions: continuationFallbackActions(prompt, currentDesign) }
    };
  }

  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const response = await client.responses.create({
    model,
    input: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userMessage }
    ]
  });
  const rawText = response.output_text || "";
  const parsedJson = JSON.parse(rawText);
  return {
    source: "openai_receding_horizon_planner",
    model,
    system: systemPrompt,
    user: userMessage,
    plan: {
      family: allowedFamilies.has(parsedJson?.family) ? parsedJson.family : familyFromPrompt(prompt),
      rationale: parsedJson?.rationale || "Continuation repair plan.",
      actions: sanitizeContinuationActions(parsedJson, prompt, currentDesign)
    }
  };
}

function continuationFallbackActions(prompt, currentDesign) {
  const actions = [];
  const features = currentDesign?.features || [];
  if (wantsFlowerBackrest(prompt) && !features.some((feature) => feature.type === "decorative_curve" && /flower|petal|blossom/i.test(feature.note || ""))) {
    actions.push(
      { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, width: 30, height: 30, radius: 8, note: "flower backrest center blossom" } },
      { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, width: 48, height: 24, radius: 6, note: "six petal flower pattern on backrest" } },
      { tool: "add_feature", params: { type: "decorative_curve", x: 45, y: 42, width: 18, height: 36, radius: 4, note: "flower stem and leaf curves on backrest" } }
    );
  }
  if (currentDesign && currentDesign.load_newtons < 1600 && /1600\s*n/i.test(prompt)) {
    actions.push({ tool: "set_load", params: { point_mm: [currentDesign.base_length_mm / 2, 0, currentDesign.base_thickness_mm], vector_n: [0, 0, -1600] } });
  }
  return actions;
}

function runToolEpisode(prompt = "", actions = null, initialDesign = null) {
  const family = familyFromPrompt(prompt);
  return runPythonTool("run-actions", {
    prompt,
    actions: actions || actionsForFamily(family, prompt),
    initial_design: initialDesign
  });
}

function summarizeSimulation(simulation) {
  if (!simulation?.element_results) return simulation;
  return {
    method: simulation.method,
    node_count: simulation.nodes?.length,
    element_count: simulation.tets?.length || simulation.elements?.length,
    max_stress_mpa: simulation.max_stress_mpa,
    max_strain_microstrain: simulation.max_strain_microstrain,
    tip_deflection_mm: simulation.tip_deflection_mm,
    max_displacement_mm: simulation.max_displacement_mm,
    safety_factor: simulation.safety_factor,
    mass_g: simulation.mass_g,
    score: simulation.score,
    force_vector_n: simulation.force_vector_n,
    load_case: simulation.load_case,
    stress_regions: simulation.stress_regions,
    verdict: simulation.verdict
  };
}

function summarizeToolResult(result) {
  if (!result?.simulation) return result || {};
  return {
    ...result,
    simulation: summarizeSimulation(result.simulation)
  };
}

function invalidGeometryPenalty(design) {
  let penalty = 0;
  for (const feature of design.features) {
    const outside =
      feature.x < 0 ||
      feature.x > design.base_length_mm ||
      feature.y < -design.base_width_mm / 2 ||
      feature.y > design.base_width_mm / 2;
    if (outside) penalty += 0.08;
    if (feature.type === "lightening_hole" && feature.radius > design.base_width_mm / 3) penalty += 0.12;
    if (feature.type === "rib" && feature.height < design.base_thickness_mm) penalty += 0.04;
  }
  return clamp(penalty, 0, 0.8);
}

const sampleDesign = {
  title: "Two-rib lightweight cantilever bracket",
  rationale:
    "A broad thin base keeps bolt spacing stable, two diagonal ribs move material toward the bending load path, and small lightening holes reduce mass away from the fixed edge.",
  material: "aluminum_6061",
  load_newtons: 120,
  load_point_x_mm: 90,
  load_point_y_mm: 0,
  base_length_mm: 105,
  base_width_mm: 44,
  base_thickness_mm: 4,
  fixed_holes: [
    { x: 12, y: -13, radius: 3 },
    { x: 12, y: 13, radius: 3 }
  ],
  features: [
    { type: "rib", x: 16, y: -14, x2: 88, y2: -4, width: 5, height: 18, radius: 0, note: "lower diagonal rib" },
    { type: "rib", x: 16, y: 14, x2: 88, y2: 4, width: 5, height: 18, radius: 0, note: "upper diagonal rib" },
    { type: "rib", x: 18, y: 0, x2: 96, y2: 0, width: 4, height: 12, radius: 0, note: "center spine rib" },
    { type: "lightening_hole", x: 52, y: -13, x2: 0, y2: 0, width: 0, height: 0, radius: 4, note: "low-stress pocket" },
    { type: "lightening_hole", x: 52, y: 13, x2: 0, y2: 0, width: 0, height: 0, radius: 4, note: "low-stress pocket" },
    { type: "boss", x: 92, y: 0, x2: 0, y2: 0, width: 0, height: 7, radius: 6, note: "load application boss" }
  ],
  expected_failure_mode: "Bending stress at the fixed edge and rib roots.",
  action_plan: ["Search the load path", "Add ribs along tension/compression lines", "Remove material from low-stress regions", "Run simulation", "Iterate dimensions"]
};

function defaultSystemPrompt() {
  return [
    "You are a mechanical design assistant producing constrained parametric CAD JSON.",
    "Pick an identifiable family before designing: bracket, wall_hook, torque_clamp, motor_stator, chair, or bike_fixture.",
    "Use family-specific features when appropriate: hook_curve for hooks, clamp_jaw for clamps, stator_ring/stator_tooth for motors, seat_panel/chair_leg/chair_back for chairs, and rib/lightening_hole/boss for brackets.",
    "Use millimeters and newtons. Keep coordinates inside the base plate: x from 0 to base_length_mm and y from -base_width_mm/2 to +base_width_mm/2.",
    "The environment runs a coarse 3D linear tetrahedral elasticity solve with a fixed left face and inferred load point unless the prompt specifies otherwise.",
    "Do not turn non-bracket objects into ribbed plates. A hook must visibly be a hook, a stator must be circular with teeth, and a chair must have a seat and legs.",
    "Use every numeric field in the schema. For unused feature fields, set numeric values to 0 and explain in note.",
    "Do not output markdown. Return only the structured design."
  ].join("\n");
}

function feedbackPrompt(prompt, previousDesign, previousAnalysis, iteration, maxIterations) {
  if (!previousDesign) return prompt;
  return [
    prompt,
    "",
    `Iteration ${iteration} of ${maxIterations}. Improve the previous design using this verifier feedback.`,
    `Previous title: ${previousDesign.title}`,
    `Score: ${previousAnalysis.score}`,
    `Mass: ${previousAnalysis.mass_g} g`,
    `Stress: ${previousAnalysis.max_stress_mpa} MPa`,
    `Strain: ${previousAnalysis.max_strain_microstrain} microstrain`,
    `Safety factor: ${previousAnalysis.safety_factor}`,
    `Tip deflection: ${previousAnalysis.tip_deflection_mm} mm`,
    `Thermal proxy rise: ${previousAnalysis.thermal_delta_c_proxy} C`,
    `FEA method: ${previousAnalysis.fea?.method || "unknown"}`,
    `Highest-stress regions: ${JSON.stringify(previousAnalysis.stress_regions || [])}`,
    `Verdict: ${previousAnalysis.verdict}`,
    "Return a revised design. Preserve useful load-path features, reduce mass if safety factor is excessive, and improve weak areas if stress or deflection is high."
  ].join("\n");
}

async function generateDesignForModel(client, model, prompt, previousDesign = null, previousAnalysis = null, iteration = 1, maxIterations = 1, systemPrompt = defaultSystemPrompt()) {
  const userMessage = feedbackPrompt(prompt, previousDesign, previousAnalysis, iteration, maxIterations);
  const response = await client.responses.parse({
    model,
    input: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userMessage }
    ],
    text: {
      format: zodTextFormat(DesignSchema, "mechanical_design")
    }
  });

  const design = response.output_parsed;
  const analysis = simulateDesign(design, prompt);
  return {
    design,
    analysis,
    model,
    trace: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userMessage },
      { role: "assistant", content: design },
      { role: "tool", name: "run_python_3d_fea", content: analysis }
    ]
  };
}

async function runIterativeBenchmark(client, model, prompt, iterations, systemPrompt = defaultSystemPrompt()) {
  const trace = [];
  let previousDesign = null;
  let previousAnalysis = null;
  for (let iteration = 1; iteration <= iterations; iteration += 1) {
    const result = await generateDesignForModel(client, model, prompt, previousDesign, previousAnalysis, iteration, iterations, systemPrompt);
    trace.push({ iteration, ...result });
    previousDesign = result.design;
    previousAnalysis = result.analysis;
  }
  return {
    model,
    iterations,
    best: trace.reduce((best, item) => (item.analysis.score > best.analysis.score ? item : best), trace[0]),
    final: trace[trace.length - 1],
    trace
  };
}

app.get("/api/sample", (_req, res) => {
  res.json({ design: sampleDesign, analysis: simulateDesign(sampleDesign), source: "local_sample" });
});

app.post("/api/tool-episode", async (req, res) => {
  const prompt = String(req.body?.prompt || "").trim();
  const targetToolCalls = clampToolBudget(req.body?.target_tool_calls);
  try {
    let planner;
    try {
      planner = await planToolActionsWithModel(prompt);
    } catch (error) {
      const family = familyFromPrompt(prompt);
      planner = {
        source: "deterministic_fallback",
        model: process.env.MODEL_NAME || "gpt-5.4",
        system: toolPlannerSystemPrompt(),
        user: prompt,
        error: error instanceof Error ? error.message : "Unknown planner error",
        plan: { family, rationale: "Model planner failed; used local family template.", actions: actionsForFamily(family, prompt) }
      };
    }
    const baseActions = normalizePlannedActions(planner.plan, prompt);
    const expandedActions = expandLongHorizonActions(baseActions, targetToolCalls);
    planner = {
      ...planner,
      plan: {
        ...planner.plan,
        base_actions: baseActions,
        actions: expandedActions,
        target_tool_calls: targetToolCalls,
        executable_action_count: expandedActions.length
      }
    };
    const result = runToolEpisode(prompt, expandedActions);
    const simulation = result.last_result?.simulation || simulateDesign(result.design, prompt);
    const trace = (result.trace || []).map((item) => ({
      role: "tool",
      name: item.action?.tool || "unknown_tool",
      content: {
        step: item.step,
        params: item.action?.params || {},
        result: summarizeToolResult(item.result),
        design_snapshot: item.design || null
      }
    }));
    res.json({
      source: "python_tool_episode",
      planner,
      target_tool_calls: targetToolCalls,
      design: result.design,
      analysis: simulation,
      trace
    });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : "Unknown Python tool episode error" });
  }
});

app.post("/api/receding-agent", async (req, res) => {
  const prompt = String(req.body?.prompt || "").trim();
  const targetToolCalls = clampToolBudget(req.body?.target_tool_calls);
  const model = process.env.MODEL_NAME || "gpt-5.4";
  try {
    let trace = [];
    const plannerRounds = [];
    let design = null;
    let analysis = null;
    const maxRounds = clamp(Math.ceil(targetToolCalls / 60), 2, 4);
    const finalActions = [microAction("export_cadquery"), microAction("run_fea"), microAction("commit_design")];
    const perRoundBudget = Math.max(12, Math.floor((targetToolCalls - finalActions.length) / maxRounds));

    let initialPlanner;
    try {
      initialPlanner = await planToolActionsWithModel(prompt);
    } catch (error) {
      const family = familyFromPrompt(prompt);
      initialPlanner = {
        source: "deterministic_fallback",
        model,
        system: toolPlannerSystemPrompt(),
        user: prompt,
        error: error instanceof Error ? error.message : "Unknown planner error",
        plan: { family, rationale: "Model planner failed; used local family template.", actions: actionsForFamily(family, prompt) }
      };
    }
    const firstBaseActions = normalizePlannedActions(initialPlanner.plan, prompt).filter((action) => !["export_cadquery", "run_fea", "commit_design"].includes(action.tool));
    const firstBuildCount = Math.min(firstBaseActions.length, Math.max(7, Math.ceil(firstBaseActions.length * 0.62)));
    const firstChunk = expandActionChunk(firstBaseActions.slice(0, firstBuildCount), perRoundBudget, 1);
    const firstResult = runToolEpisode(prompt, [...firstChunk, microAction("run_fea", { round: 1, reason: "checkpoint before replanning" })]);
    design = firstResult.design;
    analysis = firstResult.last_result?.simulation || simulateDesign(design, prompt);
    trace = trace.concat((firstResult.trace || []).map((item, index) => ({
      role: "tool",
      name: item.action?.tool || "unknown_tool",
      content: {
        step: index + 1,
        round: 1,
        params: item.action?.params || {},
        result: summarizeToolResult(item.result),
        design_snapshot: item.design || null
      }
    })));
    plannerRounds.push({
      round: 1,
      kind: "initial_plan",
      source: initialPlanner.source,
      model: initialPlanner.model,
      system: initialPlanner.system,
      user: initialPlanner.user,
      plan: { ...initialPlanner.plan, base_actions: firstBaseActions, executed_actions: firstChunk }
    });

    const remainingInitialActions = firstBaseActions.slice(firstBuildCount);
    for (let round = 2; round <= maxRounds; round += 1) {
      let continuation;
      try {
        continuation = await planContinuationWithModel(prompt, design, analysis, round, maxRounds);
      } catch (error) {
        continuation = {
          source: "deterministic_continuation_fallback",
          model,
          system: "Local fallback continuation planner.",
          user: JSON.stringify(compactDesignObservation(design, analysis, prompt), null, 2),
          error: error instanceof Error ? error.message : "Unknown continuation planner error",
          plan: { family: familyFromPrompt(prompt), rationale: "Continuation planner failed; used local semantic repair.", actions: continuationFallbackActions(prompt, design) }
        };
      }

      const carryover = round === 2 ? remainingInitialActions : [];
      const continuationActions = sanitizeContinuationActions(continuation.plan, prompt, design);
      const roundActions = [...carryover, ...continuationActions].filter((action, index, all) => {
        const key = JSON.stringify(action);
        return all.findIndex((candidate) => JSON.stringify(candidate) === key) === index;
      });
      if (!roundActions.length) {
        plannerRounds.push({ round, kind: "replan_noop", ...continuation, observation: compactDesignObservation(design, analysis, prompt) });
        continue;
      }

      const chunk = expandActionChunk(roundActions, perRoundBudget, round);
      const result = runToolEpisode(prompt, [...chunk, microAction("run_fea", { round, reason: "checkpoint after replanning" })], design);
      const offset = trace.length;
      design = result.design;
      analysis = result.last_result?.simulation || simulateDesign(design, prompt);
      trace = trace.concat((result.trace || []).map((item, index) => ({
        role: "tool",
        name: item.action?.tool || "unknown_tool",
        content: {
          step: offset + index + 1,
          round,
          params: item.action?.params || {},
          result: summarizeToolResult(item.result),
          design_snapshot: item.design || null
        }
      })));
      plannerRounds.push({
        round,
        kind: "replan",
        source: continuation.source,
        model: continuation.model,
        system: continuation.system,
        user: continuation.user,
        error: continuation.error || null,
        observation: compactDesignObservation(design, analysis, prompt),
        plan: { ...continuation.plan, carryover_actions: carryover, executed_actions: chunk }
      });
    }

    const finalChunk = finalActions;
    const finalResult = runToolEpisode(prompt, finalChunk, design);
    const offset = trace.length;
    design = finalResult.design;
    analysis = finalResult.last_result?.simulation || simulateDesign(design, prompt);
    trace = trace.concat((finalResult.trace || []).map((item, index) => ({
      role: "tool",
      name: item.action?.tool || "unknown_tool",
      content: {
        step: offset + index + 1,
        round: maxRounds + 1,
        params: item.action?.params || {},
        result: summarizeToolResult(item.result),
        design_snapshot: item.design || null
      }
    })));

    res.json({
      source: "receding_horizon_agent",
      planner: {
        source: "receding_horizon",
        model,
        rounds: plannerRounds,
        target_tool_calls: targetToolCalls,
        executable_action_count: trace.length
      },
      target_tool_calls: targetToolCalls,
      design,
      analysis,
      trace
    });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : "Unknown receding-horizon agent error" });
  }
});

app.get("/api/system-prompt", (_req, res) => {
  res.json({ system_prompt: defaultSystemPrompt() });
});

app.post("/api/generate", async (req, res) => {
  loadEnv();
  const model = process.env.MODEL_NAME || "gpt-5.4";
  const prompt = String(req.body?.prompt || "").trim();
  const systemPrompt = String(req.body?.system_prompt || defaultSystemPrompt());
  if (!prompt) {
    res.status(400).json({ error: "Prompt is required." });
    return;
  }

  if (!process.env.OPENAI_API_KEY) {
    res.status(400).json({
      error: "OPENAI_API_KEY is missing. Copy .env.example to .env and paste your key.",
      design: sampleDesign,
      analysis: simulateDesign(sampleDesign)
    });
    return;
  }

  try {
    const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    const result = await generateDesignForModel(client, model, prompt, null, null, 1, 1, systemPrompt);
    res.json({ ...result, source: "openai" });
  } catch (error) {
    res.status(500).json({
      error: error instanceof Error ? error.message : "Unknown OpenAI generation error",
      design: sampleDesign,
      analysis: simulateDesign(sampleDesign)
    });
  }
});

app.post("/api/benchmark", async (req, res) => {
  loadEnv();
  const prompt = String(req.body?.prompt || "").trim();
  const systemPrompt = String(req.body?.system_prompt || defaultSystemPrompt());
  const models = Array.isArray(req.body?.models) && req.body.models.length ? req.body.models.map(String) : ["gpt-5.4"];
  const iterations = clamp(Number(req.body?.iterations || 3), 1, 5);

  if (!prompt) {
    res.status(400).json({ error: "Prompt is required." });
    return;
  }

  if (!process.env.OPENAI_API_KEY) {
    res.status(400).json({ error: "OPENAI_API_KEY is missing in root .env or experiment .env." });
    return;
  }

  try {
    const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    const startedAt = Date.now();
    const results = [];
    for (const benchmarkModel of models) {
      try {
        results.push(await runIterativeBenchmark(client, benchmarkModel, prompt, iterations, systemPrompt));
      } catch (error) {
        results.push({
          model: benchmarkModel,
          error: error instanceof Error ? error.message : "Unknown model benchmark error",
          trace: []
        });
      }
    }
    res.json({
      source: "openai",
      prompt,
      iterations,
      elapsed_ms: Date.now() - startedAt,
      results
    });
  } catch (error) {
    res.status(500).json({
      error: error instanceof Error ? error.message : "Unknown benchmark error"
    });
  }
});

app.listen(port, () => {
  console.log(`MechForge API listening on http://localhost:${port}`);
});
