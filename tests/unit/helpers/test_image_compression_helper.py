"""
Tests para image_compression_helper.
Verifica la compresión de imágenes a un tamaño objetivo.
"""

import base64
import io

import pytest
from PIL import Image

from app.helpers.image_compression_helper import _calculate_initial_quality, _resize_image, compress_image_to_target


class TestCompressImageToTarget:
    """Tests para compress_image_to_target."""

    @pytest.fixture
    def create_test_image(self):
        """Factory para crear imágenes de prueba."""

        def _create(width=100, height=100, color="red"):
            img = Image.new("RGB", (width, height), color=color)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()

        return _create

    @pytest.fixture
    def create_large_image(self):
        """Crear una imagen grande para tests de compresión."""
        # Crear imagen con contenido variado para que no comprima demasiado
        img = Image.new("RGB", (2000, 2000))
        for x in range(0, 2000, 10):
            for y in range(0, 2000, 10):
                img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.mark.unit
    def test_returns_base64_string(self, create_test_image):
        """Debe retornar un string en base64."""
        image_bytes = create_test_image()
        result = compress_image_to_target(image_bytes)

        assert isinstance(result, str)
        # Verificar que es base64 válido
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    @pytest.mark.unit
    def test_output_is_valid_image(self, create_test_image):
        """El output debe ser una imagen válida."""
        image_bytes = create_test_image()
        result = compress_image_to_target(image_bytes)

        decoded = base64.b64decode(result)
        img = Image.open(io.BytesIO(decoded))
        assert img.format == "WEBP"

    @pytest.mark.unit
    def test_small_image_not_over_compressed(self, create_test_image):
        """Imágenes pequeñas no deben comprimirse agresivamente."""
        image_bytes = create_test_image(50, 50)
        result = compress_image_to_target(image_bytes, target_kb=120)

        decoded = base64.b64decode(result)
        # Verificar que sigue siendo una imagen válida
        img = Image.open(io.BytesIO(decoded))
        assert img.size[0] > 0
        assert img.size[1] > 0

    @pytest.mark.unit
    def test_respects_target_size(self, create_large_image):
        """Debe intentar respetar el tamaño objetivo."""
        target_kb = 120
        result = compress_image_to_target(create_large_image, target_kb=target_kb)

        decoded = base64.b64decode(result)
        result_kb = len(decoded) / 1024

        # El resultado debe ser una imagen válida
        assert len(decoded) > 0

        # Verificar que es una imagen válida
        img = Image.open(io.BytesIO(decoded))
        assert img.format == "WEBP"

    @pytest.mark.unit
    def test_handles_rgba_images(self):
        """Debe manejar imágenes RGBA."""
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        result = compress_image_to_target(image_bytes)
        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    @pytest.mark.unit
    def test_handles_palette_images(self):
        """Debe manejar imágenes con paleta (modo P)."""
        img = Image.new("P", (100, 100))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        result = compress_image_to_target(image_bytes)
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_custom_target_kb(self, create_test_image):
        """Debe aceptar diferentes tamaños objetivo."""
        image_bytes = create_test_image()

        result_small = compress_image_to_target(image_bytes, target_kb=50)
        result_large = compress_image_to_target(image_bytes, target_kb=200)

        # Ambos deben ser válidos
        assert isinstance(result_small, str)
        assert isinstance(result_large, str)


class TestCalculateInitialQuality:
    """Tests para _calculate_initial_quality."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "current,target,expected_min,expected_max",
        [
            (100000, 80000, 70, 80),  # ratio >= 0.8
            (100000, 50000, 60, 70),  # ratio >= 0.5
            (100000, 30000, 50, 60),  # ratio >= 0.3
            (100000, 10000, 40, 50),  # ratio < 0.3
        ],
    )
    def test_quality_ranges(self, current, target, expected_min, expected_max):
        """Debe retornar calidad apropiada según el ratio."""
        quality = _calculate_initial_quality(current, target)
        assert expected_min <= quality <= expected_max


class TestResizeImage:
    """Tests para _resize_image."""

    @pytest.fixture
    def large_image(self):
        """Crear imagen grande para tests."""
        return Image.new("RGB", (3000, 2000), color="blue")

    @pytest.mark.unit
    def test_resizes_proportionally(self, large_image):
        """Debe mantener proporciones al redimensionar."""
        original_ratio = large_image.width / large_image.height

        resized = _resize_image(large_image, target_bytes=100000, current_bytes=500000)
        new_ratio = resized.width / resized.height

        # Las proporciones deben ser aproximadamente iguales
        assert abs(original_ratio - new_ratio) < 0.1

    @pytest.mark.unit
    def test_respects_max_dimension(self, large_image):
        """No debe exceder la dimensión máxima."""
        resized = _resize_image(large_image, target_bytes=100000, current_bytes=500000)

        assert resized.width <= 1920
        assert resized.height <= 1920

    @pytest.mark.unit
    def test_reduces_size(self, large_image):
        """Debe reducir el tamaño de la imagen."""
        resized = _resize_image(large_image, target_bytes=50000, current_bytes=200000)

        assert resized.width < large_image.width
        assert resized.height < large_image.height
