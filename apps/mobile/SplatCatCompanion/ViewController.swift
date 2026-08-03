import UIKit
import ARKit
import SceneKit

class ARScannerViewController: UIViewController, ARSCNViewDelegate, ARSessionDelegate {
    var sceneView: ARSCNView!
    var streamer: StreamerService?
    private var lastKeyframeTime: TimeInterval = 0
    private let ciContext = CIContext(options: [.useSoftwareRenderer: false]) // Reuse context across frames
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        sceneView = ARSCNView(frame: view.bounds)
        sceneView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(sceneView)
        
        sceneView.delegate = self
        sceneView.session.delegate = self
        sceneView.showsStatistics = true
        sceneView.debugOptions = [.showFeaturePoints]
        
        setupARConfiguration()
    }
    
    private func setupARConfiguration() {
        guard ARWorldTrackingConfiguration.isSupported else {
            print("ARWorldTracking is not supported on this device.")
            return
        }
        
        let config = ARWorldTrackingConfiguration()
        if ARWorldTrackingConfiguration.supportsSceneReconstruction(.meshWithClassification) {
            config.sceneReconstruction = .meshWithClassification
        }
        config.frameSemantics = [.smoothedSceneDepth]
        config.environmentTexturing = .automatic
        
        sceneView.session.run(config)
    }
    
    // ARSessionDelegate - Called for every ARFrame
    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        guard let streamer = streamer, streamer.isStreaming else { return }
        
        let currentTime = frame.timestamp
        if currentTime - lastKeyframeTime > 0.33 {
            lastKeyframeTime = currentTime
            processAndStreamFrame(frame)
        }
    }
    
    private func processAndStreamFrame(_ frame: ARFrame) {
        let poseMatrix = frame.camera.transform
        let pixelBuffer = frame.capturedImage
        
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = ciContext.createCGImage(ciImage, from: ciImage.extent) else { return }
        let uiImage = UIImage(cgImage: cgImage)
        guard let jpegData = uiImage.jpegData(compressionQuality: 0.6) else { return }
        let base64Image = jpegData.base64EncodedString()
        
        streamer?.sendARFramePayload(pose: poseMatrix, imageBase64: base64Image, timestamp: frame.timestamp)
    }
}
