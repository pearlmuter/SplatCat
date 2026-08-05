import unittest
import torch
import os

def compute_photometric_reconstruction_loss(rendered_img: torch.Tensor, target_img: torch.Tensor, lambda_ssim: float = 0.2) -> torch.Tensor:
    """
    Computes combined L1 + SSIM photometric reconstruction loss.
    L_total = (1 - lambda_ssim) * L1 + lambda_ssim * (1 - SSIM)
    """
    l1_loss = torch.mean(torch.abs(rendered_img - target_img))
    
    # Simplified structural similarity proxy for fast TDD verification
    c1, c2 = 0.01**2, 0.03**2
    mu_x, mu_y = torch.mean(rendered_img), torch.mean(target_img)
    sigma_x, sigma_y = torch.var(rendered_img), torch.var(target_img)
    sigma_xy = torch.mean((rendered_img - mu_x) * (target_img - mu_y))
    
    ssim = ((2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)) / ((mu_x**2 + mu_y**2 + c1) * (sigma_x + sigma_y + c2))
    ssim_loss = 1.0 - ssim
    
    return (1.0 - lambda_ssim) * l1_loss + lambda_ssim * ssim_loss

def should_export_live_checkpoint(iteration: int, export_interval: int = 300, max_iterations: int = 3000) -> bool:
    """Returns True if current iteration is a live 3D viewport checkpoint export milestone."""
    if iteration <= 0:
        return False
    return (iteration % export_interval == 0) or (iteration == max_iterations)

class TestMetalEnginePipeline(unittest.TestCase):
    def test_photometric_loss_identical_images(self):
        img = torch.rand((3, 64, 64))
        loss = compute_photometric_reconstruction_loss(img, img.clone())
        self.assertAlmostEqual(loss.item(), 0.0, places=4)

    def test_photometric_loss_different_images(self):
        img1 = torch.zeros((3, 64, 64))
        img2 = torch.ones((3, 64, 64))
        loss = compute_photometric_reconstruction_loss(img1, img2)
        self.assertTrue(loss.item() > 0.0)

    def test_live_checkpoint_export_milestones(self):
        self.assertTrue(should_export_live_checkpoint(300))
        self.assertTrue(should_export_live_checkpoint(600))
        self.assertTrue(should_export_live_checkpoint(3000))
        self.assertFalse(should_export_live_checkpoint(150))
        self.assertFalse(should_export_live_checkpoint(0))

if __name__ == '__main__':
    unittest.main()
