pub mod frame_extractor;
pub mod sfm_glomap;
pub mod splat_trainer;
pub mod splat_compressor;
pub mod live_stream_server;

pub use frame_extractor::FrameExtractor;
pub use sfm_glomap::GlomapPoseSolver;
pub use splat_trainer::SplatTrainer;
pub use splat_compressor::SplatCompressor;
pub use live_stream_server::LiveStreamServer;

#[derive(Debug, Clone)]
pub struct ProcessingProgress {
    pub stage: String,
    pub progress_pct: f32,
    pub current_iteration: u32,
    pub total_iterations: u32,
    pub active_splats: usize,
    pub fps: f32,
}
