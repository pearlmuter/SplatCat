# Wayfinder Map: SplatCat 3DGS Quality & Architecture Research Roadmap

## Notes
- **Domain**: SplatCat 3D Gaussian Splatting Suite
- **Skills**: `/wayfinder`, `/domain-modeling`, `/grilling`

---

## web-viewport-rendering-architecture: WebGL vs WebGPU 3DGS Tile Rasterizer Architecture

Blocked by: None
Status: resolved
Type: Research

### Question
What is the optimal long-term rendering architecture for SplatCat's 3D viewport on web and desktop? How do custom WebGL ShaderMaterials compare to WebGPU tile rasterizers (`wgpu-splat` / `Brush` / PlayCanvas `SuperSplat` / `gsplat.js`) in terms of GPU sorting, alpha blending fidelity, and frame-rate performance for 500k+ to 2M+ Gaussians?

### Answer
**Decision**: Dedicated WebGPU Compute Radix-Sort Architecture for Desktop Application.
1. **Desktop App (Tauri / macOS Native Host)**: Leverages 100% native WebGPU compute pipelines with in-VRAM GPU Radix Sorting (`wgpu-splat` / `Brush`). Because the desktop host is guaranteed to run on Apple Silicon Metal GPUs with WebGPU support, no WebGL fallback engine is needed inside the desktop app codebase.
2. **Web Exporter**: Web export packages target lightweight HTML5/WebGL single-file SPZ viewers for universal browser sharing.

---

## metal-gpu-photometric-optimization: Differentiable Camera Projection & Image Loss Engine

Blocked by: None
Status: resolved
Type: Research

### Question
How should SplatCat optimize Gaussian positions, colors, scales, rotations, and opacities via image-based photometric reconstruction loss ($L_1 + L_{\text{SSIM}}$) on Apple Silicon Metal GPUs? What are the architectural pros, cons, and performance limits of PyTorch MPS vs Brush Rust/wgpu vs gsplat Metal ports?

### Answer
**Decision**: Native Rust / `wgpu` (`Brush`) Differentiable Metal Engine.
1. **Performance**: Runs natively on Apple Silicon Metal GPUs via `wgpu` compute shaders, avoiding Python GIL locks and PyTorch MPS tensor dispatch overhead.
2. **Architecture**: Compiles into a lightweight native executable/library bundled inside the Tauri desktop app, eliminating external PyTorch Python environment dependencies.
3. **Loss & Density Control**: Performs $L_1 + L_{\text{SSIM}}$ image reconstruction loss, adaptive Gaussian splitting, cloning, and alpha pruning entirely in VRAM.

---

## textureless-surface-depth-priors: Monocular Depth Supervision for Walls & Glossy Surfaces

Blocked by: None
Status: open
Type: Research

### Question
How should SplatCat reconstruct textureless painted walls, floor planes, and reflective TV screens where SIFT feature extraction yields 0 points? Should we integrate Monocular Depth Networks (Depth Anything V2 / ZoeDepth), RANSAC planar boundary extrapolation, or PatchMatch MVS stereo depth maps?

### Answer
*To be resolved in session.*

---

## video-capture-and-frame-preprocessing: Video Capture Quality & Pre-Processing Workflows

Blocked by: None
Status: open
Type: Research

### Question
What video capture protocols and automated pre-processing steps (exposure normalization, Laplacian motion blur filtering, AE/AF lock guidelines) will prevent photometric flickers and floaters during 3DGS training?

### Answer
*To be resolved in session.*
