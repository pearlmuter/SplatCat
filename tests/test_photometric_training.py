#!/usr/bin/env python3
import os
import shutil
import tempfile
import unittest
import numpy as np
from PIL import Image

from train_photometric import (
    read_cameras_txt,
    read_images_txt,
    build_views_from_colmap,
    load_keyframes,
    train_photometric,
    read_cameras_bin,
    read_images_bin,
)


def make_synthetic_colmap(workdir, width=64, height=64, f=100.0):
    """Builds a synthetic COLMAP TXT sparse model + keyframes.

    Two cameras look at a small set of colored points at the origin.
    Ground-truth keyframes are painted analytically (numpy circles at the
    projected centers) — independent of the differentiable renderer.
    Returns (cameras, images, points).
    """
    sparse = os.path.join(workdir, "sparse", "txt")
    os.makedirs(sparse, exist_ok=True)

    cx, cy = width / 2.0, height / 2.0

    # camera poses: world-to-camera [R | t]; cameras look along +Z at origin
    cameras = {}
    images = []
    points = {
        1: ([0.0, 0.0, 0.0], [0.9, 0.1, 0.1]),
        2: ([0.3, 0.0, 0.0], [0.1, 0.9, 0.1]),
        3: ([0.0, 0.3, 0.0], [0.1, 0.1, 0.9]),
    }

    def look_at(pos):
        """Camera at pos looking at origin, world-to-cam R such that +Z points to origin."""
        d = np.array([0.0, 0.0, 0.0]) - np.array(pos)
        z = d / (np.linalg.norm(d) + 1e-9)
        x = np.cross(np.array([0.0, 1.0, 0.0]), z)
        x = x / (np.linalg.norm(x) + 1e-9)
        y = np.cross(z, x)
        R = np.stack([x, y, z])
        # world-to-cam translation: t = -R @ pos
        t = -R @ np.array(pos, dtype=np.float64)
        return _rot_to_quat(R), t

    poses = [[0.0, 0.0, 2.0], [0.5, 0.0, 2.2]]
    for i, pos in enumerate(poses):
        cam_id = i + 1
        cameras[cam_id] = ("SIMPLE_RADIAL", width, height, [f, cx, cy, 0.0])
        qvec, tvec = look_at(pos)
        images.append((cam_id, qvec, tvec, f"frame_{cam_id:04d}.png"))

    # ground-truth keyframes painted with numpy
    frames_dir = os.path.join(workdir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    keyframes = {}
    for cam_id, qvec, tvec, name in images:
        R = np.eye(4)
        R[:3, :3] = _rotmat(qvec)
        R[:3, 3] = tvec
        img = np.zeros((height, width, 3))
        for pid, (pt, col) in points.items():
            pc = R[:3, :3] @ np.array(pt) + tvec
            depth = pc[2]
            if depth <= 0.05:
                continue
            u = f * pc[0] / depth + cx
            v = f * pc[1] / depth + cy
            r = 4
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    yy, xx = int(round(v + dy)), int(round(u + dx))
                    if 0 <= yy < height and 0 <= xx < width and dx * dx + dy * dy <= r * r:
                        img[yy, xx] = col
        keyframes[name] = img
        Image.fromarray((img * 255).astype(np.uint8)).save(os.path.join(frames_dir, name))

    with open(os.path.join(sparse, "cameras.txt"), "w") as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        for cid, (model, w, h, params) in cameras.items():
            f.write(f"{cid} {model} {w} {h} " + " ".join(f"{p:.6f}" for p in params) + "\n")

    with open(os.path.join(sparse, "images.txt"), "w") as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        f.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
        for cam_id, qvec, tvec, name in images:
            f.write(f"{cam_id} " + " ".join(f"{q:.6f}" for q in qvec) + " " +
                    " ".join(f"{t:.6f}" for t in tvec) + f" {cam_id} {name}\n")
            f.write("\n")

    with open(os.path.join(sparse, "points3D.txt"), "w") as f:
        f.write("# 3D point list with one line of data per point:\n")
        f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]\n")
        for pid, (pt, col) in points.items():
            f.write(f"{pid} " + " ".join(f"{p:.6f}" for p in pt) + " " +
                    f"{int(col[0]*255)} {int(col[1]*255)} {int(col[2]*255)} 0.5\n")

    return sparse, frames_dir, points


def _rot_to_quat(R):
    """Stable 3x3 rotation matrix -> quaternion [w, x, y, z] (Shepperd's method)."""
    tr = np.trace(R)
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2.0
        w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s
        y = (R[0, 2] - R[2, 0]) / s
        z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        w = (R[2, 1] - R[1, 2]) / s
        x = 0.25 * s
        y = (R[0, 1] + R[1, 0]) / s
        z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        w = (R[0, 2] - R[2, 0]) / s
        x = (R[0, 1] + R[1, 0]) / s
        y = 0.25 * s
        z = (R[1, 2] + R[2, 1]) / s
    else:
        s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        w = (R[1, 0] - R[0, 1]) / s
        x = (R[0, 2] + R[2, 0]) / s
        y = (R[1, 2] + R[2, 1]) / s
        z = 0.25 * s
    return np.array([w, x, y, z])


def _rotmat(qvec):
    w, x, y, z = qvec
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


class TestPoseReaders(unittest.TestCase):

    def test_read_cameras_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            sparse, _, _ = make_synthetic_colmap(tmp)
            cameras = read_cameras_txt(os.path.join(sparse, "cameras.txt"))
        self.assertEqual(list(cameras.keys()), [1, 2])
        self.assertEqual(cameras[1][0], "SIMPLE_RADIAL")
        self.assertEqual(cameras[1][1], 64)
        self.assertEqual(cameras[1][3][0], 100.0)

    def test_read_images_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            sparse, _, _ = make_synthetic_colmap(tmp)
            images = read_images_txt(os.path.join(sparse, "images.txt"))
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0]["name"], "frame_0001.png")
        self.assertEqual(len(images[0]["qvec"]), 4)
        self.assertEqual(len(images[0]["tvec"]), 3)

    def test_build_views_produces_intrinsics_and_viewmats(self):
        with tempfile.TemporaryDirectory() as tmp:
            sparse, frames, _ = make_synthetic_colmap(tmp)
            views = build_views_from_colmap(sparse, frames)
        self.assertEqual(len(views), 2)
        self.assertEqual(views[0]["K"].shape, (3, 3))
        self.assertEqual(views[0]["viewmat"].shape, (4, 4))

    def test_load_keyframes_returns_normalized_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            sparse, frames, _ = make_synthetic_colmap(tmp)
            keyframes = load_keyframes(frames)
        self.assertEqual(set(keyframes.keys()), {"frame_0001.png", "frame_0002.png"})
        self.assertTrue(keyframes["frame_0001.png"].dtype == np.float32)
        self.assertLessEqual(keyframes["frame_0001.png"].max(), 1.0)

    def test_read_cameras_bin_roundtrip(self):
        import struct
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cameras.bin")
            with open(path, "wb") as f:
                f.write(struct.pack("<Q", 1))
                f.write(struct.pack("<I", 7))          # camera_id
                f.write(struct.pack("<i", 2))          # SIMPLE_RADIAL
                f.write(struct.pack("<QQ", 1280, 720))  # width, height
                f.write(struct.pack("<4d", 800.0, 640.0, 360.0, 0.0))  # f, cx, cy, k
            cameras = read_cameras_bin(path)
        self.assertEqual(list(cameras.keys()), [7])
        self.assertEqual(cameras[7][1], 1280)
        self.assertEqual(cameras[7][3][0], 800.0)

    def test_read_images_bin_roundtrip(self):
        import struct
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "images.bin")
            with open(path, "wb") as f:
                f.write(struct.pack("<Q", 1))
                f.write(struct.pack("<I", 3))                       # image_id
                f.write(struct.pack("<4d", 1.0, 0.0, 0.0, 0.0))     # qvec
                f.write(struct.pack("<3d", 0.1, 0.2, 0.3))          # tvec
                f.write(struct.pack("<I", 7))                       # camera_id
                f.write(b"frame_0001.png\x00")                      # name
                f.write(struct.pack("<Q", 0))                       # no points2D
            images = read_images_bin(path)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["name"], "frame_0001.png")
        self.assertEqual(images[0]["camera_id"], 7)
        np.testing.assert_allclose(images[0]["tvec"], [0.1, 0.2, 0.3])


class TestPhotometricTraining(unittest.TestCase):

    def test_training_reduces_photometric_loss_against_keyframes(self):
        with tempfile.TemporaryDirectory() as tmp:
            sparse, frames, points = make_synthetic_colmap(tmp)
            output_ply = os.path.join(tmp, "model.ply")
            loss_history = train_photometric(
                sparse, frames, output_ply,
                iterations=60,
                init_points=[np.array(p) for p, _ in points.values()],
                init_colors=[np.array(c) for _, c in points.values()],
                width=64, height=64,
            )
            self.assertGreater(len(loss_history), 5)
            self.assertTrue(np.isfinite(loss_history[0]))
            self.assertLess(loss_history[-1], loss_history[0])
            self.assertTrue(os.path.exists(output_ply))

    def test_training_writes_contract_conformant_ply(self):
        from train_3dgs_metal import parse_ply_per_viewer_contract
        with tempfile.TemporaryDirectory() as tmp:
            sparse, frames, points = make_synthetic_colmap(tmp)
            output_ply = os.path.join(tmp, "model.ply")
            train_photometric(
                sparse, frames, output_ply,
                iterations=15,
                init_points=[np.array(p) for p, _ in points.values()],
                init_colors=[np.array(c) for _, c in points.values()],
                width=64, height=64,
            )
            parsed = parse_ply_per_viewer_contract(output_ply)
            self.assertGreater(len(parsed["xyz"]), 0)
            self.assertEqual(parsed["malformed_lines"], 0)


if __name__ == "__main__":
    unittest.main()