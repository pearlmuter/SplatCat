import SwiftUI

@main
struct SplatCatCompanionApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    @StateObject private var streamer = StreamerService()
    
    var body: some View {
        ZStack {
            ARViewContainer(streamer: streamer)
                .edgesIgnoringSafeArea(.all)
            
            VStack {
                HStack {
                    Text("🐾 SplatCat AR Companion")
                        .font(.headline)
                        .padding(8)
                        .background(Color.black.opacity(0.6))
                        .cornerRadius(10)
                        .foregroundColor(.white)
                    Spacer()
                    Text(streamer.isConnected ? "🟢 Streaming" : "🔴 Disconnected")
                        .font(.subheadline)
                        .padding(8)
                        .background(Color.black.opacity(0.6))
                        .cornerRadius(10)
                        .foregroundColor(.white)
                }
                .padding()
                
                Spacer()
                
                HStack(spacing: 20) {
                    VStack {
                        Text("Sent Frames")
                            .font(.caption)
                            .foregroundColor(.gray)
                        Text("\(streamer.sentFrameCount)")
                            .font(.title2)
                            .bold()
                            .foregroundColor(.cyan)
                    }
                    
                    Button(action: {
                        streamer.toggleStreaming()
                    }) {
                        Text(streamer.isStreaming ? "Stop Live Stream" : "Start Live Stream")
                            .bold()
                            .padding()
                            .frame(maxWidth: .infinity)
                            .background(streamer.isStreaming ? Color.red : Color.indigo)
                            .foregroundColor(.white)
                            .cornerRadius(16)
                    }
                }
                .padding()
                .background(Color.black.opacity(0.75))
                .cornerRadius(20)
                .padding()
            }
        }
    }
}

struct ARViewContainer: UIViewControllerRepresentable {
    let streamer: StreamerService
    
    func makeUIViewController(context: Context) -> ARScannerViewController {
        let vc = ARScannerViewController()
        vc.streamer = streamer
        return vc
    }
    
    func updateUIViewController(_ uiViewController: ARScannerViewController, context: Context) {}
}
