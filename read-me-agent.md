# SplatCat 🐾 — 3D Gaussian Splatting Suite

> **SplatCat** is an Apple Silicon-native 3D Gaussian Splatting suite that converts standard smartphone videos into real-time, high-density 3D Gaussian Splatting scenes rendered directly on Metal GPU and WebGL/WebGPU.

---

## 🎯 What SplatCat Is & Intends To Be

**SplatCat** bridges the gap between raw video capture and high-performance 3D Gaussian Splatting on macOS and web platforms:

1. **Instant Video-to-3D Reconstruction**: Turn ordinary MOV/MP4 videos into 500,000+ 3D Gaussian Splats on Apple Silicon M-series GPUs without requiring expensive NVIDIA CUDA cloud infrastructure.
2. **Interactive 3D Viewport Controls**: Precise spatial navigation featuring a 3D ViewCube gizmo, upright model flipping, Euler rotation sliders, real-time bounding wireframe crop box, and point-cloud trimming.
3. **Process-Safe Background Work Manager**: Built-in process control using native macOS signals (`kill -STOP` / `kill -CONT`) allowing users to pause high-intensity COLMAP or Metal GPU tasks on demand when system resources are needed for other work.
4. **Real-Time Viewport Live Streaming**: Watch intermediate PLY checkpoints stream live into the 3D viewport as optimization progresses.
5. **iOS Companion Streamer Integration**: Live streaming pre-posed LiDAR keyframe streams from iPhone/iPad cameras directly into SplatCat via WebSockets (`ws://localhost:8765`).
6. **Windows 95 Retro Design System**: Distinctive 90s retro interface using square block buttons (`border-radius: 0px`), hard offset block shadows (`box-shadow: 3px 3px 0px #000`), and exact extracted SplatCat brand colors (`#FDD100` Cat Gold, `#14171C` Dark Slate, `#38BDF8` Cyan).

---

## 🏗️ Architecture & Technology Stack

- **Desktop Host**: macOS Native App built with Swift (`build_mac_app.swift`), WebKit WKWebView bridge, and Cocoa NSApplication.
- **Structure-from-Motion (SfM)**: COLMAP single-camera feature extraction, SIFT GPU matching, and Bundle Adjustment solver.
- **3DGS Optimization**: PyTorch Metal GPU engine (`train_3dgs_metal.py`) utilizing Apple Metal Performance Shaders (MPS), Statistical Outlier Removal (SOR), k-NN adaptive scaling, and normal-aware surface patch expansion.
- **3D Web Viewer**: Three.js WebGL/WebGPU engine (`packages/web-viewer/viewer.js`) supporting spherical harmonic color decoding, local WebGL clipping planes, and live PLY parsing.

---

## 📜 Record of Latest Work & Recent Milestones

### 1. High-Density 3D Scene Reconstruction (597,730 3D Gaussians)
- Processed 643 keyframes extracted at `10 fps` from room video (`/Users/emil/Downloads/testfile.MOV`).
- Solved camera poses via COLMAP SfM yielding 87,386 sparse 3D points.
- Applied Statistical Outlier Removal (SOR) to prune 1,996 background floaters (85,390 clean points).
- Expanded density via Dense Surface Patch Expansion, yielding **597,730 surface-aligned 3D Gaussians** exported to [`packages/web-viewer/livingroom_597k.ply`](file:///Users/emil/Documents/Codex/SplatCat/packages/web-viewer/livingroom_597k.ply).

### 2. Keyframe Extraction Safety Cap (1,000 Images Max)
- Enforced a hard limit of `-vframes 1000` in FFmpeg extraction across [`build_mac_app.swift`](file:///Users/emil/Documents/Codex/SplatCat/build_mac_app.swift) and [`auto_evaluate_pipeline.py`](file:///Users/emil/Documents/Codex/SplatCat/auto_evaluate_pipeline.py).
- Verified via TDD unit test suite [`tests/test_image_capping.py`](file:///Users/emil/Documents/Codex/SplatCat/tests/test_image_capping.py) (**PASSED 100% OK**).

### 3. Background Job `⏸️ Pause Work` / `▶️ Resume Work` Control
- Implemented script message handler `togglePauseProcess` in [`build_mac_app.swift`](file:///Users/emil/Documents/Codex/SplatCat/build_mac_app.swift) and UI binding in [`apps/desktop/app.js`](file:///Users/emil/Documents/Codex/SplatCat/apps/desktop/app.js).
- Sends `SIGSTOP` / `SIGCONT` signals to active COLMAP and PyTorch process PIDs to pause background work instantly without losing state.

### 4. Real-Time Viewport Checkpoint Live Streaming
- Updated [`train_3dgs_metal.py`](file:///Users/emil/Documents/Codex/SplatCat/train_3dgs_metal.py) to save intermediate PLY checkpoints every 300 iterations.
- Enabled live viewport streaming in [`viewer.js`](file:///Users/emil/Documents/Codex/SplatCat/packages/web-viewer/viewer.js) to render 3D point cloud growth in real-time.

### 5. Flat Vector Logo & Windows 95 Button Redesign
- Generated clean 2D flat vector cat illustration (`apps/desktop/icon_true.png`) without pre-rendered rounded squircle frames or artificial drop shadows. Updated macOS Dock icon (`SplatCat.app/Contents/Resources/AppIcon.icns`).
- Extracted exact palette (`#FDD100`, `#14171C`, `#38BDF8`) and updated button styling in [`apps/desktop/style.css`](file:///Users/emil/Documents/Codex/SplatCat/apps/desktop/style.css) and [`packages/web-viewer/style.css`](file:///Users/emil/Documents/Codex/SplatCat/packages/web-viewer/style.css) to square Windows 95 block controls with hard offset shadows.

### 6. Textureless Walls & Specular TV Computer Vision Research
- Documented computer vision literature analysis in [`docs/research/textureless_walls_and_specular_surfaces.md`](file:///Users/emil/Documents/Codex/SplatCat/docs/research/textureless_walls_and_specular_surfaces.md), detailing why flat plaster walls (SIFT DoG contrast threshold failure) and specular TV glass (Lambertian reflection violation) fail in classical SfM, along with planar extrapolation and monocular depth prior solutions.

---

*Repository*: [pearlmuter/SplatCat](https://github.com/pearlmuter/SplatCat.git)  
*Latest Commit*: `71216ef`
