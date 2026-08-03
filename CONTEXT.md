# SplatCat Domain Glossary

## Keyframe
- **Definition**: A selected high-sharpness video frame extracted at a fixed temporal sampling rate (e.g. 2–5 FPS) used as input for 3D reconstruction.
- **Distinctions**: Distinct from raw video frames; filtered by Laplacian variance sharpness metrics to reject motion blur.

## Camera Pose
- **Definition**: The 6-Degree-of-Freedom (6DoF) spatial location and orientation of the camera in 3D world coordinates for a given frame, specified by a 3x3 rotation matrix (or unit quaternion) and a 3-element translation vector.
- **Synonyms**: Extrinsics, 6DoF Transform.
- **Distinctions**: Distinct from Intrinsics (focal length $f_x, f_y$ and principal point $c_x, c_y$).

## Gaussian Splat
- **Definition**: A 3D volumetric rendering primitive defined by a 3D center position $(x, y, z)$, 3D covariance matrix (decomposed into scale $s \in \mathbb{R}^3$ and rotation quaternion $q \in \mathbb{R}^4$), opacity $\alpha \in [0, 1]$, and color defined by Spherical Harmonics ($SH$) coefficients.
- **Synonyms**: 3DGS Primitive, Gaussian Ellipsoid.

## Structure-from-Motion (SfM)
- **Definition**: The process of estimating 3D structure (sparse point cloud) and camera poses simultaneously from a set of overlapping 2D images.
- **Distinctions**: GLOMAP performs global SfM, whereas COLMAP traditionally uses incremental SfM.

## SPZ Compression
- **Definition**: A specialized binary compression container format created by Scaniverse/Niantic for 3D Gaussian Splatting models, combining fractional coordinate quantization with DEFLATE/Zstandard entropy coding to achieve 80–90% file size reduction over standard `.ply` files.
