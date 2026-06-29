from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

input_md = Path("DESIGN.md")
output_pdf = Path("DESIGN.pdf")

lines = input_md.read_text(encoding="utf-8").splitlines()

c = canvas.Canvas(str(output_pdf), pagesize=letter)
width, height = letter
margin = 72
y = height - margin
line_height = 14

for line in lines:
    if y < margin:
        c.showPage()
        y = height - margin
    if line.startswith("# "):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, line[2:].strip())
        y -= line_height * 2
    elif line.startswith("## "):
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, line[3:].strip())
        y -= line_height * 1.5
    elif line.startswith("### "):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, line[4:].strip())
        y -= line_height * 1.5
    else:
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, line)
        y -= line_height

c.save()
print(f"Exported {output_pdf}")
