import Foundation
import simd
import Combine

class StreamerService: ObservableObject {
    @Published var isConnected = false
    @Published var isStreaming = false
    @Published var sentFrameCount = 0
    @Published var hostAddress = "ws://localhost:8765"
    
    private var webSocketTask: URLSessionWebSocketTask?
    
    init() {
        connectToMacApp()
    }
    
    func connectToMacApp() {
        guard let macAppUrl = URL(string: hostAddress) else { return }
        let session = URLSession(configuration: .default)
        webSocketTask = session.webSocketTask(with: macAppUrl)
        webSocketTask?.resume()
        
        DispatchQueue.main.async { [weak self] in
            self?.isConnected = true
        }
    }
    
    func toggleStreaming() {
        isStreaming.toggle()
    }
    
    func sendARFramePayload(pose: simd_float4x4, imageBase64: String, timestamp: TimeInterval) {
        guard isStreaming else { return }
        
        let matrixArray: [Float] = [
            pose.columns.0.x, pose.columns.0.y, pose.columns.0.z, pose.columns.0.w,
            pose.columns.1.x, pose.columns.1.y, pose.columns.1.z, pose.columns.1.w,
            pose.columns.2.x, pose.columns.2.y, pose.columns.2.z, pose.columns.2.w,
            pose.columns.3.x, pose.columns.3.y, pose.columns.3.z, pose.columns.3.w
        ]
        
        let payload: [String: Any] = [
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
                    print("WebSocket send error: \(error)")
                } else {
                    DispatchQueue.main.async {
                        self?.sentFrameCount += 1
                    }
                }
            }
        }
    }
}
