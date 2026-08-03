/**
 * SplatCat macOS Desktop Controller App
 */

(function () {
  const navItems = document.querySelectorAll('.nav-item');
  const tabPages = document.querySelectorAll('.tab-page');
  const dropzone = document.getElementById('video-dropzone');
  const videoInput = document.getElementById('video-file-input');
  const processingCard = document.getElementById('processing-card');
  const progressFill = document.getElementById('progress-fill');
  const statusText = document.getElementById('pipeline-status-text');
  const arFrameCountEl = document.getElementById('ar-frame-count');
  const btnExportDesktop = document.getElementById('btn-export-desktop');

  let activeTab = 'create';
  let arFrameCount = 0;

  function initApp() {
    setupTabNavigation();
    setupVideoUpload();
    setupLiveARSimulator();
    setupExporter();
  }

  function setupTabNavigation() {
    navItems.forEach((item) => {
      item.addEventListener('click', () => {
        const targetTab = item.dataset.tab;
        
        navItems.forEach((n) => n.classList.remove('active'));
        tabPages.forEach((p) => p.classList.remove('active'));

        item.classList.add('active');
        document.getElementById(`tab-${targetTab}`).classList.add('active');
        activeTab = targetTab;
      });
    });
  }

  function setupVideoUpload() {
    videoInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        startVideoPipeline(e.target.files[0].name);
      }
    });

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--highlight)';
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.style.borderColor = 'rgba(99, 102, 241, 0.4)';
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'rgba(99, 102, 241, 0.4)';
      if (e.dataTransfer.files.length > 0) {
        startVideoPipeline(e.dataTransfer.files[0].name);
      }
    });
  }

  function startVideoPipeline(filename) {
    processingCard.classList.remove('hidden');
    progressFill.style.width = '0%';
    statusText.textContent = `Processing "${filename}"...`;

    const steps = [
      { id: 'step-extract', pct: 25, label: 'Frame Extraction & Sharpness Filter' },
      { id: 'step-glomap', pct: 50, label: 'GLOMAP Structure-from-Motion Poses' },
      { id: 'step-brush', pct: 80, label: 'Brush 3DGS Training (Metal GPU)' },
      { id: 'step-spz', pct: 100, label: 'SPZ Compression Complete' },
    ];

    let currentStep = 0;

    const interval = setInterval(() => {
      if (currentStep < steps.length) {
        const step = steps[currentStep];
        progressFill.style.width = `${step.pct}%`;
        statusText.textContent = step.label;
        document.getElementById(step.id).classList.add('step-done');
        currentStep++;
      } else {
        clearInterval(interval);
        statusText.textContent = '✨ 3D Splat Ready! Opening 3D Viewport...';
        
        setTimeout(() => {
          document.querySelector('[data-tab="viewport"]').click();
        }, 1200);
      }
    }, 1500);
  }

  function setupLiveARSimulator() {
    // Simulate live frames arriving from iOS companion app
    setInterval(() => {
      arFrameCount += Math.floor(Math.random() * 3);
      arFrameCountEl.textContent = arFrameCount.toLocaleString();
    }, 2000);
  }

  function setupExporter() {
    btnExportDesktop.addEventListener('click', () => {
      const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SplatCat Exported 3D Gaussian Model</title>
  <style>
    body { margin: 0; background: #0a0c10; color: #fff; font-family: sans-serif; overflow: hidden; }
    #canvas { width: 100vw; height: 100vh; display: block; }
    .footer { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(16,20,28,0.8); backdrop-filter: blur(10px); padding: 10px 24px; border-radius: 30px; border: 1px solid rgba(255,255,255,0.1); }
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>
</head>
<body>
  <canvas id="canvas"></canvas>
  <div class="footer">🐾 Rendered with SplatCat WebGPU / WebGL Engine</div>
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
      a.download = 'splatcat_web_export.html';
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  window.addEventListener('DOMContentLoaded', initApp);
})();
