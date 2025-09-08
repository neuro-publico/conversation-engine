from fpdf import FPDF
import requests
import io
import os
from typing import Optional, Tuple
try:
    import PIL.Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILImage = None
    PILLOW_AVAILABLE = False

# Constantes de diseño
class PDFConstants:
    # Colores
    HEADER_COLOR = (0, 0, 0)  # Negro para el header (título y línea)
    SECTION_BG_COLOR = (64, 64, 64)  # Gris oscuro más suave para el fondo del título de la sección
    SECTION_BORDER_COLOR = (255, 140, 0)  # Naranja/dorado para el borde
    WHITE_COLOR = (255, 255, 255)
    BLACK_COLOR = (0, 0, 0)
    GRAY_COLOR = (128, 128, 128)
    LIGHT_GRAY_COLOR = (200, 200, 200)
    
    # Tamaños de fuente
    HEADER_FONT_SIZE = 16
    COVER_TITLE_FONT_SIZE = 28
    SECTION_TITLE_FONT_SIZE = 14
    CONTENT_FONT_SIZE = 12
    FOOTER_FONT_SIZE = 10
    
    # Márgenes y espaciado
    PAGE_MARGIN = 15
    HEADER_MARGIN = 10
    OVERLAY_HEIGHT = 80
    LINE_WIDTH_THIN = 0.3
    LINE_WIDTH_MEDIUM = 0.5
    LINE_WIDTH_THICK = 0.7
    
    # Otros
    IMAGE_QUALITY = 85
    TEMP_IMAGE_PATH = "/tmp/temp_cover_image.jpg"
    REQUEST_TIMEOUT = 10


class PDFGenerator(FPDF):
    def __init__(self, product_name: str):
        super().__init__()
        self.product_name = product_name
        self.custom_title: Optional[str] = None
        self.header_height = 0
        self.version = "1.0"
        self.first_section = True  # Para controlar la primera sección

    def header(self) -> None:
        """Genera el header de cada página (excepto la portada)."""
        if self.page_no() == 1:
            return
            
        initial_y = self.get_y()
        
        self.set_font("Helvetica", "B", PDFConstants.HEADER_FONT_SIZE)
        self.set_text_color(*PDFConstants.HEADER_COLOR)
        
        title = self.custom_title if self.custom_title else f"User Manual for {self.product_name}"
        clean_title = self._clean_text_for_latin1(title)
        
        self.set_y(PDFConstants.HEADER_MARGIN)
        width_available = self.w - (2 * PDFConstants.HEADER_MARGIN)
        self.x = PDFConstants.HEADER_MARGIN
        
        self.multi_cell(width_available, 8, clean_title, align="C")
        
        end_y = self.get_y() + 2
        self.set_line_width(PDFConstants.LINE_WIDTH_MEDIUM)
        self.set_draw_color(*PDFConstants.HEADER_COLOR)
        self.line(PDFConstants.HEADER_MARGIN, end_y, self.w - PDFConstants.HEADER_MARGIN, end_y)
        
        self.set_y(end_y + PDFConstants.HEADER_MARGIN)
        self.header_height = self.get_y() - initial_y

    def footer(self) -> None:
        """Genera el footer de cada página (excepto la portada)."""
        if self.page_no() == 1:
            return
            
        self.set_y(-20)
        self.set_font("Helvetica", "I", PDFConstants.FOOTER_FONT_SIZE)
        self.set_text_color(*PDFConstants.GRAY_COLOR)
        self.cell(0, 10, f"Page {self.page_no()-1}", 0, 0, "C")

    def add_cover_page(self, title: str, subtitle: str = "", image_url: Optional[str] = None) -> None:
        """
        Crea la página de portada del PDF.
        
        Args:
            title: Título principal de la portada
            subtitle: Subtítulo opcional
            image_url: URL de imagen opcional para usar como fondo
        """
        self.add_page()
        
        page_width = self.w
        page_height = self.h
        
        if image_url and PILLOW_AVAILABLE:
            # Solo mostrar la imagen sin texto si hay imagen
            self._create_image_only_cover(image_url, page_width, page_height)
        else:
            # Portada tradicional con texto si no hay imagen
            title_y_pos, title_color = self._create_cover_background(None, page_width, page_height)
            self._add_cover_text(title, subtitle, title_y_pos, title_color, page_width, page_height, None)
        
        self.add_page()
    
    def _create_cover_background(self, image_url: Optional[str], page_width: float, page_height: float) -> Tuple[float, Tuple[int, int, int]]:
        """Crea el fondo de la portada (imagen o borde tradicional)."""
        if image_url and PILLOW_AVAILABLE:
            image_result = self._download_and_process_image(image_url)
            if image_result:
                temp_path, img_width, img_height = image_result
                
                available_width = page_width - 2 * PDFConstants.PAGE_MARGIN
                available_height = page_height - 2 * PDFConstants.PAGE_MARGIN
                
                x_pos, y_pos, final_width, final_height = self._calculate_image_dimensions(
                    img_width, img_height, available_width, available_height
                )
                
                self.image(temp_path, x=x_pos, y=y_pos, w=final_width, h=final_height)
                self._cleanup_temp_image()
                
                # Crear overlay para el título
                overlay_y = page_height - PDFConstants.OVERLAY_HEIGHT - PDFConstants.PAGE_MARGIN
                self.set_fill_color(*PDFConstants.BLACK_COLOR)
                self.rect(PDFConstants.PAGE_MARGIN, overlay_y, 
                         page_width - 2 * PDFConstants.PAGE_MARGIN, 
                         PDFConstants.OVERLAY_HEIGHT, 'F')
                
                return overlay_y + 15, PDFConstants.WHITE_COLOR
        
        # Portada tradicional con borde
        self.set_draw_color(*PDFConstants.HEADER_COLOR)
        self.set_line_width(PDFConstants.LINE_WIDTH_THICK)
        self.rect(PDFConstants.PAGE_MARGIN, PDFConstants.PAGE_MARGIN, 
                 page_width - 2 * PDFConstants.PAGE_MARGIN, 
                 page_height - 2 * PDFConstants.PAGE_MARGIN)
        
        return page_height * 0.4, PDFConstants.HEADER_COLOR
    
    def _add_cover_text(self, title: str, subtitle: str, title_y_pos: float, 
                       title_color: Tuple[int, int, int], page_width: float, 
                       page_height: float, image_url: Optional[str]) -> None:
        """Agrega el texto de la portada."""
        self.set_font("Helvetica", "B", PDFConstants.COVER_TITLE_FONT_SIZE)
        self.set_text_color(*title_color)
        
        text_width = page_width - 2 * PDFConstants.PAGE_MARGIN - 20
        
        self.set_y(title_y_pos)
        self.set_x(PDFConstants.PAGE_MARGIN + 10)
        clean_title = self._clean_text_for_latin1(title)
        self.multi_cell(text_width, 18, clean_title, align="C")
        
        # Solo mostrar subtítulo y versión si no hay imagen
        if not image_url:
            if subtitle:
                self.ln(15)
                self.set_font("Helvetica", "", 18)
                self.set_text_color(80, 80, 80)
                self.set_x(PDFConstants.PAGE_MARGIN + 10)
                clean_subtitle = self._clean_text_for_latin1(subtitle)
                self.multi_cell(text_width, 12, clean_subtitle, align="C")
            
            self.set_font("Helvetica", "I", 11)
            self.set_text_color(100, 100, 100)
            version_y = page_height - PDFConstants.PAGE_MARGIN - 20
            self.set_y(version_y)
            self.set_x(PDFConstants.PAGE_MARGIN + 10)
            self.multi_cell(text_width, 10, f"Document Version: {self.version}", align="C")
    
    def set_document_version(self, version: str) -> None:
        """Establece la versión del documento."""
        self.version = version
    
    def set_custom_title(self, title: str) -> None:
        """Establece el título personalizado que aparecerá en el header de cada página."""
        self.custom_title = title
    
    def _download_and_process_image(self, image_url: str) -> Optional[Tuple[str, int, int]]:
        """
        Descarga y procesa una imagen desde una URL.
        
        Returns:
            Tuple con (ruta_temporal, ancho, alto) o None si falla
        """
        try:
            response = requests.get(image_url, timeout=PDFConstants.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            image = PILImage.open(io.BytesIO(response.content))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image.save(PDFConstants.TEMP_IMAGE_PATH, "JPEG", quality=PDFConstants.IMAGE_QUALITY)
            
            return PDFConstants.TEMP_IMAGE_PATH, image.width, image.height
            
        except Exception as e:
            print(f"Error al procesar imagen: {e}")
            return None
    
    def _calculate_image_dimensions(self, img_width: int, img_height: int, 
                                   available_width: float, available_height: float) -> Tuple[float, float, float, float]:
        """
        Calcula las dimensiones y posición para centrar una imagen manteniendo la proporción.
        
        Returns:
            Tuple con (x_pos, y_pos, final_width, final_height)
        """
        scale_width = available_width / img_width
        scale_height = available_height / img_height
        scale = min(scale_width, scale_height)
        
        final_width = img_width * scale
        final_height = img_height * scale
        
        x_pos = (self.w - final_width) / 2
        y_pos = (self.h - final_height) / 2
        
        return x_pos, y_pos, final_width, final_height
    
    def _cleanup_temp_image(self) -> None:
        """Elimina el archivo temporal de imagen si existe."""
        if os.path.exists(PDFConstants.TEMP_IMAGE_PATH):
            os.remove(PDFConstants.TEMP_IMAGE_PATH)
    
    def _create_image_only_cover(self, image_url: str, page_width: float, page_height: float) -> None:
        """Crea una portada que muestra solo la imagen sin texto."""
        image_result = self._download_and_process_image(image_url)
        if image_result:
            temp_path, img_width, img_height = image_result
            
            # Usar toda la página disponible para la imagen
            available_width = page_width
            available_height = page_height
            
            x_pos, y_pos, final_width, final_height = self._calculate_image_dimensions(
                img_width, img_height, available_width, available_height
            )
            
            # Centrar la imagen en toda la página
            x_pos = (page_width - final_width) / 2
            y_pos = (page_height - final_height) / 2
            
            self.image(temp_path, x=x_pos, y=y_pos, w=final_width, h=final_height)
            self._cleanup_temp_image()
    
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

    def add_section(self, title: str, content: str) -> None:
        """
        Agrega una sección al PDF con título en negrita y contenido.
        Cada sección inicia en una nueva página.
        
        Args:
            title: Título de la sección
            content: Contenido de la sección
        """
        # Cada sección inicia en una nueva página (excepto la primera)
        if not self.first_section:
            self.add_page()
        else:
            self.first_section = False

        # Crear el borde naranja exterior primero
        margin = 10
        current_y = self.get_y()
        
        # Dibujar el rectángulo del borde naranja
        self.set_draw_color(*PDFConstants.SECTION_BORDER_COLOR)
        self.set_line_width(0.5)  # Línea más delgada
        self.rect(margin, current_y, self.w - 2*margin, 16)  # Rectángulo exterior
        
        # Crear el título con fondo negro y texto blanco (con pequeño margen interno)
        self.set_font("Helvetica", "B", PDFConstants.SECTION_TITLE_FONT_SIZE)
        self.set_text_color(*PDFConstants.WHITE_COLOR)  # Texto blanco
        self.set_fill_color(*PDFConstants.SECTION_BG_COLOR)  # Fondo negro
        
        # Posicionar el título con un pequeño margen interno
        self.set_xy(margin + 2, current_y + 2)  # 2 puntos de separación
        clean_title = self._clean_text_for_latin1(title)
        self.cell(self.w - 2*margin - 4, 12, clean_title, ln=False, fill=True, align="C", border=0)
        
        # Mover a la siguiente línea
        self.set_y(current_y + 16 + 6)

        # Contenido de la sección
        self.set_text_color(*PDFConstants.BLACK_COLOR)
        self.set_font("Helvetica", "", PDFConstants.CONTENT_FONT_SIZE)

        formatted_text = self._format_content(content)
        self.multi_cell(0, 8, formatted_text)

        # Separador entre secciones
        self.ln(8)
        self.set_draw_color(*PDFConstants.LIGHT_GRAY_COLOR)
        self.set_line_width(PDFConstants.LINE_WIDTH_THIN)
        current_y = self.get_y()
        self.line(PDFConstants.HEADER_MARGIN, current_y, self.w - PDFConstants.HEADER_MARGIN, current_y)
        self.ln(10)
    
    def _format_content(self, content) -> str:
        """Formatea el contenido de una sección."""
        if isinstance(content, list):
            text = "\n".join(str(item) for item in content)
        else:
            text = content.replace("\\n", "\n")
        
        # Limpiar caracteres que no son compatibles con latin-1
        return self._clean_text_for_latin1(text)
    
    def _clean_text_for_latin1(self, text: str) -> str:
        """Limpia el texto para que sea compatible con latin-1."""
        # Reemplazos de caracteres especiales comunes
        replacements = {
            '\u2022': '•',  # Bullet point
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2026': '...',  # Horizontal ellipsis
            '\u00a0': ' ',  # Non-breaking space
        }
        
        # Aplicar reemplazos
        for unicode_char, replacement in replacements.items():
            text = text.replace(unicode_char, replacement)
        
        # Intentar codificar y decodificar para detectar otros problemas
        try:
            text.encode('latin-1')
            return text
        except UnicodeEncodeError:
            # Si aún hay problemas, reemplazar caracteres problemáticos
            return text.encode('latin-1', errors='replace').decode('latin-1')
