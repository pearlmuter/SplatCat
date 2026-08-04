# Literature & Algorithmic Research: Textureless Walls & Specular TV Surfaces in Structure-from-Motion (SfM) and 3D Gaussian Splatting (3DGS)

## Problem Formulation
In video-to-3D reconstructions of indoor rooms (such as the armchair corner scene), users observe that high-contrast foreground objects (e.g., the armchair fabric texture) reconstruct with high point density, whereas:
1. **Painted Plaster Walls & Smooth Doors** are missing entirely or appear as sparse floating points.
2. **TV Screens, Windows & Polished Tables** exhibit empty voids or distorted depth geometry.

---

## 1. Computer Vision Literature Diagnosis

### A. The SIFT Scale-Space Contrast Failure on Textureless Walls
- **Mechanism**: Standard COLMAP Structure-from-Motion utilizes **SIFT** (*Scale-Invariant Feature Transform*, Lowe 2004) to detect keyframe keypoints.
- **Root Cause**: SIFT computes Difference of Gaussians (DoG) scale-space octave images:
  $$D(x,y,\sigma) = (L(x,y,k\sigma) - L(x,y,\sigma)) * I(x,y)$$
  Keypoints are selected at local spatial maxima/minima of $D(x,y,\sigma)$ where the Hessian matrix determinant meets a threshold:
  $$\frac{\text{Tr}(H)^2}{\text{Det}(H)} < \frac{(r+1)^2}{r}$$
- **Failure Mode**: On flat painted walls, spatial pixel variance is near zero ($\nabla I \approx 0$). The DoG response fails to meet the contrast threshold ($\text{Det}(H) \approx 0$), resulting in zero SIFT keypoint extractions on smooth plaster walls. Because SfM requires $\ge 3$ intersecting feature rays for 3D point triangulation, textureless walls yield 0 triangulated 3D points.

### B. Lambertian Assumption Violation on Specular TV Glass
- **Mechanism**: Epipolar feature matching assumes **Lambertian Reflectance**:
  $$I(u, v, \mathbf{d}) = I(u, v)$$
  where pixel intensity $I$ at image coordinate $(u,v)$ remains constant regardless of viewing direction $\mathbf{d}$.
- **Failure Mode**: TV screens and glass panels exhibit strong **specular highlights** governed by the Cook-Torrance BRDF:
  $$f_r = \frac{D \cdot F \cdot G}{4 (\mathbf{n} \cdot \mathbf{v}) (\mathbf{n} \cdot \mathbf{l})}$$
  As the camera moves around the chair, specular reflections of room lights and windows shift across the TV glass surface. SIFT descriptors match moving reflection highlights across keyframes rather than the physical TV frame—violating epipolar geometry and causing bundle adjustment to reject the points as outliers.

---

## 2. Proposed Algorithmic Solutions for SplatCat

### Solution 1: RANSAC Ground-Plane & Wall Patch Extrapolator
- **Concept**: Fit 3D planar primitives to detected floor/skirting boundaries and project dense surface-aligned 3D Gaussian patches across wall bounding planes.
- **Algorithm**:
  1. Fit floor plane $\mathbf{n}_{\text{floor}} \cdot \mathbf{x} + d = 0$ using RANSAC on lower centroid points.
  2. Compute vertical wall planes orthogonal to $\mathbf{n}_{\text{floor}}$.
  3. Interpolate planar Gaussian patches across the unfeatured wall regions bounded by floor and ceiling planes.

### Solution 2: Monocular Depth Prior Initialization (Depth Anything V2 / ZoeDepth)
- **Concept**: Feed monocular depth network estimations $D(x,y)$ alongside COLMAP camera poses.
- **Algorithm**: Unproject low-contrast wall pixels into 3D using pinhole intrinsics:
  $$\mathbf{X} = D(u,v) \mathbf{K}^{-1} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}$$
  This initializes Gaussian splat seeds on textureless walls where SIFT extracted zero features.

### Solution 3: Deep Neural Feature Matching (SuperPoint + LightGlue)
- **Concept**: Replace classical SIFT with deep learning feature extractors (SuperPoint / DISK + LightGlue).
- **Algorithm**: SuperPoint learns low-level edge/shading gradients that classical DoG discards, enabling feature extraction on smooth walls and subtle paint transitions.

---

## References
1. Lowe, D. G. (2004). Distinctive image features from scale-invariant keypoints. *IJCV*, 60(2), 91-110.
2. Schonberger, J. L., & Frahm, J. M. (2016). Structure-from-motion revisited. In *CVPR* (pp. 4104-4113).
3. Kerbl, B., Kopanas, G., Leimkühler, T., & Drettakis, G. (2023). 3D Gaussian Splatting for Real-Time Radiance Field Rendering. *ACM TOG / SIGGRAPH*.
4. Yang, Z., et al. (2024). Depth Anything: Unleashing the Power of Large-Scale Unlabeled Data. *CVPR*.
