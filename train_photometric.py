#!/usr/bin/env python3
"""
SplatCat Photometric Training Driver (Issue #22 / PRD 0003 T3)

Runs real photometric optimization of 3D Gaussians against captured
keyframes using the differentiable renderer (gaussian_renderer.py).

Keyframes, camera poses (intrinsics + extrinsics) from a COLMAP sparse
model, and the sparse point cloud feed an Adam optimizer that minimizes
    0.8 * L1 + 0.2 * SSIM
between rendered and captured keyframes per ADR 0005. The exported PLY obeys
the viewer attribute contract (log-scales, SH DC colors, quaternion layout).
"""

import glob
import os
import time

import numpy as np


def read_cameras_txt(path):
    """Parses COLMAP cameras.txt into {camera_id: (model, width, height, params)}."""
    cameras = {}
    with open(path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            cam_id = int(parts[0])
            model = parts[1]
            width = int(parts[2])
            height = int(parts[3])
            params = [float(p) for p in parts[4:]]
            cameras[cam_id] = (model, width, height, params)
    return cameras


def read_images_txt(path):
    """Parses COLMAP images.txt into a list of image dicts.

    The file stores each image as two logical lines: the pose line
    (IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME) followed by a
    POINTS2D line (possibly blank). Only pose lines are parsed here.
    """
    images = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 10:
                continue  # points2D line or blank
            try:
                img_id = int(parts[0])
                qvec = [float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])]
                tvec = [float(parts[5]), float(parts[6]), float(parts[7])]
                cam_id = int(parts[8])
                name = parts[9]
                images.append({
                    "id": img_id,
                    "qvec": qvec,
                    "tvec": tvec,
                    "camera_id": cam_id,
                    "name": name,
                })
            except ValueError:
                continue
    return images


def _quat_to_rot32(q):
    """COLMAP qvec [w, x, y, z] -> (3, 3) rotation matrix (float32)."""
    w, x, y, z = q[0], q[1], q[2], q[3]
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float32)


def _find_model_dir(colmap_dir):
    """Resolves the sparse model directory: largest points3D.bin subdir, else TXT dir."""
    bin_cands = glob.glob(os.path.join(colmap_dir, "**", "points3D.bin"), recursive=True) + \
                glob.glob(os.path.join(colmap_dir, "points3D.bin"))
    txt_cands = glob.glob(os.path.join(colmap_dir, "**", "points3D.txt"), recursive=True) + \
                glob.glob(os.path.join(colmap_dir, "points3D.txt"))
    candidates = [os.path.dirname(p) for p in bin_cands + txt_cands if os.path.exists(p)]
    if not candidates:
        return colmap_dir
    def size_of(d):
        s = 0
        for f in ("points3D.bin", "points3D.txt"):
            p = os.path.join(d, f)
            if os.path.exists(p):
                s = max(s, os.path.getsize(p))
        return s
    return max(set(candidates), key=size_of)


def read_cameras_bin(path):
    """Parses COLMAP cameras.bin into {camera_id: (model, width, height, params)}."""
    import struct
    cameras = {}
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            cam_id = struct.unpack("<I", f.read(4))[0]
            model_id = struct.unpack("<i", f.read(4))[0]
            width, height = struct.unpack("<QQ", f.read(16))
            num_params = {0: 3, 1: 4, 2: 4, 3: 5, 4: 8, 5: 9, 6: 12, 7: 12, 8: 15}.get(model_id, 4)
            params = list(struct.unpack(f"<{num_params}d", f.read(8 * num_params)))
            cameras[cam_id] = (model_id, width, height, params)
    return cameras


def read_images_bin(path):
    """Parses COLMAP images.bin into a list of image dicts."""
    import struct
    images = []
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            img_id = struct.unpack("<I", f.read(4))[0]
            qvec = list(struct.unpack("<4d", f.read(32)))
            tvec = list(struct.unpack("<3d", f.read(24)))
            cam_id = struct.unpack("<I", f.read(4))[0]
            name_bytes = b""
            while True:
                b = f.read(1)
                if b == b"\x00" or not b:
                    break
                name_bytes += b
            name = name_bytes.decode("utf-8", errors="replace")
            num_pts = struct.unpack("<Q", f.read(8))[0]
            f.read(num_pts * 24)  # skip points2D (x, y, point3D_id)
            images.append({
                "id": img_id, "qvec": qvec, "tvec": tvec,
                "camera_id": cam_id, "name": name,
            })
    return images


def build_views_from_colmap(sparse_dir, frames_dir=None):
    """Builds {name: {K, viewmat}} from a COLMAP sparse model (TXT or binary).

    Supports SIMPLE_RADIAL / PINHOLE / SIMPLE_PINHOLE intrinsics. viewmat is
    (4, 4) world-to-camera matching the renderer's convention (camera along +Z).
    """
    model_dir = _find_model_dir(sparse_dir)
    cameras_txt = os.path.join(model_dir, "cameras.txt")
    images_txt = os.path.join(model_dir, "images.txt")
    if os.path.exists(cameras_txt) and os.path.exists(images_txt):
        cameras = read_cameras_txt(cameras_txt)
        images = read_images_txt(images_txt)
    else:
        cameras = read_cameras_bin(os.path.join(model_dir, "cameras.bin"))
        images = read_images_bin(os.path.join(model_dir, "images.bin"))

    model_names = {0: "SIMPLE_PINHOLE", 1: "PINHOLE", 2: "SIMPLE_RADIAL",
                   3: "RADIAL", 4: "OPENCV", 5: "OPENCV_FISHEYE"}

    views = []
    for img in images:
        cam = cameras.get(img["camera_id"])
        if cam is None:
            continue
        model, width, height, params = cam
        if isinstance(model, int):
            model = model_names.get(model, "UNKNOWN")
        if model == "SIMPLE_RADIAL" and len(params) >= 4:
            f, cx, cy = params[0], params[1], params[2]
        elif model == "PINHOLE" and len(params) >= 4:
            f, cx, cy = params[0], params[2], params[3]
        elif model == "SIMPLE_PINHOLE" and len(params) >= 3:
            f, cx, cy = params[0], params[1], params[2]
        else:
            continue

        if frames_dir is not None:
            img_path = os.path.join(frames_dir, img["name"])
            if not os.path.exists(img_path):
                continue
            img["_path"] = img_path

        K = np.array([
            [f, 0.0, cx],
            [0.0, f, cy],
            [0.0, 0.0, 1.0],
        ], dtype=np.float32)
        R = _quat_to_rot32(np.array(img["qvec"], dtype=np.float32))
        t = np.array(img["tvec"], dtype=np.float32)
        viewmat = np.eye(4, dtype=np.float32)
        viewmat[:3, :3] = R
        viewmat[:3, 3] = t

        views.append({
            "name": img["name"],
            "camera_id": img["camera_id"],
            "width": width,
            "height": height,
            "K": K,
            "viewmat": viewmat,
            "_path": img.get("_path"),
        })
    return views


def load_keyframes(frames_dir, resize=None):
    """Loads keyframe PNG/JPG from frames_dir into normalized float32 RGB {name: HWC}.

    resize=(w, h) optionally downsamples during load so training runs with a
    reduced render size never hold the full-res frames in memory.
    """
    from PIL import Image
    keyframes = {}
    patterns = [os.path.join(frames_dir, "*.png"), os.path.join(frames_dir, "*.jpg"),
                os.path.join(frames_dir, "*.jpeg")]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    for path in sorted(set(files)):
        name = os.path.basename(path)
        img = Image.open(path).convert("RGB")
        if resize is not None:
            img = img.resize(resize, Image.BILINEAR)
        keyframes[name] = np.asarray(img, dtype=np.float32) / 255.0
    return keyframes


def _read_sparse_points(colmap_dir):
    """Reads COLMAP sparse points3D (bin preferred, txt fallback) -> (xyz, rgb)."""
    import struct
    bin_cands = glob.glob(os.path.join(colmap_dir, "**", "points3D.bin"), recursive=True) + \
                glob.glob(os.path.join(colmap_dir, "points3D.bin"))
    bin_cands = sorted({p for p in bin_cands if os.path.exists(p)}, key=os.path.getsize, reverse=True)
    for path in bin_cands:
        try:
            with open(path, "rb") as f:
                n = struct.unpack("<Q", f.read(8))[0]
                if n > 0:
                    xyz, rgb = [], []
                    for _ in range(n):
                        head = f.read(43)
                        if len(head) < 43:
                            break
                        _, x, y, z, r, g, b, _err = struct.unpack("<QdddBBBd", head)
                        tl = struct.unpack("<Q", f.read(8))[0]
                        f.read(tl * 8)
                        xyz.append([x, y, z])
                        rgb.append([r / 255.0, g / 255.0, b / 255.0])
                    if xyz:
                        return np.array(xyz, dtype=np.float32), np.array(rgb, dtype=np.float32)
        except Exception:
            continue
    txt_cands = glob.glob(os.path.join(colmap_dir, "**", "points3D.txt"), recursive=True) + \
                glob.glob(os.path.join(colmap_dir, "points3D.txt"))
    for path in sorted({p for p in txt_cands if os.path.exists(p)}, key=os.path.getsize, reverse=True):
        xyz, rgb = [], []
        with open(path, "r") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 7:
                    try:
                        xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
                        rgb.append([int(parts[4]) / 255.0, int(parts[5]) / 255.0, int(parts[6]) / 255.0])
                    except ValueError:
                        continue
        if xyz:
            return np.array(xyz, dtype=np.float32), np.array(rgb, dtype=np.float32)
    return None, None


def _export_ply(output_ply, means, colors, opacities, scales, quats, SH_C0):
    """Writes the current parameter state to a contract-conformant PLY."""
    import torch
    from train_3dgs_metal import write_3dgs_ply
    write_3dgs_ply(
        output_ply,
        means.detach().cpu().numpy(),
        (torch.clamp(colors, 0.0, 1.0).detach().cpu().numpy() - 0.5) / SH_C0,
        torch.sigmoid(opacities).detach().cpu().numpy(),
        scales.detach().cpu().numpy(),
        quats.detach().cpu().numpy(),
    )


def train_photometric(
    colmap_dir,
    images_dir,
    output_ply,
    iterations=3000,
    init_points=None,
    init_colors=None,
    width=None,
    height=None,
    depth_dir=None,
    render_width=None,
    render_height=None,
):
    """Runs real photometric 3DGS optimization against captured keyframes.

    depth_dir is accepted for CLI compatibility but IGNORED: the depth prior
    is explicitly dropped in this training cut (PRD 0003 T5 / ticket #24) —
    the renderer has no depth output mode, so no depth loss can be wired.

    render_width/render_height optionally downscale rendering (and targets
    and intrinsics) to speed up real runs; the exported PLY is unaffected —
    Gaussian geometry is resolution-independent.

    Returns the recorded loss history (list of floats, one per logged step).
    """
    import torch
    from gaussian_renderer import render_gaussians
    from train_3dgs_metal import write_3dgs_ply, PLY_CONTRACT_VIEWER_RULES, SH_C0
    from quality_metrics import compute_ssim

    if depth_dir:
        print(f"[Photometric] WARNING: --depth_dir is ignored; the depth stage "
              f"is explicitly dropped (PRD 0003 T5).")

    print(f"[Photometric] COLMAP dir: {colmap_dir}")
    print(f"[Photometric] Images dir: {images_dir}")
    print(f"[Photometric] Output PLY: {output_ply}")

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"[Photometric] Device: {device}")

    views = build_views_from_colmap(colmap_dir, images_dir)
    if not views:
        raise FileNotFoundError("No usable camera views found in COLMAP sparse model")

    if width is None:
        width = views[0]["width"]
    if height is None:
        height = views[0]["height"]

    # Resolve the render resolution up front so keyframes are loaded at
    # (possibly reduced) render size instead of holding full-res frames.
    if render_width is None:
        render_width = width
    if render_height is None:
        render_height = height
    resize_load = None
    if render_width != width or render_height != height:
        resize_load = (render_width, render_height)

    keyframes = load_keyframes(images_dir, resize=resize_load)
    if not keyframes:
        raise FileNotFoundError(f"No keyframe images found in {images_dir}")

    n_views = min(len(views), len(keyframes))
    if n_views == 0:
        raise FileNotFoundError("No views matched keyframes")

    # Reorder views to match keyframe names; drop unmatched
    matched = []
    used_names = set()
    for v in views:
        if v["name"] in keyframes and v["name"] not in used_names:
            matched.append((v, keyframes[v["name"]]))
            used_names.add(v["name"])
        if len(matched) >= n_views:
            break
    if not matched:
        raise FileNotFoundError("No view matched a keyframe by name")

    # Bound the training view set so all targets fit on device memory; evenly
    # subsample any larger COLMAP model down to at most MAX_TRAIN_VIEWS views.
    MAX_TRAIN_VIEWS = 200
    if len(matched) > MAX_TRAIN_VIEWS:
        stride = len(matched) / MAX_TRAIN_VIEWS
        matched = [matched[int(i * stride)] for i in range(MAX_TRAIN_VIEWS)]
        print(f"[Photometric] Subsampled to {MAX_TRAIN_VIEWS} evenly spaced training views")
    n_views = len(matched)

    # Initial Gaussian configuration from COLMAP sparse points
    if init_points is None:
        sparse_xyz, sparse_rgb = _read_sparse_points(colmap_dir)
        if sparse_xyz is not None and len(sparse_xyz) > 0:
            init_points = list(sparse_xyz)
            init_colors = list(sparse_rgb)
        else:
            init_points = [np.array([0.0, 0.0, 0.0])]
            init_colors = [np.array([0.5, 0.5, 0.5])]

    # Bound the Gaussian count: tiny random subset of the sparse cloud keeps
    # the pure-PyTorch rasterizer tractable on MPS. The optimizer adapts the
    # surviving Gaussians to the surface.
    MAX_INIT_POINTS = 50000
    if len(init_points) > MAX_INIT_POINTS:
        rng = np.random.default_rng(0)
        keep = rng.choice(len(init_points), MAX_INIT_POINTS, replace=False)
        init_points = [init_points[i] for i in keep]
        init_colors = [init_colors[i] for i in keep]
        print(f"[Photometric] Downsampled init cloud to {MAX_INIT_POINTS} Gaussians")

    means = torch.tensor(np.array(init_points, dtype=np.float32), requires_grad=True, device=device)
    colors = torch.tensor(np.array(init_colors, dtype=np.float32), requires_grad=True, device=device)
    N = means.shape[0]
    opacities = torch.full((N, 1), 0.7, dtype=torch.float32, requires_grad=True, device=device)

    viewmats = torch.tensor(np.stack([v["viewmat"] for v, _ in matched]), device=device)
    Ks = torch.tensor(np.stack([v["K"] for v, _ in matched]), device=device)
    targets = torch.tensor(
        np.stack([np.transpose(kf, (2, 0, 1)) for _, kf in matched]), device=device
    )

    # Adapt intrinsics to the render resolution; targets were loaded at it.
    # The exported Gaussian geometry is resolution-independent.
    if render_width != width or render_height != height:
        sx = render_width / width
        sy = render_height / height
        scale = torch.tensor(
            [[sx, 0.0, 0.0], [0.0, sy, 0.0], [0.0, 0.0, 1.0]],
            dtype=Ks.dtype, device=device,
        )
        Ks = scale @ Ks
        width, height = render_width, render_height
        print(f"[Photometric] Render resolution: {width}x{height}")

    # Init scales proportional to each splat's distance to the nearest camera
    # so projected size is roughly constant in screen space (~1% of the focal
    # length); a flat world-space init would blow near-field splats across
    # every tile and make some views prohibitively expensive to render.
    with torch.no_grad():
        Rv = viewmats[:, :3, :3]
        tv = viewmats[:, :3, 3]
        cams = -torch.einsum("nij,ni->nj", Rv.transpose(1, 2), tv)  # (V, 3)
        d2 = ((means.unsqueeze(1) - cams.unsqueeze(0)) ** 2).sum(-1)
        near_depth = torch.sqrt(d2.min(dim=1).values)               # (N,)
        init_scale = torch.clamp(0.01 * near_depth, 1e-4, 0.5)
    scales = torch.log(init_scale).unsqueeze(1).expand(N, 3).contiguous()
    scales = scales.clone().requires_grad_(True)
    quats = torch.zeros((N, 4), dtype=torch.float32, requires_grad=True, device=device)
    quats.data[:, 0] = 1.0

    optimizer = torch.optim.Adam([
        {"params": [means], "lr": 1e-3},
        {"params": [colors], "lr": 1e-2},
        {"params": [opacities], "lr": 5e-2},
        {"params": [scales], "lr": 5e-3},
        {"params": [quats], "lr": 1e-3},
    ])

    # A tiny subset of views per step for speed, shuffled each iteration.
    import random
    perm = list(range(n_views))

    loss_history = []
    log_every = max(1, iterations // 100)
    for step in range(1, iterations + 1):
        t_step_start = time.time()
        random.shuffle(perm)
        sel = perm[: min(2, n_views)]

        optimizer.zero_grad()
        t_render = time.time()
        img, alpha = render_gaussians(
            means, torch.clamp(quats, -1, 1), torch.exp(scales), torch.sigmoid(opacities),
            torch.clamp(colors, 0.0, 1.0),
            viewmats[sel], Ks[sel], width, height,
        )
        t_render = time.time() - t_render
        target = targets[sel]

        t_loss = time.time()
        l1 = torch.abs(img - target).mean()
        # Per-view SSIM against a per-view mean (single value per batch element)
        ssims = torch.stack([
            compute_ssim(img[i], target[i]) for i in range(img.shape[0])
        ]).mean()
        ssim_loss = 1.0 - ssims
        loss = 0.8 * l1 + 0.2 * ssim_loss

        if not torch.isfinite(loss):
            # Clamp pathological renders rather than diverging the whole run
            loss = torch.tensor(10.0, device=device, requires_grad=True)

        loss.backward()
        optimizer.step()
        with torch.no_grad():
            means.data.clamp_(min=-5.0, max=5.0)
            scales.data.clamp_(min=np.log(1e-4), max=np.log(1.0))
        t_step = time.time() - t_step_start

        if step % log_every == 0 or step == iterations:
            loss_history.append(float(loss.detach().cpu().numpy()))
            print(f"[Photometric] Iteration {step}/{iterations} - Loss: {loss.item():.6f}"
                  f" [render {t_render:.1f}s step {t_step:.1f}s]")

        if step % max(1, iterations // 4) == 0 or step == iterations:
            os.makedirs(os.path.dirname(os.path.abspath(output_ply)), exist_ok=True)
            _export_ply(output_ply, means, colors, opacities, scales, quats, SH_C0)
            print(f"[Photometric] Checkpoint PLY written to {output_ply}")

    _export_ply(output_ply, means, colors, opacities, scales, quats, SH_C0)
    print(f"[Photometric] Final model exported: {len(means)} Gaussians -> {output_ply}")
    return loss_history


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SplatCat Photometric Training Driver")
    parser.add_argument("--colmap_dir", required=True)
    parser.add_argument("--images_dir", required=True)
    parser.add_argument("--output_ply", required=True)
    parser.add_argument("--iterations", type=int, default=3000)
    parser.add_argument("--depth_dir", default=None)
    parser.add_argument("--render_width", type=int, default=None)
    parser.add_argument("--render_height", type=int, default=None)
    args = parser.parse_args()
    train_photometric(
        args.colmap_dir, args.images_dir, args.output_ply,
        iterations=args.iterations, depth_dir=args.depth_dir,
        render_width=args.render_width, render_height=args.render_height,
    )