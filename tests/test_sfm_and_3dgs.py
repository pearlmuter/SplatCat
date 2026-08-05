#!/usr/bin/env python3
import os
import tempfile
import unittest
import numpy as np
import torch
from train_3dgs_metal import write_3dgs_ply

class TestSplatCatPipeline(unittest.TestCase):

    def test_pytorch_mps_metal_gpu_availability(self):
        """Verify that PyTorch MPS (Apple Metal GPU) is available and functional."""
        self.assertTrue(torch.backends.mps.is_available(), "Apple Metal GPU (MPS) must be available on M-series Mac")
        device = torch.device("mps")
        tensor = torch.ones((10, 10), device=device)
        result = (tensor * 2.0).cpu().numpy()
        self.assertEqual(result[0, 0], 2.0, "Metal GPU tensor operations must compute correctly")

    def test_spherical_harmonics_normalization(self):
        """Verify Spherical Harmonics 0th-order color encoding/decoding."""
        c0 = 0.28209479177387814
        original_rgb = np.array([0.8, 0.5, 0.2], dtype=np.float32)
        
        # Encode RGB -> SH0
        sh_0 = (original_rgb - 0.5) / c0
        
        # Decode SH0 -> RGB
        decoded_rgb = np.clip(sh_0 * c0 + 0.5, 0.0, 1.0)
        np.testing.assert_allclose(decoded_rgb, original_rgb, rtol=1e-5, atol=1e-5)

    def test_3dgs_binary_ply_writer(self):
        """Test writing 3DGS binary PLY format file."""
        num_gaussians = 100
        xyz = np.random.randn(num_gaussians, 3).astype(np.float32)
        sh_dc = np.random.randn(num_gaussians, 3).astype(np.float32)
        opacities = np.ones((num_gaussians, 1), dtype=np.float32)
        scales = np.zeros((num_gaussians, 3), dtype=np.float32)
        quaternions = np.tile([1.0, 0.0, 0.0, 0.0], (num_gaussians, 1)).astype(np.float32)

        with tempfile.TemporaryDirectory() as tmpdir:
            ply_path = os.path.join(tmpdir, "test_model.ply")
            write_3dgs_ply(ply_path, xyz, sh_dc, opacities, scales, quaternions)

            self.assertTrue(os.path.exists(ply_path), "PLY output file must be created")
            self.assertGreater(os.path.getsize(ply_path), 500, "PLY file must contain valid header and binary data")

            with open(ply_path, "rb") as f:
                header = f.read(500).decode("ascii", errors="ignore")
                self.assertIn("element vertex 100", header)
                self.assertIn("property float f_dc_0", header)
                self.assertIn("property float rot_3", header)

if __name__ == "__main__":
    unittest.main()
