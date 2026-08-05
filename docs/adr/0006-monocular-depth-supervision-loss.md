# ADR 0006: Monocular Depth Supervision Loss for Textureless Surfaces

## Status
Accepted

## Context
Smooth plaster walls, white doors, and uniform floors lack high-frequency SIFT point features in COLMAP SfM, causing standard 3DGS optimization to leave holes or create floating splat artifacts along walls. Monocular depth estimation maps provide dense relative depth guidance across low-texture regions.

## Decision
We integrate dense relative monocular depth maps into `train_3dgs_metal.py`:
1. Keyframe images pass through `estimate_depth_maps.py` to generate dense relative depth maps $\mathcal{D}_{\text{pred}}(u,v)$.
2. During training, rendered depth maps $\mathcal{D}_{\text{rend}}(u,v)$ from current camera view $k$ are scale-normalized and regularized against predicted monocular depth:
   $$\mathcal{L}_{\text{depth}} = \lambda_{\text{depth}} \|\hat{\mathcal{D}}_{\text{rend}} - \hat{\mathcal{D}}_{\text{pred}}\|_1$$
3. Total training loss is formed as:
   $$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{photo}} + \lambda_{\text{depth}} \mathcal{L}_{\text{depth}}$$

## Consequences
- 3D Gaussians reliably anchor onto smooth plaster walls, white doors, and flat floor planes.
- Eliminates camera-space depth ambiguity and room reconstruction distortion.
