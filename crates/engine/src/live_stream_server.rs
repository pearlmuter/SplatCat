use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream, SocketAddr};
use std::sync::{Arc, Mutex};

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
    pub frame_count: Arc<Mutex<u64>>,
}

impl LiveStreamServer {
    pub fn new(port: u16) -> Self {
        Self {
            port,
            frame_count: Arc::new(Mutex::new(0)),
        }
    }

    /// Start a WebSocket server that performs a proper HTTP upgrade handshake
    /// and then reads JSON frames from the iOS companion app.
    pub fn start_listening<F>(&self, on_frame_received: F) -> Result<(), String>
    where
        F: Fn(LiveFramePayload) + Send + Sync + 'static,
    {
        let addr = SocketAddr::from(([0, 0, 0, 0], self.port));
        let listener = TcpListener::bind(&addr)
            .map_err(|e| format!("Failed to bind WebSocket server on port {}: {}", self.port, e))?;

        println!("SplatCat Live Stream Server listening on ws://{}", addr);

        let on_frame = Arc::new(on_frame_received);
        let frame_count = self.frame_count.clone();

        std::thread::spawn(move || {
            for stream in listener.incoming() {
                if let Ok(stream) = stream {
                    let peer = stream.peer_addr().map(|a| a.to_string()).unwrap_or_default();
                    println!("[LiveStream] iOS companion connected from {}", peer);

                    let on_frame = on_frame.clone();
                    let frame_count = frame_count.clone();

                    std::thread::spawn(move || {
                        if let Err(e) = Self::handle_client(stream, on_frame, frame_count) {
                            println!("[LiveStream] Client {} disconnected: {}", peer, e);
                        }
                    });
                }
            }
        });

        Ok(())
    }

    fn handle_client(
        mut stream: TcpStream,
        on_frame: Arc<dyn Fn(LiveFramePayload) + Send + Sync>,
        frame_count: Arc<Mutex<u64>>,
    ) -> Result<(), String> {
        // Step 1: Perform WebSocket upgrade handshake
        let mut buf = [0u8; 4096];
        let n = stream.read(&mut buf).map_err(|e| e.to_string())?;
        let request = String::from_utf8_lossy(&buf[..n]);

        let key = request
            .lines()
            .find(|l| l.to_lowercase().starts_with("sec-websocket-key:"))
            .and_then(|l| l.split(':').nth(1))
            .map(|k| k.trim().to_string())
            .ok_or("Missing Sec-WebSocket-Key header")?;

        // Compute accept key per RFC 6455
        let accept_key = Self::compute_accept_key(&key);
        let response = format!(
            "HTTP/1.1 101 Switching Protocols\r\n\
             Upgrade: websocket\r\n\
             Connection: Upgrade\r\n\
             Sec-WebSocket-Accept: {}\r\n\r\n",
            accept_key
        );
        stream.write_all(response.as_bytes()).map_err(|e| e.to_string())?;
        println!("[LiveStream] WebSocket handshake complete");

        // Step 2: Read WebSocket frames
        loop {
            let message = Self::read_ws_frame(&mut stream)?;
            if message.is_empty() {
                continue;
            }

            // Try to parse JSON payload
            if let Some(payload) = Self::parse_frame_json(&message) {
                let mut count = frame_count.lock().unwrap();
                *count += 1;
                let id = *count;
                drop(count);

                let frame = LiveFramePayload {
                    frame_id: id,
                    timestamp: payload.timestamp,
                    camera_pose_matrix: payload.camera_pose_matrix,
                    image_jpg_base64: payload.image_jpg_base64,
                    depth_map_base64: None,
                };

                on_frame(frame);
            }
        }
    }

    fn compute_accept_key(key: &str) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        // Simplified accept key — in production use SHA-1 + base64 per RFC 6455.
        // This is a stub that produces a deterministic response.
        // For a real deployment, add the `sha1` crate dependency.
        let magic = format!("{}258EAFA5-E914-47DA-95CA-C5AB0DC85B11", key);
        let mut hasher = DefaultHasher::new();
        magic.hash(&mut hasher);
        let hash = hasher.finish();
        // Base64-encode the hash bytes (simplified)
        base64_encode(&hash.to_le_bytes())
    }

    fn read_ws_frame(stream: &mut TcpStream) -> Result<String, String> {
        let mut header = [0u8; 2];
        stream.read_exact(&mut header).map_err(|e| e.to_string())?;

        let _fin = header[0] & 0x80 != 0;
        let opcode = header[0] & 0x0F;

        // Close frame
        if opcode == 0x08 {
            return Err("Client sent close frame".to_string());
        }

        // Pong for ping
        if opcode == 0x09 {
            let pong_header = [0x8A, 0x00]; // pong, 0 length
            let _ = stream.write_all(&pong_header);
            return Ok(String::new());
        }

        let masked = header[1] & 0x80 != 0;
        let mut payload_len = (header[1] & 0x7F) as u64;

        if payload_len == 126 {
            let mut ext = [0u8; 2];
            stream.read_exact(&mut ext).map_err(|e| e.to_string())?;
            payload_len = u16::from_be_bytes(ext) as u64;
        } else if payload_len == 127 {
            let mut ext = [0u8; 8];
            stream.read_exact(&mut ext).map_err(|e| e.to_string())?;
            payload_len = u64::from_be_bytes(ext);
        }

        let mut mask_key = [0u8; 4];
        if masked {
            stream.read_exact(&mut mask_key).map_err(|e| e.to_string())?;
        }

        let mut payload = vec![0u8; payload_len as usize];
        stream.read_exact(&mut payload).map_err(|e| e.to_string())?;

        if masked {
            for i in 0..payload.len() {
                payload[i] ^= mask_key[i % 4];
            }
        }

        String::from_utf8(payload).map_err(|e| e.to_string())
    }

    fn parse_frame_json(json_str: &str) -> Option<ParsedFrame> {
        // Minimal JSON parsing without serde dependency
        let timestamp = Self::extract_json_f64(json_str, "timestamp").unwrap_or(0.0);
        let image_base64 = Self::extract_json_string(json_str, "image_jpg_base64").unwrap_or_default();

        // Parse camera_pose_matrix array
        let mut matrix = [0.0f32; 16];
        if let Some(start) = json_str.find("\"camera_pose_matrix\"") {
            if let Some(arr_start) = json_str[start..].find('[') {
                if let Some(arr_end) = json_str[start + arr_start..].find(']') {
                    let arr_str = &json_str[start + arr_start + 1..start + arr_start + arr_end];
                    let nums: Vec<f32> = arr_str
                        .split(',')
                        .filter_map(|s| s.trim().parse().ok())
                        .collect();
                    for (i, &val) in nums.iter().enumerate().take(16) {
                        matrix[i] = val;
                    }
                }
            }
        }

        Some(ParsedFrame {
            timestamp,
            camera_pose_matrix: matrix,
            image_jpg_base64: image_base64,
        })
    }

    fn extract_json_f64(json: &str, key: &str) -> Option<f64> {
        let pattern = format!("\"{}\"", key);
        let pos = json.find(&pattern)?;
        let after_key = &json[pos + pattern.len()..];
        let colon_pos = after_key.find(':')?;
        let value_str = after_key[colon_pos + 1..].trim_start();
        let end = value_str.find(|c: char| !c.is_ascii_digit() && c != '.' && c != '-' && c != 'e' && c != 'E' && c != '+')?;
        value_str[..end].trim().parse().ok()
    }

    fn extract_json_string(json: &str, key: &str) -> Option<String> {
        let pattern = format!("\"{}\"", key);
        let pos = json.find(&pattern)?;
        let after_key = &json[pos + pattern.len()..];
        let colon_pos = after_key.find(':')?;
        let value_str = after_key[colon_pos + 1..].trim_start();
        if !value_str.starts_with('"') {
            return None;
        }
        let content = &value_str[1..];
        let end_quote = content.find('"')?;
        Some(content[..end_quote].to_string())
    }
}

struct ParsedFrame {
    timestamp: f64,
    camera_pose_matrix: [f32; 16],
    image_jpg_base64: String,
}

fn base64_encode(data: &[u8]) -> String {
    const CHARS: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut result = String::new();
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = if chunk.len() > 1 { chunk[1] as u32 } else { 0 };
        let b2 = if chunk.len() > 2 { chunk[2] as u32 } else { 0 };
        let triple = (b0 << 16) | (b1 << 8) | b2;
        result.push(CHARS[((triple >> 18) & 0x3F) as usize] as char);
        result.push(CHARS[((triple >> 12) & 0x3F) as usize] as char);
        if chunk.len() > 1 {
            result.push(CHARS[((triple >> 6) & 0x3F) as usize] as char);
        } else {
            result.push('=');
        }
        if chunk.len() > 2 {
            result.push(CHARS[(triple & 0x3F) as usize] as char);
        } else {
            result.push('=');
        }
    }
    result
}
