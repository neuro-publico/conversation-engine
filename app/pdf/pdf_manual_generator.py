import base64
import os
from app.pdf.pdf_generator import PDFGenerator
from app.configurations.pdf_manual_config import PDF_MANUAL_SECTIONS, PDF_MANUAL_SECTION_ORDER


class PDFManualGenerator:
    def __init__(self, product_name: str):
        self.product_name = product_name
        self.pdf = PDFGenerator(product_name)

    async def create_manual(self, data: dict) -> str:
        self.pdf.add_cover_page(
            f"User Manual for {self.product_name}",
            "Everything You Need to Know to Get Started"
        )
        self.pdf.set_auto_page_break(auto=True, margin=20)

        for key in PDF_MANUAL_SECTION_ORDER:
            self.pdf.add_section(PDF_MANUAL_SECTIONS[key], data.get(key, ""))

        pdf_str = self.pdf.output(dest="S")
        pdf_bytes = pdf_str.encode("latin1")

        base64_str = base64.b64encode(pdf_bytes).decode("utf-8")

        return base64_str