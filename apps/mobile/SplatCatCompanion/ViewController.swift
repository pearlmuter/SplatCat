import UIKit
import ARKit
import SceneKit

class ARScannerViewController: UIViewController, ARSCNViewDelegate, ARSessionDelegate {
    var sceneView: ARSCNView!
    var streamer: StreamerService?
    private var lastKeyframeTime: TimeInterval = 0
    private let ciContext = CIContext(options: [.useSoftwareRenderer: false])
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        // Full screen ARView layout
        sceneView = ARSCNView(frame: .zero)
        sceneView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(sceneView)
        
        NSLayoutConstraint.activate([
            sceneView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            sceneView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            sceneView.topAnchor.constraint(equalTo: view.topAnchor),
            sceneView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
        
        sceneView.delegate = self
        sceneView.session.delegate = self
        sceneView.showsStatistics = true
        sceneView.debugOptions = [.showFeaturePoints]
        
        // Initialize SceneKit scene
        let scene = SCNScene()
        sceneView.scene = scene
        
        setupARConfiguration()
    }
    
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        sceneView.frame = view.bounds
    }
    
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        setupARConfiguration()
    }
    
    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sceneView.session.pause()
    }
    
    private func setupARConfiguration() {
        guard ARWorldTrackingConfiguration.isSupported else {
            print("ARWorldTracking is not supported on this device/simulator.")
            return
        }
        
        let config = ARWorldTrackingConfiguration()
        if ARWorldTrackingConfiguration.supportsSceneReconstruction(.meshWithClassification) {
            config.sceneReconstruction = .meshWithClassification
        }
        config.frameSemantics = [.smoothedSceneDepth]
        config.environmentTexturing = .automatic
        config.isLightEstimationEnabled = true
        
        sceneView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
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
