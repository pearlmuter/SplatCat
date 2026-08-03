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
    @State private var isEditingIP = false
    @State private var ipInputText = ""
    
    var body: some View {
        ZStack {
            Color.black.edgesIgnoringSafeArea(.all)
            
            ARViewContainer(streamer: streamer)
                .edgesIgnoringSafeArea(.all)
            
            VStack {
                // Header Bar
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
                    
                    Button(action: {
                        ipInputText = streamer.rawAddress
                        isEditingIP = true
                    }) {
                        HStack(spacing: 6) {
                            Text(streamer.isConnected ? "🟢 Connected" : "🔴 Offline")
                                .font(.caption)
                                .bold()
                            Image(systemName: "pencil.circle.fill")
                                .font(.caption)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(Color.black.opacity(0.75))
                        .cornerRadius(12)
                        .foregroundColor(streamer.isConnected ? .green : .red)
                    }
                }
                .padding()
                
                Spacer()
                
                // Bottom Control Card
                VStack(spacing: 12) {
                    HStack {
                        VStack(alignment: .leading) {
                            Text("Mac Server IP")
                                .font(.caption2)
                                .foregroundColor(.gray)
                            Button(action: {
                                ipInputText = streamer.rawAddress
                                isEditingIP = true
                            }) {
                                HStack(spacing: 4) {
                                    Text(streamer.hostAddress)
                                        .font(.system(.caption, design: .monospaced))
                                        .foregroundColor(.cyan)
                                    Image(systemName: "pencil")
                                        .font(.caption2)
                                        .foregroundColor(.cyan)
                                }
                            }
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
        .alert("Connect to Mac Desktop App", isPresented: $isEditingIP) {
            TextField("Mac LAN IP (e.g. 10.0.0.4)", text: $ipInputText)
                .keyboardType(.numbersAndPunctuation)
                .autocapitalization(.none)
            Button("Save & Connect") {
                streamer.updateHostAddress(ipInputText)
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Enter your Mac's LAN IP address. Make sure SplatCat Desktop is open on your Mac.")
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
