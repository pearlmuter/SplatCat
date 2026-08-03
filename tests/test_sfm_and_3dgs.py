#!/usr/bin/env python3
import os
import unittest
import numpy as np
import torch

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

    def test_ply_file_integrity(self):
        """Verify PLY file header structure and property count."""
        ply_path = "packages/web-viewer/real_livingroom.ply"
        self.assertTrue(os.path.exists(ply_path), "real_livingroom.ply must exist in packages/web-viewer/")
        
        with open(ply_path, "r") as f:
            header_lines = []
            for line in f:
                line_str = line.strip()
                header_lines.append(line_str)
                if line_str == "end_header":
                    break
        
        self.assertIn("ply", header_lines[0])
        self.assertIn("format ascii 1.0", header_lines[1])
        vertex_element_found = any("element vertex" in line for line in header_lines)
        self.assertTrue(vertex_element_found, "PLY header must define 'element vertex'")

if __name__ == "__main__":
    unittest.main()
