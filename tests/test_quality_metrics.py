#!/usr/bin/env python3
import unittest
import numpy as np
from auto_evaluate_pipeline import (
    compute_psnr,
    compute_ssim,
    evaluate_quality,
    score_trained_model,
    load_ply_tensors,
    ACCEPTANCE_BAR,
)
from tests.test_photometric_training import make_synthetic_colmap

class TestQualityMetrics(unittest.TestCase):

    def test_psnr_identical_images_is_infinite(self):
        img = np.full((8, 8, 3), 0.5, dtype=np.float32)
        self.assertTrue(np.isinf(compute_psnr(img, img)))

    def test_psnr_known_value(self):
        # MSE = (0.1)^2 across all channels/pixels, float range [0,1] -> PSNR = 20
        a = np.zeros((8, 8, 3), dtype=np.float32)
        b = np.full((8, 8, 3), 0.1, dtype=np.float32)
        self.assertAlmostEqual(compute_psnr(a, b), 20.0, places=4)

    def test_psnr_tensor_input(self):
        import torch
        a = torch.zeros((8, 8, 3))
        b = torch.full((8, 8, 3), 0.1)
        self.assertAlmostEqual(compute_psnr(a, b), 20.0, places=4)

    def test_ssim_identical_is_one(self):
        img = np.random.RandomState(0).rand(16, 16, 3).astype(np.float32)
        self.assertAlmostEqual(compute_ssim(img, img), 1.0, places=5)

    def test_ssim_different_is_below_one(self):
        a = np.zeros((16, 16, 3), dtype=np.float32)
        b = np.ones((16, 16, 3), dtype=np.float32)
        self.assertLess(compute_ssim(a, b), 1.0)
        self.assertGreater(compute_ssim(a, b), 0.0)

    def test_evaluate_quality_passes_identical(self):
        img = np.random.RandomState(1).rand(16, 16, 3).astype(np.float32)
        result = evaluate_quality([img], [img.copy()])
        self.assertTrue(result["passed"])
        self.assertIn("psnr", result)
        self.assertIn("ssim", result)

    def test_evaluate_quality_fails_black_vs_white(self):
        black = np.zeros((16, 16, 3), dtype=np.float32)
        white = np.ones((16, 16, 3), dtype=np.float32)
        result = evaluate_quality([black], [white])
        self.assertFalse(result["passed"])

    def test_acceptance_bar_has_recorded_thresholds(self):
        self.assertIn("psnr_min", ACCEPTANCE_BAR)
        self.assertIn("ssim_min", ACCEPTANCE_BAR)
        self.assertIsInstance(ACCEPTANCE_BAR["psnr_min"], (int, float))

    def test_multiple_views_averaged(self):
        rng = np.random.RandomState(2)
        a = rng.rand(16, 16, 3).astype(np.float32)
        b = rng.rand(16, 16, 3).astype(np.float32)
        result = evaluate_quality([a, b], [a.copy(), b.copy()])
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["per_view"]), 2)

    def test_score_trained_model_on_synthetic_scene(self):
        import tempfile, os
        from train_photometric import train_photometric
        with tempfile.TemporaryDirectory() as tmp:
            sparse, frames, points = make_synthetic_colmap(tmp)
            output_ply = os.path.join(tmp, "model.ply")
            train_photometric(
                sparse, frames, output_ply,
                iterations=120,
                init_points=[np.array(p) for p, _ in points.values()],
                init_colors=[np.array(c) for _, c in points.values()],
                width=64, height=64,
            )
            result = score_trained_model(output_ply, sparse, frames)
        self.assertIn("psnr", result)
        self.assertIn("ssim", result)
        self.assertGreater(result["psnr"], 10.0)
        self.assertGreater(result["ssim"], 0.3)
        self.assertGreaterEqual(len(result["per_view"]), 1)

    def test_load_ply_tensors_returns_render_ready_shapes(self):
        import tempfile, os
        from train_3dgs_metal import write_3dgs_ply
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "model.ply")
            n = 4
            xyz = np.zeros((n, 3))
            sh = np.full((n, 3), 0.5)  # gray in SH space -> (0.5*C0+0.5) RGB
            op = np.full((n, 1), 0.9)
            sc = np.full((n, 3), -3.0)  # log-scale
            quat = np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (n, 1))
            write_3dgs_ply(path, xyz, sh, op, sc, quat)
            params = load_ply_tensors(path)
        self.assertEqual(params["means"].shape, (4, 3))
        self.assertEqual(params["colors"].shape, (4, 3))
        self.assertEqual(params["opacities"].shape, (4, 1))
        self.assertEqual(params["scales"].shape, (4, 3))
        self.assertEqual(params["quats"].shape, (4, 4))
        # log-scale -3 -> exp = ~0.0498
        self.assertAlmostEqual(float(params["scales"][0, 0]), np.exp(-3.0), places=4)

if __name__ == "__main__":
    unittest.main()