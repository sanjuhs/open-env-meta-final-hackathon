import * as THREE from "three";
import { CSG } from "three-csg-ts";

class ScadParser {
  constructor(source) {
    this.tokens = tokenize(source);
    this.index = 0;
  }

  parseProgram(stopAtBrace = false) {
    const nodes = [];
    while (!this.done()) {
      if (stopAtBrace && this.peek()?.value === "}") break;
      if (this.peek()?.value === ";") {
        this.index += 1;
        continue;
      }
      nodes.push(this.parseStatement());
    }
    return nodes;
  }

  parseStatement() {
    const node = this.parseCall();
    const next = this.peek();
    if (next?.value === "{") {
      this.consume("{");
      node.children = this.parseProgram(true);
      this.consume("}");
    } else if (isChildTakingCall(node.name) && next?.type === "identifier") {
      node.children = [this.parseStatement()];
    }
    if (this.peek()?.value === ";") this.index += 1;
    return node;
  }

  parseCall() {
    const name = this.consumeType("identifier").value;
    this.consume("(");
    const args = [];
    const named = {};
    while (!this.done() && this.peek()?.value !== ")") {
      if (this.peek()?.type === "identifier" && this.peek(1)?.value === "=") {
        const key = this.consumeType("identifier").value;
        this.consume("=");
        named[key] = this.parseValue();
      } else if (this.peek()?.value === "$" && this.peek(1)?.type === "identifier" && this.peek(2)?.value === "=") {
        this.consume("$");
        const key = `$${this.consumeType("identifier").value}`;
        this.consume("=");
        named[key] = this.parseValue();
      } else {
        args.push(this.parseValue());
      }
      if (this.peek()?.value === ",") this.index += 1;
    }
    this.consume(")");
    return { name, args, named, children: [] };
  }

  parseValue() {
    const token = this.peek();
    if (!token) throw new Error("Unexpected end of SCAD input.");
    if (token.value === "[") {
      this.consume("[");
      const values = [];
      while (!this.done() && this.peek()?.value !== "]") {
        values.push(this.parseValue());
        if (this.peek()?.value === ",") this.index += 1;
      }
      this.consume("]");
      return values;
    }
    if (token.type === "number") {
      this.index += 1;
      return Number(token.value);
    }
    if (token.type === "identifier") {
      this.index += 1;
      if (token.value === "true") return true;
      if (token.value === "false") return false;
      return token.value;
    }
    throw new Error(`Unexpected token "${token.value}" while parsing value.`);
  }

  consume(value) {
    const token = this.peek();
    if (token?.value !== value) throw new Error(`Expected "${value}" but found "${token?.value || "end of input"}".`);
    this.index += 1;
    return token;
  }

  consumeType(type) {
    const token = this.peek();
    if (token?.type !== type) throw new Error(`Expected ${type} but found "${token?.value || "end of input"}".`);
    this.index += 1;
    return token;
  }

  peek(offset = 0) {
    return this.tokens[this.index + offset];
  }

  done() {
    return this.index >= this.tokens.length;
  }
}

function tokenize(source) {
  const stripped = String(source)
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/.*$/gm, "");
  const tokens = [];
  const pattern = /\s*(-?\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_]*|\$|[()[\]{},;=])/gy;
  let index = 0;
  while (index < stripped.length) {
    pattern.lastIndex = index;
    const match = pattern.exec(stripped);
    if (!match) {
      if (/\s/.test(stripped[index])) {
        index += 1;
        continue;
      }
      throw new Error(`Unsupported SCAD syntax near "${stripped.slice(index, index + 24)}".`);
    }
    const value = match[1];
    tokens.push({ value, type: /^-?\d/.test(value) ? "number" : /^[A-Za-z_]/.test(value) ? "identifier" : "symbol" });
    index = pattern.lastIndex;
  }
  return tokens;
}

function isChildTakingCall(name) {
  return ["translate", "rotate", "scale", "color", "union", "difference", "intersection"].includes(name);
}

function vector(value, fallback, length = 3) {
  const source = Array.isArray(value) ? value : [value];
  return Array.from({ length }, (_, index) => Number(source[index] ?? fallback[index] ?? 0));
}

function firstNumber(node, keys, fallback) {
  for (const key of keys) {
    if (Number.isFinite(Number(node.named[key]))) return Number(node.named[key]);
  }
  for (const arg of node.args) {
    if (Number.isFinite(Number(arg))) return Number(arg);
  }
  return fallback;
}

function nodeChildren(node) {
  if (!node.children?.length) throw new Error(`${node.name} requires child geometry.`);
  return node.children;
}

function prepareMesh(mesh) {
  mesh.updateMatrixWorld(true);
  mesh.updateMatrix();
  return mesh;
}

function evaluateBoolean(children, operation, material) {
  if (operation === "union" && children.length > 24) {
    throw new Error(`Renderer safety limit: union has ${children.length} children. Keep generated SCAD to 24 or fewer union children so the browser CSG step cannot hang.`);
  }
  let result = prepareMesh(evaluateNode(children[0], material));
  for (const child of children.slice(1)) {
    const next = prepareMesh(evaluateNode(child, material));
    if (operation === "union") result = CSG.union(result, next);
    if (operation === "difference") result = CSG.subtract(result, next);
    if (operation === "intersection") result = CSG.intersect(result, next);
    result.material = material;
  }
  result.geometry.computeVertexNormals();
  return result;
}

function evaluateNode(node, material) {
  if (node.name === "cube") {
    const size = vector(node.named.size ?? node.args[0] ?? 1, [1, 1, 1]);
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(Math.max(size[0], 0.01), Math.max(size[1], 0.01), Math.max(size[2], 0.01)), material);
    if (node.named.center !== true) mesh.position.set(size[0] / 2, size[1] / 2, size[2] / 2);
    return mesh;
  }

  if (node.name === "sphere") {
    const radius = Math.max(firstNumber(node, ["r"], Number(node.named.d || 2) / 2 || 1), 0.01);
    const segments = Math.min(Math.max(Number(node.named.$fn || 16), 8), 24);
    return new THREE.Mesh(new THREE.SphereGeometry(radius, segments, 12), material);
  }

  if (node.name === "cylinder") {
    const height = Math.max(Number(node.named.h ?? node.args[0] ?? 1), 0.01);
    const radius = firstNumber(node, ["r"], Number(node.named.d || 2) / 2 || 1);
    const r1Raw = node.named.r1 ?? (node.named.d1 === undefined ? undefined : Number(node.named.d1) / 2) ?? radius;
    const r2Raw = node.named.r2 ?? (node.named.d2 === undefined ? undefined : Number(node.named.d2) / 2) ?? radius;
    const r1 = Math.max(Number(r1Raw), 0.01);
    const r2 = Math.max(Number(r2Raw), 0.01);
    const segments = Math.min(Math.max(Number(node.named.$fn || 16), 8), 24);
    const geometry = new THREE.CylinderGeometry(r2, r1, height, segments);
    geometry.rotateX(Math.PI / 2);
    const mesh = new THREE.Mesh(geometry, material);
    if (node.named.center !== true) mesh.position.z = height / 2;
    return mesh;
  }

  if (node.name === "union") {
    return evaluateBoolean(nodeChildren(node), "union", material);
  }

  if (node.name === "difference") {
    return evaluateBoolean(nodeChildren(node), "difference", material);
  }

  if (node.name === "intersection") {
    return evaluateBoolean(nodeChildren(node), "intersection", material);
  }

  if (node.name === "translate") {
    const mesh = evaluateNode(nodeChildren(node)[0], material);
    const [x, y, z] = vector(node.args[0] ?? node.named.v, [0, 0, 0]);
    mesh.position.add(new THREE.Vector3(x, y, z));
    return mesh;
  }

  if (node.name === "rotate") {
    const mesh = evaluateNode(nodeChildren(node)[0], material);
    const [x, y, z] = vector(node.args[0] ?? node.named.a, [0, 0, 0]);
    mesh.rotation.x += THREE.MathUtils.degToRad(x);
    mesh.rotation.y += THREE.MathUtils.degToRad(y);
    mesh.rotation.z += THREE.MathUtils.degToRad(z);
    return mesh;
  }

  if (node.name === "scale") {
    const mesh = evaluateNode(nodeChildren(node)[0], material);
    const [x, y, z] = vector(node.args[0] ?? node.named.v, [1, 1, 1]);
    mesh.scale.multiply(new THREE.Vector3(x || 1, y || 1, z || 1));
    return mesh;
  }

  if (node.name === "color") {
    return evaluateNode(nodeChildren(node)[0], material);
  }

  throw new Error(`Unsupported OpenSCAD call "${node.name}". Supported subset: cube, sphere, cylinder, translate, rotate, scale, union, difference, intersection.`);
}

export function renderScadToGroup(source, material) {
  const parser = new ScadParser(source);
  const nodes = parser.parseProgram();
  if (!nodes.length) throw new Error("SCAD input did not contain any renderable geometry.");
  const complexity = countRenderableNodes(nodes);
  if (complexity.primitives > 24) {
    throw new Error(`Renderer safety limit: ${complexity.primitives} primitives. Keep generated SCAD to 24 or fewer primitives.`);
  }
  const mesh = nodes.length === 1 ? evaluateNode(nodes[0], material) : evaluateBoolean(nodes, "union", material);
  mesh.geometry.computeBoundingBox();
  mesh.geometry.computeBoundingSphere();
  const topology = analyzeMeshTopology(mesh.geometry);
  const box = mesh.geometry.boundingBox;
  const dimensions = new THREE.Vector3();
  box.getSize(dimensions);
  const group = new THREE.Group();
  group.add(mesh);
  return {
    group,
    stats: {
      root_nodes: nodes.length,
      triangles: mesh.geometry.index ? mesh.geometry.index.count / 3 : mesh.geometry.attributes.position.count / 3,
      bounding_box: {
        min: [box.min.x, box.min.y, box.min.z],
        max: [box.max.x, box.max.y, box.max.z]
      },
      dimensions: {
        x: dimensions.x,
        y: dimensions.y,
        z: dimensions.z
      },
      connected_components: topology.connected_components,
      floating_parts: Math.max(0, topology.connected_components - 1),
      boundary_edges: topology.boundary_edges,
      non_manifold_edges: topology.non_manifold_edges,
      watertight: topology.boundary_edges === 0 && topology.non_manifold_edges === 0,
      supported_subset: "cube/sphere/cylinder + translate/rotate/scale + union/difference/intersection"
    }
  };
}

function countRenderableNodes(nodes) {
  let total = 0;
  let primitives = 0;
  const stack = [...nodes];
  while (stack.length) {
    const node = stack.pop();
    total += 1;
    if (["cube", "sphere", "cylinder"].includes(node.name)) primitives += 1;
    for (const child of node.children || []) stack.push(child);
  }
  return { total, primitives };
}

function analyzeMeshTopology(geometry) {
  const position = geometry.attributes.position;
  const index = geometry.index;
  const faces = [];
  const vertexKeyToId = new Map();

  function vertexId(rawIndex) {
    const x = position.getX(rawIndex).toFixed(5);
    const y = position.getY(rawIndex).toFixed(5);
    const z = position.getZ(rawIndex).toFixed(5);
    const key = `${x},${y},${z}`;
    if (!vertexKeyToId.has(key)) vertexKeyToId.set(key, vertexKeyToId.size);
    return vertexKeyToId.get(key);
  }

  const triCount = index ? index.count / 3 : position.count / 3;
  for (let tri = 0; tri < triCount; tri += 1) {
    const a = index ? index.getX(tri * 3) : tri * 3;
    const b = index ? index.getX(tri * 3 + 1) : tri * 3 + 1;
    const c = index ? index.getX(tri * 3 + 2) : tri * 3 + 2;
    faces.push([vertexId(a), vertexId(b), vertexId(c)]);
  }

  const edgeCounts = new Map();
  const adjacency = Array.from({ length: vertexKeyToId.size }, () => new Set());
  for (const [a, b, c] of faces) {
    for (const [u, v] of [[a, b], [b, c], [c, a]]) {
      const key = u < v ? `${u}:${v}` : `${v}:${u}`;
      edgeCounts.set(key, (edgeCounts.get(key) || 0) + 1);
      adjacency[u].add(v);
      adjacency[v].add(u);
    }
  }

  let boundaryEdges = 0;
  let nonManifoldEdges = 0;
  for (const count of edgeCounts.values()) {
    if (count === 1) boundaryEdges += 1;
    if (count > 2) nonManifoldEdges += 1;
  }

  const visited = new Set();
  let connectedComponents = 0;
  for (let start = 0; start < adjacency.length; start += 1) {
    if (visited.has(start)) continue;
    connectedComponents += 1;
    const stack = [start];
    visited.add(start);
    while (stack.length) {
      const current = stack.pop();
      for (const next of adjacency[current]) {
        if (!visited.has(next)) {
          visited.add(next);
          stack.push(next);
        }
      }
    }
  }

  return {
    connected_components: connectedComponents,
    boundary_edges: boundaryEdges,
    non_manifold_edges: nonManifoldEdges
  };
}
