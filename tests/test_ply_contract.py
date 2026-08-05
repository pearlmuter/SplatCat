#!/usr/bin/env python3
import os
import tempfile
import unittest
import numpy as np
from train_3dgs_metal import write_3dgs_ply, parse_ply_per_viewer_contract

C0 = 0.28209479177387814

def make_gaussians(n=8):
    xyz = np.random.RandomState(0).randn(n, 3).astype(np.float32) * 0.5
    rgb = np.random.RandomState(1).uniform(0.1, 0.9, size=(n, 3)).astype(np.float32)
    sh_dc = (rgb - 0.5) / C0
    opacities = np.full((n, 1), 1.7, dtype=np.float32)
    scales = np.random.RandomState(2).uniform(0.002, 0.02, size=(n, 3)).astype(np.float32)
    scales_log = np.log(scales)
    quaternions = np.tile([1.0, 0.0, 0.0, 0.0], (n, 1)).astype(np.float32)
    return xyz, sh_dc, opacities, scales_log, quaternions, rgb

class TestPlyContract(unittest.TestCase):

    def test_roundtrip_recovering_positions(self):
        xyz, sh_dc, op, sc_log, quat, _ = make_gaussians()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "model.ply")
            write_3dgs_ply(path, xyz, sh_dc, op, sc_log, quat)
            parsed = parse_ply_per_viewer_contract(path)
        np.testing.assert_allclose(parsed["xyz"], xyz, atol=1e-5)

    def test_roundtrip_recovering_rgb_colors(self):
        xyz, sh_dc, op, sc_log, quat, rgb = make_gaussians()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "model.ply")
            write_3dgs_ply(path, xyz, sh_dc, op, sc_log, quat)
            parsed = parse_ply_per_viewer_contract(path)
        np.testing.assert_allclose(parsed["rgb"], rgb, atol=1e-4)

    def test_roundtrip_recovering_log_scales(self):
        xyz, sh_dc, op, sc_log, quat, _ = make_gaussians()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "model.ply")
            write_3dgs_ply(path, xyz, sh_dc, op, sc_log, quat)
            parsed = parse_ply_per_viewer_contract(path)
        np.testing.assert_allclose(parsed["log_scales"], sc_log, atol=1e-4)

    def test_corrupted_opacity_flags_validator(self):
        xyz, sh_dc, op, sc_log, quat, _ = make_gaussians()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "model.ply")
            write_3dgs_ply(path, xyz, sh_dc, op, sc_log, quat)
            with open(path, "a") as f:
                f.write("garbage not a splat line\n")
            parsed = parse_ply_per_viewer_contract(path)
        self.assertIn("malformed_lines", parsed)
        self.assertEqual(parsed["malformed_lines"], 1)

    def test_known_good_ply_literal_index_alignment(self):
        # Hand-written PLY line: index 0..16 mapping per the viewer contract.
        # xyz=(1,2,3) nx..=(0,0,0) f_dc=(0.6,0.4,0.2) opacity=2.0
        # log_scales=(-2.0,-2.0,-2.0) rot=(1,0,0,0)
        ply_text = (
            "ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\n"
            "property float y\nproperty float z\nproperty float nx\nproperty float ny\n"
            "property float nz\nproperty float f_dc_0\nproperty float f_dc_1\n"
            "property float f_dc_2\nproperty float opacity\nproperty float scale_0\n"
            "property float scale_1\nproperty float scale_2\nproperty float rot_0\n"
            "property float rot_1\nproperty float rot_2\nproperty float rot_3\nend_header\n"
            "1 2 3 0 0 0 0.6 0.4 0.2 2.0 -2.0 -2.0 -2.0 1 0 0 0\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "known.ply")
            with open(path, "w") as f:
                f.write(ply_text)
            parsed = parse_ply_per_viewer_contract(path)
        np.testing.assert_allclose(parsed["xyz"][0], [1.0, 2.0, 3.0])
        np.testing.assert_allclose(parsed["rgb"][0], [0.6 * C0 + 0.5, 0.4 * C0 + 0.5, 0.2 * C0 + 0.5])
        np.testing.assert_allclose(parsed["log_scales"][0], [-2.0, -2.0, -2.0])
        np.testing.assert_allclose(parsed["quaternions"][0], [1.0, 0.0, 0.0, 0.0])
        self.assertEqual(parsed["opacity"][0], 2.0)
        self.assertEqual(parsed["malformed_lines"], 0)

if __name__ == "__main__":
    unittest.main()