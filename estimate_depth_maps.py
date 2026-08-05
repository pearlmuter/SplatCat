#!/usr/bin/env python3
"""
SplatCat Depth Stage — Explicitly DROPPED in this training cut (PRD 0003 T5 / ticket #24)

The architecture historically claimed a monocular depth prior
(Depth Anything V2, ADR 0006) but shipped a luminance/y-gradient heuristic
that never supervised anything: the differentiable renderer has no depth
output mode, so no depth loss could be wired through it. Per PRD 0003
("The monocular depth prior is either made real or explicitly dropped"),
this stage is now an honest no-op rather than a silent placeholder.

To make the depth prior REAL in a future cut, you need:
  1. A true per-keyframe relative depth network (e.g. Depth Anything V2).
  2. A depth rendering mode in gaussian_renderer.py (alpha-composited
     z-value per pixel, matching the RGB pass).
  3. A scale-normalized L1 depth loss wired into train_photometric().
Then un-drop this stage and feed the trainer's --depth_dir.
"""

import sys


def process_depth_maps_directory(frames_dir: str, output_depth_dir: str = None) -> int:
    """Explicitly dropped: returns 0 and produces no files."""
    print(f"[DepthEstimation] Depth stage explicitly dropped (PRD 0003 T5). "
          f"No depth maps generated for {frames_dir}.")
    return 0


if __name__ == '__main__':
    fdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/splatcat_run/frames"
    sys.exit(0 if process_depth_maps_directory(fdir) >= 0 else 1)
