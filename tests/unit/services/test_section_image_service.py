import pytest

from app.requests.section_image_request import SectionImageRequest
from app.services.section_image_service import SectionImageService


@pytest.fixture
def service():
    return SectionImageService()


@pytest.fixture
def base_request():
    return SectionImageRequest(
        product_name="AirPods Tercera Generación",
        product_description="Excelente calidad de sonido. Bluetooth. Carga inalámbrica.",
        language="es",
        product_image_url="https://example.com/airpods.jpg",
        template_image_url="https://example.com/template.webp",
        image_format="9:16",
        price=29990,
        price_fake=44985,
        user_prompt="Modifica esta imagen para el producto.",
        detect_cta_buttons=True,
        owner_id="test-owner",
    )


class TestParseCtaButtons:

    def test_single_button(self, service):
        text = 'BOTONES:\n- "COMPRAR AHORA" en [850, 160, 920, 840]'
        result = service._parse_cta_buttons(text)
        assert len(result) == 1
        assert result[0].label == "COMPRAR AHORA"
        assert result[0].coords == [850, 160, 920, 840]

    def test_multiple_buttons(self, service):
        text = 'BOTONES:\n- "COMPRAR" en [850, 160, 920, 840]\n- "VER MÁS" en [700, 200, 750, 800]'
        result = service._parse_cta_buttons(text)
        assert len(result) == 2
        assert result[0].label == "COMPRAR"
        assert result[1].label == "VER MÁS"

    def test_no_buttons_ninguno(self, service):
        text = "BOTONES: ninguno"
        result = service._parse_cta_buttons(text)
        assert result == []

    def test_no_buttons_none(self, service):
        text = "BOTONES: none"
        result = service._parse_cta_buttons(text)
        assert result == []

    def test_empty_text(self, service):
        result = service._parse_cta_buttons("")
        assert result == []

    def test_none_text(self, service):
        result = service._parse_cta_buttons(None)
        assert result == []

    def test_text_without_botones(self, service):
        text = "Here is the image generated for your product."
        result = service._parse_cta_buttons(text)
        assert result == []

    def test_coordinates_out_of_range(self, service):
        text = 'BOTONES:\n- "COMPRAR" en [850, 160, 1200, 840]'
        result = service._parse_cta_buttons(text)
        assert result == []

    def test_inverted_rectangle(self, service):
        text = 'BOTONES:\n- "COMPRAR" en [920, 840, 850, 160]'
        result = service._parse_cta_buttons(text)
        assert result == []

    def test_mixed_valid_and_invalid(self, service):
        text = (
            'BOTONES:\n'
            '- "VÁLIDO" en [850, 160, 920, 840]\n'
            '- "INVÁLIDO" en [920, 840, 850, 160]\n'
            '- "TAMBIÉN VÁLIDO" en [700, 100, 780, 900]'
        )
        result = service._parse_cta_buttons(text)
        assert len(result) == 2
        assert result[0].label == "VÁLIDO"
        assert result[1].label == "TAMBIÉN VÁLIDO"

    def test_text_with_extra_content_before_botones(self, service):
        text = (
            "Aquí tienes la landing page adaptada.\n\n"
            'BOTONES:\n- "PEDIR AHORA →" en [860, 172, 936, 828]'
        )
        result = service._parse_cta_buttons(text)
        assert len(result) == 1
        assert result[0].label == "PEDIR AHORA →"

    def test_coordinates_at_boundaries(self, service):
        text = 'BOTONES:\n- "COMPRAR" en [0, 0, 1000, 1000]'
        result = service._parse_cta_buttons(text)
        assert len(result) == 1
        assert result[0].coords == [0, 0, 1000, 1000]


class TestBuildPrompt:

    def test_includes_system_prompt(self, service, base_request):
        prompt = service._build_prompt(base_request)
        assert "expert e-commerce landing page designer" in prompt

    def test_includes_cta_detection_when_enabled(self, service, base_request):
        base_request.detect_cta_buttons = True
        prompt = service._build_prompt(base_request)
        assert "INSTRUCCIÓN OBLIGATORIA DE TEXTO" in prompt
        assert "BOTONES:" in prompt

    def test_excludes_cta_detection_when_disabled(self, service, base_request):
        base_request.detect_cta_buttons = False
        prompt = service._build_prompt(base_request)
        assert "INSTRUCCIÓN OBLIGATORIA DE TEXTO" not in prompt

    def test_excludes_cta_when_include_cta_false(self, service, base_request):
        base_request.detect_cta_buttons = True
        prompt = service._build_prompt(base_request, include_cta_instruction=False)
        assert "INSTRUCCIÓN OBLIGATORIA DE TEXTO" not in prompt

    def test_includes_product_info(self, service, base_request):
        prompt = service._build_prompt(base_request)
        assert "AirPods Tercera Generación" in prompt
        assert "Bluetooth" in prompt
        assert "es" in prompt

    def test_includes_prices(self, service, base_request):
        prompt = service._build_prompt(base_request)
        assert "29,990" in prompt or "29990" in prompt
        assert "44,985" in prompt or "44985" in prompt

    def test_no_prices_when_none(self, service, base_request):
        base_request.price = None
        base_request.price_fake = None
        prompt = service._build_prompt(base_request)
        assert "PRICING" not in prompt

    def test_includes_user_prompt(self, service, base_request):
        prompt = service._build_prompt(base_request)
        assert "Modifica esta imagen" in prompt

    def test_includes_user_instructions(self, service, base_request):
        base_request.user_instructions = "Usa colores vibrantes"
        prompt = service._build_prompt(base_request)
        assert "Usa colores vibrantes" in prompt

    def test_no_user_instructions_when_none(self, service, base_request):
        base_request.user_instructions = None
        prompt = service._build_prompt(base_request)
        assert "Additional instructions" not in prompt


class TestCollectImageUrls:

    def test_both_urls(self, service, base_request):
        urls = service._collect_image_urls(base_request)
        assert len(urls) == 2
        assert urls[0] == "https://example.com/template.webp"
        assert urls[1] == "https://example.com/airpods.jpg"

    def test_no_template(self, service, base_request):
        base_request.template_image_url = None
        urls = service._collect_image_urls(base_request)
        assert len(urls) == 1
        assert urls[0] == "https://example.com/airpods.jpg"
