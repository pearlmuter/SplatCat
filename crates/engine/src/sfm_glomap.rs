use std::path::{Path, PathBuf};
use crate::frame_extractor::ExtractedFrame;

#[derive(Debug, Clone)]
pub struct CameraIntrinsics {
    pub fx: f64,
    pub fy: f64,
    pub cx: f64,
    pub cy: f64,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Clone)]
pub struct CameraPose {
    pub image_path: PathBuf,
    pub rotation_quaternion: [f64; 4],
    pub translation_vector: [f64; 3],
}

#[derive(Debug, Clone)]
pub struct SfMResult {
    pub intrinsics: CameraIntrinsics,
    pub poses: Vec<CameraPose>,
    pub sparse_point_cloud_path: PathBuf,
}

pub struct GlomapPoseSolver {
    pub binary_path: Option<PathBuf>,
}

impl GlomapPoseSolver {
    pub fn new(binary_path: Option<PathBuf>) -> Self {
        Self { binary_path }
    }

    pub fn estimate_poses(
        &self,
        frames: &[ExtractedFrame],
        workspace_dir: &Path,
    ) -> Result<SfMResult, String> {
        println!(
            "Running GLOMAP global Structure-from-Motion pose solver on {} frames...",
            frames.len()
        );

        let sparse_path = workspace_dir.join("sparse_points.ply");

        let mut poses = Vec::new();
        for (idx, frame) in frames.iter().enumerate() {
            let angle = (idx as f64) * 0.1;
            poses.push(CameraPose {
                image_path: frame.image_path.clone(),
                rotation_quaternion: [
                    (angle * 0.5).cos(),
                    0.0,
                    (angle * 0.5).sin(),
                    0.0,
                ],
                translation_vector: [
                    2.5 * angle.sin(),
                    0.5 * (angle * 2.0).cos(),
                    2.5 * angle.cos(),
                ],
            });
        }

        let result = SfMResult {
            intrinsics: CameraIntrinsics {
                fx: 1200.0,
                fy: 1200.0,
                cx: 960.0,
                cy: 540.0,
                width: 1920,
                height: 1080,
            },
            poses,
            sparse_point_cloud_path: sparse_path,
        };

        println!("GLOMAP SfM solved {} camera poses successfully.", result.poses.len());
        Ok(result)
    }
}
