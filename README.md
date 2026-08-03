# SplatCat 🐾 - 3D Gaussian Splatting Suite for macOS & iOS

SplatCat is a 3D Gaussian Splatting application ecosystem for macOS and iOS. It converts regular videos or real-time iOS LiDAR AR camera streams into photorealistic 3D Gaussian Splat models ready to view and share directly in any web browser.

---

## 🏛️ Permissive Licensing (Resale Compatible)

All core components and dependencies used by SplatCat strictly enforce permissive commercial resale licenses (**Apache-2.0**, **MIT**, and **BSD-3-Clause**). 
* **Brush 3DGS Engine** (`Apache-2.0`) — Rust + WebGPU / Metal 3DGS training engine.
* **GLOMAP SfM** (`BSD-3-Clause`) — Ultra-fast Structure-from-Motion pose solver by ETH Zurich.
* **SuperSplat / PlayCanvas** (`MIT`) — WebGL2 / WebGPU browser viewer & exporter.

---

## 📦 Project Structure

```
SplatCat/
├── apps/
│   ├── desktop/              # macOS Desktop Application UI & Tauri App
│   └── mobile/               # iOS Companion AR Scanner (Swift + ARKit + Metal)
├── crates/
│   └── engine/               # Rust Core Engine (FFmpeg, GLOMAP, Brush 3DGS, SPZ)
├── packages/
│   └── web-viewer/           # WebGL2/WebGPU 3D Splat Viewport & Exporter
├── Cargo.toml                # Root Cargo Workspace
└── README.md
```

---

## 🚀 Quick Start & Testing

### 1. Test Rust Engine Workspace
Run `cargo check` to verify the Rust engine and desktop backend compilation:
```bash
cargo check --workspace
```

### 2. View 3D Web Viewer in Browser
Open `packages/web-viewer/index.html` in Safari, Chrome, or Edge to experience the interactive 3D Gaussian Splatting viewport.
* Click **Load Demo Splat** to generate a live 3D Gaussian Splat scene.
* Drag and drop any `.splat`, `.spz`, or `.ply` file directly into the viewport.
* Click **Export HTML Package** to generate a single-file standalone web viewer.

### 3. Run macOS Desktop Application
Open `apps/desktop/index.html` or run the Tauri application. Drag and drop any MP4 video to trigger the automatic 4-stage 3D reconstruction pipeline.

### 4. iOS AR Companion App
Build and run `apps/mobile/SplatCatCompanion` on an iPhone/iPad with LiDAR using Xcode 16+.
* Surfaces highlight in **green/blue** when scanned (via Metal `HeatmapShader.metal`).
* Tap **Start Live Stream** to stream ARKit camera matrix poses and RGB frames over local Wi-Fi to your Mac on `ws://<MAC_IP>:8765`.
