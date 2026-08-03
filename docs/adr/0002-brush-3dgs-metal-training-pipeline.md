# 2. Brush 3DGS Differentiable Rasterization & Metal GPU Training Pipeline

- **Status**: Accepted
- **Date**: 2026-08-03

## Context and Problem Statement
3D Gaussian Splatting requires optimizing 50,000–500,000 3D Gaussians (position, scale, rotation, opacity, spherical harmonics) against input images via differentiable tile rasterization. On macOS, CUDA is unavailable, requiring Apple Metal GPU acceleration (`wgpu` or PyTorch MPS / Metal Performance Shaders).

## Decision Drivers
- High FPS rasterization on Apple Silicon (M1/M2/M3/M4 GPUs).
- Permissive licensing (Apache-2.0 / MIT).
- Native Rust integration (`splatcat-engine` wgpu pipeline).

## Considered Options
1. **Brush Rust/wgpu Compute Pipeline**: Native Rust implementation using `wgpu` compute shaders compiled to Metal Performance Shaders.
2. **PyTorch MPS / gsplat backend**: Python sub-process running PyTorch with Metal Performance Shaders.
3. **CPU Differentiable Rasterizer**: Fallback software rasterizer.

## Decision Outcome
Chosen option: **Option 1 (Brush Rust/wgpu Compute Pipeline)** with PyTorch MPS secondary worker.

### Positives
- Zero CUDA dependency; runs natively on Apple Silicon Metal GPUs.
- Apache-2.0 permissively licensed.
- Direct memory sharing with macOS WebKit canvas via Metal textures.
