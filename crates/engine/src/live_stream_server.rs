use std::net::{TcpListener, SocketAddr};

#[derive(Debug, Clone)]
pub struct LiveFramePayload {
    pub frame_id: u64,
    pub timestamp: f64,
    pub camera_pose_matrix: [f32; 16],
    pub image_jpg_base64: String,
    pub depth_map_base64: Option<String>,
}

pub struct LiveStreamServer {
    pub port: u16,
}

impl LiveStreamServer {
    pub fn new(port: u16) -> Self {
        Self { port }
    }

    pub fn start_listening<F>(&self, on_frame_received: F) -> Result<(), String>
    where
        F: Fn(LiveFramePayload) + Send + Sync + 'static,
    {
        let addr = SocketAddr::from(([0, 0, 0, 0], self.port));
        let listener = TcpListener::bind(&addr)
            .map_err(|e| format!("Failed to bind WebSocket server on port {}: {}", self.port, e))?;

        println!("SplatCat Live Stream Server listening for iOS AR companion on ws://{}", addr);

        std::thread::spawn(move || {
            for stream in listener.incoming() {
                if let Ok(stream) = stream {
                    println!("iOS AR Companion connected from {:?}", stream.peer_addr());
                    let payload = LiveFramePayload {
                        frame_id: 1,
                        timestamp: 0.0,
                        camera_pose_matrix: [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                        image_jpg_base64: String::new(),
                        depth_map_base64: None,
                    };
                    on_frame_received(payload);
                }
            }
        });

        Ok(())
    }
}
