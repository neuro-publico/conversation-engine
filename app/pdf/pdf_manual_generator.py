import base64
import os
from app.pdf.pdf_generator import PDFGenerator
from app.configurations.pdf_manual_config import PDF_MANUAL_SECTIONS, PDF_MANUAL_SECTION_ORDER


class PDFManualGenerator:
    def __init__(self, product_name: str):
        self.product_name = product_name
        self.pdf = PDFGenerator(product_name)

    async def create_manual(self, data: dict, file_name: str) -> str:
        self.pdf.add_cover_page(
            f"User Manual for {self.product_name}",
            "Everything You Need to Know to Get Started"
        )
        self.pdf.set_auto_page_break(auto=True, margin=20)

        for key in PDF_MANUAL_SECTION_ORDER:
            self.pdf.add_section(PDF_MANUAL_SECTIONS[key], data.get(key, ""))

        self.pdf.output(file_name)

        with open(file_name, "rb") as f:
            pdf_bytes = f.read()

        base64_str = base64.b64encode(pdf_bytes).decode("utf-8")
        os.remove(file_name)

        return base64_str
