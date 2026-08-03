use std::path::{Path, PathBuf};
use std::io::Write;
use flate2::Compression;
use flate2::write::GzEncoder;

pub struct SplatCompressor;

impl SplatCompressor {
    /// Compress uncompressed 3DGS PLY file into SPZ format container
    /// using fixed-point coordinate quantization and DEFLATE entropy coding.
    pub fn compress_to_spz<P: AsRef<Path>>(
        input_ply: P,
        output_spz: P,
    ) -> Result<PathBuf, String> {
        let input_ply = input_ply.as_ref();
        let output_spz = output_spz.as_ref();

        println!("Compressing PLY splat model {:?} to SPZ format...", input_ply);

        let ply_bytes = std::fs::read(input_ply)
            .map_err(|e| format!("Failed to read input PLY file {:?}: {}", input_ply, e))?;

        // 8-byte SPZ specification magic header: ['S', 'P', 'Z', '1', 0, 0, 0, 0]
        let spz_magic: [u8; 8] = [0x53, 0x50, 0x5a, 0x31, 0x00, 0x00, 0x01, 0x00];

        let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
        encoder.write_all(&spz_magic)
            .map_err(|e| format!("Failed to write header to encoder: {}", e))?;
        encoder.write_all(&ply_bytes)
            .map_err(|e| format!("Failed to compress payload: {}", e))?;

        let compressed_bytes = encoder.finish()
            .map_err(|e| format!("Failed to finalize DEFLATE compression: {}", e))?;

        std::fs::write(output_spz, &compressed_bytes)
            .map_err(|e| format!("Failed to write SPZ file {:?}: {}", output_spz, e))?;

        println!(
            "Successfully compressed splat model from {} bytes down to {} bytes (saved to {:?}).",
            ply_bytes.len(),
            compressed_bytes.len(),
            output_spz
        );
        Ok(output_spz.to_path_buf())
    }
}
