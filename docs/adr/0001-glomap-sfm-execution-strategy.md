# 1. GLOMAP Structure-from-Motion Execution Strategy

- **Status**: Accepted
- **Date**: 2026-08-03

## Context and Problem Statement
SplatCat requires fast, accurate 6DoF camera pose estimation from video keyframes or unposed image sequences. Traditional incremental COLMAP is robust but slow (taking minutes to hours). GLOMAP provides up to 10–100x faster global SfM, but requires C++ compilation against Ceres Solver and SQLite database files (`colmap.db`).

## Decision Drivers
- Permissive licensing (GLOMAP is BSD-3-Clause).
- Processing speed on Apple Silicon (M-series Mac).
- Reliability: seamless fallback if native `glomap` binary is missing.

## Considered Options
1. **CLI Process Invocation with Homebrew/Bundled Binary & OpenCV Fallback**: Wrap native `glomap` CLI invocation (`glomap mapper --database_path colmap.db`) with automatic fallback to light-weight feature matching if native binary is unavailable.
2. **Direct C++ FFI Bindings via Rust `cc` / `bindgen`**: Compile GLOMAP into `splatcat-engine` as a static library.
3. **Pure Python COLMAP wrapper**: Call `pycolmap`.

## Decision Outcome
Chosen option: **Option 1 (CLI Process Invocation + Dual Pipeline Fallback)**.

### Positives
- Avoids complex C++ build matrix setup inside Rust `cargo build`.
- Preserves permissive BSD-3-Clause licensing.
- Allows user to install official Homebrew `colmap` / `glomap` packages while providing an immediate zero-dependency fallback for rapid testing.
