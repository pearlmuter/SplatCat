use std::path::PathBuf;
use splatcat_engine::{FrameExtractor, GlomapPoseSolver, SplatTrainer, SplatCompressor, LiveStreamServer};

fn main() {
    println!("Starting SplatCat macOS Desktop Engine Core v0.1.0...");

    let live_server = LiveStreamServer::new(8765);
    if let Err(e) = live_server.start_listening(|payload| {
        println!("Received iOS AR frame #{} timestamp={}", payload.frame_id, payload.timestamp);
    }) {
        eprintln!("Failed to start live stream server: {}", e);
    }

    println!("SplatCat Desktop Core initialized successfully.");
}

pub fn run_video_pipeline(video_path: PathBuf, output_dir: PathBuf) -> Result<PathBuf, String> {
    println!("Processing video file {:?}...", video_path);

    let extractor = FrameExtractor::new(2.0, 100.0);
    let frames_dir = output_dir.join("frames");
    let frames = extractor.extract_keyframes(&video_path, &frames_dir)?;

    let sfm_solver = GlomapPoseSolver::new(None);
    let sfm_result = sfm_solver.estimate_poses(&frames, &output_dir)?;

    let trainer = SplatTrainer::new(1000, 32.5);
    let ply_path = trainer.train_splat(&sfm_result, &output_dir, |prog| {
        println!("Stage: {} Progress: {:.1}%", prog.stage, prog.progress_pct);
    })?;

    let spz_path = output_dir.join("model.spz");
    let compressed_spz = SplatCompressor::compress_to_spz(&ply_path, &spz_path)?;

    Ok(compressed_spz)
}
