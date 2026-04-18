-- One-time seed for the section-image prompts migrated out of section_image_service.py
-- into the existing agent-config registry (DB `agents`, table `agent_configs`).
--
-- Run this manually in both environments (dev, prod) AFTER conversation-engine is
-- deployed with the code that reads these agent_ids. The code has hardcoded fallbacks,
-- so the seed is not strictly required for the service to keep working — it enables
-- runtime editing via agent-config (UI or PUT) without a deploy.
--
-- To run:
--   psql -h <db-host> -U <admin-user> -d agents -f seed_ai_prompts.sql
--
-- Re-running is safe (ON CONFLICT DO NOTHING) but will NOT overwrite an already
-- edited prompt. To force an overwrite during bring-up, change DO NOTHING to
-- DO UPDATE SET prompt = EXCLUDED.prompt.

INSERT INTO agent_configs (
    agent_id,
    description,
    prompt,
    provider_ai,
    model_ai,
    preferences,
    project
) VALUES (
    'section_image_system',
    'System prompt for conversation-engine section image generation (Gemini). Read by section_image_service._build_prompt() with 60s cache and a hardcoded fallback.',
    'You are an expert e-commerce landing page designer specializing in high-converting sales funnels for Latin American markets.

You will receive:
1. A prompt describing the section style and layout
2. A STYLE REFERENCE image (template) — match its layout, composition, typography, and visual style as closely as possible
3. A PRODUCT PHOTO — the REAL product that this landing page is selling
4. A SALES ANGLE that defines the communication strategy — adapt all copy, headlines, and messaging to match this angle

CRITICAL — TEMPLATE vs PRODUCT DISTINCTION:
- The STYLE REFERENCE image is a TEMPLATE that contains EXAMPLE/PLACEHOLDER products. These are NOT the real product.
- You MUST REPLACE every example product, placeholder image, and sample photo in the template with the REAL PRODUCT PHOTO provided.
- NEVER keep the template''s example products in the final image. The only product visible must be the one from the PRODUCT PHOTO.

ABSOLUTE RULES:
- Every label, brand name, text on packaging, color, shape, and proportion of the REAL PRODUCT must be IDENTICAL to the provided photo
- Mobile-first vertical layout
- All text in the specified language
- Professional, high-quality, ready-to-use section with good legibility and well-positioned elements
- No mockup frames, browser windows, or device frames
- Create well-structured, well-diagrammed designs based on the reference template — clear visual hierarchy, readable text, and balanced element placement
- Adapt ALL text to the specific product — do NOT copy text from the template. Your priority is to communicate the product clearly and persuasively from the provided sales angle
- Adapt colors to match the real product''s packaging colors automatically
- If brand colors are provided, they DEFINE the color identity — adapt the template''s colors to these brand tones so all sections share a consistent look. Respect the template''s light/dark logic (dark stays dark, light stays light) but in the brand''s color tones
- If a sales angle is provided, ALL text (headlines, benefits, CTAs, badges) must align with that angle''s tone and messaging
- If pricing is provided, use the EXACT formatted values — do not change currency symbols, decimal separators, or number format',
    'gemini',
    'gemini-3.1-flash-image-preview',
    '{"temperature": 1.0, "max_tokens": 4096, "top_p": 1.0}'::jsonb,
    'default'
) ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO agent_configs (
    agent_id,
    description,
    prompt,
    provider_ai,
    model_ai,
    preferences,
    project
) VALUES (
    'section_image_cta_detection',
    'Appended to the section-image prompt when detect_cta_buttons=true. Makes Gemini emit CTA button coordinates in text before generating the image, so the frontend can render clickable overlays.',
    '[INSTRUCCIÓN OBLIGATORIA DE TEXTO]
Primero responde en texto: ¿dónde vas a poner los botones CTA en la imagen? Escribe:
BOTONES:
- "texto del botón" en [ymin, xmin, ymax, xmax] coords 0-1000
Si no hay botones en este tipo de sección, escribe: BOTONES: ninguno
Solo detecta botones de acción (comprar, pedir, agregar al carrito). No detectes badges, labels o texto decorativo.
Después de escribir esto, genera la imagen.',
    'gemini',
    'gemini-3.1-flash-image-preview',
    '{"temperature": 1.0, "max_tokens": 4096, "top_p": 1.0}'::jsonb,
    'default'
) ON CONFLICT (agent_id) DO NOTHING;


-- ---------------------------------------------------------------------------
-- HTML sections (Universal Builder) — read by section_html_service.py via
-- PromptConfigService. Same deployment story: hardcoded fallbacks exist in
-- app/prompts/section_html_prompts.py, this seed just enables runtime editing.
-- ---------------------------------------------------------------------------

INSERT INTO agent_configs (
    agent_id,
    description,
    prompt,
    provider_ai,
    model_ai,
    preferences,
    project
) VALUES (
    'section_html_generate_system',
    'System prompt for conversation-engine HTML section generation (initial create flow). Read by section_html_service._do_generate() with 60s cache and a hardcoded fallback.',
    'REPLACE ME: seed-time copy of FALLBACK_GENERATE_SYSTEM_PROMPT from app/prompts/section_html_prompts.py. When bringing up dev/prod, paste the full fallback value in here. Leaving this placeholder is harmless — the service uses the hardcoded fallback automatically.',
    'gemini',
    'gemini-3.1-pro-preview',
    '{"temperature": 1.0, "max_output_tokens": 14336, "thinking_level": "low"}'::jsonb,
    'default'
) ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO agent_configs (
    agent_id,
    description,
    prompt,
    provider_ai,
    model_ai,
    preferences,
    project
) VALUES (
    'section_html_edit_system',
    'System prompt for conversation-engine HTML section editing (chat-driven edits). Read by section_html_service.edit_section_html() with 60s cache and a hardcoded fallback.',
    'REPLACE ME: seed-time copy of FALLBACK_EDIT_SYSTEM_PROMPT from app/prompts/section_html_prompts.py.',
    'gemini',
    'gemini-3.1-pro-preview',
    '{"temperature": 1.0, "max_output_tokens": 32768, "thinking_level": "low"}'::jsonb,
    'default'
) ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO agent_configs (
    agent_id,
    description,
    prompt,
    provider_ai,
    model_ai,
    preferences,
    project
) VALUES (
    'section_html_image_orchestrator',
    'System prompt for orchestrating image generation prompts from HTML (one prompt per placehold.co). Read by section_html_service.orchestrate_image_prompts() with 60s cache and a hardcoded fallback.',
    'REPLACE ME: seed-time copy of FALLBACK_IMAGE_ORCHESTRATOR_PROMPT from app/prompts/section_html_prompts.py.',
    'gemini',
    'gemini-3.1-pro-preview',
    '{"temperature": 1.0, "max_output_tokens": 14336, "thinking_level": "low"}'::jsonb,
    'default'
) ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO agent_configs (
    agent_id,
    description,
    prompt,
    provider_ai,
    model_ai,
    preferences,
    project
) VALUES (
    'section_html_template_studio',
    'System prompt for generating reusable HTML templates via chat in the template studio. Read by section_html_service.generate_template_html() with 60s cache and a hardcoded fallback.',
    'REPLACE ME: seed-time copy of FALLBACK_TEMPLATE_STUDIO_PROMPT from app/prompts/section_html_prompts.py.',
    'gemini',
    'gemini-3.1-pro-preview',
    '{"temperature": 1.0, "max_output_tokens": 14336, "thinking_level": "low"}'::jsonb,
    'default'
) ON CONFLICT (agent_id) DO NOTHING;


-- Sanity check
SELECT agent_id, LEFT(prompt, 80) AS preview, LENGTH(prompt) AS chars, provider_ai, model_ai, updated_at
FROM agent_configs
WHERE agent_id IN (
    'section_image_system',
    'section_image_cta_detection',
    'section_html_generate_system',
    'section_html_edit_system',
    'section_html_image_orchestrator',
    'section_html_template_studio'
)
ORDER BY agent_id;
