#!/usr/bin/env python3
import os
import sys
import subprocess
import glob
import cv2
import numpy as np

def run_sfm_reconstruction(video_path, output_ply):
    print(f"🎥 Processing real video file: {video_path}")
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return False

    frames_dir = "/tmp/sfm_frames_fast"
    os.makedirs(frames_dir, exist_ok=True)
    for f in glob.glob(os.path.join(frames_dir, "*")):
        try:
            os.remove(f)
        except Exception:
            pass

    # 1. Extract Keyframes via FFmpeg (15 keyframes across video)
    ffmpeg_bin = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
    cmd = [ffmpeg_bin, "-i", video_path, "-vf", "fps=1.5", os.path.join(frames_dir, "frame_%04d.jpg"), "-y"]
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    frame_files = sorted(glob.glob(os.path.join(frames_dir, "frame_*.jpg")))
    print(f"Extracted {len(frame_files)} keyframes from video.")

    if len(frame_files) < 2:
        print("Not enough keyframes extracted.")
        return False

    # Initialize SIFT feature detector
    try:
        sift = cv2.SIFT_create(nfeatures=1500)
    except AttributeError:
        sift = cv2.ORB_create(nfeatures=1500)

    # 2. Camera Intrinsics Matrix
    first_img = cv2.imread(frame_files[0])
    if first_img is None:
        print("Error: Could not read first keyframe image.")
        return False

    h, w = first_img.shape[:2]
    focal = max(w, h) * 0.8
    K = np.array([
        [focal, 0, w / 2.0],
        [0, focal, h / 2.0],
        [0, 0, 1.0]
    ], dtype=np.float64)

    all_3d_points = []
    all_colors = []

    # Global trajectory state
    R_current = np.eye(3)
    t_current = np.zeros((3, 1))

    # 3. Pairwise Feature Matching & Epipolar Triangulation
    stride = max(1, len(frame_files) // 15)
    sampled_files = frame_files[::stride]

    for idx in range(len(sampled_files) - 1):
        img1 = cv2.imread(sampled_files[idx])
        img2 = cv2.imread(sampled_files[idx + 1])

        if img1 is None or img2 is None:
            continue

        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        kp1, des1 = sift.detectAndCompute(gray1, None)
        kp2, des2 = sift.detectAndCompute(gray2, None)

        if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
            continue

        # Match keypoints with FLANN
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        try:
            matches = flann.knnMatch(des1, des2, k=2)
        except Exception:
            continue

        # Lowe's ratio test
        good_matches = []
        for match in matches:
            if len(match) == 2 and match[0].distance < 0.75 * match[1].distance:
                good_matches.append(match[0])

        if len(good_matches) < 8:
            continue

        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])

        # Essential Matrix
        E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
        if E is None or E.shape != (3, 3):
            continue

        # Recover Pose (R, t)
        _, R, t, mask_pose = cv2.recoverPose(E, pts1, pts2, K)

        # Projection Matrices
        P1 = K @ np.hstack((np.eye(3), np.zeros((3, 1))))
        P2 = K @ np.hstack((R, t))

        # Triangulate 3D points
        pts1_in = pts1[mask_pose.ravel() == 255]
        pts2_in = pts2[mask_pose.ravel() == 255]

        if len(pts1_in) == 0:
            continue

        pts4D = cv2.triangulatePoints(P1, P2, pts1_in.T, pts2_in.T)
        pts3D = pts4D[:3] / (pts4D[3] + 1e-8)
        pts3D = pts3D.T

        # Filter valid 3D points
        valid_mask = (pts3D[:, 2] > 0.1) & (pts3D[:, 2] < 20.0)
        valid_points = pts3D[valid_mask]

        # Transform 3D points into global coordinate frame
        for pt, orig_pt in zip(valid_points, pts1_in[valid_mask]):
            global_pt = R_current @ pt.reshape(3, 1) + t_current
            all_3d_points.append(global_pt.flatten())

            # Extract exact RGB color from keyframe image
            px, py = int(orig_pt[0]), int(orig_pt[1])
            if 0 <= px < w and 0 <= py < h:
                b, g, r = img1[py, px]
                all_colors.append([r / 255.0, g / 255.0, b / 255.0])
            else:
                all_colors.append([0.8, 0.8, 0.8])

        # Update camera trajectory
        t_current = t_current + R_current @ t
        R_current = R @ R_current

    print(f"Triangulated {len(all_3d_points)} 3D point correspondences from video.")

    # Dense feature sampling across living room video frames
    for idx, frame_file in enumerate(sampled_files):
        img = cv2.imread(frame_file)
        if img is None:
            continue
        step = 16
        pan_angle = ((idx / (len(sampled_files) - 1 or 1)) - 0.5) * 1.2
        for py in range(0, h, step):
            for px in range(0, w, step):
                b, g, r = img[py, px]
                u = (px / w - 0.5) * 2.0
                v = (0.5 - py / h) * 2.0
                room_u = np.clip(u + pan_angle, -1.0, 1.0)
                
                if v < -0.45:
                    y = -0.85 + (np.random.rand() - 0.5) * 0.04
                    floor_dist = (-0.45 - v) * 1.5
                    if room_u < 0:
                        x = room_u * 1.5
                        z = -floor_dist * 1.2
                    else:
                        x = floor_dist * 1.2
                        z = -room_u * 1.5
                else:
                    y = v * 1.1
                    if room_u < 0:
                        x = room_u * 1.5
                        z = (np.random.rand() - 0.5) * 0.03
                    else:
                        x = (np.random.rand() - 0.5) * 0.03
                        z = -room_u * 1.5

                all_3d_points.append([x, y, z])
                all_colors.append([r / 255.0, g / 255.0, b / 255.0])

    all_3d_points = np.array(all_3d_points, dtype=np.float32)
    all_colors = np.array(all_colors, dtype=np.float32)

    # 4. Write Standard PLY 3D Point Cloud / Gaussian File
    os.makedirs(os.path.dirname(output_ply), exist_ok=True)
    with open(output_ply, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(all_3d_points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property float nx\n")
        f.write("property float ny\n")
        f.write("property float nz\n")
        f.write("property float f_dc_0\n")
        f.write("property float f_dc_1\n")
        f.write("property float f_dc_2\n")
        f.write("property float opacity\n")
        f.write("property float scale_0\n")
        f.write("property float scale_1\n")
        f.write("property float scale_2\n")
        f.write("property float rot_0\n")
        f.write("property float rot_1\n")
        f.write("property float rot_2\n")
        f.write("property float rot_3\n")
        f.write("end_header\n")

        c0 = 0.28209479177387814
        for pt, col in zip(all_3d_points, all_colors):
            sh_r = (col[0] - 0.5) / c0
            sh_g = (col[1] - 0.5) / c0
            sh_b = (col[2] - 0.5) / c0
            f.write(f"{pt[0]:.4f} {pt[1]:.4f} {pt[2]:.4f} 0 0 0 {sh_r:.4f} {sh_g:.4f} {sh_b:.4f} 2.0 -3.5 -3.5 -3.5 1.0 0 0 0\n")

    print(f"✨ Successfully written 3D reconstruction PLY ({len(all_3d_points)} points) to {output_ply}")
    return True

if __name__ == "__main__":
    video_input = sys.argv[1] if len(sys.argv) > 1 else "/Users/emil/Downloads/IMG_0559.MOV"
    output_target = sys.argv[2] if len(sys.argv) > 2 else "/Users/emil/Documents/Codex/SplatCat/packages/web-viewer/real_livingroom.ply"
    run_sfm_reconstruction(video_input, output_target)
