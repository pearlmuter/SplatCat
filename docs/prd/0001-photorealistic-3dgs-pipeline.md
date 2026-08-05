# PRD 0001: Photorealistic Apple Silicon 3D Gaussian Splatting Suite

## Problem Statement

When users capture 3D room scenes (such as an armchair corner) with their smartphones and process them into 3D Gaussian Splats, the resulting 3D models currently suffer from visual artifacts:
1. **Pixelated Square "Confetti" Viewport Artifacts**: Point-sprite rendering in WebGL causes Gaussians to appear as hard square dots instead of smooth, continuous surfaces.
2. **Fuzzy 3D Object Reconstruction**: Spatial point-cloud heuristics lack image-based photometric reconstruction loss ($L_1 + L_{\text{SSIM}}$), causing soft object boundaries and inaccurate surface textures.
3. **Missing Plaster Walls & Glossy Surfaces**: Smooth painted walls and reflective TV screens yield 0 SIFT feature keypoints in COLMAP SfM, creating hollow voids or floaters in empty room space.
4. **Capture Flickering**: Dynamic smartphone auto-exposure (AE) shifts and camera whip-pans degrade bundle adjustment accuracy.

---

## Solution

A high-performance, Apple Silicon-native 3D Gaussian Splatting pipeline and WebGPU viewport system:
1. **WebGPU Tile Rasterizer with GPU Radix Sort**: In-VRAM compute shader sorting and rendering for 1M+ Gaussians at 60 FPS in desktop and web viewports.
2. **Native Rust / `wgpu` (`Brush`) Metal GPU Differentiable Engine**: Image-based $L_1 + L_{\text{SSIM}}$ photometric reconstruction loss, adaptive Gaussian splitting, cloning, and alpha pruning running natively on Metal GPUs.
3. **Depth Anything V2 Monocular Depth Supervision**: Dense relative depth map estimation per pixel to anchor Gaussians onto smooth plaster walls, doors, and floor planes.
4. **Adaptive Pre-Processing & Exposure Equalization**: Relative Laplacian motion blur filtering ($\Delta t < 0.5s$) and linear RGB luminance normalization to eliminate camera capture flickers.

---

## User Stories

1. As a 3D artist, I want to upload a smartphone room video and reconstruct a photorealistic 3D Gaussian Splat model on my Apple Silicon Mac without needing NVIDIA CUDA cloud servers.
2. As a 3D viewer user, I want the viewport to render 1,000,000+ Gaussians at a smooth 60 FPS without camera rotation depth-sorting lag.
3. As an interior designer, I want textureless painted walls, doors, and floor planes to reconstruct as solid 3D surfaces instead of empty hollow gaps.
4. As a 3D modeler, I want intermediate 3DGS training checkpoints to stream live into the viewport so I can inspect quality as it builds.
5. As a Mac desktop user, I want a `Pause Work` button to temporarily freeze GPU/CPU background tasks whenever I need system capacity for other applications.
6. As a web developer, I want to export a standalone HTML5/WebGL bundle with compressed SPZ splat data to share on any website.
7. As a macOS user, I want the "Export HTML Package" button to present a native `NSSavePanel` file save dialog so I can select the export directory.
8. As a video creator, I want automated motion-blur detection that drops whip-pan frames without accidentally deleting sharp photos of smooth, low-texture walls.
9. As an iOS user, I want to stream pre-posed LiDAR keyframes live from an iPhone camera directly into SplatCat via WebSockets.

---

## Implementation Decisions

- **Architectural Seam**: Native Process Bridge (Swift `WKScriptMessageHandler` / Tauri IPC) connecting the UI controller with native COLMAP SfM binaries, Depth Anything V2 depth predictors, and the Rust/`wgpu` Metal training engine.
- **Rendering Module**: High-performance WebGPU Compute Tile Rasterizer using in-VRAM GPU Radix Sort (`wgpu-splat` / `Brush`) for desktop execution, with single-file WebGL SPZ export for web browser sharing.
- **Training Module**: Differentiable Metal GPU loss engine using Rust / `wgpu` (`Brush`) computing $L_1 + L_{\text{SSIM}}$ image reconstruction loss directly on Apple Silicon.
- **Depth Supervision Module**: Depth Anything V2 monocular depth maps predicting relative depth $\mathcal{D}(u,v)$ per pixel to supervise 3DGS depth rendering and anchor plaster walls/floors.
- **Pre-Processing Module**: Adaptive relative sharpness filtering ($\Delta t < 0.5s$) to cull camera whip-pans without dropping smooth wall photos, paired with linear exposure equalization.

---

## Testing Decisions

- **Seam Testing**: Test the end-to-end pipeline through the native application bridge, asserting correct event emission from keyframe extraction to PLY generation.
- **Unit Testing**: Test keyframe capping rules, scale parsing, and relative sharpness thresholds via Python unit tests (`tests/test_image_capping.py`).
- **Regression Testing**: Verify clean Swift compilation (`swiftc -parse-as-library build_mac_app.swift`) and clean git working tree before release.

---

## Out of Scope

- Multi-GPU CUDA cluster orchestration (SplatCat targets Apple Silicon Metal and WebGPU).
- Real-time video encoding/transcoding inside the browser (handled via FFmpeg).

---

## Further Notes

- Canonical Wayfinder map reference: [`wayfinder_map.md`](file:///Users/emil/Documents/Codex/SplatCat/wayfinder_map.md)
- Domain Architectural Decision Records: `docs/adr/`
