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

class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var webView: WKWebView!
    let wsServer = LiveWebSocketServer()

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Set dynamic Dock icon
        let iconPath = "/Users/emil/Documents/Codex/SplatCat/apps/desktop/icon_true.png"
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
        config.userContentController.add(self, name: "processVideo")
        
        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        
        let appHtmlPath = "/Users/emil/Documents/Codex/SplatCat/apps/desktop/index.html"
        let url = URL(fileURLWithPath: appHtmlPath)
        webView.loadFileURL(url, allowingReadAccessTo: URL(fileURLWithPath: "/Users/emil/Documents/Codex/SplatCat"))

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

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        if message.name == "processVideo",
           let body = message.body as? [String: Any],
           let videoPath = body["path"] as? String {
            extractVideoFrames(videoPath: videoPath)
        }
    }

    private func extractVideoFrames(videoPath: String) {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/opt/homebrew/bin/ffmpeg")
        let outputDir = "/tmp/splatcat_keyframes"
        try? FileManager.default.createDirectory(atPath: outputDir, withIntermediateDirectories: true)
        task.arguments = ["-i", videoPath, "-vf", "fps=2", "\(outputDir)/frame_%04d.jpg", "-y"]
        try? task.run()
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

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
