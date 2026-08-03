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
    
    // Heatmap overlay tracking
    private var scannedAnchors: Set<UUID> = []
    private var heatmapMaterial: SCNMaterial?
    
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
            statusLabel.widthAnchor.constraint(equalToConstant: 260)
        ])
        
        sceneView.delegate = self
        sceneView.session.delegate = self
        sceneView.showsStatistics = true
        sceneView.debugOptions = [.showFeaturePoints]
        
        let scene = SCNScene()
        sceneView.scene = scene
        
        setupHeatmapMaterial()
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
    
    // MARK: - Heatmap Material Setup (Bug 9 fix: actually use the shader concept)
    
    private func setupHeatmapMaterial() {
        let material = SCNMaterial()
        material.diffuse.contents = UIColor(red: 0.0, green: 0.95, blue: 0.6, alpha: 0.35)
        material.isDoubleSided = true
        material.fillMode = .fill
        material.transparencyMode = .dualLayer
        heatmapMaterial = material
    }
    
    // MARK: - Camera Permissions
    
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
    
    // MARK: - AR Session Configuration (Bug 3 fix: guard LiDAR features)
    
    private func runARSession() {
        guard ARWorldTrackingConfiguration.isSupported else {
            statusLabel.text = "ARKit Not Supported (Simulator)"
            statusLabel.textColor = .yellow
            return
        }
        
        let config = ARWorldTrackingConfiguration()
        
        // LiDAR mesh reconstruction — only on Pro devices that support it
        if ARWorldTrackingConfiguration.supportsSceneReconstruction(.meshWithClassification) {
            config.sceneReconstruction = .meshWithClassification
            statusLabel.text = "LiDAR Mesh Tracking Active"
        } else {
            statusLabel.text = "Visual 6DoF Tracking Active"
        }
        
        // Depth — only request if hardware supports it (Bug 3: crashes on iPhone 13 non-Pro)
        if ARWorldTrackingConfiguration.supportsFrameSemantics(.smoothedSceneDepth) {
            config.frameSemantics.insert(.smoothedSceneDepth)
        }
        
        config.environmentTexturing = .automatic
        config.isLightEstimationEnabled = true
        
        sceneView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
    }
    
    // MARK: - ARSessionDelegate
    
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
            let reasonStr: String
            switch reason {
            case .initializing: reasonStr = "Initializing"
            case .excessiveMotion: reasonStr = "Move Slower"
            case .insufficientFeatures: reasonStr = "Low Detail"
            case .relocalizing: reasonStr = "Relocalizing"
            @unknown default: reasonStr = "Unknown"
            }
            statusLabel.text = "⚠️ Limited: \(reasonStr)"
            statusLabel.textColor = .orange
        case .notAvailable:
            statusLabel.text = "❌ Tracking Not Available"
            statusLabel.textColor = .red
        }
    }
    
    // MARK: - ARSCNViewDelegate (Bug 9 fix: visualize mesh anchors with heatmap)
    
    func renderer(_ renderer: SCNSceneRenderer, nodeFor anchor: ARAnchor) -> SCNNode? {
        guard let meshAnchor = anchor as? ARMeshAnchor else { return nil }
        
        let node = SCNNode()
        let geometry = createGeometry(from: meshAnchor)
        geometry.materials = [heatmapMaterial ?? SCNMaterial()]
        node.geometry = geometry
        scannedAnchors.insert(meshAnchor.identifier)
        return node
    }
    
    func renderer(_ renderer: SCNSceneRenderer, didUpdate node: SCNNode, for anchor: ARAnchor) {
        guard let meshAnchor = anchor as? ARMeshAnchor else { return }
        let geometry = createGeometry(from: meshAnchor)
        geometry.materials = [heatmapMaterial ?? SCNMaterial()]
        node.geometry = geometry
    }
    
    private func createGeometry(from meshAnchor: ARMeshAnchor) -> SCNGeometry {
        let vertices = meshAnchor.geometry.vertices
        let faces = meshAnchor.geometry.faces
        
        let vertexSource = SCNGeometrySource(
            buffer: vertices.buffer,
            vertexFormat: vertices.format,
            semantic: .vertex,
            vertexCount: vertices.count,
            dataOffset: vertices.offset,
            dataStride: vertices.stride
        )
        
        let faceByteCount = faces.count * faces.indexCountPerPrimitive * faces.bytesPerIndex
        let faceData = Data(
            bytesNoCopy: faces.buffer.contents(),
            count: faceByteCount,
            deallocator: .none
        )
        
        let faceElement = SCNGeometryElement(
            data: faceData,
            primitiveType: .triangles,
            primitiveCount: faces.count,
            bytesPerIndex: faces.bytesPerIndex
        )
        
        return SCNGeometry(sources: [vertexSource], elements: [faceElement])
    }
    
    // MARK: - Frame Streaming
    
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
