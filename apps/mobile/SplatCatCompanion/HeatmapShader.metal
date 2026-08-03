#include <metal_stdlib>
using namespace metal;

struct VertexInput {
    float3 position  [[attribute(0)]];
    float3 normal    [[attribute(1)]];
    float2 texCoords [[attribute(2)]];
};

struct VertexOutput {
    float4 position [[position]];
    float3 worldNormal;
    float scanDensity;
};

vertex VertexOutput heatMapVertexShader(VertexInput in [[stage_in]],
                                        constant float4x4& modelViewProjection [[buffer(1)]],
                                        constant float& scanProgress [[buffer(2)]]) {
    VertexOutput out;
    out.position = modelViewProjection * float4(in.position, 1.0);
    out.worldNormal = in.normal;
    out.scanDensity = scanProgress;
    return out;
}

fragment float4 heatMapFragmentShader(VertexOutput in [[stage_in]]) {
    // Green (0.0, 0.9, 0.5) for scanned surfaces, Red (0.9, 0.2, 0.2) for unscanned
    float3 scannedColor = float3(0.0, 0.95, 0.6);
    float3 unscannedColor = float3(0.95, 0.2, 0.3);
    
    float t = clamp(in.scanDensity, 0.0, 1.0);
    float3 finalColor = mix(unscannedColor, scannedColor, t);
    
    return float4(finalColor, 0.45); // Semi-transparent overlay
}
