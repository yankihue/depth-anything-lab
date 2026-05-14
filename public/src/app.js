import * as THREE from "three";

const params = new URLSearchParams(window.location.search);
const DATASET = (params.get("asset") || "oracle").replace(/[^a-z0-9_-]/gi, "");
const DATA_URL = `./data/${DATASET}-points.json`;
const META_URL = `./data/${DATASET}.meta.json`;

const canvas = document.getElementById("stage");
const statusEl = document.getElementById("status");
const modeName = document.getElementById("modeName");
const pointCount = document.getElementById("pointCount");
const assetName = document.getElementById("assetName");
assetName.textContent = DATASET;

const controls = {
  depthScale: document.getElementById("depthScale"),
  pointSize: document.getElementById("pointSize"),
  scatter: document.getElementById("scatter"),
  depthTint: document.getElementById("depthTint"),
  resetView: document.getElementById("resetView"),
  toggleSpin: document.getElementById("toggleSpin"),
};

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  powerPreference: "high-performance",
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
renderer.setClearColor(0x080507, 1);
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x080507, 0.035);

const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 140);
camera.position.set(0, 0, 15);

const root = new THREE.Group();
scene.add(root);

const key = new THREE.PointLight(0xd1a44d, 1.2, 22);
key.position.set(3, 4, 6);
scene.add(key);

const fill = new THREE.PointLight(0x315b9c, 0.8, 26);
fill.position.set(-5, -2, 7);
scene.add(fill);

const clock = new THREE.Clock();
const state = {
  dragging: false,
  lastX: 0,
  lastY: 0,
  rotX: -0.05,
  rotY: 0.18,
  targetRotX: -0.05,
  targetRotY: 0.18,
  zoom: 15,
  spin: false,
};

let material = null;
let points = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function onResize() {
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", onResize);
onResize();

window.addEventListener("pointerdown", (event) => {
  state.dragging = true;
  state.lastX = event.clientX;
  state.lastY = event.clientY;
});

window.addEventListener("pointerup", () => {
  state.dragging = false;
});

window.addEventListener("pointermove", (event) => {
  if (!state.dragging) return;
  const dx = event.clientX - state.lastX;
  const dy = event.clientY - state.lastY;
  state.lastX = event.clientX;
  state.lastY = event.clientY;
  state.targetRotY += dx * 0.006;
  state.targetRotX += dy * 0.004;
  state.targetRotX = Math.max(-0.85, Math.min(0.85, state.targetRotX));
});

window.addEventListener("wheel", (event) => {
  event.preventDefault();
  state.zoom += event.deltaY * 0.01;
  state.zoom = Math.max(7, Math.min(28, state.zoom));
}, { passive: false });

controls.resetView.addEventListener("click", () => {
  state.targetRotX = -0.05;
  state.targetRotY = 0.18;
  state.zoom = 15;
});

controls.toggleSpin.addEventListener("click", () => {
  state.spin = !state.spin;
  controls.toggleSpin.classList.toggle("active", state.spin);
});

function columnToAttribute(values, itemSize) {
  return new THREE.BufferAttribute(new Float32Array(values), itemSize);
}

async function loadAsset() {
  setStatus("loading point payload");
  const [payload, meta] = await Promise.all([
    fetch(DATA_URL).then((r) => {
      if (!r.ok) throw new Error(`missing ${DATA_URL}`);
      return r.json();
    }),
    fetch(META_URL).then((r) => r.ok ? r.json() : null),
  ]);

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", columnToAttribute(payload.positions, 3));
  geometry.setAttribute("color", columnToAttribute(payload.colors, 3));
  geometry.setAttribute("size", columnToAttribute(payload.sizes, 1));
  geometry.setAttribute("depth", columnToAttribute(payload.depths, 1));
  geometry.setAttribute("seed", columnToAttribute(payload.seeds, 1));
  geometry.computeBoundingSphere();

  material = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.NormalBlending,
    uniforms: {
      uTime: { value: 0 },
      uPx: { value: renderer.getPixelRatio() },
      uDepthScale: { value: Number(controls.depthScale.value) },
      uPointSize: { value: Number(controls.pointSize.value) },
      uScatter: { value: Number(controls.scatter.value) },
      uDepthTint: { value: Number(controls.depthTint.value) },
    },
    vertexShader: `
      attribute vec3 color;
      attribute float size;
      attribute float depth;
      attribute float seed;
      varying vec3 vColor;
      varying float vDepth;
      uniform float uTime;
      uniform float uPx;
      uniform float uDepthScale;
      uniform float uPointSize;
      uniform float uScatter;
      vec3 hash3(float n) {
        return fract(sin(vec3(n, n + 17.1, n + 41.7)) * vec3(43758.5453, 22578.1459, 19642.349));
      }
      void main() {
        vColor = color;
        vDepth = depth;
        vec3 p = position;
        p.z *= uDepthScale;
        vec3 rnd = hash3(seed * 113.0) - 0.5;
        p += rnd * uScatter;
        p.z += sin(uTime * 0.45 + seed * 18.0) * 0.025;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_PointSize = size * uPointSize * uPx * (120.0 / -mv.z);
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: `
      varying vec3 vColor;
      varying float vDepth;
      uniform float uDepthTint;
      void main() {
        vec2 uv = gl_PointCoord - 0.5;
        float d = dot(uv, uv);
        float alpha = exp(-d * 7.0);
        if (alpha < 0.025) discard;
        vec3 nearTint = vec3(1.0, 0.48, 0.24);
        vec3 farTint = vec3(0.2, 0.38, 0.78);
        vec3 depthColor = mix(farTint, nearTint, vDepth);
        vec3 color = mix(vColor, depthColor, uDepthTint);
        color += vec3(1.0, 0.82, 0.48) * pow(max(0.0, 1.0 - length(uv) * 2.0), 5.0) * 0.16;
        gl_FragColor = vec4(color, alpha * 0.94);
      }
    `,
  });

  points = new THREE.Points(geometry, material);
  root.add(points);

  const count = payload.positions.length / 3;
  pointCount.textContent = new Intl.NumberFormat().format(count);
  modeName.textContent = meta?.mode || payload.mode || "unknown";
  setStatus(meta?.mode === "da-v2" ? "Depth Anything V2 asset loaded" : "heuristic asset loaded");
}

function syncControls() {
  if (!material) return;
  material.uniforms.uDepthScale.value = Number(controls.depthScale.value);
  material.uniforms.uPointSize.value = Number(controls.pointSize.value);
  material.uniforms.uScatter.value = Number(controls.scatter.value);
  material.uniforms.uDepthTint.value = Number(controls.depthTint.value);
}

function tick() {
  const dt = Math.min(clock.getDelta(), 1 / 30);
  const t = clock.elapsedTime;

  if (state.spin) state.targetRotY += dt * 0.18;
  state.rotX += (state.targetRotX - state.rotX) * 0.08;
  state.rotY += (state.targetRotY - state.rotY) * 0.08;
  root.rotation.x = state.rotX;
  root.rotation.y = state.rotY;

  camera.position.z += (state.zoom - camera.position.z) * 0.08;
  camera.lookAt(0, 0, 0);

  syncControls();
  if (material) material.uniforms.uTime.value = t;
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

loadAsset().catch((error) => {
  console.error(error);
  setStatus(`missing asset: build public/data/${DATASET}-points.json`);
});
tick();
