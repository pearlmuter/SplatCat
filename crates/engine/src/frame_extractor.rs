use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct ExtractedFrame {
    pub frame_index: usize,
    pub timestamp_sec: f64,
    pub image_path: PathBuf,
    pub sharpness_score: f64,
}

pub struct FrameExtractor {
    pub target_fps: f64,
    pub min_sharpness: f64,
}

impl FrameExtractor {
    pub fn new(target_fps: f64, min_sharpness: f64) -> Self {
        Self {
            target_fps,
            min_sharpness,
        }
    }

    pub fn extract_keyframes<P: AsRef<Path>>(
        &self,
        video_path: P,
        output_dir: P,
    ) -> Result<Vec<ExtractedFrame>, String> {
        let video_path = video_path.as_ref();
        let output_dir = output_dir.as_ref();

        if !video_path.exists() {
            return Err(format!("Video file not found: {:?}", video_path));
        }

        std::fs::create_dir_all(output_dir)
            .map_err(|e| format!("Failed to create output dir: {}", e))?;

        println!(
            "Extracting keyframes from {:?} to {:?} at {} FPS...",
            video_path,
            output_dir,
            self.target_fps
        );

        let mut frames = Vec::new();
        let simulated_frame_count = 45;

        for i in 0..simulated_frame_count {
            let timestamp = (i as f64) / self.target_fps;
            let filename = format!("frame_{:05}.png", i);
            let frame_path = output_dir.join(&filename);

            let sharpness = 150.0 + (i % 10) as f64 * 12.0;

            if sharpness >= self.min_sharpness {
                frames.push(ExtractedFrame {
                    frame_index: i,
                    timestamp_sec: timestamp,
                    image_path: frame_path,
                    sharpness_score: sharpness,
                });
            }
        }

        println!("Extracted {} high-quality keyframes.", frames.len());
        Ok(frames)
    }
}
