use splatcat_engine::{SplatCompressor, FrameExtractor, SplatTrainer, GlomapPoseSolver};
use std::fs::File;
use std::io::Write;

#[test]
fn test_spz_compression_header_and_deflate() {
    let tmp_dir = std::env::temp_dir();
    let ply_path = tmp_dir.join("test_input.ply");
    let spz_path = tmp_dir.join("test_output.spz");

    // Write dummy PLY data
    let dummy_ply_data = b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nend_header\n0 0 0\n";
    let mut file = File::create(&ply_path).expect("Failed to create dummy PLY file");
    file.write_all(dummy_ply_data).expect("Failed to write dummy PLY data");

    // Compress to SPZ
    let result = SplatCompressor::compress_to_spz(&ply_path, &spz_path);
    assert!(result.is_ok(), "SPZ compression should succeed");

    let compressed_bytes = std::fs::read(&spz_path).expect("Failed to read generated SPZ file");
    assert!(compressed_bytes.len() > 0, "Compressed SPZ file must not be empty");

    // Cleanup
    let _ = std::fs::remove_file(&ply_path);
    let _ = std::fs::remove_file(&spz_path);
}

#[test]
fn test_frame_extractor_instantiation() {
    let extractor = FrameExtractor::new(2.0, 10.0);
    assert_eq!(extractor.target_fps, 2.0);
    assert_eq!(extractor.min_sharpness, 10.0);
}

#[test]
fn test_splat_trainer_instantiation() {
    let trainer = SplatTrainer::new(500, 28.5);
    assert_eq!(trainer.max_iterations, 500);
    assert_eq!(trainer.target_psnr, 28.5);
}

#[test]
fn test_glomap_pose_solver_instantiation() {
    let solver = GlomapPoseSolver::new(None);
    assert!(solver.binary_path.is_none());
}

#[test]
fn test_colmap_runner_instantiation() {
    let runner = splatcat_engine::ColmapRunner::new();
    assert!(runner.colmap_binary.to_str().unwrap().contains("colmap"));
}
