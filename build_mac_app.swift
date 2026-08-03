import Cocoa
import WebKit

class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    var window: NSWindow!
    var webView: WKWebView!

    func applicationDidFinishLaunching(_ notification: Notification) {
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
        
        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        
        let appHtmlPath = "/Users/emil/Documents/Codex/SplatCat/apps/desktop/index.html"
        let url = URL(fileURLWithPath: appHtmlPath)
        webView.loadFileURL(url, allowingReadAccessTo: URL(fileURLWithPath: "/Users/emil/Documents/Codex/SplatCat"))

        window.contentView?.addSubview(webView)
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
