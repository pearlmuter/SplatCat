# 3. SPZ Quantization & Compression Format Integration

- **Status**: Accepted
- **Date**: 2026-08-03

## Context and Problem Statement
Uncompressed 3D Gaussian Splat PLY files range from 50MB to 500MB, causing slow web loading over networks. The SPZ format (created by Scaniverse/Niantic) reduces file sizes by up to 90% (5MB to 30MB) using coordinate fixed-point quantization, log-scale quantization, small-three quaternion encoding, and DEFLATE compression.

## Decision Drivers
- MIT permissively licensed (`nianticlabs/spz`).
- Fast web decompression in JavaScript/WebGPU inside `packages/web-viewer/`.
- Native Rust compression writer in `splatcat-engine`.

## Considered Options
1. **Native Rust SPZ Encoder (`splatcat-engine`)**: Implemented directly in `splat_compressor.rs` using fixed-point quantization and `flate2` DEFLATE crate.
2. **C++ `libspz` FFI binding**: Wrap `spz.h` via C++ FFI.
3. **Web Worker Decompressor**: Client-side JS decompression only.

## Decision Outcome
Chosen option: **Option 1 (Native Rust SPZ Encoder)** paired with Web Worker browser decompressor in `viewer.js`.

### Positives
- No external C++ static library build steps required in Rust workspace.
- 100% MIT permissively licensed.
- Web viewer can load `.spz`, `.ply`, and `.splat` formats transparently.
