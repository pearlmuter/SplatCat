# PRD 0003: Working End-to-End SplatCat Pipeline

## Problem Statement

The point of SplatCat is to make 3D Gaussian Splats easily: drop a video into the Mac app, get a photorealistic, shareable 3D model out. Today that promise is broken at the core. The training step (`train_3dgs_metal.py`) never performs real photometric optimization — it never reads a keyframe, never renders Gaussians to an image, and optimizes synthetic regularizers (positions pulled toward the origin, z tugged toward 1.5) instead of an $L_1 + L_{\text{SSIM}}$ reconstruction loss against the camera views. The result is a densified sparse point cloud with k-NN scales, not a trained splat model.

Separately, the viewport has regressed: a reconstruction of a living-room corner renders as a cyan stripe of giant flat squares. The recent per-splat scale-preservation work left the viewer's PLY parser inconsistent with the writer's attribute encoding — per-splat scales are parsed but then discarded, and the shader misinterprets the encoded attributes. The monocular depth stage is also a placeholder: it applies a luminance/y-gradient heuristic, not the Depth Anything V2 depth prior the architecture claims.

The user sees: a "photorealistic 3DGS suite" whose own test scene comes out wrong.

## Solution

SplatCat converts a dropped-in video into a photorealistic 3D Gaussian Splat model, end-to-end, and the Mac app's web viewport renders it truthfully.

- The training stage performs real differentiable photometric optimization on Apple Silicon Metal GPUs: keyframes, camera poses, and intrinsics from SfM feed a differentiable rasterizer (e.g. gsplat on MPS), which renders Gaussians to images and minimizes $0.8 L_1 + 0.2 L_{\text{SSIM}}$ against the captured keyframes, per ADR 0005.
- The PLY attribute contract between the trainer and the viewer is locked and honored on both sides: log-scale conventions, Spherical Harmonic DC color layout, opacity domain, and quaternion ordering. The viewer renders per-splat scales it is given instead of discarding them.
- The monocular depth prior is either made real (a true monocular depth network producing per-keyframe relative depth maps) or explicitly dropped, and its loss wired through the renderer per ADR 0006.
- Output quality is judged by the acceptance bar defined for the living-room reference scene — not by point counts.

## User Stories

1. As a SplatCat user, I want to drag a video of a room into the Mac app, so that a 3D Gaussian Splat model of that room comes out without me configuring anything.
2. As a SplatCat user, I want the output model to look like the room I filmed, so that the app is actually useful for capturing spaces.
3. As a SplatCat user, I want solid walls and floors in the reconstruction, so that the model doesn't look like a cloud of floating points.
4. As a SplatCat user, I want colors in the reconstructed model to match the video, so that the result is photorealistic rather than smeared or swapped.
5. As a SplatCat user, I want the splats to render at their true sizes, so that the scene doesn't collapse into huge flat squares or a cyan stripe.
6. As a SplatCat user, I want to open the produced model in the web viewport, so that I can inspect, rotate, and share it.
7. As a SplatCat user, I want the training step to visibly improve the model over the raw sparse points, so that waiting for training is worth it.
8. As a SplatCat user, I want training to complete in a reasonable time on Apple Silicon, so that the workflow feels like "drop a video, get a model."
9. As a SplatCat user, I want to know whether the output is good, so that I can decide whether to re-shoot rather than guess.
10. As a SplatCat user, I want pause/resume of the training process to keep working, so that I can reclaim the GPU when needed.
11. As a SplatCat developer, I want the trainer to actually load keyframes and camera poses, so that photometric loss is computed against real views.
12. As a SplatCat developer, I want one authoritative PLY attribute contract shared by writer and viewer, so that attribute mismatches cannot silently regress rendering.
13. As a SplatCat developer, I want a synthetic-scene renderer test, so that training correctness is verifiable without filming anything.
14. As a SplatCat developer, I want the pipeline evaluator to judge quality by image metrics, so that "passed" means the model looks right, not just that it has enough points.
15. As a SplatCat developer, I want the depth stage to be honestly either real or absent, so that the codebase doesn't claim a depth prior it doesn't have.
16. As a SplatCat developer, I want the acceptance bar for the living-room scene defined up front, so that every training change is judged against the same yardstick.
17. As a SplatCat developer, I want existing pure-function tests preserved, so that the loss math and preprocessing behavior remain pinned while the pipeline changes.
18. As a SplatCat user, I want the iOS-companion capture path unaffected by these changes, so that the capture app keeps working even though this effort is video-only.

## Implementation Decisions

- **Real differentiable renderer in the Python pipeline**: introduce an MPS-capable differentiable rasterizer (gsplat MPS backend, or an equivalent torch-based forward pass) driven from the existing COLMAP sparse model and keyframes. This supersedes the earlier Rust/wgpu Brush direction (ADR 0002) for this effort; the Python pipeline remains the canonical path.
- **Training driver reads its inputs**: the optimizer must consume the keyframe images (currently never read), the COLMAP camera poses and intrinsics (6-DoF extrinsics + focal length/principal point), and the sparse SfM points as the initial Gaussian configuration.
- **Photometric loss per ADR 0005**: minimize $0.8 L_1 + 0.2 L_{\text{SSIM}}$ between rendered and captured keyframes through the differentiable renderer, with adaptive Gaussian splitting/cloning/pruning as density control (added if the chosen renderer supports it in its first cut).
- **PLY attribute contract (the one new seam)**: a single canonical attribute layout, verified by a contract validator that parses PLY exactly as the viewer's rules require — Spherical Harmonic DC coefficients (SH → RGB via $C_0 = 0.28209479177387814$), log-scale per-splat scales, opacity, and quaternion ordering. The trainer writer and the viewer parser both conform to it; per-splat scales must survive the round trip and be consumed by the viewport.
- **Viewer regression fix**: the cyan-stripe/giant-square rendering must render truthful splats — per-splat scales applied, attribute indices aligned with the locked contract. This is the first implementation work, since training quality is unjudgeable through a broken viewer.
- **Depth prior decision: EXPLICITLY DROPPED in this cut** (resolved via ticket #24): the differentiable renderer has no depth output mode, so no depth supervision loss could be wired through it (ADR 0006's claims stay future work). The Mac app no longer invokes the fake luminance/gradient depth stage; `estimate_depth_maps.py` is an honest no-op documenting how to make the prior real (depth rendering mode in the rasterizer + scale-normalized $L_1$); `train_photometric` warns and ignores any `--depth_dir`.
- **Acceptance bar**: the living-room corner video is the canonical reference scene. Quality is measured by rendered-vs-keyframe image metrics (e.g. PSNR/SSIM) plus a visual checklist; the pass/fail rule is recorded before implementation begins.
- **Pipeline evaluator**: `auto_evaluate_pipeline.py` passes only when the output clears the acceptance bar; point-count thresholds alone no longer constitute success.
- **App wiring unchanged**: the Mac app's stage orchestration (ffmpeg extraction, preprocessing, SfM, training, export) stays as-is; only the training stage's internals, the depth stage, and the viewer's parsing/rendering change.

## Testing Decisions

- A good test exercises external behavior — a PLY file round-trips through the contract validator with correct scales/colors/rotation, or a known Gaussian configuration renders to an expected image — never internal optimizer bookkeeping.
- **PLY contract validator** (new): writer output parsed under the viewer's exact rules must recover positions, colors (SH DC → RGB), log-scales, opacity, and quaternions within tolerance; an intentionally corrupted attribute must be rejected or flagged.
- **Synthetic-scene renderer test** (new): a small known Gaussian scene rendered through the differentiable rasterizer must produce an image close to a reference render, and the photometric loss must decrease when optimizing toward a target image.
- **Existing seams preserved**: the pure-function tests in the current suite (photometric loss math, preprocessing, depth-supervision loss, webgpu detection, image capping, SfM parsing) remain the prior art and stay green.
- Modules tested: the training driver (through the synthetic renderer test), the PLY contract validator, and the existing pipeline modules via their current tests.

## Out of Scope

- iOS AR streaming capture path (separate effort; the iOS app must simply keep working).
- Native Rust/wgpu Brush engine migration.
- HTML/SPZ export and sharing verification (assumed working unless the route breaks it).
- Viewport 60 FPS performance tuning at high splat counts (revisit once training produces dense models).
- Preprocessing threshold retuning (adaptive sharpness/exposure) beyond what the living-room scene exposes.

## Further Notes

- Domain vocabulary per CONTEXT.md: Keyframe, Camera Pose (extrinsics vs intrinsics), Gaussian Splat, Structure-from-Motion, SPZ Compression.
- This PRD is the synthesized destination of the wayfinder map "Working End-to-End SplatCat Pipeline" (GitHub issue #14); its child tickets ("Diagnose cyan-stripe viewer regression and lock the PLY attribute contract", "Select the MPS differentiable renderer and design the training driver", "Define the photorealistic acceptance bar for the living-room scene", "Decide depth-supervision wiring and priority in the first training cut") carry the per-decision detail.
- ADR 0005 (Differentiable Camera Pinhole Photometric Reconstruction Loss) and ADR 0006 (Monocular Depth Supervision Loss for Textureless Surfaces) are respected; this effort makes their claims true in code.
- The existing depth module is a synthetic luminance/gradient heuristic; this PRD forces an honest decision (real network or explicit drop) rather than a silent placeholder.
