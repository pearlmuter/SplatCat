#!/usr/bin/env python3
"""
SplatCat Differentiable Gaussian Rasterizer Driver (Issue #21 / PRD 0003 T2)

Renders a set of Gaussians to an image from camera poses. Two backends:

1. gsplat (CUDA builds): used automatically when its compiled runtime is
   available (`gsplat.cuda._backend._C is not None`).
2. Pure-PyTorch rasterizer (the default on Apple Silicon): a direct
   implementation of 3D Gaussian Splatting forward pass (EWA projection +
   alpha compositing) built from standard autograd ops, so it runs on MPS
   and backprops without any compiled extension.

Gaussian attribute contract (internal training representation):
- means:     (N, 3) float32 positions
- quats:     (N, 4) float32 unit quaternions [w, x, y, z]
- scales:    (N, 3) float32 *raw* per-axis scales (not log)
- opacities: (N, 1) float32 opacity in [0, 1]
- colors:    (N, 3) float32 linear RGB in [0, 1] (SH degree 0)

Camera convention matches COLMAP/gsplat: camera looks down +Z in camera
space; world-to-camera transform is viewmat (B, 4, 4); intrinsics K (B, 3, 3)
with fx, fy, cx, cy.
"""

import math

import torch

try:
    from gsplat import rasterization as _gsplat_rasterization
    from gsplat.cuda import _backend as _gsplat_backend
    _GSPLAT_OK = getattr(_gsplat_backend, "_C", None) is not None
except Exception:  # pragma: no cover
    _GSPLAT_OK = False


def _quat_to_rot(quats):
    """(N, 4) quats [w, x, y, z] -> (N, 3, 3) rotation matrices."""
    w, x, y, z = quats[:, 0], quats[:, 1], quats[:, 2], quats[:, 3]
    w2, x2, y2, z2 = w * w, x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    rot = torch.stack(
        [
            1 - 2 * (y2 + z2), 2 * (xy - wz), 2 * (xz + wy),
            2 * (xy + wz), 1 - 2 * (x2 + z2), 2 * (yz - wx),
            2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (x2 + y2),
        ],
        dim=-1,
    )
    return rot.reshape(-1, 3, 3)


def _render_gaussians_torch(means, quats, scales, opacities, colors,
                            viewmats, Ks, width, height, backgrounds=None):
    """Pure-PyTorch differentiable forward pass for 3DGS."""
    device = means.device
    B = viewmats.shape[0]
    N = means.shape[0]
    dtype = torch.float32

    out_images = []
    out_alphas = []

    fx = Ks[:, 0, 0]
    fy = Ks[:, 1, 1]
    cx = Ks[:, 0, 2]
    cy = Ks[:, 1, 2]

    for b in range(B):
        R = viewmats[b, :3, :3]           # (3, 3)
        t = viewmats[b, :3, 3]            # (3,)
        # Camera-space centers: p_cam = R @ means + t
        p_cam = means @ R.t() + t         # (N, 3)
        depth = p_cam[:, 2]               # (N,)
        vis = depth > 0.01
        depth_safe = torch.clamp(depth, min=0.01)

        u = fx[b] * p_cam[:, 0] / depth_safe + cx[b]
        v = fy[b] * p_cam[:, 1] / depth_safe + cy[b]

        # 3D covariance from rotation and scales: cov3 = (R_g S)(R_g S)^T
        S = torch.diag_embed(scales)      # (N, 3, 3)
        rot = _quat_to_rot(quats)         # (N, 3, 3)
        M = rot @ S                       # (N, 3, 3)
        cov3 = M @ M.transpose(1, 2)

        # World->camera rotation for covariance
        cov_cam = R @ cov3 @ R.t()        # (N, 3, 3)

        # Projective Jacobian (pinhole)
        z2 = depth_safe * depth_safe
        fx_s, fy_s = fx[b], fy[b]
        x_c, y_c = p_cam[:, 0], p_cam[:, 1]
        J = torch.zeros(N, 2, 3, device=device, dtype=dtype)
        J[:, 0, 0] = fx_s / depth_safe
        J[:, 0, 2] = -fx_s * x_c / z2
        J[:, 1, 1] = fy_s / depth_safe
        J[:, 1, 2] = -fy_s * y_c / z2

        cov2 = J @ cov_cam @ J.transpose(1, 2)  # (N, 2, 2)
        # Regularize to keep inversion stable
        eps = 0.3
        cov2 = cov2 + eps * torch.eye(2, device=device, dtype=dtype)

        # Inverse 2D covariance for Mahalanobis distance
        det = cov2[:, 0, 0] * cov2[:, 1, 1] - cov2[:, 0, 1] * cov2[:, 1, 0]
        det_safe = torch.clamp(det, min=1e-8)
        inv = torch.zeros(N, 2, 2, device=device, dtype=dtype)
        inv[:, 0, 0] = cov2[:, 1, 1] / det_safe
        inv[:, 1, 1] = cov2[:, 0, 0] / det_safe
        inv[:, 0, 1] = -cov2[:, 0, 1] / det_safe
        inv[:, 1, 0] = -cov2[:, 1, 0] / det_safe

        # Pixel grid
        ys, xs = torch.meshgrid(
            torch.arange(height, device=device, dtype=dtype),
            torch.arange(width, device=device, dtype=dtype),
            indexing="ij",
        )
        grid = torch.stack([xs.reshape(-1), ys.reshape(-1)], dim=-1)  # (HW, 2)

        centers = torch.stack([u, v], dim=-1)  # (N, 2)
        d = grid.unsqueeze(0) - centers.unsqueeze(1)  # (N, HW, 2)

        maha = torch.einsum("npi,nij,npj->np", d, inv, d)  # (N, HW)
        opac = opacities.reshape(-1)
        gauss_alpha = opac.unsqueeze(1) * torch.exp(-0.5 * maha)  # (N, HW)
        gauss_alpha = torch.clamp(gauss_alpha, 0.0, 1.0)
        # Kill contributions outside the visible depth range
        gauss_alpha = gauss_alpha * vis.unsqueeze(1).to(dtype)

        # Back-to-front compositing: sort far -> near
        order = torch.argsort(depth, descending=True)
        alpha_sorted = gauss_alpha[order]          # (N, HW)
        color_sorted = colors[order].unsqueeze(1)  # (N, 1, 3)

        # T_i = prod_{j<i} (1 - alpha_j); C = sum_i T_i * alpha_i * c_i
        trans = torch.cumprod(1.0 - alpha_sorted, dim=0)
        trans_shift = torch.cat([torch.ones_like(trans[:1]), trans[:-1]], dim=0)

        acc = torch.einsum("np,npc,np->pc", trans_shift, color_sorted, alpha_sorted)  # (HW, 3)
        img = acc.reshape(height, width, 3)
        # True coverage: 1 - prod(1 - alpha_i) over all splats, per pixel.
        a_accum = (1.0 - torch.prod(1.0 - alpha_sorted, dim=0)).reshape(height, width)

        if backgrounds is not None:
            bg = backgrounds[b].permute(1, 2, 0)
            img = img + (1.0 - a_accum.unsqueeze(-1)) * bg

        out_images.append(img.permute(2, 0, 1))
        out_alphas.append(a_accum)

    return (
        torch.stack(out_images),
        torch.stack(out_alphas),
    )


def render_gaussians(
    means,
    quats,
    scales,
    opacities,
    colors,
    viewmats,
    Ks,
    width,
    height,
    backgrounds=None,
):
    """Rasterizes Gaussians through every camera in the batch.

    Args:
        means:      (N, 3) positions
        quats:      (N, 4) quaternions [w, x, y, z]
        scales:     (N, 3) linear scales
        opacities:  (N, 1) opacity
        colors:     (N, 3) RGB
        viewmats:   (B, 4, 4) world-to-camera matrices
        Ks:         (B, 3, 3) intrinsics
        width, height: image size in pixels
        backgrounds: (B, 3, H, W) or None

    Returns:
        (rendered, alphas): rendered RGB (B, 3, H, W) and alpha (B, H, W).
    """
    if opacities.ndim == 2 and opacities.shape[1] == 1:
        opacities = opacities[:, 0]

    if _GSPLAT_OK:
        rendered, alphas, _ = _gsplat_rasterization(
            means,
            quats,
            scales,
            opacities,
            colors,
            viewmats,
            Ks,
            width=width,
            height=height,
            render_mode="RGB",
            sh_degree=None,
            backgrounds=backgrounds,
        )
        return rendered.permute(0, 3, 1, 2).contiguous(), alphas

    return _render_gaussians_torch(
        means, quats, scales, opacities, colors, viewmats, Ks, width, height,
        backgrounds=backgrounds,
    )


def render_single_view(
    means, quats, scales, opacities, colors, viewmat, K, width, height
):
    """Renders a single camera view; returns (img (3,H,W), alpha (H,W))."""
    img, alpha = render_gaussians(
        means, quats, scales, opacities, colors,
        viewmat.unsqueeze(0), K.unsqueeze(0), width, height,
    )
    return img[0], alpha[0]