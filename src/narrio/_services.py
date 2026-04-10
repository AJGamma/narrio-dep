from __future__ import annotations

import types

from .chunk_service import (
    CONTENT_TYPE_CONFIG,
    DEFAULT_BASE_URL as CHUNK_DEFAULT_BASE_URL,
    DEFAULT_MODEL as CHUNK_DEFAULT_MODEL,
    TIMESTAMP_FORMAT as CHUNK_TIMESTAMP_FORMAT,
    build_user_message,
    call_llm_api,
    call_openrouter,
    extract_json_text,
    load_text,
    resolve_markdown_target,
)
from .editorial_service import (
    DEFAULT_BASE_URL as EDITORIAL_DEFAULT_BASE_URL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL as EDITORIAL_DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    build_user_message as build_editorial_user_message,
    call_llm_api as call_editorial_llm_api,
    call_openrouter as call_editorial_openrouter,
    extract_json_text as extract_editorial_json,
    resolve_style_file,
    resolve_style_label,
)
from .highlight_service import (
    DEFAULT_BASE_URL as HIGHLIGHT_DEFAULT_BASE_URL,
    extract_highlights,
    save_highlights_json,
)
from .image_service import (
    DEFAULT_BASE_URL as IMAGE_DEFAULT_BASE_URL,
    DEFAULT_MODEL as IMAGE_DEFAULT_MODEL,
    build_user_message as build_image_user_message,
    call_llm_api as call_image_llm_api,
    call_openrouter as call_image_openrouter,
    decode_data_url,
    extract_image_url,
    extract_images,
    extract_message,
    project_root as image_project_root,
    suffix_from_mime,
)
from .render_service import (
    DEFAULT_MAX_TOKENS as RENDER_DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL as RENDER_DEFAULT_MODEL,
    extract_page_number,
    generate_page_image,
    load_editorial_pages,
    load_text as load_render_text,
    prepare_reference_image,
    resolve_reference_image,
)

# Create chunkify module alias
chunkify = types.ModuleType("chunkify")
chunkify.CONTENT_TYPE_CONFIG = CONTENT_TYPE_CONFIG
chunkify.DEFAULT_BASE_URL = CHUNK_DEFAULT_BASE_URL
chunkify.DEFAULT_MODEL = CHUNK_DEFAULT_MODEL
chunkify.TIMESTAMP_FORMAT = CHUNK_TIMESTAMP_FORMAT
chunkify.build_user_message = build_user_message
chunkify.call_llm_api = call_llm_api
chunkify.call_openrouter = call_openrouter
chunkify.extract_json_text = extract_json_text
chunkify.load_text = load_text
chunkify.resolve_markdown_target = resolve_markdown_target

# Create stylify module alias
stylify = types.ModuleType("stylify")
stylify.DEFAULT_BASE_URL = EDITORIAL_DEFAULT_BASE_URL
stylify.DEFAULT_MODEL = EDITORIAL_DEFAULT_MODEL
stylify.DEFAULT_MAX_TOKENS = DEFAULT_MAX_TOKENS
stylify.DEFAULT_TEMPERATURE = DEFAULT_TEMPERATURE
stylify.build_user_message = build_editorial_user_message
stylify.call_llm_api = call_editorial_llm_api
stylify.call_openrouter = call_editorial_openrouter
stylify.extract_json_text = extract_editorial_json
stylify.resolve_style_file = resolve_style_file
stylify.resolve_style_label = resolve_style_label

# Create red_image module alias
red_image = types.ModuleType("red_image")
red_image.DEFAULT_MODEL = RENDER_DEFAULT_MODEL
red_image.DEFAULT_MAX_TOKENS = RENDER_DEFAULT_MAX_TOKENS
red_image.DEFAULT_BASE_URL = IMAGE_DEFAULT_BASE_URL
red_image.extract_page_number = extract_page_number
red_image.generate_page_image = generate_page_image
red_image.load_editorial_pages = load_editorial_pages
red_image.load_text = load_render_text
red_image.prepare_reference_image = prepare_reference_image
red_image.resolve_reference_image = resolve_reference_image
# From image_service
red_image.IMAGE_DEFAULT_MODEL = IMAGE_DEFAULT_MODEL
red_image.build_user_message = build_image_user_message
red_image.call_llm_api = call_image_llm_api
red_image.call_openrouter = call_image_openrouter
red_image.decode_data_url = decode_data_url
red_image.extract_image_url = extract_image_url
red_image.extract_images = extract_images
red_image.extract_message = extract_message
red_image.project_root = image_project_root
red_image.suffix_from_mime = suffix_from_mime

# Create extract_highlights module alias
extract_highlights_mod = types.ModuleType("extract_highlights")
extract_highlights_mod.DEFAULT_BASE_URL = HIGHLIGHT_DEFAULT_BASE_URL
extract_highlights_mod.extract_highlights = extract_highlights
extract_highlights_mod.save_highlights_json = save_highlights_json

# Make module available as extract_highlights
extract_highlights = extract_highlights_mod
