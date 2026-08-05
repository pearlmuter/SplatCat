# 4. Native macOS NSSavePanel Integration for HTML Export

- **Status**: Accepted
- **Date**: 2026-08-05

## Context and Problem Statement
When users export standalone WebGL/WebGPU 3D HTML packages from SplatCat, standard web `Blob` downloads (`<a download="...">`) download files silently to `~/Downloads` without user prompt. Users need to specify target directories (e.g. project folders, desktop) and custom filenames when saving HTML packages in the native macOS application.

## Decision Drivers
- High native macOS UI alignment (AppKit sheet modal dialogs).
- Zero third-party web wrapper dependencies (native WKWebView script message bridge).
- Seamless fallback for standard browser environments.

## Considered Options
1. **WKScriptMessageHandler with AppKit `NSSavePanel`**: Register a custom WebKit message handler (`exportHtmlNative`) that presents a native modal sheet `NSSavePanel` when exporting from the native Swift wrapper, while preserving standard Blob URL download logic in plain browser runtimes.
2. **WKDownloadDelegate Interception**: Intercept standard WebKit file downloads via `WKDownloadDelegate`.
3. **HTML5 File System Access API**: Use `window.showSaveFilePicker()` in JS.

## Decision Outcome
Chosen option: **Option 1 (WKScriptMessageHandler + AppKit NSSavePanel)**.

### Positives
- Provides native macOS modal sheet experience embedded into the app window.
- Allows user directory selection, custom naming, and file overwrite confirmation via system dialogs.
- Robust cross-platform web fallback when running outside the native macOS AppKit bundle.
