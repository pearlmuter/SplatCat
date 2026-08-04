# Wayfinder Map: SplatCat 3DGS Quality & UI Roadmap

## Notes
- **Domain**: SplatCat 3D Gaussian Splatting Suite
- **Skills**: `/wayfinder`, `/domain-modeling`

---

## native-nssavepanel: Native macOS NSSavePanel Dialog for HTML Export

Blocked by: None
Status: open
Type: Task

### Question
How to prompt the user with a native macOS file selection dialog (`NSSavePanel`) when exporting HTML packages, allowing them to choose the exact destination directory and filename instead of downloading silently to `~/Downloads`?

### Answer
*To be resolved in session.*

---

## webgl-elliptical-shader: Custom WebGL 2D Elliptical Gaussian Fragment Shader

Blocked by: None
Status: open
Type: Prototype

### Question
How to replace Three.js `THREE.PointsMaterial` square point sprites with a custom WebGL fragment shader (`ShaderMaterial`) that calculates the 2D projected covariance matrix $\Sigma'$ and renders true smooth 2D elliptical Gaussians with exponential alpha falloff ($\exp(-r^2)$)?

### Answer
*To be resolved in session.*

---

## camera-photometric-loss: PyTorch Metal Camera Pinhole Projection & Photometric Loss

Blocked by: webgl-elliptical-shader
Status: open
Type: Research

### Question
How to upgrade `train_3dgs_metal.py` to project 3D Gaussians onto COLMAP camera poses using pinhole camera parameters and compute $L_1 + L_{\text{SSIM}}$ image reconstruction loss against training keyframes on Metal GPU (MPS)?

### Answer
*To be resolved in session.*

---

## monocular-depth-priors: Monocular Depth Map Supervision for Textureless Walls

Blocked by: camera-photometric-loss
Status: open
Type: Research

### Question
How to integrate monocular depth estimation (Depth Anything V2 / ZoeDepth) to supervise Gaussian depth rendering and anchor splats onto textureless plaster walls and floor planes where SIFT extracted 0 points?

### Answer
*To be resolved in session.*
