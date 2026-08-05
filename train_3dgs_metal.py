#!/usr/bin/env python3
"""
SplatCat PLY contract module (Issue #7 & Issue #6)

Houses the authoritative PLY attribute contract between the trainer and the
web viewer, the contract parser/validator, and pure-function loss math
(photometric, depth-supervision) preserved as prior-art test seams.

The real training driver is train_photometric.py (PRD 0003 T3): the legacy
fake optimizer that never read keyframes was removed in this cut.
"""

import os
import sys
import math
import glob
import struct
import argparse
import numpy as np

try:
    import torch
except ImportError:
    torch = None

def compute_photometric_loss(rendered_img, target_img, lambda_ssim: float = 0.2):
    """Computes L1 + SSIM photometric reconstruction loss between rendered splats and target keyframe."""
    l1_loss = torch.mean(torch.abs(rendered_img - target_img))
    
    # Structural Similarity (SSIM) approximation
    c1, c2 = 0.01**2, 0.03**2
    mu_x, mu_y = torch.mean(rendered_img), torch.mean(target_img)
    sigma_x, sigma_y = torch.var(rendered_img), torch.var(target_img)
    sigma_xy = torch.mean((rendered_img - mu_x) * (target_img - mu_y))
    
    ssim = ((2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)) / ((mu_x**2 + mu_y**2 + c1) * (sigma_x + sigma_y + c2))
    ssim_loss = 1.0 - ssim
    
    return (1.0 - lambda_ssim) * l1_loss + lambda_ssim * ssim_loss

def compute_depth_supervision_loss(rendered_depth, predicted_depth):
    """Scale-normalized L1 depth loss (prior-art pure function, PRD 0003 test seam).

    NOT wired into any pipeline stage in this cut: the depth prior is
    explicitly dropped (PRD 0003 T5 / ticket #24). Preserved so a future
    real depth network + renderer depth mode can adopt it (ADR 0006).
    """
    rend_min, rend_max = rendered_depth.min(), rendered_depth.max()
    pred_min, pred_max = predicted_depth.min(), predicted_depth.max()
    
    if (rend_max - rend_min) > 1e-6:
        norm_rendered = (rendered_depth - rend_min) / (rend_max - rend_min)
    else:
        norm_rendered = rendered_depth
        
    if (pred_max - pred_min) > 1e-6:
        norm_predicted = (predicted_depth - pred_min) / (pred_max - pred_min)
    else:
        norm_predicted = predicted_depth
        
    return torch.mean(torch.abs(norm_rendered - norm_predicted))

# Spherical-Harmonics DC basis constant C0 = 1/(2*sqrt(pi)). One authoritative
# value shared by the writer, the contract parser, the trainer, and the evaluator.
SH_C0 = 0.28209479177387814

PLY_CONTRACT_VIEWER_RULES = (
    "Viewer-compatible ASCII PLY attribute layout: "
    "parts[0..2]=xyz, parts[3..5]=nx/ny/nz, parts[6..8]=SH DC (f_dc_0..2), "
    "parts[9]=opacity, parts[10..12]=log-scales (scale_0..2), "
    "parts[13..16]=quaternion (rot_0..3). "
    "Scales are stored as log-scale and recovered by the viewer via exp() per "
    "packages/web-viewer/viewer.js:219-225."
)

def parse_ply_per_viewer_contract(ply_path):
    """Parses an ASCII 3DGS PLY under the exact attribute rules the web viewer uses.

    Returns a dict with arrays xyz, rgb (SH DC decoded to linear RGB), opacity,
    log_scales, quaternions plus a malformed_lines count. Mirrors viewer.js
    index alignment and SH decode (sh * C0 + 0.5).
    """
    xyz, rgb, opacity, log_scales, quaternions = [], [], [], [], []
    malformed = 0
    c0 = SH_C0
    with open(ply_path, "r") as f:
        in_header = True
        for raw in f:
            line = raw.strip()
            if in_header:
                if line == "end_header":
                    in_header = False
                continue
            if not line:
                continue
            parts = line.split()
            if len(parts) < 17:
                malformed += 1
                continue
            try:
                xyz.append([float(parts[0]), float(parts[1]), float(parts[2])])
                rgb.append([
                    float(parts[6]) * c0 + 0.5,
                    float(parts[7]) * c0 + 0.5,
                    float(parts[8]) * c0 + 0.5,
                ])
                opacity.append(float(parts[9]))
                log_scales.append([float(parts[10]), float(parts[11]), float(parts[12])])
                quaternions.append([float(parts[13]), float(parts[14]), float(parts[15]), float(parts[16])])
            except ValueError:
                malformed += 1
    return {
        "xyz": np.array(xyz, dtype=np.float32),
        "rgb": np.array(rgb, dtype=np.float32),
        "opacity": np.array(opacity, dtype=np.float32),
        "log_scales": np.array(log_scales, dtype=np.float32),
        "quaternions": np.array(quaternions, dtype=np.float32),
        "malformed_lines": malformed,
    }


def read_points3d_binary(bin_file):
    points = []
    colors = []
    try:
        with open(bin_file, "rb") as f:
            num_points = struct.unpack("<Q", f.read(8))[0]
            for _ in range(num_points):
                binary_point_header = f.read(43)
                if len(binary_point_header) < 43:
                    break
                point_id, x, y, z, r, g, b, error = struct.unpack("<QdddBBBd", binary_point_header)
                track_len_data = f.read(8)
                if len(track_len_data) < 8:
                    break
                track_len = struct.unpack("<Q", track_len_data)[0]
                f.read(track_len * 8)
                points.append([x, y, z])
                colors.append([r / 255.0, g / 255.0, b / 255.0])
    except Exception as e:
        print(f"[3DGS Metal] Error reading binary points3D: {e}")
    return points, colors

def write_3dgs_ply(filename, xyz, sh_dc, opacities, scales, quaternions):
    num_pts = len(xyz)
    header = (
        "ply\n"
        "format ascii 1.0\n"
        f"element vertex {num_pts}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property float nx\n"
        "property float ny\n"
        "property float nz\n"
        "property float f_dc_0\n"
        "property float f_dc_1\n"
        "property float f_dc_2\n"
        "property float opacity\n"
        "property float scale_0\n"
        "property float scale_1\n"
        "property float scale_2\n"
        "property float rot_0\n"
        "property float rot_1\n"
        "property float rot_2\n"
        "property float rot_3\n"
        "end_header\n"
    )

    with open(filename, "w") as f:
        f.write(header)
        for i in range(num_pts):
            f.write(f"{xyz[i,0]:.6f} {xyz[i,1]:.6f} {xyz[i,2]:.6f} 0.000000 0.000000 0.000000 {sh_dc[i,0]:.6f} {sh_dc[i,1]:.6f} {sh_dc[i,2]:.6f} {opacities[i,0]:.6f} {scales[i,0]:.6f} {scales[i,1]:.6f} {scales[i,2]:.6f} {quaternions[i,0]:.6f} {quaternions[i,1]:.6f} {quaternions[i,2]:.6f} {quaternions[i,3]:.6f}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metal 3D Gaussian Splatting Optimizer")
    parser.add_argument("--colmap_dir", required=True, help="Path to COLMAP sparse directory")
    parser.add_argument("--images_dir", required=True, help="Path to extracted frame images")
    parser.add_argument("--depth_dir", default=None, help="Path to monocular depth maps directory")
    parser.add_argument("--output_ply", required=True, help="Path to save output 3DGS PLY model")
    parser.add_argument("--iterations", type=int, default=3000, help="Number of optimization iterations")
    parser.add_argument("--render_width", type=int, default=None, help="Optional render downscale width")
    parser.add_argument("--render_height", type=int, default=None, help="Optional render downscale height")

    args = parser.parse_args()
    from train_photometric import train_photometric
    train_photometric(
        args.colmap_dir, args.images_dir, args.output_ply,
        iterations=args.iterations, depth_dir=args.depth_dir,
        render_width=args.render_width, render_height=args.render_height,
    )
