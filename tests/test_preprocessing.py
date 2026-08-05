import unittest
import numpy as np
from PIL import Image, ImageFilter
from preprocess_keyframes import (
    compute_laplacian_variance,
    filter_relative_motion_blur,
    normalize_linear_exposure
)

class TestPreprocessingPipeline(unittest.TestCase):
    def test_laplacian_variance_sharp_vs_blurred(self):
        # Create synthetic sharp grid image
        sharp_img = np.zeros((100, 100, 3), dtype=np.uint8)
        sharp_img[::10, :, :] = 255
        sharp_img[:, ::10, :] = 255
        
        # Create blurred version via PIL BoxBlur
        pil_sharp = Image.fromarray(sharp_img)
        pil_blurred = pil_sharp.filter(ImageFilter.BoxBlur(5))
        blurred_img = np.array(pil_blurred)
        
        sharp_var = compute_laplacian_variance(sharp_img)
        blurred_var = compute_laplacian_variance(blurred_img)
        
        self.assertTrue(sharp_var > blurred_var, f"{sharp_var} is not greater than {blurred_var}")

    def test_relative_motion_blur_filtering(self):
        # Sequence: sharp, sharp, whip-pan (blurred), sharp, sharp
        variances = [300.0, 320.0, 50.0, 310.0, 305.0]
        flags = filter_relative_motion_blur(variances, relative_drop_threshold=0.5)
        self.assertEqual(flags, [True, True, False, True, True])

    def test_linear_exposure_normalization(self):
        dark_img = np.ones((100, 100, 3), dtype=np.uint8) * 50
        norm_img = normalize_linear_exposure(dark_img, target_mean_luminance=128.0)
        norm_lum = 0.299 * norm_img[:, :, 0] + 0.587 * norm_img[:, :, 1] + 0.114 * norm_img[:, :, 2]
        self.assertAlmostEqual(np.mean(norm_lum), 128.0, delta=5.0)

if __name__ == '__main__':
    unittest.main()
