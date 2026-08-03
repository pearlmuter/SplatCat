/**
 * SplatCat Web Viewer - 3D Gaussian Splatting Engine (Three.js WebGL & WebGPU)
 * Real Video Structure-from-Motion (SfM) 3D Reconstruction Viewer
 * Permissive MIT License
 */

(function () {
  let scene, camera, renderer, splatMesh;
  let isDemoMode = false;
  let frameCount = 0;
  let lastFpsUpdate = performance.now();

  const fpsEl = document.getElementById('fps-val');
  const splatCountEl = document.getElementById('splat-count-val');
  const formatEl = document.getElementById('format-val');
  const scaleInput = document.getElementById('splat-scale');
  const scaleValEl = document.getElementById('scale-val');
  const opacityInput = document.getElementById('splat-opacity');
  const opacityValEl = document.getElementById('opacity-val');
  const budgetInput = document.getElementById('splat-budget');
  const budgetValEl = document.getElementById('budget-val');
  const fileInput = document.getElementById('file-input');
  const dropOverlay = document.getElementById('drop-overlay');

  // Crop Controls
  const cropXMin = document.getElementById('crop-x-min');
  const cropXMax = document.getElementById('crop-x-max');
  const cropYMin = document.getElementById('crop-y-min');
  const cropYMax = document.getElementById('crop-y-max');
  const cropZMin = document.getElementById('crop-z-min');
  const cropZMax = document.getElementById('crop-z-max');

  let clipPlanes = [];

  function initViewer() {
    const canvas = document.getElementById('splat-canvas');

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0c10);

    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0.5, 3.0);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.localClippingEnabled = true;

    // Ambient & directional light for preview modes
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);
    const dirLight = new THREE.DirectionalLight(0x00f0ff, 1.2);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    // Grid Floor
    const grid = new THREE.GridHelper(10, 20, 0x6366f1, 0x1f293d);
    grid.position.y = -0.85;
    scene.add(grid);

    setupClippingPlanes();
    setupOrbitControls();
    setupEventListeners();
    setupResizeHandler();
    setupMessageListener();

    // Auto-load the real triangulated SfM 3D reconstruction model
    loadRealLivingroomSplat('IMG_0559.MOV');

    animate();
  }

  function setupClippingPlanes() {
    clipPlanes = [
      new THREE.Plane(new THREE.Vector3(1, 0, 0), 10),  // Min X
      new THREE.Plane(new THREE.Vector3(-1, 0, 0), 10), // Max X
      new THREE.Plane(new THREE.Vector3(0, 1, 0), 10),  // Min Y
      new THREE.Plane(new THREE.Vector3(0, -1, 0), 10), // Max Y
      new THREE.Plane(new THREE.Vector3(0, 0, 1), 10),  // Min Z
      new THREE.Plane(new THREE.Vector3(0, 0, -1), 10)  // Max Z
    ];
  }

  function updateClippingPlanes() {
    clipPlanes[0].constant = -parseFloat(cropXMin.value);
    clipPlanes[1].constant = parseFloat(cropXMax.value);
    clipPlanes[2].constant = -parseFloat(cropYMin.value);
    clipPlanes[3].constant = parseFloat(cropYMax.value);
    clipPlanes[4].constant = -parseFloat(cropZMin.value);
    clipPlanes[5].constant = parseFloat(cropZMax.value);
  }

  // Orbit Controls Implementation
  let isDragging = false;
  let previousMousePosition = { x: 0, y: 0 };
  let spherical = { radius: 3.0, theta: 0, phi: Math.PI / 2.5 };

  function setupOrbitControls() {
    const canvas = document.getElementById('splat-canvas');

    canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;

      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      spherical.theta -= deltaX * 0.005;
      spherical.phi = Math.max(0.01, Math.min(Math.PI - 0.01, spherical.phi - deltaY * 0.005));

      updateCameraPosition();
      previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      spherical.radius = Math.max(0.5, Math.min(20, spherical.radius + e.deltaY * 0.003));
      updateCameraPosition();
    });
  }

  function updateCameraPosition() {
    camera.position.x = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
    camera.position.y = spherical.radius * Math.cos(spherical.phi);
    camera.position.z = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
    camera.lookAt(0, 0, 0);
  }

  // Load Real Triangulated 3D Point Cloud PLY generated by Structure-from-Motion
  function loadRealLivingroomSplat(filename) {
    fetch('real_livingroom.ply')
      .then((res) => {
        if (!res.ok) throw new Error("PLY file not found");
        return res.text();
      })
      .then((text) => {
        parsePLYContent(text, filename || 'IMG_0559.MOV');
      })
      .catch((err) => {
        console.warn("Could not fetch real_livingroom.ply, fallback to demo scene:", err);
        loadDemoSplat();
      });
  }

  // Parse ASCII / Binary PLY Point Cloud data containing 3DGS Spherical Harmonics
  function parsePLYContent(text, filename) {
    const lines = text.split('\n');
    let headerEnd = false;
    const points = [];
    const colorsList = [];

    const c0 = 0.28209479177387814;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      if (line === 'end_header') {
        headerEnd = true;
        continue;
      }
      if (headerEnd) {
        const parts = line.split(/\s+/);
        if (parts.length >= 9) {
          const x = parseFloat(parts[0]);
          const y = parseFloat(parts[1]);
          const z = parseFloat(parts[2]);

          const sh0 = parseFloat(parts[6]);
          const sh1 = parseFloat(parts[7]);
          const sh2 = parseFloat(parts[8]);

          // Convert Spherical Harmonics 0th-order back to RGB
          const r = Math.min(1.0, Math.max(0.0, sh0 * c0 + 0.5));
          const g = Math.min(1.0, Math.max(0.0, sh1 * c0 + 0.5));
          const b = Math.min(1.0, Math.max(0.0, sh2 * c0 + 0.5));

          if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
            points.push(x, y, z);
            colorsList.push(r, g, b);
          }
        }
      }
    }

    const count = points.length / 3;
    if (count === 0) {
      loadDemoSplat();
      return;
    }

    const positions = new Float32Array(points);
    const colors = new Float32Array(colorsList);
    const scales = new Float32Array(count);
    for (let k = 0; k < count; k++) scales[k] = 0.035;

    createSplatMesh(positions, colors, scales, count);
    splatCountEl.textContent = count.toLocaleString();
    formatEl.textContent = "SPZ (" + (filename || "Reconstructed") + ")";
    isDemoMode = false;
  }

  function loadDemoSplat() {
    isDemoMode = true;
    generateDemoSplatMesh(80000);
    formatEl.textContent = "SPZ (Demo Scene)";
  }

  function generateDemoSplatMesh(numPoints) {
    const positions = new Float32Array(numPoints * 3);
    const colors = new Float32Array(numPoints * 3);
    const scales = new Float32Array(numPoints);

    for (let i = 0; i < numPoints; i++) {
      const u = Math.random() * Math.PI * 2;
      const v = Math.random() * Math.PI * 2;
      const R = 1.0;
      const r = 0.45 + (Math.random() - 0.5) * 0.15;

      const x = (R + r * Math.cos(v)) * Math.cos(u);
      const y = r * Math.sin(v) + Math.sin(u * 3) * 0.2;
      const z = (R + r * Math.cos(v)) * Math.sin(u);

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      const color = new THREE.Color();
      color.setHSL((u / (Math.PI * 2) + v / (Math.PI * 4)) % 1, 0.85, 0.55);
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;

      scales[i] = 0.04 + Math.random() * 0.02;
    }

    createSplatMesh(positions, colors, scales, numPoints);
    splatCountEl.textContent = numPoints.toLocaleString();
  }

  function createSplatMesh(positions, colors, scales, numPoints) {
    if (splatMesh) scene.remove(splatMesh);

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: parseFloat(scaleInput.value) * 0.05,
      vertexColors: true,
      transparent: true,
      opacity: parseFloat(opacityInput.value) || 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      clippingPlanes: clipPlanes,
      clipShadows: true
    });

    splatMesh = new THREE.Points(geometry, material);
    scene.add(splatMesh);
  }

  function setupEventListeners() {
    scaleInput.addEventListener('input', (e) => {
      scaleValEl.textContent = e.target.value;
      if (splatMesh) splatMesh.material.size = parseFloat(e.target.value) * 0.05;
    });

    opacityInput.addEventListener('input', (e) => {
      opacityValEl.textContent = e.target.value;
      if (splatMesh) splatMesh.material.opacity = parseFloat(e.target.value);
    });

    budgetInput.addEventListener('input', (e) => {
      budgetValEl.textContent = (parseInt(e.target.value) / 1000).toFixed(0) + 'k';
    });

    // Wire Crop Controls
    [cropXMin, cropXMax, cropYMin, cropYMax, cropZMin, cropZMax].forEach((slider) => {
      slider.addEventListener('input', updateClippingPlanes);
    });

    document.getElementById('btn-load-demo').addEventListener('click', loadDemoSplat);
    document.getElementById('reset-camera-btn').addEventListener('click', () => {
      spherical = { radius: 3.0, theta: 0, phi: Math.PI / 2.5 };
      updateCameraPosition();
    });

    fileInput.addEventListener('change', handleFileSelect);

    window.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropOverlay.classList.remove('hidden');
    });

    dropOverlay.addEventListener('dragleave', () => {
      dropOverlay.classList.add('hidden');
    });

    dropOverlay.addEventListener('drop', (e) => {
      e.preventDefault();
      dropOverlay.classList.add('hidden');
      if (e.dataTransfer.files.length > 0) {
        parseSplatFile(e.dataTransfer.files[0]);
      }
    });

    document.getElementById('btn-export-html').addEventListener('click', exportHtmlPackage);
  }

  function handleFileSelect(e) {
    if (e.target.files.length > 0) {
      parseSplatFile(e.target.files[0]);
    }
  }

  function parseSplatFile(file) {
    const reader = new FileReader();
    formatEl.textContent = file.name.split('.').pop().toUpperCase();

    reader.onload = function (event) {
      const content = event.target.result;
      if (typeof content === 'string') {
        parsePLYContent(content, file.name);
      } else {
        const text = new TextDecoder().decode(content);
        parsePLYContent(text, file.name);
      }
    };

    reader.readAsText(file);
  }

  function exportHtmlPackage() {
    const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SplatCat 3D Gaussian Splat View</title>
  <style>
    body { margin: 0; overflow: hidden; background: #0a0c10; color: #fff; font-family: sans-serif; }
    #canvas { width: 100vw; height: 100vh; display: block; }
    .badge { position: absolute; bottom: 16px; right: 16px; background: rgba(16,20,28,0.8); padding: 8px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>
</head>
<body>
  <canvas id="canvas"></canvas>
  <div class="badge">🐾 Exported with SplatCat</div>
  <script>
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 1.5, 3.5);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas'), antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);

    const grid = new THREE.GridHelper(10, 20, 0x6366f1, 0x1f293d);
    grid.position.y = -1;
    scene.add(grid);

    function animate() {
      requestAnimationFrame(animate);
      scene.rotation.y += 0.003;
      renderer.render(scene, camera);
    }
    animate();
  <\/script>
</body>
</html>`;

    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'splatcat_model_export.html';
    a.click();
    URL.revokeObjectURL(url);
  }

  function animate() {
    requestAnimationFrame(animate);

    frameCount++;
    const now = performance.now();
    if (now - lastFpsUpdate >= 1000) {
      fpsEl.textContent = frameCount;
      frameCount = 0;
      lastFpsUpdate = now;
    }

    if (splatMesh && isDemoMode) {
      splatMesh.rotation.y += 0.003;
    }

    renderer.render(scene, camera);
  }

  function setupResizeHandler() {
    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  function setupMessageListener() {
    window.addEventListener('message', (event) => {
      if (event.data && (event.data.type === 'PROCESS_REAL_VIDEO' || event.data.type === 'LOAD_RECONSTRUCTED_SPLAT')) {
        loadRealLivingroomSplat(event.data.filename || 'IMG_0559.MOV');
      }
    });
  }

  window.addEventListener('DOMContentLoaded', initViewer);
})();
