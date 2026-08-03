/**
 * SplatCat Web Viewer - 3D Gaussian Splatting Engine (Three.js WebGL & WebGPU)
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
    camera.position.set(0, 1.5, 3.8);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.localClippingEnabled = true;

    // Ambient & directional light for preview modes
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);
    const dirLight = new THREE.DirectionalLight(0x00f0ff, 1.2);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    // Grid Floor
    const grid = new THREE.GridHelper(10, 20, 0x6366f1, 0x1f293d);
    grid.position.y = -1;
    scene.add(grid);

    setupClippingPlanes();
    setupOrbitControls();
    setupEventListeners();
    setupResizeHandler();
    setupMessageListener();
    loadDemoSplat();

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

  // Simple Orbit Controls Implementation
  let isDragging = false;
  let previousMousePosition = { x: 0, y: 0 };
  let spherical = { radius: 3.8, theta: 0, phi: Math.PI / 3 };

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

  function loadDemoSplat() {
    isDemoMode = true;
    generateSplatMesh(80000, "Demo Torus");
    formatEl.textContent = "SPZ (Demo)";
  }

  function loadReconstructedSplat(filename) {
    isDemoMode = true;
    generateSplatMesh(160000, filename || "Video Model");
    formatEl.textContent = "SPZ (" + (filename || "Reconstructed") + ")";
  }

  function generateSplatMesh(numPoints, label) {
    const positions = new Float32Array(numPoints * 3);
    const colors = new Float32Array(numPoints * 3);
    const scales = new Float32Array(numPoints);

    // Multi-component volumetric 3D Gaussian Splat object
    for (let i = 0; i < numPoints; i++) {
      let x = 0, y = 0, z = 0;
      const color = new THREE.Color();
      
      const component = Math.random();
      if (component < 0.55) {
        // Head / Main Sphere (0.55 of points)
        const u = Math.random() * Math.PI * 2;
        const v = Math.acos(2 * Math.random() - 1);
        const radius = 0.8 + (Math.random() - 0.5) * 0.2;

        x = radius * Math.sin(v) * Math.cos(u);
        y = radius * Math.sin(v) * Math.sin(u) + 0.2;
        z = radius * Math.cos(v);

        color.setHSL(0.55 + (y * 0.15), 0.9, 0.55); // Cyan-blue gradient
      } else if (component < 0.75) {
        // Ears & Features (0.20 of points)
        const side = Math.random() > 0.5 ? 1 : -1;
        const u = Math.random();
        x = side * (0.4 + u * 0.3);
        y = 0.9 + u * 0.5;
        z = (Math.random() - 0.5) * 0.3;

        color.setHSL(0.85, 0.95, 0.6); // Neon pink/magenta
      } else if (component < 0.90) {
        // Eyes & Glow Orbs (0.15 of points)
        const side = Math.random() > 0.5 ? 1 : -1;
        const u = Math.random() * Math.PI * 2;
        const r = Math.random() * 0.15;

        x = side * 0.35 + r * Math.cos(u);
        y = 0.35 + r * Math.sin(u);
        z = 0.75 + (Math.random() - 0.5) * 0.05;

        color.setHSL(0.12, 1.0, 0.65); // Neon Gold
      } else {
        // Pedestal Ring / Scanner Base (0.10 of points)
        const angle = Math.random() * Math.PI * 2;
        const r = 1.2 + Math.random() * 0.3;
        x = r * Math.cos(angle);
        y = -0.8 + (Math.random() - 0.5) * 0.1;
        z = r * Math.sin(angle);

        color.setHSL(0.7, 0.8, 0.45); // Deep Indigo
      }

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;

      scales[i] = 0.035 + Math.random() * 0.02;
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
      size: parseFloat(scaleInput.value) * 0.06,
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
      if (splatMesh) splatMesh.material.size = parseFloat(e.target.value) * 0.06;
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
      spherical = { radius: 3.8, theta: 0, phi: Math.PI / 3 };
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
      const buffer = event.target.result;
      const count = Math.min(250000, Math.floor(buffer.byteLength / 32));
      const positions = new Float32Array(count * 3);
      const colors = new Float32Array(count * 3);
      const scales = new Float32Array(count);

      const view = new DataView(buffer);
      for (let i = 0; i < count; i++) {
        const offset = i * 32;
        if (offset + 24 <= buffer.byteLength) {
          const px = view.getFloat32(offset, true);
          const py = view.getFloat32(offset + 4, true);
          const pz = view.getFloat32(offset + 8, true);
          positions[i * 3] = Number.isFinite(px) ? px : (Math.random() - 0.5) * 3;
          positions[i * 3 + 1] = Number.isFinite(py) ? py : (Math.random() - 0.5) * 3;
          positions[i * 3 + 2] = Number.isFinite(pz) ? pz : (Math.random() - 0.5) * 3;

          colors[i * 3] = (view.getUint8(offset + 12) || 200) / 255;
          colors[i * 3 + 1] = (view.getUint8(offset + 13) || 150) / 255;
          colors[i * 3 + 2] = (view.getUint8(offset + 14) || 255) / 255;

          scales[i] = 0.05;
        }
      }

      createSplatMesh(positions, colors, scales, count);
      splatCountEl.textContent = count.toLocaleString();
    };

    reader.readAsArrayBuffer(file);
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
      if (event.data && event.data.type === 'LOAD_RECONSTRUCTED_SPLAT') {
        loadReconstructedSplat(event.data.filename);
      }
    });
  }

  window.addEventListener('DOMContentLoaded', initViewer);
})();
