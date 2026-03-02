# app/report_generator.py

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import ListFlowable, ListItem
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.styles import ListStyle
import io


def generate_pdf_report(result):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = styles["Heading1"]

    elements.append(Paragraph("AI Resume Screening Report", heading))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"Candidate: {result['filename']}", normal))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph(f"Final ATS Score: {result['final_score']}%", normal))
    elements.append(Paragraph(f"Semantic Score: {result['semantic_score']}%", normal))
    elements.append(Paragraph(f"Skill Score: {result['skill_score']}%", normal))
    elements.append(Paragraph(f"Experience Score: {result['experience_score']}%", normal))

    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Matched Skills:", styles["Heading2"]))
    for skill in result["matched_skills"]:
        elements.append(Paragraph(f"- {skill}", normal))

    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Missing Skills:", styles["Heading2"]))
    for skill in result["missing_skills"]:
        elements.append(Paragraph(f"- {skill}", normal))

    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("AI Explanation:", styles["Heading2"]))
    elements.append(Paragraph(result["explanation"], normal))

    doc.build(elements)
    buffer.seek(0)

    return buffer