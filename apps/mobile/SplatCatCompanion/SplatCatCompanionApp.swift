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
            Color.black.edgesIgnoringSafeArea(.all)
            
            ARViewContainer(streamer: streamer)
                .edgesIgnoringSafeArea(.all)
            
            VStack {
                HStack {
                    HStack(spacing: 8) {
                        Image(uiImage: UIImage(named: "AppIcon") ?? UIImage())
                            .resizable()
                            .frame(width: 24, height: 24)
                            .cornerRadius(6)
                        Text("SplatCat")
                            .font(.headline)
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Color.black.opacity(0.75))
                    .cornerRadius(12)
                    
                    Spacer()
                    
                    Text(streamer.isConnected ? "🟢 Connected" : "🔴 Offline")
                        .font(.caption)
                        .bold()
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(Color.black.opacity(0.75))
                        .cornerRadius(12)
                        .foregroundColor(streamer.isConnected ? .green : .red)
                }
                .padding()
                
                Spacer()
                
                VStack(spacing: 12) {
                    HStack {
                        VStack(alignment: .leading) {
                            Text("Mac Server")
                                .font(.caption2)
                                .foregroundColor(.gray)
                            Text(streamer.hostAddress)
                                .font(.system(.caption, design: .monospaced))
                                .foregroundColor(.cyan)
                        }
                        Spacer()
                        VStack(alignment: .trailing) {
                            Text("Streamed Poses")
                                .font(.caption2)
                                .foregroundColor(.gray)
                            Text("\(streamer.sentFrameCount)")
                                .font(.title3)
                                .bold()
                                .foregroundColor(.white)
                        }
                    }
                    
                    Button(action: {
                        streamer.toggleStreaming()
                    }) {
                        HStack {
                            Image(systemName: streamer.isStreaming ? "stop.fill" : "record.circle.fill")
                            Text(streamer.isStreaming ? "Stop Live Scanning Stream" : "Start Live Scanning Stream")
                                .bold()
                        }
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(streamer.isStreaming ? Color.red : Color.indigo)
                        .foregroundColor(.white)
                        .cornerRadius(16)
                    }
                }
                .padding()
                .background(Color.black.opacity(0.85))
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
