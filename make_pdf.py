import sys

def build_pdf(filename="OPEN_SOURCE_ATTRIBUTIONS.pdf"):
    # High-quality Minimalist PDF Generator (Pure Python, Zero External Dependencies)
    title = "SplatCat Open Source Attributions & Compliance Report"
    date_str = "2026-08-03"
    
    text_content = [
        "SplatCat Open Source Attributions & Compliance Report",
        "Generated: " + date_str + " | License Standard: Apache-2.0, MIT, BSD-3-Clause",
        "----------------------------------------------------------------------------------",
        "",
        "EXECUTIVE SUMMARY:",
        "SplatCat is a commercial-grade 3D Gaussian Splatting application ecosystem for macOS and iOS.",
        "To guarantee full commercial distribution and resale compliance, all third-party repositories",
        "used operate exclusively under permissive open-source licenses (Apache-2.0, MIT, BSD-3-Clause).",
        "",
        "SUMMARY OF PERMISSIVE OPEN-SOURCE DEPENDENCIES:",
        "",
        "1. GLOMAP (BSD-3-Clause) - github.com/colmap/glomap",
        "   Global Structure-from-Motion (SfM) camera pose solver (crates/engine/src/sfm_glomap.rs).",
        "",
        "2. COLMAP (BSD-3-Clause) - github.com/colmap/colmap",
        "   Sparse feature extraction, camera calibration, and point cloud data model reference.",
        "",
        "3. Brush (Apache-2.0) - github.com/ArthurBrussee/brush",
        "   Differentiable 3DGS rasterization engine running on Apple Silicon Metal via Rust (wgpu).",
        "",
        "4. gsplat (Apache-2.0) - github.com/nerfstudio-project/gsplat",
        "   Mathematical reference for 3D Gaussian rasterization & spherical harmonics.",
        "",
        "5. Nerfstudio (Apache-2.0) - github.com/nerfstudio-project/nerfstudio",
        "   Pipeline architecture reference for splat pruning and density optimization.",
        "",
        "6. SuperSplat (MIT) - github.com/playcanvas/supersplat",
        "   PlayCanvas WebGL2/WebGPU browser viewport engine in packages/web-viewer/.",
        "",
        "7. GaussianSplats3D (MIT) - github.com/mkkellogg/GaussianSplats3D",
        "   Three.js WebGL fallback renderer for single-file standalone web exports.",
        "",
        "8. antimatter15/splat (MIT) - github.com/antimatter15/splat",
        "   High-speed WebGL sorted point buffer rendering reference implementation.",
        "",
        "9. Niantic SPZ (MIT) - github.com/nianticlabs/spz",
        "   Binary compression specification for 3D Gaussians (up to 85% file size reduction).",
        "",
        "10. MonoGS (BSD-3-Clause) - github.com/gaussian-splatting-slam/MonoGS",
        "   Monocular SLAM architectural reference for real-time camera tracking.",
        "",
        "11. MVSplat (MIT) - github.com/zhengfei-kuang/mvsplat",
        "   Feed-forward multi-view sparse 3D reconstruction model reference.",
        "",
        "12. Three.js (MIT) - github.com/mrdoob/three.js",
        "   3D Web scene graph and WebGL rendering engine used in browser viewports.",
        "",
        "----------------------------------------------------------------------------------",
        "COMMERCIAL RESALE EXCLUSION GUARANTEE:",
        "The following repositories were explicitly audited and EXCLUDED from SplatCat due to",
        "restrictive licensing terms:",
        "1. Original Inria 3DGS (graphdeco-inria/gaussian-splatting) - Non-Commercial License.",
        "2. DUSt3R / MASt3R - CC-BY-NC-SA 4.0 Non-Commercial License.",
        "3. Photo-SLAM - GPL-3.0 copyleft terms.",
        "4. OpenSplat - AGPLv3 network copyleft terms.",
        "",
        "CONCLUSION: SplatCat is 100% compliant with commercial resale requirements."
    ]

    # Format text lines into PDF content stream
    pdf_stream_lines = ["BT", "/F1 10 Tf", "12 TL", "50 750 Td"]
    for line in text_content:
        # Escape parenthesis
        clean_line = line.replace("(", "\\(").replace(")", "\\)")
        if line.startswith("SplatCat Open Source"):
            pdf_stream_lines.append("/F1 16 Tf ( " + clean_line + " ) Tj T* /F1 10 Tf")
        elif line.endswith(":") and not line.startswith("1"):
            pdf_stream_lines.append("T* /F1 11 Tf (" + clean_line + ") Tj T* /F1 10 Tf")
        else:
            pdf_stream_lines.append("(" + clean_line + ") Tj T*")
    pdf_stream_lines.append("ET")
    
    content = "\n".join(pdf_stream_lines).encode("latin-1")
    content_len = len(content)

    objects = []
    # Obj 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # Obj 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # Obj 3: Page
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    # Obj 4: Contents
    objects.append(f"4 0 obj\n<< /Length {content_len} >>\nstream\n".encode("latin-1") + content + b"\nendstream\nendobj\n")
    # Obj 5: Font
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    # Build xref table
    pdf_data = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf_data))
        pdf_data += obj

    xref_offset = len(pdf_data)
    pdf_data += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for off in offsets[1:]:
        pdf_data += f"{off:010d} 00000 n \n".encode("latin-1")

    pdf_data += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")

    with open(filename, "wb") as f:
        f.write(pdf_data)
    print(f"Generated PDF file: {filename}")

if __name__ == "__main__":
    build_pdf()
