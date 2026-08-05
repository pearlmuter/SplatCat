import unittest
import torch
from train_3dgs_metal import compute_depth_supervision_loss

class TestDepthSupervision(unittest.TestCase):
    def test_identical_depth_maps_zero_loss(self):
        depth_a = torch.linspace(0.1, 2.0, steps=100).reshape(10, 10)
        depth_b = depth_a.clone()
        loss = compute_depth_supervision_loss(depth_a, depth_b)
        self.assertAlmostEqual(loss.item(), 0.0, places=5)

    def test_different_depth_maps_positive_loss(self):
        depth_a = torch.ones((10, 10)) * 1.0
        depth_b = torch.ones((10, 10)) * 5.0
        depth_b[0, 0] = 0.0 # scale difference
        loss = compute_depth_supervision_loss(depth_a, depth_b)
        self.assertTrue(loss.item() > 0.0)

if __name__ == '__main__':
    unittest.main()
