import unittest
import numpy as np
import torch

def compute_depth_supervision_loss(rendered_depth: torch.Tensor, predicted_depth: torch.Tensor) -> torch.Tensor:
    """
    Computes depth supervision loss between rendered 3DGS depth map
    and predicted monocular depth map (Depth Anything V2).
    Both depth maps are normalized to [0.0, 1.0] before L1 loss.
    """
    rend_min, rend_max = rendered_depth.min(), rendered_depth.max()
    pred_min, pred_max = predicted_depth.min(), predicted_depth.max()
    
    if (rend_max - rend_min) > 1e-6:
        norm_rendered = (rendered_depth - rend_min) / (rend_max - rend_min)
    else:
        norm_rendered = rendered_depth
        
    if (pred_max - pred_min) > 1e-6:
        norm_predicted = (predicted_depth - pred_min) / (pred_max - pred_min)
    else:
        norm_predicted = predicted_depth
        
    return torch.mean(torch.abs(norm_rendered - norm_predicted))

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
