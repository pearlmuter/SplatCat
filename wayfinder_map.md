# Wayfinder Map: SplatCat 3DGS Quality & UI Roadmap

## Notes
- **Domain**: SplatCat 3D Gaussian Splatting Suite
- **Skills**: `/wayfinder`, `/domain-modeling`

---

## native-nssavepanel: Native macOS NSSavePanel Dialog for HTML Export

Blocked by: None
Status: resolved
Type: Task

### Question
How to prompt the user with a native macOS file selection dialog (`NSSavePanel`) when exporting HTML packages, allowing them to choose the exact destination directory and filename instead of downloading silently to `~/Downloads`?

### Answer
By bridging `WKWebView` script message handling with macOS AppKit `NSSavePanel`:
1. Register script message handler `exportHtmlNative` with `config.userContentController.add(self, name: "exportHtmlNative")` in `build_mac_app.swift`.
2. In `userContentController(_:didReceive:)`, intercept `exportHtmlNative` messages containing HTML string content and suggested default filename (`splatcat_web_export.html`).
3. Instantiate `NSSavePanel`, configuring `title`, `nameFieldStringValue`, `canCreateDirectories = true`, and restricting `allowedContentTypes` to `.html`.
4. Present `savePanel.beginSheetModal(for: window)` on main thread. Upon approval (`.OK`), write the payload to `savePanel.url` using UTF-8 encoding.
5. Evaluate `window.splatcatOnExportComplete(success, pathOrError)` JS completion callback.
6. In `apps/desktop/app.js`, feature-detect `window.webkit.messageHandlers.exportHtmlNative` on `#btn-export-desktop` click to dispatch the message, retaining standard `Blob` / `<a>` download fallback for plain Web browser sessions.

---

## webgl-elliptical-shader: Custom WebGL 2D Elliptical Gaussian Fragment Shader

Blocked by: None
Status: resolved
Type: Prototype

### Question
How to replace Three.js `THREE.PointsMaterial` square point sprites with a custom WebGL fragment shader (`ShaderMaterial`) that calculates the 2D projected covariance matrix $\Sigma'$ and renders true smooth 2D elliptical Gaussians with exponential alpha falloff ($\exp(-r^2)$)?

### Answer
Replaced default `THREE.PointsMaterial` in `packages/web-viewer/viewer.js` with custom `THREE.ShaderMaterial`:
1. **Vertex Shader**: Calculates distance-scaled perspective point size `gl_PointSize = max(1.0, uSplatScale * splatScale * (400.0 / dist))` and passes `vColor` / `vOpacity` to fragment stage.
2. **Fragment Shader**: Transforms normalized point coordinates `uv = gl_PointCoord * 2.0 - 1.0`, computes radial distance $r^2 = uv \cdot uv$, discards fragments outside unit circle ($r^2 > 1.0$), and renders smooth exponential 2D Gaussian opacity falloff $\alpha = v\text{Opacity} \cdot \exp(-4.0 \cdot r^2)$.
3. Replaced square billboard sprites with smoothly blended Gaussian splats, eliminating point-cloud "confetti" artifacts.

---

## camera-photometric-loss: PyTorch Metal Camera Pinhole Projection & Photometric Loss

Blocked by: None
Status: open
Type: Research

### Question
How to upgrade `train_3dgs_metal.py` to project 3D Gaussians onto COLMAP camera poses using pinhole camera parameters and compute $L_1 + L_{\text{SSIM}}$ image reconstruction loss against training keyframes on Metal GPU (MPS)?

### Answer
*To be resolved in session.*

---

## monocular-depth-priors: Monocular Depth Map Supervision for Textureless Walls

Blocked by: camera-photometric-loss
Status: open
Type: Research

### Question
How to integrate monocular depth estimation (Depth Anything V2 / ZoeDepth) to supervise Gaussian depth rendering and anchor splats onto textureless plaster walls and floor planes where SIFT extracted 0 points?

### Answer
*To be resolved in session.*
