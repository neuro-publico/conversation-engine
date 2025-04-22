from fpdf import FPDF


class PDFGenerator(FPDF):
    def __init__(self, product_name):
        super().__init__()
        self.product_name = product_name
        self.header_height = 0
        self.version = "1.0"  # Versión del documento

    def header(self):
        if self.page_no() == 1:
            return
            
        initial_y = self.get_y()
        
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 51, 102)
        
        title = f"User Manual for {self.product_name}"
        
        self.set_y(10)
        
        width_available = self.w - 20
        self.x = 10
        
        self.multi_cell(width_available, 8, title, align="C")
        
        end_y = self.get_y() + 2
        self.set_line_width(0.5)
        self.set_draw_color(0, 51, 102)
        self.line(10, end_y, self.w - 10, end_y)
        
        self.set_y(end_y + 10)
        
        self.header_height = self.get_y() - initial_y

    def footer(self):
        # No mostrar el pie de página en la primera página (portada)
        if self.page_no() == 1:
            return
            
        self.set_y(-20)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()-1}", 0, 0, "C")  # Restar 1 porque la portada no cuenta

    def add_cover_page(self, title, subtitle=""):
        self.add_page()
        
        # Dimensiones y márgenes
        page_width = self.w
        page_height = self.h
        margin = 15
        
        # Borde completo alrededor de la página
        self.set_draw_color(0, 51, 102)
        self.set_line_width(0.7)
        self.rect(margin, margin, page_width - 2*margin, page_height - 2*margin)
        
        # Título principal
        self.set_font("Helvetica", "B", 24)  # Reducir ligeramente el tamaño para evitar desbordamiento
        self.set_text_color(0, 51, 102)
        
        # Definir el ancho efectivo del texto con márgenes seguros
        text_width = page_width - 2*margin - 20  # 10px de margen adicional a cada lado
        
        # Posicionar para el título
        self.set_y(page_height * 0.3)  # Aproximadamente a 1/3 de la página
        self.set_x(margin + 10)  # Margen izquierdo + margen adicional
        
        # Dibujar el título con múltiples líneas si es necesario
        self.multi_cell(text_width, 16, title, align="C")
        
        # Guardar posición después del título
        title_end_y = self.get_y()
        
        # Subtítulo si existe
        if subtitle:
            self.ln(15)  # Espacio entre título y subtítulo
            self.set_font("Helvetica", "", 18)
            self.set_text_color(80, 80, 80)
            self.set_x(margin + 10)  # Asegurar margen correcto
            self.multi_cell(text_width, 12, subtitle, align="C")
        
        # Agregar información de la versión en la parte inferior, dentro del marco
        self.set_font("Helvetica", "I", 11)
        self.set_text_color(100, 100, 100)
        
        # Posicionar el texto de versión en la parte inferior pero dentro del marco
        version_y = page_height - margin - 20  # 20 puntos arriba del borde inferior
        self.set_y(version_y)
        self.set_x(margin + 10)
        self.multi_cell(text_width, 10, f"Document Version: {self.version}", align="C")
        
        self.add_page()
    
    # Método para establecer la versión del documento
    def set_document_version(self, version):
        self.version = version
    
    def get_multi_cell_height(self, w, h, txt, align="J"):
        x = self.x
        y = self.y
        
        lines = 1
        width = 0
        text = txt.split(' ')
        for word in text:
            word_width = self.get_string_width(word + ' ')
            if width + word_width > w:
                lines += 1
                width = word_width
            else:
                width += word_width
        
        self.x = x
        self.y = y
        
        return lines * h

    def add_section(self, title, content):
        if self.get_y() > self.h * 0.6:
            self.add_page()

        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(0, 102, 204)
        self.cell(0, 12, title, ln=True, fill=True, align="C", border=1)
        self.ln(6)

        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 12)

        if isinstance(content, list):
            formatted_text = "\n".join(str(item) for item in content)
        else:
            formatted_text = content.replace("\\n", "\n")

        self.multi_cell(0, 8, formatted_text)

        self.ln(8)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        current_y = self.get_y()
        self.line(10, current_y, self.w - 10, current_y)
        self.ln(10)
