import unittest
import torch
from train_3dgs_metal import compute_photometric_loss

def should_export_live_checkpoint(iteration: int, export_interval: int = 300, max_iterations: int = 3000) -> bool:
    """Returns True if current iteration is a live 3D viewport checkpoint export milestone."""
    if iteration <= 0:
        return False
    return (iteration % export_interval == 0) or (iteration == max_iterations)

class TestMetalEnginePipeline(unittest.TestCase):
    def test_photometric_loss_identical_images(self):
        img = torch.rand((3, 64, 64))
        loss = compute_photometric_loss(img, img.clone())
        self.assertAlmostEqual(loss.item(), 0.0, places=4)

    def test_photometric_loss_different_images(self):
        img1 = torch.zeros((3, 64, 64))
        img2 = torch.ones((3, 64, 64))
        loss = compute_photometric_loss(img1, img2)
        self.assertTrue(loss.item() > 0.0)

    def test_live_checkpoint_export_milestones(self):
        self.assertTrue(should_export_live_checkpoint(300))
        self.assertTrue(should_export_live_checkpoint(600))
        self.assertTrue(should_export_live_checkpoint(3000))
        self.assertFalse(should_export_live_checkpoint(150))
        self.assertFalse(should_export_live_checkpoint(0))

if __name__ == '__main__':
    unittest.main()
