import Cocoa
import WebKit
import Network

class LiveWebSocketServer {
    private var listener: NWListener?
    var onFrameReceived: (([String: Any]) -> Void)?

    func start(port: UInt16) {
        do {
            let parameters = NWParameters(tls: nil, tcp: NWProtocolTCP.Options())
            let wsOptions = NWProtocolWebSocket.Options()
            wsOptions.autoReplyPing = true
            parameters.defaultProtocolStack.applicationProtocols.insert(wsOptions, at: 0)
            
            guard let endpointPort = NWEndpoint.Port(rawValue: port) else { return }
            listener = try NWListener(using: parameters, on: endpointPort)
            
            listener?.stateUpdateHandler = { state in
                switch state {
                case .ready:
                    print("🟢 [SplatCat Mac Server] WebSocket listening on port \(port)")
                case .failed(let err):
                    print("🔴 [SplatCat Mac Server] WebSocket listener failed: \(err)")
                default:
                    break
                }
            }
            
            listener?.newConnectionHandler = { [weak self] connection in
                print("📱 [SplatCat Mac Server] Companion connected from \(connection.endpoint)")
                self?.handleConnection(connection)
            }
            
            listener?.start(queue: .main)
        } catch {
            print("🔴 [SplatCat Mac Server] Failed to initialize NWListener: \(error)")
        }
    }

    private func handleConnection(_ connection: NWConnection) {
        connection.start(queue: .main)
        receiveNextMessage(connection)
    }

    private func receiveNextMessage(_ connection: NWConnection) {
        connection.receiveMessage { [weak self] content, context, isComplete, error in
            if let data = content, !data.isEmpty {
                if let jsonObject = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] {
                    self?.onFrameReceived?(jsonObject)
                }
            }
            if error == nil {
                self?.receiveNextMessage(connection)
            } else {
                print("ℹ️ [SplatCat Mac Server] Connection closed or error: \(String(describing: error))")
            }
        }
    }
}

@main
class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.run()
    }
    var window: NSWindow!
    var webView: WKWebView!
    let wsServer = LiveWebSocketServer()

    func applicationDidFinishLaunching(_ notification: Notification) {
        let projectDir = "/Users/emil/Documents/Codex/SplatCat"
        let iconPath = "\(projectDir)/apps/desktop/icon_true.png"
        if let iconImage = NSImage(contentsOfFile: iconPath) {
            NSApp.applicationIconImage = iconImage
        }

        let windowMask: NSWindow.StyleMask = [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView]
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 830),
            styleMask: windowMask,
            backing: .buffered,
            defer: false
        )
        window.center()
        window.title = "SplatCat 🐾 — 3D Gaussian Splatting Suite"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.backgroundColor = NSColor(red: 0.05, green: 0.06, blue: 0.08, alpha: 1.0)
        window.isMovableByWindowBackground = true

        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")
        config.setValue(true, forKey: "allowUniversalAccessFromFileURLs")
        config.userContentController.add(self, name: "processVideo")
        config.userContentController.add(self, name: "openFilePicker")
        config.userContentController.add(self, name: "togglePauseProcess")
        config.userContentController.add(self, name: "exportHtmlNative")

        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        webView.uiDelegate = self
        
        let appHtmlPath = "\(projectDir)/apps/desktop/index.html"
        let url = URL(fileURLWithPath: appHtmlPath)
        webView.loadFileURL(url, allowingReadAccessTo: URL(fileURLWithPath: projectDir))

        window.contentView?.addSubview(webView)
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        // Start live WebSocket server on port 8765
        wsServer.onFrameReceived = { [weak self] dict in
            if let jsonData = try? JSONSerialization.data(withJSONObject: dict),
               let jsonStr = String(data: jsonData, encoding: .utf8) {
                DispatchQueue.main.async {
                    let js = "if (window.splatcatOnARFrame) window.splatcatOnARFrame(\(jsonStr));"
                    self?.webView.evaluateJavaScript(js, completionHandler: nil)
                }
            }
        }
        wsServer.start(port: 8765)
    }

    var activeSubprocessPID: Int32 = -1
    var isProcessPaused: Bool = false

    // Handle WKWebView file upload dialogs (NSOpenPanel)
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = true
        openPanel.canChooseDirectories = false
        openPanel.allowsMultipleSelection = parameters.allowsMultipleSelection
        openPanel.message = "Select Video File for 3D Gaussian Splatting"
        openPanel.begin { response in
            if response == .OK, let url = openPanel.urls.first {
                completionHandler(openPanel.urls)
                DispatchQueue.main.async {
                    let js = "if (window.splatcatOnNativeFileSelected) window.splatcatOnNativeFileSelected('\(url.path)');"
                    self.webView.evaluateJavaScript(js, completionHandler: nil)
                }
            } else {
                completionHandler(nil)
            }
        }
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        if message.name == "openFilePicker" {
            let openPanel = NSOpenPanel()
            openPanel.canChooseFiles = true
            openPanel.canChooseDirectories = false
            openPanel.allowsMultipleSelection = false
            openPanel.message = "Select Video File for 3D Gaussian Splatting"
            openPanel.begin { [weak self] response in
                if response == .OK, let url = openPanel.urls.first {
                    DispatchQueue.main.async {
                        let js = "if (window.splatcatOnNativeFileSelected) window.splatcatOnNativeFileSelected('\(url.path)');"
                        self?.webView.evaluateJavaScript(js, completionHandler: nil)
                    }
                }
            }
        } else if message.name == "processVideo",
           let body = message.body as? [String: Any],
           let videoPath = body["path"] as? String {
            let videoName = (body["name"] as? String) ?? (videoPath as NSString).lastPathComponent
            runFull3DGSPipeline(videoPath: videoPath, videoName: videoName)
        } else if message.name == "togglePauseProcess" {
            if activeSubprocessPID > 0 {
                if isProcessPaused {
                    kill(activeSubprocessPID, SIGCONT)
                    isProcessPaused = false
                    let js = "if (window.splatcatOnPauseStateChanged) window.splatcatOnPauseStateChanged(false);"
                    webView.evaluateJavaScript(js, completionHandler: nil)
                } else {
                    kill(activeSubprocessPID, SIGSTOP)
                    isProcessPaused = true
                    let js = "if (window.splatcatOnPauseStateChanged) window.splatcatOnPauseStateChanged(true);"
                    webView.evaluateJavaScript(js, completionHandler: nil)
                }
            }
        } else if message.name == "exportHtmlNative",
           let body = message.body as? [String: Any],
           let htmlContent = body["content"] as? String {
            let defaultName = (body["defaultName"] as? String) ?? "splatcat_web_export.html"
            DispatchQueue.main.async { [weak self] in
                let savePanel = NSSavePanel()
                savePanel.title = "Export Standalone HTML 3D Viewer"
                savePanel.nameFieldStringValue = defaultName
                savePanel.canCreateDirectories = true
                if #available(macOS 11.0, *) {
                    savePanel.allowedContentTypes = [.html]
                } else {
                    savePanel.allowedFileTypes = ["html"]
                }
                let targetWindow = self?.window ?? NSApp.keyWindow
                let handleSave: (NSApplication.ModalResponse) -> Void = { response in
                    if response == .OK, let targetURL = savePanel.url {
                        do {
                            try htmlContent.write(to: targetURL, atomically: true, encoding: .utf8)
                            print("🟢 [SplatCat Mac] Exported HTML package successfully to: \(targetURL.path)")
                            let js = "if (window.splatcatOnExportComplete) window.splatcatOnExportComplete(true, '\(targetURL.path)');"
                            self?.webView.evaluateJavaScript(js, completionHandler: nil)
                        } catch {
                            print("🔴 [SplatCat Mac] Failed to write HTML export: \(error)")
                            let js = "if (window.splatcatOnExportComplete) window.splatcatOnExportComplete(false, '\(error.localizedDescription)');"
                            self?.webView.evaluateJavaScript(js, completionHandler: nil)
                        }
                    }
                }
                if let win = targetWindow {
                    savePanel.beginSheetModal(for: win, completionHandler: handleSave)
                } else {
                    savePanel.begin(completionHandler: handleSave)
                }
            }
        }
    }

    private func runFull3DGSPipeline(videoPath: String, videoName: String) {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let fm = FileManager.default
            let workDir = "/tmp/splatcat_run"
            let framesDir = "\(workDir)/frames"
            let sparseDir = "\(workDir)/sparse"
            let txtDir = "\(workDir)/sparse/txt"
            let dbPath = "\(workDir)/database.db"
            let outputPlyPath = "\(workDir)/output_model.ply"

            try? fm.removeItem(atPath: workDir)
            try? fm.createDirectory(atPath: framesDir, withIntermediateDirectories: true)
            try? fm.createDirectory(atPath: sparseDir, withIntermediateDirectories: true)

            func logConsole(_ level: String, _ text: String) {
                DispatchQueue.main.async {
                    let escaped = text.replacingOccurrences(of: "'", with: "\\'").replacingOccurrences(of: "\n", with: " ")
                    let js = "if (window.splatcatLog) window.splatcatLog('\(level)', '\(escaped)');"
                    self?.webView.evaluateJavaScript(js, completionHandler: nil)
                }
            }

            func updateProgress(pct: Int, label: String, done: Bool = false, plyData: String? = nil) {
                logConsole(done ? "SUCCESS" : "INFO", label)
                DispatchQueue.main.async {
                    let escapedLabel = label.replacingOccurrences(of: "'", with: "\\'").replacingOccurrences(of: "\n", with: " ")
                    let base64Ply = (done && plyData != nil) ? (plyData!.data(using: .utf8)?.base64EncodedString() ?? "") : ""
                    let js = "if (window.splatcatUpdateProgress) window.splatcatUpdateProgress(\(pct), '\(escapedLabel)', \(done ? "true" : "false"), '\(base64Ply)');"
                    self?.webView.evaluateJavaScript(js, completionHandler: nil)
                }
            }

            func runSubprocess(bin: String, args: [String], description: String) -> Int32 {
                logConsole("EXEC", "\(bin) \(args.joined(separator: " "))")
                let process = Process()
                process.executableURL = URL(fileURLWithPath: bin)
                process.arguments = args

                let pipe = Pipe()
                let errPipe = Pipe()
                process.standardOutput = pipe
                process.standardError = errPipe

                let outHandle = pipe.fileHandleForReading
                let errHandle = errPipe.fileHandleForReading

                outHandle.readabilityHandler = { handle in
                    let data = handle.availableData
                    if !data.isEmpty, let line = String(data: data, encoding: .utf8) {
                        logConsole("OUT", line.trimmingCharacters(in: .whitespacesAndNewlines))
                    }
                }

                errHandle.readabilityHandler = { handle in
                    let data = handle.availableData
                    if !data.isEmpty, let line = String(data: data, encoding: .utf8) {
                        logConsole("ERR", line.trimmingCharacters(in: .whitespacesAndNewlines))
                    }
                }

                do {
                    try process.run()
                    self?.activeSubprocessPID = process.processIdentifier
                    process.waitUntilExit()
                    self?.activeSubprocessPID = -1
                    outHandle.readabilityHandler = nil
                    errHandle.readabilityHandler = nil
                    logConsole(process.terminationStatus == 0 ? "INFO" : "ERROR", "\(description) exited with code \(process.terminationStatus)")
                    return process.terminationStatus
                } catch {
                    logConsole("ERROR", "Failed to start \(description): \(error)")
                    return -1
                }
            }

            logConsole("START", "Initializing 3D Gaussian Splatting pipeline for file: \(videoPath)")

            guard fm.fileExists(atPath: videoPath) else {
                logConsole("ERROR", "Input video file not found at path: \(videoPath)")
                updateProgress(pct: 100, label: "❌ Error: Video file not found at \(videoPath)", done: false)
                return
            }

            // Stage 1: FFmpeg keyframe extraction (capped at max 1000 images)
            updateProgress(pct: 15, label: "Extracting keyframes from \(videoName) (capped at 1,000 max images)...")
            let ffmpegCode = runSubprocess(bin: "/opt/homebrew/bin/ffmpeg", args: ["-i", videoPath, "-vf", "fps=10", "-vframes", "1000", "\(framesDir)/frame_%04d.jpg", "-y"], description: "FFmpeg keyframe extraction")
            if ffmpegCode != 0 {
                logConsole("ERROR", "FFmpeg keyframe extraction failed.")
                return
            }

            // Stage 1.5: Adaptive Blur Filtering & Exposure Equalization Pre-Processing
            let projectDir = "/Users/emil/Documents/Codex/SplatCat"
            let venvPython = "\(projectDir)/.venv/bin/python"
            let preScript = "\(projectDir)/preprocess_keyframes.py"
            updateProgress(pct: 25, label: "Equalizing keyframe exposure & culling motion-blurred whip-pans...")
            let preCode = runSubprocess(bin: venvPython, args: [preScript, framesDir], description: "Keyframe pre-processing")
            if preCode != 0 {
                logConsole("ERROR", "Keyframe pre-processing encountered a non-zero exit code: \(preCode). Continuing with extracted frames.")
            }

            // Stage 2: COLMAP feature_extractor
            updateProgress(pct: 35, label: "Running COLMAP SIFT feature extraction...")
            let featCode = runSubprocess(bin: "/opt/homebrew/bin/colmap", args: ["feature_extractor", "--database_path", dbPath, "--image_path", framesDir, "--ImageReader.camera_model", "SIMPLE_RADIAL", "--ImageReader.single_camera", "1", "--SiftExtraction.max_num_features", "8192"], description: "COLMAP feature extraction")
            if featCode != 0 {
                logConsole("ERROR", "COLMAP feature extraction failed.")
                return
            }

            // Stage 3: COLMAP sequential_matcher
            updateProgress(pct: 55, label: "Running COLMAP sequential feature matching...")
            let matchCode = runSubprocess(bin: "/opt/homebrew/bin/colmap", args: ["sequential_matcher", "--database_path", dbPath], description: "COLMAP sequential matching")
            if matchCode != 0 {
                logConsole("ERROR", "COLMAP feature matching failed.")
                return
            }

            // Stage 4: COLMAP mapper (Bundle Adjustment)
            updateProgress(pct: 75, label: "Running COLMAP Bundle Adjustment & camera pose solver...")
            let mapperCode = runSubprocess(bin: "/opt/homebrew/bin/colmap", args: ["mapper", "--database_path", dbPath, "--image_path", framesDir, "--output_path", sparseDir], description: "COLMAP sparse mapper")
            if mapperCode != 0 {
                logConsole("ERROR", "COLMAP mapper failed.")
                return
            }

            // Convert to TXT
            let subdirs = (try? fm.contentsOfDirectory(atPath: sparseDir)) ?? []
            var bestSubdir = "0"
            var maxSize: UInt64 = 0
            for dir in subdirs {
                let binPath = "\(sparseDir)/\(dir)/points3D.bin"
                if let attrs = try? fm.attributesOfItem(atPath: binPath),
                   let size = attrs[.size] as? UInt64, size > maxSize {
                    maxSize = size
                    bestSubdir = dir
                }
            }
            let modelInputPath = "\(sparseDir)/\(bestSubdir)"
            try? fm.createDirectory(atPath: txtDir, withIntermediateDirectories: true)
            logConsole("INFO", "Converting sparse model from \(modelInputPath) (points3D.bin size: \(maxSize) bytes) to TXT...")
            _ = runSubprocess(bin: "/opt/homebrew/bin/colmap", args: ["model_converter", "--input_path", modelInputPath, "--output_path", txtDir, "--output_type", "TXT"], description: "COLMAP model converter")

            // Stage 5: PyTorch Metal GPU 3DGS Trainer
            updateProgress(pct: 90, label: "Optimizing 3D Gaussians on Apple Metal GPU (PyTorch MPS)...")
            let pyScript = "\(projectDir)/train_3dgs_metal.py"
            _ = runSubprocess(bin: venvPython, args: [pyScript, "--colmap_dir", sparseDir, "--images_dir", framesDir, "--output_ply", outputPlyPath, "--iterations", "3000"], description: "PyTorch Metal 3DGS optimizer")

            // Read output PLY and send to UI
            if fm.fileExists(atPath: outputPlyPath),
               let plyContent = try? String(contentsOfFile: outputPlyPath, encoding: .utf8) {
                updateProgress(pct: 100, label: "Real 3D Gaussian Splat complete!", done: true, plyData: plyContent)
            } else {
                updateProgress(pct: 100, label: "COLMAP model output complete! Loading 3D Viewport...", done: true)
            }
        }
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            window?.makeKeyAndOrderFront(nil)
        }
        return true
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}
