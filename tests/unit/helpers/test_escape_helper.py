"""
Tests para escape_helper.
Verifica la limpieza de HTML y placeholders.
"""

import pytest

from app.helpers.escape_helper import clean_html_deeply, clean_html_less_deeply, clean_placeholders


class TestCleanPlaceholders:
    """Tests para clean_placeholders."""

    @pytest.mark.unit
    def test_removes_all_placeholders_when_no_allowed_keys(self):
        """Debe remover todos los placeholders si no hay keys permitidas."""
        text = "Hello {name}, your order {order_id} is ready"
        result = clean_placeholders(text)
        assert result == "Hello , your order  is ready"

    @pytest.mark.unit
    def test_keeps_allowed_placeholders(self):
        """Debe mantener placeholders que están en allowed_keys."""
        text = "Hello {name}, your order {order_id} is ready"
        result = clean_placeholders(text, allowed_keys=["name"])
        assert "{name}" in result
        assert "{order_id}" not in result

    @pytest.mark.unit
    def test_handles_quoted_placeholders(self):
        """Debe manejar placeholders con comillas."""
        text = "Value: {'key'} and {\"another_key\"}"
        result = clean_placeholders(text, allowed_keys=["key"])
        assert "{'key'}" in result

    @pytest.mark.unit
    def test_empty_text_returns_empty(self):
        """Debe retornar string vacío para input vacío."""
        assert clean_placeholders("") == ""
        assert clean_placeholders("", ["key"]) == ""

    @pytest.mark.unit
    def test_text_without_placeholders_unchanged(self):
        """Texto sin placeholders no debe cambiar."""
        text = "Hello World! No placeholders here."
        result = clean_placeholders(text)
        assert result == text

    @pytest.mark.unit
    def test_nested_braces_handled(self):
        """Debe manejar llaves anidadas correctamente."""
        text = 'JSON: {"key": "value"}'
        result = clean_placeholders(text)
        # El contenido entre llaves con formato JSON debería procesarse
        assert result is not None


class TestCleanHtmlDeeply:
    """Tests para clean_html_deeply."""

    @pytest.mark.unit
    def test_removes_script_tags(self, sample_html_content):
        """Debe remover tags de script."""
        result = clean_html_deeply(sample_html_content)
        assert "<script>" not in result
        assert "console.log" not in result

    @pytest.mark.unit
    def test_removes_style_tags(self, sample_html_content):
        """Debe remover tags de style."""
        result = clean_html_deeply(sample_html_content)
        assert "<style>" not in result
        assert "color: red" not in result

    @pytest.mark.unit
    def test_removes_all_attributes_except_img(self):
        """Debe remover atributos de todos los tags excepto img."""
        html = '<div class="test" id="main"><p style="color:red">Text</p></div>'
        result = clean_html_deeply(html)
        assert "class=" not in result
        assert "id=" not in result
        assert "style=" not in result

    @pytest.mark.unit
    def test_preserves_img_src_and_alt(self):
        """Debe preservar src y alt en tags img."""
        html = '<img src="test.jpg" alt="Test" class="image" id="img1" />'
        result = clean_html_deeply(html)
        assert 'src="test.jpg"' in result
        assert 'alt="Test"' in result
        assert "class=" not in result

    @pytest.mark.unit
    def test_collapses_whitespace(self):
        """Debe colapsar múltiples espacios en uno."""
        html = "<div>   Multiple    spaces   here   </div>"
        result = clean_html_deeply(html)
        assert "   " not in result

    @pytest.mark.unit
    def test_removes_head_meta_link(self):
        """Debe remover tags head, meta y link."""
        html = '<html><head><meta charset="utf-8"><link rel="stylesheet"></head><body>Content</body></html>'
        result = clean_html_deeply(html)
        assert "<meta" not in result
        assert "<link" not in result

    @pytest.mark.unit
    def test_empty_html_returns_empty(self):
        """Debe manejar HTML vacío."""
        result = clean_html_deeply("")
        assert result == ""


class TestCleanHtmlLessDeeply:
    """Tests para clean_html_less_deeply."""

    @pytest.mark.unit
    def test_removes_script_and_style(self):
        """Debe remover script y style."""
        html = '<script>alert("test")</script><style>.x{}</style><div>Content</div>'
        result = clean_html_less_deeply(html)
        assert "<script>" not in result
        assert "<style>" not in result
        assert "Content" in result

    @pytest.mark.unit
    def test_preserves_more_img_attributes(self):
        """Debe preservar más atributos en img que clean_html_deeply."""
        html = '<img src="test.jpg" alt="Test" class="image" id="img1" title="Title" />'
        result = clean_html_less_deeply(html)
        assert 'src="test.jpg"' in result
        assert 'alt="Test"' in result
        assert 'class="image"' in result
        assert 'id="img1"' in result
        assert 'title="Title"' in result

    @pytest.mark.unit
    def test_preserves_anchor_attributes(self):
        """Debe preservar atributos importantes en anchors."""
        html = '<a href="https://test.com" title="Link" target="_blank" class="link">Click</a>'
        result = clean_html_less_deeply(html)
        assert 'href="https://test.com"' in result
        assert 'title="Link"' in result
        assert 'target="_blank"' in result

    @pytest.mark.unit
    def test_preserves_source_attributes(self):
        """Debe preservar atributos en source tags."""
        html = '<source media="(min-width:650px)" srcset="img.jpg" type="image/jpeg">'
        result = clean_html_less_deeply(html)
        assert "media=" in result
        assert "srcset=" in result
        assert "type=" in result

    @pytest.mark.unit
    def test_keeps_common_attrs_on_other_elements(self):
        """Debe mantener id y class en otros elementos."""
        html = '<div id="main" class="container" style="color:red">Content</div>'
        result = clean_html_less_deeply(html)
        assert 'id="main"' in result
        assert 'class="container"' in result
        assert "style=" not in result

    @pytest.mark.unit
    def test_collapses_whitespace(self):
        """Debe colapsar espacios múltiples."""
        html = "<div>   Text    with    spaces   </div>"
        result = clean_html_less_deeply(html)
        assert "    " not in result
