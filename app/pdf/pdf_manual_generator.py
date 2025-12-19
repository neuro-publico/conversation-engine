import base64
import os
from app.pdf.pdf_generator import PDFGenerator
from app.configurations.pdf_manual_config import PDF_MANUAL_SECTION_ORDER, get_sections_for_language


class PDFManualGenerator:
    def __init__(self, product_name: str, language: str = "es"):
        self.product_name = product_name
        self.language = language
        self.sections = get_sections_for_language(language)
        self.pdf = PDFGenerator(product_name)

    async def create_manual(self, data: dict, title: str = None, image_url: str = None) -> str:
        # Usar el título personalizado si se proporciona, sino usar el por defecto
        cover_title = title if title else f"User Manual for {self.product_name}"
        
        # Establecer el título personalizado para que aparezca en el header de todas las páginas
        if title:
            self.pdf.set_custom_title(title)
        
        self.pdf.add_cover_page(
            cover_title,
            "Everything You Need to Know to Get Started",
            image_url
        )
        self.pdf.set_auto_page_break(auto=True, margin=20)

        for key in PDF_MANUAL_SECTION_ORDER:
            self.pdf.add_section(self.sections[key], data.get(key, ""))

        pdf_str = self.pdf.output(dest="S")
        pdf_bytes = pdf_str.encode("latin1")

        base64_str = base64.b64encode(pdf_bytes).decode("utf-8")

        return base64_str