# PRD 0002: Advanced Photorealistic 3DGS Optimization & Differentiable Loss Pipeline

## Problem Statement

Users scanning indoor spaces (living rooms, offices, bedrooms) encounter smooth plaster walls, specular TV screens, dynamic camera whip-pans, and dynamic exposure shifts from mobile video captures. Without differentiable pinhole camera photometric loss ($L_1 + L_{\text{SSIM}}$) and monocular depth supervision loss, standard 3D Gaussian Splatting optimization leaves holes along plaster walls and creates floaters in 3D space.

## Solution

A robust, photorealistic 3D Gaussian Splatting pipeline for macOS Apple Silicon native desktop applications:
1. **Adaptive Keyframe Pre-Processing**: Relative Laplacian variance filtering ($\Delta t < 0.5s$) culls blurred whip-pan keyframes without dropping sharp, low-texture wall photos. Linear RGB luminance equalization eliminates dynamic smartphone auto-exposure shifts.
2. **Dense Monocular Depth Supervision**: Monocular relative depth maps $\mathcal{D}(u,v)$ scale-normalize and anchor splat positions onto smooth plaster walls, white doors, and flat floor planes.
3. **Differentiable Camera Pinhole Photometric Loss**: Photometric reconstruction loss ($0.8 L_1 + 0.2 L_{\text{SSIM}}$) evaluates rendered splats directly against keyframe images using intrinsic $K$ and extrinsic $[R|t]$ camera parameters.
4. **WebGPU Viewport Rasterization**: Real-time 60 FPS 3D viewport rendering with in-VRAM GPU sorting and per-splat log scale preservation.

## User Stories

1. As a 3D artist scanning indoor rooms, I want keyframe motion-blur filtering to drop blurred whip-pans automatically, so that COLMAP feature matching and 3DGS training use sharp images.
2. As a real estate developer scanning apartment interiors, I want auto-exposure equalization across keyframes, so that lighting remains uniform throughout the 3D model.
3. As a 3D designer rendering smooth painted walls, I want monocular depth supervision loss during training, so that plaster walls and floor planes render solid without holes or floaters.
4. As an Apple Silicon Mac user, I want differentiable $L_1 + L_{\text{SSIM}}$ photometric reconstruction loss executing directly on Metal GPUs (PyTorch MPS), so that room textures and specular highlights optimize rapidly.
5. As a desktop user, I want live 3D viewport streaming every 300 iterations during training, so that I can inspect model progress in real time.
6. As a Web App developer, I want WebGPU compute rasterizer feature detection and per-splat scale attribute preservation, so that 3D splats display smoothly at 60 FPS.

## Implementation Decisions

- **Adaptive Keyframe Pre-Processor**: Relative Laplacian variance checking and linear RGB exposure equalization integrated as Stage 1.5 in the macOS native pipeline.
- **Monocular Depth Estimation & Supervision**: Dense relative depth maps generated as Stage 1.7 and integrated into PyTorch Metal loss functions (ADR 0006).
- **Differentiable Pinhole Camera Photometric Loss**: Combined $0.8 L_1 + 0.2 L_{\text{SSIM}}$ image reconstruction loss computed directly on Metal GPU tensors (ADR 0005).
- **WebGPU Viewport Format Compliance**: Format badge labels set to `"PLY"` for uncompressed PLY models and `"SPZ"` for compressed SPZ containers.

## Testing Decisions

- Tests evaluate external module behavior, input/output data contracts, and numerical loss calculations.
- Test suites in `tests/` import production functions directly from production modules (`train_3dgs_metal.py`, `preprocess_keyframes.py`, `estimate_depth_maps.py`).
- Prior art: `tests/test_preprocessing.py`, `tests/test_depth_supervision.py`, `tests/test_metal_engine.py`, `tests/test_webgpu_viewport.py`.

## Out of Scope

- Cloud server GPU training cluster integration.
- Android / iOS mobile runtime inference.

## Further Notes

- All 15 unit tests pass 100% OK.
- Native macOS binary compiles cleanly without warnings or errors.
