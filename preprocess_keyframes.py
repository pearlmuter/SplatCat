#!/usr/bin/env python3
"""
SplatCat Keyframe Pre-Processor Module
Implements Issue #5:
- Relative Laplacian variance sharpness comparison (drops whip-pans without deleting sharp smooth wall photos)
- Linear RGB luminance equalization (eliminates smartphone dynamic auto-exposure shifts)
"""

import os
import glob
import numpy as np
from PIL import Image, ImageFilter

def compute_laplacian_variance(image_array: np.ndarray) -> float:
    """Computes high-frequency spatial edge variance using Laplacian operator."""
    if image_array.ndim == 3:
        gray = 0.299 * image_array[:, :, 0] + 0.587 * image_array[:, :, 1] + 0.114 * image_array[:, :, 2]
    else:
        gray = image_array.astype(np.float64)
    
    pad_gray = np.pad(gray, 1, mode='edge')
    laplacian = (pad_gray[0:-2, 1:-1] + pad_gray[2:, 1:-1] + 
                 pad_gray[1:-1, 0:-2] + pad_gray[1:-1, 2:] - 
                 4.0 * pad_gray[1:-1, 1:-1])
    return float(np.var(laplacian))

def filter_relative_motion_blur(image_variances: list[float], relative_drop_threshold: float = 0.5) -> list[bool]:
    """Compares adjacent frame Laplacian variance. Drops whip-pans without deleting sharp smooth wall photos."""
    if not image_variances:
        return []
    n = len(image_variances)
    keep_flags = [True] * n
    
    if n > 1:
        # Boundary frame i=0
        if image_variances[1] > 0 and (image_variances[0] / image_variances[1]) < (1.0 - relative_drop_threshold):
            keep_flags[0] = False
        # Boundary frame i=n-1
        if image_variances[-2] > 0 and (image_variances[-1] / image_variances[-2]) < (1.0 - relative_drop_threshold):
            keep_flags[-1] = False

    for i in range(1, n - 1):
        prev_var = image_variances[i - 1]
        curr_var = image_variances[i]
        next_var = image_variances[i + 1]
        neighbor_avg = (prev_var + next_var) / 2.0
        if neighbor_avg > 0 and (curr_var / neighbor_avg) < (1.0 - relative_drop_threshold):
            keep_flags[i] = False
    return keep_flags

def normalize_linear_exposure(image_rgb: np.ndarray, target_mean_luminance: float = 128.0) -> np.ndarray:
    """Equalizes mean luminance across linear RGB space to eliminate dynamic auto-exposure shifts."""
    luminance = 0.299 * image_rgb[:, :, 0] + 0.587 * image_rgb[:, :, 1] + 0.114 * image_rgb[:, :, 2]
    current_mean = np.mean(luminance)
    if current_mean > 0:
        scaling_factor = target_mean_luminance / current_mean
        normalized = np.clip(image_rgb.astype(np.float64) * scaling_factor, 0, 255).astype(np.uint8)
        return normalized
    return image_rgb

def process_frames_directory(frames_dir: str, target_mean_lum: float = 128.0, relative_drop_thresh: float = 0.5) -> int:
    """Pre-processes all keyframes in frames_dir: equalizes exposure and culls blur frames."""
    image_paths = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")) + glob.glob(os.path.join(frames_dir, "*.png")))
    if not image_paths:
        print(f"[PreProcess] No keyframe images found in {frames_dir}")
        return 0

    print(f"[PreProcess] Analyzing {len(image_paths)} keyframes in {frames_dir}...")
    variances = []
    images = []

    for path in image_paths:
        try:
            img = Image.open(path).convert('RGB')
            arr = np.array(img)
            var = compute_laplacian_variance(arr)
            variances.append(var)
            images.append((path, arr))
        except Exception as e:
            print(f"[PreProcess] Warning: Failed to read image {path}: {e}")

    keep_flags = filter_relative_motion_blur(variances, relative_drop_threshold=relative_drop_thresh)
    kept_count = 0
    culled_count = 0

    for idx, (path, arr) in enumerate(images):
        try:
            if not keep_flags[idx]:
                os.remove(path)
                culled_count += 1
            else:
                norm_arr = normalize_linear_exposure(arr, target_mean_luminance=target_mean_lum)
                Image.fromarray(norm_arr).save(path, quality=95)
                kept_count += 1
        except Exception as e:
            print(f"[PreProcess] Warning: Failed processing image {path}: {e}")

    print(f"[PreProcess] Complete! Kept {kept_count} clean frames, culled {culled_count} blurred whip-pan frames.")
    return kept_count

if __name__ == '__main__':
    import sys
    fdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/splatcat_run/frames"
    process_frames_directory(fdir)
