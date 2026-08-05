#!/usr/bin/env python3
"""
SplatCat quality metrics (single source of truth).

Used by both the pipeline evaluator (auto_evaluate_pipeline.py) and the
photometric trainer (train_photometric.py) so the acceptance-bar score and
the training loss share one consistent estimator.

SSIM is the single-window approximation with population (biased) variance
so an image compared with itself scores exactly 1.0.
"""

import math

import numpy as np
import torch


def compute_psnr(a, b):
    """Peak Signal-to-Noise Ratio between two images in float [0,1] range."""
    if not isinstance(a, torch.Tensor):
        a = torch.tensor(np.asarray(a, dtype=np.float32))
    if not isinstance(b, torch.Tensor):
        b = torch.tensor(np.asarray(b, dtype=np.float32))
    mse = torch.mean((a - b) ** 2)
    if mse == 0:
        return float("inf")
    return float(10.0 * math.log10(1.0 / float(mse)))


def compute_ssim(a, b):
    """Structural Similarity between two images (single-window approximation).

    Uses population variance (unbiased=False) so identical inputs score 1.0.
    """
    if not isinstance(a, torch.Tensor):
        a = torch.tensor(np.asarray(a, dtype=np.float32))
    if not isinstance(b, torch.Tensor):
        b = torch.tensor(np.asarray(b, dtype=np.float32))
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    mu_a, mu_b = torch.mean(a), torch.mean(b)
    var_a, var_b = torch.var(a, unbiased=False), torch.var(b, unbiased=False)
    cov = torch.mean((a - mu_a) * (b - mu_b))
    ssim = ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / \
           ((mu_a ** 2 + mu_b ** 2 + c1) * (var_a + var_b + c2))
    return torch.clamp(ssim, 0.0, 1.0)
