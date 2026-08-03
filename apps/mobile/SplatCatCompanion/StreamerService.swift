import Foundation
import simd
import Combine
import Network

class StreamerService: ObservableObject {
    @Published var isConnected = false
    @Published var isStreaming = false
    @Published var sentFrameCount = 0
    @Published var hostAddress = "ws://10.0.0.4:8765"
    
    private var webSocketTask: URLSessionWebSocketTask?
    private var session: URLSession?
    private var pingTimer: Timer?
    
    init() {}
    
    func toggleStreaming() {
        if isStreaming {
            stopStreaming()
        } else {
            startStreaming()
        }
    }
    
    private func startStreaming() {
        guard let url = URL(string: hostAddress) else {
            print("[StreamerService] Invalid host URL: \(hostAddress)")
            return
        }
        
        let config = URLSessionConfiguration.default
        config.waitsForConnectivity = true
        config.timeoutIntervalForResource = 30
        session = URLSession(configuration: config)
        
        webSocketTask = session?.webSocketTask(with: url)
        webSocketTask?.resume()
        
        // Start the receive loop so we can detect disconnection
        receiveLoop()
        
        // Ping every 5 seconds to check liveness
        DispatchQueue.main.async { [weak self] in
            self?.isStreaming = true
            self?.pingTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
                self?.sendPing()
            }
        }
        
        // Send an initial handshake message
        let hello: [String: Any] = [
            "type": "hello",
            "client": "SplatCat-iOS",
            "version": "0.1"
        ]
        if let data = try? JSONSerialization.data(withJSONObject: hello),
           let str = String(data: data, encoding: .utf8) {
            webSocketTask?.send(.string(str)) { [weak self] error in
                DispatchQueue.main.async {
                    if let error = error {
                        print("[StreamerService] Handshake failed: \(error)")
                        self?.isConnected = false
                    } else {
                        print("[StreamerService] Connected to Mac at \(self?.hostAddress ?? "")")
                        self?.isConnected = true
                    }
                }
            }
        }
    }
    
    private func stopStreaming() {
        pingTimer?.invalidate()
        pingTimer = nil
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        session?.invalidateAndCancel()
        session = nil
        
        DispatchQueue.main.async { [weak self] in
            self?.isStreaming = false
            self?.isConnected = false
        }
    }
    
    private func receiveLoop() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    print("[StreamerService] Server: \(text)")
                case .data(let data):
                    print("[StreamerService] Server binary: \(data.count) bytes")
                @unknown default:
                    break
                }
                // Continue listening
                self?.receiveLoop()
            case .failure(let error):
                print("[StreamerService] Connection lost: \(error)")
                DispatchQueue.main.async {
                    self?.isConnected = false
                    self?.isStreaming = false
                    self?.pingTimer?.invalidate()
                    self?.pingTimer = nil
                }
            }
        }
    }
    
    private func sendPing() {
        webSocketTask?.sendPing { [weak self] error in
            DispatchQueue.main.async {
                if let error = error {
                    print("[StreamerService] Ping failed: \(error)")
                    self?.isConnected = false
                    self?.isStreaming = false
                    self?.stopStreaming()
                } else {
                    self?.isConnected = true
                }
            }
        }
    }
    
    func sendARFramePayload(pose: simd_float4x4, imageBase64: String, timestamp: TimeInterval) {
        guard isStreaming, isConnected else { return }
        
        let matrixArray: [Float] = [
            pose.columns.0.x, pose.columns.0.y, pose.columns.0.z, pose.columns.0.w,
            pose.columns.1.x, pose.columns.1.y, pose.columns.1.z, pose.columns.1.w,
            pose.columns.2.x, pose.columns.2.y, pose.columns.2.z, pose.columns.2.w,
            pose.columns.3.x, pose.columns.3.y, pose.columns.3.z, pose.columns.3.w
        ]
        
        let payload: [String: Any] = [
            "type": "ar_frame",
            "frame_id": sentFrameCount + 1,
            "timestamp": timestamp,
            "camera_pose_matrix": matrixArray,
            "image_jpg_base64": imageBase64
        ]
        
        if let jsonData = try? JSONSerialization.data(withJSONObject: payload),
           let jsonString = String(data: jsonData, encoding: .utf8) {
            let message = URLSessionWebSocketTask.Message.string(jsonString)
            webSocketTask?.send(message) { [weak self] error in
                if let error = error {
                    print("[StreamerService] Send error: \(error)")
                    DispatchQueue.main.async {
                        self?.isConnected = false
                    }
                } else {
                    DispatchQueue.main.async {
                        self?.sentFrameCount += 1
                    }
                }
            }
        }
    }
}
