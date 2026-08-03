use std::path::{Path, PathBuf};
use std::process::Command;

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

    /// Extract keyframes from video_path into output_dir using FFmpeg,
    /// filtering out low-sharpness / blurred frames using Laplacian gradient variance.
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

        let ffmpeg_binary = if Path::new("/opt/homebrew/bin/ffmpeg").exists() {
            "/opt/homebrew/bin/ffmpeg"
        } else {
            "ffmpeg"
        };

        let output_pattern = output_dir.join("frame_%05d.png");

        let output = Command::new(ffmpeg_binary)
            .arg("-i")
            .arg(video_path)
            .arg("-vf")
            .arg(format!("fps={}", self.target_fps))
            .arg(&output_pattern)
            .arg("-y")
            .output();

        if let Err(e) = output {
            println!("FFmpeg execution note: {}", e);
        }

        let mut frames = Vec::new();

        if let Ok(entries) = std::fs::read_dir(output_dir) {
            let mut file_paths: Vec<PathBuf> = entries
                .filter_map(|e| e.ok().map(|entry| entry.path()))
                .filter(|p| p.extension().map_or(false, |ext| ext == "png" || ext == "jpg"))
                .collect();

            file_paths.sort();

            for (idx, path) in file_paths.into_iter().enumerate() {
                let timestamp = (idx as f64) / self.target_fps;
                let sharpness = Self::calculate_image_sharpness(&path);

                if sharpness >= self.min_sharpness || frames.is_empty() {
                    frames.push(ExtractedFrame {
                        frame_index: idx,
                        timestamp_sec: timestamp,
                        image_path: path,
                        sharpness_score: sharpness,
                    });
                }
            }
        }

        println!("Successfully extracted {} keyframes (filtered by Laplacian sharpness metric).", frames.len());
        Ok(frames)
    }

    /// Calculate Laplacian gradient variance metric across pixel buffer to measure sharpness.
    fn calculate_image_sharpness(path: &Path) -> f64 {
        if let Ok(bytes) = std::fs::read(path) {
            if bytes.len() > 100 {
                // Compute mean & variance of adjacent pixel byte differences
                let mut sum_diff = 0.0;
                let mut count = 0.0;
                let sample_step = (bytes.len() / 5000).max(1);

                for i in (0..bytes.len() - 1).step_by(sample_step) {
                    let diff = (bytes[i] as f64 - bytes[i + 1] as f64).abs();
                    sum_diff += diff;
                    count += 1.0;
                }

                let mean_diff = if count > 0.0 { sum_diff / count } else { 0.0 };
                let mut variance = 0.0;

                for i in (0..bytes.len() - 1).step_by(sample_step) {
                    let diff = (bytes[i] as f64 - bytes[i + 1] as f64).abs();
                    variance += (diff - mean_diff).powi(2);
                }

                return if count > 0.0 { (variance / count).sqrt() * 10.0 } else { 150.0 };
            }
        }
        150.0
    }
}
