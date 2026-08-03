import UIKit
import ARKit
import SceneKit
import AVFoundation

class ARScannerViewController: UIViewController, ARSCNViewDelegate, ARSessionDelegate {
    var sceneView: ARSCNView!
    var streamer: StreamerService?
    private var lastKeyframeTime: TimeInterval = 0
    private let ciContext = CIContext(options: [.useSoftwareRenderer: false])
    private var statusLabel: UILabel!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        view.backgroundColor = .black
        
        // Full screen ARView layout
        sceneView = ARSCNView(frame: .zero)
        sceneView.backgroundColor = .black
        sceneView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(sceneView)
        
        // Status label overlay for camera diagnostic
        statusLabel = UILabel()
        statusLabel.text = "Initializing AR Camera..."
        statusLabel.textColor = .cyan
        statusLabel.font = UIFont.monospacedSystemFont(ofSize: 12, weight: .bold)
        statusLabel.backgroundColor = UIColor.black.withAlphaComponent(0.65)
        statusLabel.layer.cornerRadius = 8
        statusLabel.layer.masksToBounds = true
        statusLabel.textAlignment = .center
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(statusLabel)
        
        NSLayoutConstraint.activate([
            sceneView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            sceneView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            sceneView.topAnchor.constraint(equalTo: view.topAnchor),
            sceneView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            
            statusLabel.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 12),
            statusLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            statusLabel.heightAnchor.constraint(equalToConstant: 28),
            statusLabel.widthAnchor.constraint(equalToConstant: 220)
        ])
        
        sceneView.delegate = self
        sceneView.session.delegate = self
        sceneView.showsStatistics = true
        sceneView.debugOptions = [.showFeaturePoints]
        
        let scene = SCNScene()
        sceneView.scene = scene
        
        checkCameraPermissionAndRun()
    }
    
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        sceneView.frame = view.bounds
    }
    
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        checkCameraPermissionAndRun()
    }
    
    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sceneView.session.pause()
    }
    
    private func checkCameraPermissionAndRun() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            runARSession()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    if granted {
                        self?.runARSession()
                    } else {
                        self?.statusLabel.text = "Camera Permission Denied"
                        self?.statusLabel.textColor = .red
                    }
                }
            }
        default:
            statusLabel.text = "Camera Permission Required"
            statusLabel.textColor = .orange
        }
    }
    
    private func runARSession() {
        guard ARWorldTrackingConfiguration.isSupported else {
            statusLabel.text = "ARKit Not Supported (Simulator)"
            statusLabel.textColor = .yellow
            return
        }
        
        let config = ARWorldTrackingConfiguration()
        if ARWorldTrackingConfiguration.supportsSceneReconstruction(.meshWithClassification) {
            config.sceneReconstruction = .meshWithClassification
            statusLabel.text = "LiDAR Mesh Tracking Active"
        } else {
            statusLabel.text = "Visual 6DoF Tracking Active"
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
    
    func session(_ session: ARSession, cameraDidChangeTrackingState camera: ARCamera) {
        switch camera.trackingState {
        case .normal:
            statusLabel.text = "🟢 Tracking Normal"
            statusLabel.textColor = .green
        case .limited(let reason):
            statusLabel.text = "⚠️ Tracking Limited (\(reason))"
            statusLabel.textColor = .orange
        case .notAvailable:
            statusLabel.text = "❌ Tracking Not Available"
            statusLabel.textColor = .red
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
