use std::path::{Path, PathBuf};
use std::process::Command;
use std::fs;

#[derive(Debug, Clone)]
pub struct CameraPose {
    pub image_id: u32,
    pub image_name: String,
    pub qvec: [f64; 4], // w, x, y, z
    pub tvec: [f64; 3], // x, y, z
    pub camera_id: u32,
}

#[derive(Debug, Clone)]
pub struct Point3D {
    pub id: u64,
    pub xyz: [f64; 3],
    pub rgb: [u8; 3],
    pub error: f64,
}

pub struct ColmapRunner {
    pub colmap_binary: PathBuf,
}

impl ColmapRunner {
    pub fn new() -> Self {
        let default_path = PathBuf::from("/opt/homebrew/bin/colmap");
        let binary = if default_path.exists() {
            default_path
        } else {
            PathBuf::from("colmap")
        };
        Self { colmap_binary: binary }
    }

    pub fn run_sfm_pipeline(
        &self,
        images_dir: &Path,
        workspace_dir: &Path,
    ) -> Result<PathBuf, String> {
        let db_path = workspace_dir.join("database.db");
        let sparse_dir = workspace_dir.join("sparse");

        fs::create_dir_all(&sparse_dir)
            .map_err(|e| format!("Failed to create sparse output directory: {}", e))?;

        // Step 1: Feature Extraction
        println!("[SplatCat SfM] Running COLMAP feature_extractor...");
        let feat_status = Command::new(&self.colmap_binary)
            .arg("feature_extractor")
            .arg("--database_path")
            .arg(&db_path)
            .arg("--image_path")
            .arg(images_dir)
            .arg("--ImageReader.camera_model")
            .arg("OPENCV")
            .status()
            .map_err(|e| format!("Failed to run colmap feature_extractor: {}", e))?;

        if !feat_status.success() {
            return Err("COLMAP feature_extractor failed".into());
        }

        // Step 2: Sequential Matching (Optimized for ordered video frames)
        println!("[SplatCat SfM] Running COLMAP sequential_matcher...");
        let match_status = Command::new(&self.colmap_binary)
            .arg("sequential_matcher")
            .arg("--database_path")
            .arg(&db_path)
            .status()
            .map_err(|e| format!("Failed to run colmap sequential_matcher: {}", e))?;

        if !match_status.success() {
            return Err("COLMAP sequential_matcher failed".into());
        }

        // Step 3: Sparse Reconstruction (Mapper / Bundle Adjustment)
        println!("[SplatCat SfM] Running COLMAP mapper (Bundle Adjustment)...");
        let mapper_status = Command::new(&self.colmap_binary)
            .arg("mapper")
            .arg("--database_path")
            .arg(&db_path)
            .arg("--image_path")
            .arg(images_dir)
            .arg("--output_path")
            .arg(&sparse_dir)
            .status()
            .map_err(|e| format!("Failed to run colmap mapper: {}", e))?;

        if !mapper_status.success() {
            return Err("COLMAP mapper failed".into());
        }

        let model_dir = sparse_dir.join("0");
        if !model_dir.exists() {
            return Err("COLMAP model output directory sparse/0/ was not created".into());
        }

        // Step 4: Convert binary models to TXT for easy parsing if needed
        let txt_dir = sparse_dir.join("txt");
        let _ = fs::create_dir_all(&txt_dir);
        let _ = Command::new(&self.colmap_binary)
            .arg("model_converter")
            .arg("--input_path")
            .arg(&model_dir)
            .arg("--output_path")
            .arg(&txt_dir)
            .arg("--output_type")
            .arg("TXT")
            .status();

        Ok(model_dir)
    }
}
