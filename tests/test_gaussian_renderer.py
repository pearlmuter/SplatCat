#!/usr/bin/env python3
import os
import tempfile
import unittest
import numpy as np
import torch
from gaussian_renderer import render_gaussians

class TestGaussianRenderer(unittest.TestCase):

    def setUp(self):
        self.width, self.height = 64, 64
        self.f = 50.0
        self.cx, self.cy = 32.0, 32.0
        K = torch.tensor(
            [[self.f, 0.0, self.cx], [0.0, self.f, self.cy], [0.0, 0.0, 1.0]],
            dtype=torch.float32,
        )
        self.K = K.unsqueeze(0)
        identity = torch.eye(4, dtype=torch.float32)
        self.viewmats = identity.unsqueeze(0)

    def test_single_gaussian_projects_to_image_center(self):
        # One opaque red Gaussian at (0,0,1) along +z of an identity viewmat.
        means = torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float32)
        quats = torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32)
        scales = torch.tensor([[0.08, 0.08, 0.08]], dtype=torch.float32)
        opacities = torch.tensor([[0.95]], dtype=torch.float32)
        colors = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)

        img, alpha = render_gaussians(
            means, quats, scales, opacities, colors,
            self.viewmats, self.K, self.width, self.height,
        )
        # Brightest red pixel should coincide with the projected center.
        r = img[0, 0].cpu()
        max_idx = torch.argmax(r).item()
        y, x = max_idx // self.width, max_idx % self.width
        self.assertLess(abs(x - self.cx), 3)
        self.assertLess(abs(y - self.cy), 3)
        self.assertGreater(float(r.flatten().max()), 0.8)

    def test_offset_gaussian_projectable_off_center(self):
        # Gaussian at (0, 0, 1) offset +x by 0.1 world units with f=50, 64px:
        # projected pixel offset = f * (0.1 / 1.0) = 5px to the right.
        means = torch.tensor([[0.1, 0.0, 1.0]], dtype=torch.float32)
        quats = torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32)
        scales = torch.tensor([[0.08, 0.08, 0.08]], dtype=torch.float32)
        opacities = torch.tensor([[0.95]], dtype=torch.float32)
        colors = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)

        img, _ = render_gaussians(
            means, quats, scales, opacities, colors,
            self.viewmats, self.K, self.width, self.height,
        )
        r = img[0, 0].cpu()
        max_idx = torch.argmax(r).item()
        y, x = max_idx // self.width, max_idx % self.width
        self.assertLess(abs(x - (self.cx + 5)), 3)
        self.assertLess(abs(y - self.cy), 3)

    def test_renders_on_mps(self):
        if not torch.backends.mps.is_available():
            self.skipTest("MPS not available")
        means = torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float32, device="mps")
        quats = torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32, device="mps")
        scales = torch.tensor([[0.08, 0.08, 0.08]], dtype=torch.float32, device="mps")
        opacities = torch.tensor([[0.95]], dtype=torch.float32, device="mps")
        colors = torch.tensor([[1.0, 0.0, 0.3]], dtype=torch.float32, device="mps")
        img, _ = render_gaussians(
            means, quats, scales, opacities, colors,
            self.viewmats.to("mps"), self.K.to("mps"), self.width, self.height,
        )
        self.assertEqual(img.device.type, "mps")
        self.assertTrue(torch.isfinite(img).all())

    def test_gradients_flow_through_renderer(self):
        # Optimizing means toward the target image must produce usable gradients.
        means = torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float32, requires_grad=True)
        quats = torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32)
        scales = torch.tensor([[0.08, 0.08, 0.08]], dtype=torch.float32)
        opacities = torch.tensor([[0.95]], dtype=torch.float32)
        colors = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)

        img, _ = render_gaussians(
            means, quats, scales, opacities, colors,
            self.viewmats, self.K, self.width, self.height,
        )
        target = torch.zeros_like(img)
        target[0, 0, self.height // 2 - 2, self.width // 2 - 2] = 1.0
        loss = torch.nn.functional.l1_loss(img, target)
        loss.backward()
        self.assertIsNotNone(means.grad)
        self.assertTrue(torch.isfinite(means.grad).all())
        self.assertGreater(torch.abs(means.grad).sum(), 0.0)

    def test_mps_backprop(self):
        if not torch.backends.mps.is_available():
            self.skipTest("MPS not available")
        means = torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float32, device="mps", requires_grad=True)
        quats = torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32, device="mps")
        scales = torch.tensor([[0.08, 0.08, 0.08]], dtype=torch.float32, device="mps")
        opacities = torch.tensor([[0.95]], dtype=torch.float32, device="mps")
        colors = torch.tensor([[1.0, 0.0, 0.3]], dtype=torch.float32, device="mps")
        img, _ = render_gaussians(
            means, quats, scales, opacities, colors,
            self.viewmats.to("mps"), self.K.to("mps"), self.width, self.height,
        )
        target = torch.zeros_like(img)
        target[0, 0, self.height // 2 - 2, self.width // 2 - 2] = 1.0
        loss = torch.nn.functional.l1_loss(img, target)
        loss.backward()
        self.assertIsNotNone(means.grad)
        self.assertTrue(torch.isfinite(means.grad).all())

    def test_batch_rendering_multiple_cameras(self):
        n_cams = 2
        viewmats = identity = torch.eye(4, dtype=torch.float32).unsqueeze(0).repeat(n_cams, 1, 1)
        Ks = self.K.repeat(n_cams, 1, 1)
        means = torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float32)
        quats = torch.tensor([[1.0, 0.0, 0.0, 0.0]], dtype=torch.float32)
        scales = torch.tensor([[0.08, 0.08, 0.08]], dtype=torch.float32)
        opacities = torch.tensor([[0.95]], dtype=torch.float32)
        colors = torch.tensor([[0.0, 1.0, 0.0]], dtype=torch.float32)
        img, alpha = render_gaussians(
            means, quats, scales, opacities, colors,
            viewmats, Ks, self.width, self.height,
        )
        self.assertEqual(img.shape, (n_cams, 3, self.height, self.width))
        self.assertEqual(alpha.shape, (n_cams, self.height, self.width))
        # Green channel should dominate both camera renders.
        g = img[0, 1].cpu()
        self.assertGreater(float(g.flatten().max()), 0.8)

if __name__ == "__main__":
    unittest.main()