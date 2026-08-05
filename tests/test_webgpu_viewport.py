import unittest

def is_webgpu_supported_environment(user_agent: str, has_navigator_gpu: bool) -> bool:
    """Returns True if the runtime environment supports WebGPU compute shaders."""
    if not has_navigator_gpu:
        return False
    return True

def compute_gpu_sort_buffer_size(num_splats: int) -> int:
    """Calculates GPU VRAM buffer bytes required for parallel GPU Radix Sort (Key: float32, Value: uint32)."""
    bytes_per_splat = 8 # 4 bytes depth key + 4 bytes splat index
    return num_splats * bytes_per_splat

class TestWebGPUViewportPipeline(unittest.TestCase):
    def test_webgpu_feature_detection(self):
        self.assertTrue(is_webgpu_supported_environment("Mozilla/5.0 Safari/17.0", True))
        self.assertFalse(is_webgpu_supported_environment("Mozilla/5.0 Safari/14.0", False))

    def test_gpu_sort_buffer_allocation(self):
        # 1,000,000 splats require 8,000,000 bytes (8MB) of VRAM
        buf_size = compute_gpu_sort_buffer_size(1_000_000)
        self.assertEqual(buf_size, 8_000_000)

if __name__ == '__main__':
    unittest.main()
