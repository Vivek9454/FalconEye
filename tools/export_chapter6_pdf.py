import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

ROOT = os.path.dirname(os.path.dirname(__file__))
DOC = os.path.join(ROOT, 'docs', 'CHAPTER6_TESTING.md')
ASSETS = os.path.join(ROOT, 'assets')


def build_pdf(out_path):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER)
    h2 = styles['Heading2']
    body = styles['BodyText']
    body.fontName = 'Times-Roman'
    story = []

    # Title
    story.append(Paragraph('Chapter 6 — Testing', title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Load markdown as plain paragraphs (simple handling)
    with open(DOC, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    for ln in lines:
        if ln.startswith('## '):
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph(ln[3:], h2))
            story.append(Spacer(1, 0.05 * inch))
        elif ln.startswith('- ') or ln.startswith('  - '):
            story.append(Paragraph(ln, body))
        elif ln.strip() == 'Figures':
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph('Figures', h2))
            story.append(Spacer(1, 0.05 * inch))
        elif ln.strip().startswith('- Figure 6.1'):
            p = os.path.join(ASSETS, 'testing_class_distribution.png')
            if os.path.exists(p):
                story.append(Image(p, width=6.0*inch, height=4.0*inch))
                story.append(Paragraph('Figure 6.1: Weekly Detections by Class', body))
                story.append(Spacer(1, 0.2 * inch))
        elif ln.strip().startswith('- Figure 6.2'):
            p = os.path.join(ASSETS, 'testing_precision_recall.png')
            if os.path.exists(p):
                story.append(Image(p, width=6.0*inch, height=4.0*inch))
                story.append(Paragraph('Figure 6.2: Average Precision/Recall by Class', body))
                story.append(Spacer(1, 0.2 * inch))
        elif ln.strip().startswith('- Figure 6.3'):
            p = os.path.join(ASSETS, 'testing_latency_trend.png')
            if os.path.exists(p):
                story.append(Image(p, width=6.0*inch, height=4.0*inch))
                story.append(Paragraph('Figure 6.3: Median Alert Latency Over Time', body))
                story.append(Spacer(1, 0.2 * inch))
        elif ln.startswith('# '):
            # ignore the main header, already added
            continue
        else:
            if ln.strip():
                story.append(Paragraph(ln, body))
            else:
                story.append(Spacer(1, 0.08 * inch))

    # Additional figures if available
    story.append(PageBreak())
    story.append(Paragraph('Additional Figures', h2))
    story.append(Spacer(1, 0.1 * inch))

    extras = [
        ('architecture.png', 'System Architecture'),
        ('flow_input_process_output.png', 'Input–Process–Output Flow'),
        ('class_distribution_present.png', 'Representative Class Distribution'),
        ('dataset_today_collage.jpg', 'Daily Samples Collage'),
        ('dataset_today_targets.jpg', 'Daily Targets Collage'),
    ]
    for fname, caption in extras:
        p = os.path.join(ASSETS, fname)
        if os.path.exists(p):
            story.append(Image(p, width=6.0*inch, height=4.0*inch))
            story.append(Paragraph(caption, body))
            story.append(Spacer(1, 0.2 * inch))

    # Try to include a detection snapshot if present
    try:
        candidates = [f for f in os.listdir(ASSETS) if 'detect' in f.lower() and f.lower().endswith(('.jpg','.png'))]
        if candidates:
            p = os.path.join(ASSETS, sorted(candidates)[0])
            story.append(Image(p, width=6.0*inch, height=4.0*inch))
            story.append(Paragraph('Sample Annotated Detection', body))
            story.append(Spacer(1, 0.2 * inch))
    except Exception:
        pass

    doc = SimpleDocTemplate(out_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    doc.build(story)
    return out_path


if __name__ == '__main__':
    out = os.path.expanduser('~/Downloads/Chapter6_Testing_FalconEye.pdf')
    print(build_pdf(out))
