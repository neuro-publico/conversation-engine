from fpdf import FPDF


class PDFGenerator(FPDF):
    def __init__(self, product_name):
        super().__init__()
        self.product_name = product_name

    def header(self):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(0, 51, 102)  # Azul oscuro
        self.cell(0, 10, f"User Manual for {self.product_name}", ln=True, align="C")
        self.ln(5)
        self.set_line_width(0.5)
        self.set_draw_color(0, 51, 102)
        self.line(10, 25, self.w - 10, 25)
        self.ln(10)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def add_cover_page(self, title, subtitle=""):
        self.add_page()
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(0, 51, 102)
        self.ln(40)  # Espacio superior para la portada
        self.cell(0, 20, title, ln=True, align="C")
        if subtitle:
            self.ln(10)
            self.set_font("Helvetica", "", 16)
            self.cell(0, 10, subtitle, ln=True, align="C")
        self.ln(20)
        self.add_page()

    def add_section(self, title, content):
        if self.get_y() > self.h * 0.6:
            self.add_page()

        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(0, 102, 204)  # Azul
        self.cell(0, 12, title, ln=True, fill=True, align="C", border=1)
        self.ln(6)

        # Contenido de la sección
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 12)

        if isinstance(content, list):
            formatted_text = "\n".join(str(item) for item in content)
        else:
            formatted_text = content.replace("\\n", "\n")

        self.multi_cell(0, 8, formatted_text)

        self.ln(8)
        self.set_draw_color(200, 200, 200)  # Línea gris claro
        self.set_line_width(0.3)
        current_y = self.get_y()
        self.line(10, current_y, self.w - 10, current_y)
        self.ln(10)
