PDF_MANUAL_SECTIONS_TRANSLATIONS = {
    "es": {
        "introduction": "Introducción",
        "main_features": "Características principales",
        "usage_instructions": "Instrucciones de uso",
        "troubleshooting": "Solución de problemas",
        "faq": "Preguntas frecuentes"
    },
    "en": {
        "introduction": "Introduction",
        "main_features": "Main Features",
        "usage_instructions": "Usage Instructions",
        "troubleshooting": "Troubleshooting",
        "faq": "Frequently Asked Questions"
    },
    "pt": {
        "introduction": "Introdução",
        "main_features": "Características Principais",
        "usage_instructions": "Instruções de Uso",
        "troubleshooting": "Solução de Problemas",
        "faq": "Perguntas Frequentes"
    }
}

PDF_MANUAL_SECTIONS = PDF_MANUAL_SECTIONS_TRANSLATIONS["es"]

PDF_MANUAL_SECTION_ORDER = [
    "introduction",
    "main_features",
    "usage_instructions",
    "troubleshooting",
    "faq"
]


def get_sections_for_language(language: str = "es") -> dict:
    return PDF_MANUAL_SECTIONS_TRANSLATIONS.get(language, PDF_MANUAL_SECTIONS_TRANSLATIONS["es"])
