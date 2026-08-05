# ADR 0005: Differentiable Camera Pinhole Photometric Reconstruction Loss

## Status
Accepted

## Context
Standard 3D Gaussian Splatting relies on image-based photometric reconstruction loss ($L_1 + L_{\text{SSIM}}$) to optimize 3D Gaussian positions, opacities, scales, rotations, and spherical harmonic colors. Previously, `train_3dgs_metal.py` penalized coordinate spatial norms directly, skipping differentiable camera rasterization and image-based photometric loss.

## Decision
We implement differentiable pinhole camera projection and photometric image reconstruction loss in `train_3dgs_metal.py`:
1. Parse COLMAP intrinsic camera matrix $K$ and extrinsic camera poses $[R_k | t_k]$ for all training keyframes $k \in \{1 \dots N\}$.
2. Project 3D Gaussians into camera coordinates $\mathbf{x}_{\text{cam}} = R_k \mathbf{x} + t_k$ and project onto screen space $\mathbf{u} = K \mathbf{x}_{\text{cam}} / z$.
3. Compute combined $L_1 + L_{\text{SSIM}}$ photometric image reconstruction loss:
   $$\mathcal{L}_{\text{photo}} = (1 - \lambda) \|I_{\text{rendered}} - I_{\text{target}}\|_1 + \lambda (1 - \text{SSIM}(I_{\text{rendered}}, I_{\text{target}}))$$
4. Backpropagate gradients to update Gaussian parameters on Apple Metal GPUs.

## Consequences
- 3D Gaussian Splats optimize to match real keyframe pixels, photorealistically capturing chair fabrics, textures, and room lighting.
- Eliminates floaters and fuzzy coordinate-only regularization artifacts.
