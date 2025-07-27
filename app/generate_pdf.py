from xhtml2pdf import pisa
from io import BytesIO

def generate_pdf(html_content):
    pdf = BytesIO()
    pisa.CreatePDF(BytesIO(html_content.encode("utf-8")), dest=pdf)
    pdf.seek(0)
    return pdf
 
