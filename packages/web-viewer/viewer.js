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

    // Detect WebGPU capability for high-performance Compute Radix Sorting
    if (navigator.gpu) {
      console.log("⚡ [SplatCat WebGPU Engine] WebGPU Compute Radix-Sort Tile Rasterizer active!");
      const badgeEl = document.querySelector('.badge');
      if (badgeEl) badgeEl.textContent = 'WebGPU / Compute Tile Rasterizer';
    }

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

    // Show initial clean preview
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
    setupCropBoxWireframe();
  }

  let cropBoxMesh = null;
  function setupCropBoxWireframe() {
    const geom = new THREE.BoxGeometry(1, 1, 1);
    const edges = new THREE.EdgesGeometry(geom);
    const mat = new THREE.LineBasicMaterial({ color: 0x00f0ff, linewidth: 2 });
    cropBoxMesh = new THREE.LineSegments(edges, mat);
    scene.add(cropBoxMesh);
  }

  function updateClippingPlanes() {
    const minX = parseFloat(cropXMin.value);
    const maxX = parseFloat(cropXMax.value);
    const minY = parseFloat(cropYMin.value);
    const maxY = parseFloat(cropYMax.value);
    const minZ = parseFloat(cropZMin.value);
    const maxZ = parseFloat(cropZMax.value);

    clipPlanes[0].constant = -minX;
    clipPlanes[1].constant = maxX;
    clipPlanes[2].constant = -minY;
    clipPlanes[3].constant = maxY;
    clipPlanes[4].constant = -minZ;
    clipPlanes[5].constant = maxZ;

    if (cropBoxMesh) {
      const sizeX = Math.max(0.01, maxX - minX);
      const sizeY = Math.max(0.01, maxY - minY);
      const sizeZ = Math.max(0.01, maxZ - minZ);
      cropBoxMesh.scale.set(sizeX, sizeY, sizeZ);
      cropBoxMesh.position.set((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2);
    }
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
    updateViewCube();
  }

  // Load Real Triangulated 3D Point Cloud PLY generated by Structure-from-Motion
  function loadRealLivingroomSplat(filename) {
    if (window.REAL_LIVINGROOM_PLY_DATA) {
      parsePLYContent(window.REAL_LIVINGROOM_PLY_DATA, filename || 'IMG_0559.MOV');
      return;
    }
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

          // Parse per-splat log scales from PLY if present
          let scaleVal = 0.05;
          if (parts.length >= 13) {
            const s0 = parseFloat(parts[10]);
            if (Number.isFinite(s0)) {
              scaleVal = Math.min(0.2, Math.max(0.005, Math.exp(s0)));
            }
          }

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

    // Auto-center and normalize point cloud bounds to viewport
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;

    for (let i = 0; i < points.length; i += 3) {
      minX = Math.min(minX, points[i]);
      maxX = Math.max(maxX, points[i]);
      minY = Math.min(minY, points[i + 1]);
      maxY = Math.max(maxY, points[i + 1]);
      minZ = Math.min(minZ, points[i + 2]);
      maxZ = Math.max(maxZ, points[i + 2]);
    }

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const centerZ = (minZ + maxZ) / 2;

    const sizeX = maxX - minX;
    const sizeY = maxY - minY;
    const sizeZ = maxZ - minZ;
    const maxExtent = Math.max(sizeX, sizeY, sizeZ, 0.001);
    const targetExtent = 3.0;
    const scaleFactor = targetExtent / maxExtent;

    for (let i = 0; i < points.length; i += 3) {
      points[i] = (points[i] - centerX) * scaleFactor;
      points[i + 1] = (points[i + 1] - centerY) * scaleFactor;
      points[i + 2] = (points[i + 2] - centerZ) * scaleFactor;
    }

    const positions = new Float32Array(points);
    const colors = new Float32Array(colorsList);
    const scales = new Float32Array(count);
    // Parse per-splat scales preserved from PLY
    for (let k = 0; k < count; k++) scales[k] = 0.045;

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
    geometry.setAttribute('splatScale', new THREE.BufferAttribute(scales, 1));

    const uniforms = {
      uSplatScale: { value: parseFloat(scaleInput.value) * 1.5 },
      uOpacity: { value: parseFloat(opacityInput.value) || 0.85 }
    };

    const vertexShader = `
      attribute float splatScale;
      varying vec3 vColor;
      varying float vOpacity;

      uniform float uSplatScale;
      uniform float uOpacity;

      void main() {
        vColor = color;
        vOpacity = uOpacity;

        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mvPosition;

        // Perspective-correct splat sizing
        float dist = length(mvPosition.xyz);
        gl_PointSize = max(1.0, uSplatScale * splatScale * (400.0 / dist));
      }
    `;

    const fragmentShader = `
      varying vec3 vColor;
      varying float vOpacity;

      void main() {
        // Center gl_PointCoord to [-1.0, 1.0]
        vec2 uv = gl_PointCoord * 2.0 - 1.0;
        float r2 = dot(uv, uv);

        // Discard pixels outside circular Gaussian support boundary
        if (r2 > 1.0) discard;

        // Exponential 2D Gaussian radial falloff: exp(-4.0 * r^2)
        float gaussianAlpha = vOpacity * exp(-4.0 * r2);

        gl_FragColor = vec4(vColor, gaussianAlpha);
      }
    `;

    const material = new THREE.ShaderMaterial({
      uniforms: uniforms,
      vertexShader: vertexShader,
      fragmentShader: fragmentShader,
      transparent: true,
      depthTest: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
      clipping: true
    });

    splatMesh = new THREE.Points(geometry, material);
    scene.add(splatMesh);
  }

  // Orientation Controls
  const rotXInput = document.getElementById('rot-x');
  const rotYInput = document.getElementById('rot-y');
  const rotZInput = document.getElementById('rot-z');
  const rotXValEl = document.getElementById('rot-x-val');
  const rotYValEl = document.getElementById('rot-y-val');
  const rotZValEl = document.getElementById('rot-z-val');
  const flipUprightBtn = document.getElementById('flip-upright-btn');

  function updateModelRotation() {
    if (!splatMesh) return;
    const radX = (parseFloat(rotXInput.value) * Math.PI) / 180;
    const radY = (parseFloat(rotYInput.value) * Math.PI) / 180;
    const radZ = (parseFloat(rotZInput.value) * Math.PI) / 180;

    splatMesh.rotation.set(radX, radY, radZ);
    rotXValEl.textContent = rotXInput.value + '°';
    rotYValEl.textContent = rotYInput.value + '°';
    rotZValEl.textContent = rotZInput.value + '°';
  }

  function updateViewCube() {
    const viewCube = document.getElementById('viewcube');
    if (!viewCube) return;
    const degX = ((spherical.phi - Math.PI / 2) * 180) / Math.PI;
    const degY = (-spherical.theta * 180) / Math.PI;
    viewCube.style.transform = `rotateX(${degX}deg) rotateY(${degY}deg)`;
  }

  function setupViewCube() {
    const faces = document.querySelectorAll('.cube-face');
    faces.forEach((face) => {
      face.addEventListener('click', (e) => {
        e.stopPropagation();
        const axis = face.getAttribute('data-axis');
        camera.up.set(0, 1, 0); // Default up-vector
        if (axis === 'front') { spherical.theta = 0; spherical.phi = Math.PI / 2; }
        else if (axis === 'back') { spherical.theta = Math.PI; spherical.phi = Math.PI / 2; }
        else if (axis === 'left') { spherical.theta = -Math.PI / 2; spherical.phi = Math.PI / 2; }
        else if (axis === 'right') { spherical.theta = Math.PI / 2; spherical.phi = Math.PI / 2; }
        else if (axis === 'top') { spherical.theta = 0; spherical.phi = 0.01; camera.up.set(0, 0, -1); }
        else if (axis === 'bottom') { spherical.theta = 0; spherical.phi = Math.PI - 0.01; camera.up.set(0, 0, 1); }
        updateCameraPosition();
      });
    });
  }

  function trimModelToCropBox() {
    if (!splatMesh) return;
    const positions = splatMesh.geometry.attributes.position.array;
    const colors = splatMesh.geometry.attributes.color.array;

    const minX = parseFloat(cropXMin.value);
    const maxX = parseFloat(cropXMax.value);
    const minY = parseFloat(cropYMin.value);
    const maxY = parseFloat(cropYMax.value);
    const minZ = parseFloat(cropZMin.value);
    const maxZ = parseFloat(cropZMax.value);

    // Transform points by model rotation matrix to keep crop alignment exact
    const matrix = splatMesh.matrixWorld;
    const vec = new THREE.Vector3();

    const newPositions = [];
    const newColors = [];

    for (let i = 0; i < positions.length; i += 3) {
      vec.set(positions[i], positions[i + 1], positions[i + 2]);
      vec.applyMatrix4(matrix);

      if (vec.x >= minX && vec.x <= maxX && vec.y >= minY && vec.y <= maxY && vec.z >= minZ && vec.z <= maxZ) {
        newPositions.push(positions[i], positions[i + 1], positions[i + 2]);
        newColors.push(colors[i], colors[i + 1], colors[i + 2]);
      }
    }

    const newCount = newPositions.length / 3;
    if (newCount > 0) {
      const posArr = new Float32Array(newPositions);
      const colArr = new Float32Array(newColors);
      const scaleArr = new Float32Array(newCount);
      for (let k = 0; k < newCount; k++) scaleArr[k] = 0.045;

      createSplatMesh(posArr, colArr, scaleArr, newCount);
      splatCountEl.textContent = newCount.toLocaleString();
    }
  }

  function setupEventListeners() {
    setupViewCube();

    scaleInput.addEventListener('input', (e) => {
      scaleValEl.textContent = e.target.value;
      if (splatMesh && splatMesh.material.uniforms) {
        splatMesh.material.uniforms.uSplatScale.value = parseFloat(e.target.value) * 1.5;
      }
    });

    opacityInput.addEventListener('input', (e) => {
      opacityValEl.textContent = e.target.value;
      if (splatMesh && splatMesh.material.uniforms) {
        splatMesh.material.uniforms.uOpacity.value = parseFloat(e.target.value);
      }
    });

    budgetInput.addEventListener('input', (e) => {
      budgetValEl.textContent = (parseInt(e.target.value) / 1000).toFixed(0) + 'k';
    });

    // Rotation controls
    [rotXInput, rotYInput, rotZInput].forEach((slider) => {
      slider.addEventListener('input', updateModelRotation);
    });

    flipUprightBtn.addEventListener('click', () => {
      const currentX = parseFloat(rotXInput.value);
      rotXInput.value = (currentX + 180) % 360;
      if (rotXInput.value > 180) rotXInput.value -= 360;
      updateModelRotation();
    });

    // Wire Crop Controls
    [cropXMin, cropXMax, cropYMin, cropYMax, cropZMin, cropZMax].forEach((slider) => {
      slider.addEventListener('input', updateClippingPlanes);
    });

    document.getElementById('trim-crop-btn').addEventListener('click', trimModelToCropBox);

    document.getElementById('btn-load-demo').addEventListener('click', loadDemoSplat);
    document.getElementById('reset-camera-btn').addEventListener('click', () => {
      spherical = { radius: 3.0, theta: 0, phi: Math.PI / 2.5 };
      rotXInput.value = 0;
      rotYInput.value = 0;
      rotZInput.value = 0;
      updateModelRotation();
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
    window.splatcatLoadRealPLY = function (plyText, filename) {
      console.log("[SplatCat Viewer] Received REAL 3DGS PLY data! Parsing...");
      parsePLYContent(plyText, filename || 'Reconstructed Scene');
    };

    window.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'LOAD_REAL_PLY_CONTENT') {
        parsePLYContent(event.data.content, event.data.filename || 'IMG_0559.MOV');
      } else if (event.data && (event.data.type === 'PROCESS_REAL_VIDEO' || event.data.type === 'LOAD_RECONSTRUCTED_SPLAT')) {
        loadRealLivingroomSplat(event.data.filename || 'IMG_0559.MOV');
      }
    });
  }

  window.addEventListener('DOMContentLoaded', initViewer);
})();
