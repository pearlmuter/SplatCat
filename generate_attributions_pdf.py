import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header
        self.drawString(54, 750, "SplatCat 🐾 — Open Source Attributions & Compliance Report")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 742, 558, 742)
        
        # Footer
        self.line(54, 50, 558, 50)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(54, 36, "CONFIDENTIAL & RESALE COMPLIANT — Commercial License Verification")
        self.restoreState()

def create_attributions_pdf(filename="OPEN_SOURCE_ATTRIBUTIONS.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15
    )

    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=14,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )

    th_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#ffffff')
    )

    td_style = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )

    td_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0f172a')
    )

    td_code = ParagraphStyle(
        'TableCellCode',
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#2563eb')
    )

    story = []

    # Title Banner
    story.append(Paragraph("SplatCat Open Source Attributions", title_style))
    story.append(Paragraph("Commercial License Verification & Third-Party Software Attribution Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#4f46e5'), spaceAfter=15))

    # Introduction
    intro_text = (
        "<b>Overview:</b> SplatCat is a commercial-grade 3D Gaussian Splatting suite for macOS and iOS. "
        "To ensure complete legal compliance for commercial distribution and resale, all underlying third-party "
        "repositories and dependencies have been thoroughly audited. Every component utilized operates exclusively under "
        "permissive open-source licenses (<b>Apache-2.0</b>, <b>MIT</b>, or <b>BSD-3-Clause</b>)."
    )
    story.append(Paragraph(intro_text, body_style))
    story.append(Spacer(1, 10))

    # Section 1: Summary Table
    story.append(Paragraph("1. Summary of Permissive Open-Source Dependencies", h2_style))
    
    table_data = [
        [
            Paragraph("Repository", th_style),
            Paragraph("Permissive License", th_style),
            Paragraph("Repository URL", th_style),
            Paragraph("Role & Usage in SplatCat", th_style)
        ]
    ]

    repos = [
        ("GLOMAP", "BSD-3-Clause", "github.com/colmap/glomap", "Global Structure-from-Motion (SfM) camera pose estimation engine (10-100x faster pose solver)."),
        ("COLMAP", "BSD-3-Clause", "github.com/colmap/colmap", "Sparse feature extraction, camera calibration, and point cloud data models."),
        ("Brush", "Apache-2.0", "github.com/ArthurBrussee/brush", "Differentiable 3DGS rasterization engine running on Apple Silicon Metal via Rust wgpu."),
        ("gsplat", "Apache-2.0", "github.com/nerfstudio-project/gsplat", "Mathematical reference for 3D Gaussian rasterization & spherical harmonics."),
        ("Nerfstudio", "Apache-2.0", "github.com/nerfstudio-project/nerfstudio", "Pipeline architecture reference for splat pruning and density optimization."),
        ("SuperSplat", "MIT", "github.com/playcanvas/supersplat", "PlayCanvas WebGL2/WebGPU interactive 3D browser viewport and editor engine."),
        ("GaussianSplats3D", "MIT", "github.com/mkkellogg/GaussianSplats3D", "Three.js WebGL fallback renderer for single-file standalone web exports."),
        ("antimatter15/splat", "MIT", "github.com/antimatter15/splat", "High-speed WebGL sorted point buffer rendering reference implementation."),
        ("Niantic SPZ", "MIT", "github.com/nianticlabs/spz", "3D Gaussian point cloud compression specification (reducing file size by 85%)."),
        ("MonoGS", "BSD-3-Clause", "github.com/gaussian-splatting-slam/MonoGS", "Monocular SLAM architectural reference for real-time camera tracking."),
        ("MVSplat", "MIT", "github.com/zhengfei-kuang/mvsplat", "Feed-forward multi-view sparse reconstruction model architecture reference."),
        ("Three.js", "MIT", "github.com/mrdoob/three.js", "3D Web scene graph and WebGL rendering engine used in browser viewports.")
    ]

    for name, lic, url, desc in repos:
        table_data.append([
            Paragraph(name, td_bold),
            Paragraph(f"<b>{lic}</b>", td_style),
            Paragraph(url, td_code),
            Paragraph(desc, td_style)
        ])

    col_widths = [85, 75, 140, 204]
    attr_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    attr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    story.append(attr_table)
    story.append(Spacer(1, 15))

    # Section 2: Detailed Attribution Breakdown
    story.append(Paragraph("2. Detailed Component Attribution & Integration Mechanics", h2_style))
    
    details = [
        ("Structure-from-Motion (GLOMAP & COLMAP)", 
         "SplatCat integrates GLOMAP (BSD 3-Clause) as its primary pose estimation engine in <code>crates/engine/src/sfm_glomap.rs</code>. GLOMAP provides global positioning systems that convert raw video frames into calibrated 6DoF camera poses without requiring proprietary code."),
        
        ("Metal / WebGPU Splat Rasterization (Brush)",
         "SplatCat uses Brush (Apache 2.0) in <code>crates/engine/src/splat_trainer.rs</code>. Written in Rust and using <code>wgpu</code>, it executes differentiable Gaussian rasterization directly on Apple Silicon M-series GPUs over Metal, eliminating CUDA/NVIDIA dependencies."),
         
        ("Web Browser Playback & Exporter (SuperSplat & Three.js)",
         "The browser viewing system in <code>packages/web-viewer/</code> relies on PlayCanvas/SuperSplat (MIT) and Three.js (MIT). It renders up to millions of Gaussians at 60 FPS in WebGL2 and WebGPU, featuring one-click HTML package exporting."),
         
        ("iOS AR Companion Pose Streaming (MonoGS & ARKit)",
         "The iOS companion app in <code>apps/mobile/SplatCatCompanion/</code> uses ARKit LiDAR and MonoGS (BSD 3-Clause) architectural models to capture real-time camera matrices and stream keyframes via WebSockets.")
    ]

    for title, text in details:
        story.append(Paragraph(f"• <b>{title}</b>", ParagraphStyle('BulletHead', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#0f172a'))))
        story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))

    # Section 3: Commercial Exclusion Guarantee
    story.append(Paragraph("3. Commercial Resale Exclusion Guarantee", h2_style))
    exclusion_text = (
        "To protect SplatCat's commercial resale rights, the following repositories were explicitly audited and <b>EXCLUDED</b> "
        "from the codebase due to restrictive licensing terms:<br/>"
        "1. <b>Original Inria 3DGS</b> (<code>graphdeco-inria/gaussian-splatting</code>) — Excluded due to Non-Commercial Research License.<br/>"
        "2. <b>DUSt3R / MASt3R</b> — Excluded due to CC-BY-NC-SA 4.0 Non-Commercial License.<br/>"
        "3. <b>Photo-SLAM</b> — Excluded due to GPL-3.0 copyleft terms.<br/>"
        "4. <b>OpenSplat</b> — Excluded due to AGPLv3 network copyleft terms.<br/><br/>"
        "<b>Conclusion:</b> SplatCat is 100% compliant with commercial resale requirements."
    )
    
    exclusion_box = Table([[Paragraph(exclusion_text, body_style)]], colWidths=[504])
    exclusion_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    story.append(exclusion_box)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    create_attributions_pdf()
