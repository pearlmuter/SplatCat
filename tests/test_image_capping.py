#!/usr/bin/env python3
"""
Unit tests for keyframe image extraction capping (max 1000 images).
"""
import os
import sys
import unittest
import subprocess

class TestImageCapping(unittest.TestCase):
    def test_ffmpeg_vframes_cap_argument(self):
        """Verify that keyframe extraction includes -vframes 1000 parameter."""
        with open("build_mac_app.swift", "r") as f:
            content = f.read()
        self.assertIn("-vframes", content, "build_mac_app.swift must specify -vframes argument for FFmpeg keyframe extraction")
        self.assertIn("1000", content, "build_mac_app.swift must cap keyframe extraction to 1000 images maximum")

    def test_auto_evaluate_pipeline_cap_argument(self):
        """Verify auto_evaluate_pipeline.py includes -vframes 1000 parameter."""
        with open("auto_evaluate_pipeline.py", "r") as f:
            content = f.read()
        self.assertIn("-vframes", content, "auto_evaluate_pipeline.py must specify -vframes argument")
        self.assertIn("1000", content, "auto_evaluate_pipeline.py must cap keyframe extraction to 1000 images maximum")

if __name__ == "__main__":
    unittest.main()
