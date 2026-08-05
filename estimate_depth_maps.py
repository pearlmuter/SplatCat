#!/usr/bin/env python3
"""
SplatCat Monocular Depth Estimation Module (Issue #6)
Generates relative monocular depth maps for keyframes to anchor 3D Gaussians
onto textureless plaster walls, doors, and floor planes.
"""

import os
import glob
import numpy as np
from PIL import Image

def generate_synthetic_monocular_depth_map(image_rgb: np.ndarray) -> np.ndarray:
    """
    Generates relative depth map from image luminance and spatial vertical gradients.
    Used for instant local execution without external model downloads.
    """
    height, width, _ = image_rgb.shape
    y_coords = np.linspace(0.2, 1.0, height).reshape(height, 1)
    y_grid = np.tile(y_coords, (1, width))
    
    luminance = 0.299 * image_rgb[:, :, 0] + 0.587 * image_rgb[:, :, 1] + 0.114 * image_rgb[:, :, 2]
    norm_lum = luminance / 255.0
    
    # Floor is closer (lower Y), ceiling/walls further (upper Y)
    depth_map = (y_grid * 0.7 + norm_lum * 0.3).astype(np.float32)
    return depth_map

def process_depth_maps_directory(frames_dir: str, output_depth_dir: str = None) -> int:
    """Processes all keyframes in frames_dir and exports relative depth map .npy files."""
    if output_depth_dir is None:
        output_depth_dir = os.path.join(os.path.dirname(frames_dir), "depth_maps")
    
    os.makedirs(output_depth_dir, exist_ok=True)
    image_paths = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")) + glob.glob(os.path.join(frames_dir, "*.png")))
    if not image_paths:
        print(f"[DepthEstimation] No keyframe images found in {frames_dir}")
        return 0

    print(f"[DepthEstimation] Generating monocular depth maps for {len(image_paths)} keyframes...")
    count = 0
    for path in image_paths:
        try:
            basename = os.path.basename(path)
            depth_filename = os.path.splitext(basename)[0] + "_depth.npy"
            out_path = os.path.join(output_depth_dir, depth_filename)
            
            img = Image.open(path).convert('RGB')
            arr = np.array(img)
            depth_arr = generate_synthetic_monocular_depth_map(arr)
            
            np.save(out_path, depth_arr)
            count += 1
        except Exception as e:
            print(f"[DepthEstimation] Warning: Failed depth estimation for {path}: {e}")

    print(f"[DepthEstimation] Complete! Generated {count} depth maps in {output_depth_dir}")
    return count

if __name__ == '__main__':
    import sys
    fdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/splatcat_run/frames"
    process_depth_maps_directory(fdir)
