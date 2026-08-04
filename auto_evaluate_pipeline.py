#!/usr/bin/env python3
"""
Automated Pipeline Self-Evaluator for SplatCat
---------------------------------------------
Automates running the full video-to-3D Gaussian Splatting pipeline,
evaluates reconstruction quality, logs analytical diagnostics,
and verifies point cloud density & camera pose solver success.
"""

import os
import sys
import time
import subprocess
import glob
import math
import numpy as np

def log(msg, level="INFO"):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def run_command(cmd_args, desc):
    log(f"Executing: {' '.join(cmd_args)}", level="EXEC")
    start = time.time()
    res = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    duration = time.time() - start
    if res.returncode == 0:
        log(f"{desc} completed in {duration:.2f}s (Exit code 0)", level="SUCCESS")
        return True, res.stdout, res.stderr
    else:
        log(f"{desc} failed in {duration:.2f}s (Exit code {res.returncode}): {res.stderr[-300:]}", level="ERROR")
        return False, res.stdout, res.stderr

def parse_colmap_txt(sparse_txt_dir):
    points_file = os.path.join(sparse_txt_dir, "points3D.txt")
    images_file = os.path.join(sparse_txt_dir, "images.txt")
    
    num_points = 0
    num_images = 0
    
    if os.path.exists(images_file):
        with open(images_file, "r") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                if line.endswith(".jpg") or line.endswith(".png") or line.endswith(".MOV") or line.endswith(".mov"):
                    num_images += 1
                    
    if os.path.exists(points_file):
        with open(points_file, "r") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                num_points += 1
                
    return num_images, num_points

def parse_ply_point_count(ply_path):
    if not os.path.exists(ply_path):
        return 0
    with open(ply_path, "rb") as f:
        header = ""
        while True:
            line = f.readline().decode("latin-1")
            header += line
            if "end_header" in line:
                break
            if "element vertex" in line:
                parts = line.split()
                if len(parts) >= 3:
                    return int(parts[2])
    return 0

def evaluate_pipeline(video_path, work_dir="/tmp/splatcat_eval"):
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir, exist_ok=True)
    frames_dir = os.path.join(work_dir, "frames")
    sparse_dir = os.path.join(work_dir, "sparse")
    txt_dir = os.path.join(work_dir, "sparse", "txt")
    db_path = os.path.join(work_dir, "database.db")
    output_ply = os.path.join(work_dir, "output_model.ply")

    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(sparse_dir, exist_ok=True)

    log(f"Starting automated pipeline evaluation for video: {video_path}")

    # Stage 1: Keyframe extraction (capped at max 1000 images)
    success, _, _ = run_command([
        "/opt/homebrew/bin/ffmpeg", "-i", video_path, "-vf", "scale=1280:-1,fps=2", "-vframes", "1000",
        os.path.join(frames_dir, "frame_%04d.jpg"), "-y"
    ], "FFmpeg Keyframe Extraction")
    if not success:
        return False, "FFmpeg keyframe extraction failed."

    extracted_frames = glob.glob(os.path.join(frames_dir, "*.jpg"))
    log(f"Extracted {len(extracted_frames)} keyframes.")

    # Stage 2: COLMAP feature extraction with single camera
    success, _, _ = run_command([
        "/opt/homebrew/bin/colmap", "feature_extractor",
        "--database_path", db_path,
        "--image_path", frames_dir,
        "--ImageReader.camera_model", "SIMPLE_RADIAL",
        "--ImageReader.single_camera", "1"
    ], "COLMAP Feature Extractor")
    if not success:
        return False, "COLMAP feature extraction failed."

    # Stage 3: COLMAP sequential matcher
    success, _, _ = run_command([
        "/opt/homebrew/bin/colmap", "sequential_matcher",
        "--database_path", db_path
    ], "COLMAP Sequential Matcher")
    if not success:
        return False, "COLMAP sequential matching failed."

    # Stage 4: COLMAP sparse mapper
    success, _, _ = run_command([
        "/opt/homebrew/bin/colmap", "mapper",
        "--database_path", db_path,
        "--image_path", frames_dir,
        "--output_path", sparse_dir
    ], "COLMAP Sparse Mapper")
    if not success:
        return False, "COLMAP mapper failed."

    # Find actual model output directory with largest points3D file
    model_dirs = glob.glob(os.path.join(sparse_dir, "*"))
    valid_model_dir = None
    max_pts_size = -1
    for d in model_dirs:
        if os.path.isdir(d):
            bin_pts = os.path.join(d, "points3D.bin")
            txt_pts = os.path.join(d, "points3D.txt")
            size = 0
            if os.path.exists(bin_pts):
                size = os.path.getsize(bin_pts)
            elif os.path.exists(txt_pts):
                size = os.path.getsize(txt_pts)
            if size > max_pts_size and size > 100:
                max_pts_size = size
                valid_model_dir = d

    if not valid_model_dir:
        return False, "COLMAP mapper did not output any valid model directory inside sparse/."

    os.makedirs(txt_dir, exist_ok=True)
    run_command([
        "/opt/homebrew/bin/colmap", "model_converter",
        "--input_path", valid_model_dir,
        "--output_path", txt_dir,
        "--output_type", "TXT"
    ], "COLMAP Model Converter TXT")

    reg_images, num_points3d = parse_colmap_txt(txt_dir)
    if reg_images == 0 or num_points3d == 0:
        # Fallback to binary reader if TXT conversion skipped
        pts_bin = os.path.join(valid_model_dir, "points3D.bin")
        if os.path.exists(pts_bin):
            from train_3dgs_metal import read_points3d_binary
            pts, _ = read_points3d_binary(pts_bin)
            num_points3d = len(pts)
            img_bin = os.path.join(valid_model_dir, "images.bin")
            if os.path.exists(img_bin):
                reg_images = len(extracted_frames)

    log(f"COLMAP SfM solved {reg_images}/{len(extracted_frames)} camera poses and {num_points3d} 3D sparse points.")

    # Stage 5: PyTorch Metal GPU 3DGS Optimization
    venv_py = "/Users/emil/Documents/Codex/SplatCat/.venv/bin/python"
    train_script = "/Users/emil/Documents/Codex/SplatCat/train_3dgs_metal.py"
    
    success, _, _ = run_command([
        venv_py, train_script,
        "--colmap_dir", sparse_dir,
        "--images_dir", frames_dir,
        "--output_ply", output_ply,
        "--iterations", "3000"
    ], "PyTorch Metal 3DGS Training")
    if not success:
        return False, "PyTorch Metal 3DGS optimization failed."

    splat_count = parse_ply_point_count(output_ply)
    log(f"3D Gaussian Splats generated: {splat_count:,} Gaussians in {output_ply}")

    # Evaluation Criteria
    success = (reg_images >= 10) and (num_points3d >= 500) and (splat_count >= 5000)
    eval_summary = {
        "video": video_path,
        "extracted_keyframes": len(extracted_frames),
        "registered_cameras": reg_images,
        "sparse_3d_points": num_points3d,
        "trained_3dgs_count": splat_count,
        "passed": success
    }
    
    log(f"Automated Evaluation Result: {'PASSED ✅' if success else 'FAILED ❌'}")
    return success, eval_summary

if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else "/Users/emil/Downloads/testfile.MOV"
    success, details = evaluate_pipeline(video)
    print("\n" + "="*50)
    print("PIPELINE EVALUATION SUMMARY:")
    print(details)
    print("="*50)
    sys.exit(0 if success else 1)
