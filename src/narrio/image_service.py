#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import http.client
import json
import mimetypes
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib import error, request


DEFAULT_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3.1-flash-image-preview"
TIMESTAMP_FORMAT = "%y%m%d-%H%M%S"
DEFAULT_TEST_PROMPT = {
    "layout": "Centered Hero Typography",
    "background": "Mesh Gradient (#A5C9FF, #D8B4FE, #FFD1E3) with 80px Gaussian Blur",
    "elements": {
        "title_block": {
            "text": "提升生活质量的十件小事",
            "font": "Geometric Sans-Serif Bold",
            "letter_spacing": "-3%",
            "color": "#FFFFFF",
            "position": "Center",
        },
        "subtitle_block": {
            "text": "微小的行动 显著的改变",
            "font": "Modern Humanist Regular",
            "color": "rgba(255,255,255,0.9)",
            "position": "Center Bottom (+20px)",
        },
        "decorative": "Floating 8-petal radial symmetry icon at center top",
    },
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sanitize_path_segment(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return cleaned or "untitled"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_prompt_json_text(prompt: str | None, prompt_file: str | None) -> str:
    if prompt:
        source_text = prompt.strip()
    elif prompt_file:
        source_text = load_text(Path(prompt_file).expanduser().resolve())
    else:
        source_text = json.dumps(DEFAULT_TEST_PROMPT, ensure_ascii=False, indent=2)

    try:
        parsed = json.loads(source_text)
    except json.JSONDecodeError:
        return source_text

    return json.dumps(parsed, ensure_ascii=False, indent=2)


def default_reference_image(root: Path) -> str:
    candidate = root / "process" / "styles" / "OpenAI" / "ref.webp"
    if candidate.exists():
        return str(candidate)
    return ""


def encode_image_to_data_url(image_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(image_path.name)
    mime = mime_type or "application/octet-stream"
    binary = image_path.read_bytes()
    encoded = base64.b64encode(binary).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_user_message(prompt_json_text: str, reference_image_attached: bool) -> str:
    return (
        f"```json\n{prompt_json_text}\n```"
    )


def call_llm_api(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    timeout: int,
    reference_image: Path | None,
    aspect_ratio: str | None,
    image_size: str | None,
    max_tokens: int | None = None,
    modalities: list[str] | None = None,
) -> dict:
    content: list[dict[str, object]] = [{"type": "text", "text": user_message}]
    if reference_image:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": encode_image_to_data_url(reference_image)},
            }
        )

    payload: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": modalities or ["image", "text"],
        "stream": False,
    }

    image_config: dict[str, str] = {}
    if aspect_ratio:
        image_config["aspect_ratio"] = aspect_ratio
    if image_size:
        image_config["image_size"] = image_size
    if image_config:
        payload["image_config"] = image_config
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/narrio/narrio",
        "X-Title": "Narrio",
    }
    req = request.Request(base_url, data=body, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API 请求失败：HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"API 连接失败：{exc.reason}") from exc
    except http.client.HTTPException as exc:
        raise RuntimeError(f"API 连接异常：{exc}") from exc

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"API 返回格式异常：{response_text}") from exc


def call_images_api(
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    timeout: int,
    reference_image: Path | None = None,
    aspect_ratio: str | None = None,
    image_size: str | None = None,
    n: int = 1,
) -> dict:
    """
    Call images/generations API endpoint.

    This format is used by providers like api.sydney-ai.com and api.ourzhishi.top.

    Note: reference_image is currently not supported for images/generations API
    as it requires public HTTP URLs, not local files or data URLs.
    """
    # images/generations API doesn't support reference images via data URLs
    # The API expects public HTTP URLs in the prompt, which we don't have for local files
    # So we skip the reference image for now
    full_prompt = prompt

    # Map aspect_ratio format (e.g., "3:4") to size format (e.g., "3x4")
    size = None
    if aspect_ratio:
        size = aspect_ratio.replace(":", "x")
    elif image_size:
        size = image_size

    payload: dict[str, object] = {
        "model": model,
        "prompt": full_prompt,
        "n": n,
        "response_format": "url",
    }

    if size:
        payload["size"] = size

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/narrio/narrio",
        "X-Title": "Narrio",
    }
    req = request.Request(base_url, data=body, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API 请求失败：HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"API 连接失败：{exc.reason}") from exc
    except http.client.HTTPException as exc:
        raise RuntimeError(f"API 连接异常：{exc}") from exc

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"API 返回格式异常：{response_text}") from exc


def extract_message(response_data: dict) -> dict:
    try:
        return response_data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"API 返回内容缺少 message：{json.dumps(response_data, ensure_ascii=False)}") from exc


def extract_images_from_generations(response_data: dict) -> list[dict]:
    """
    Extract images from images/generations API response.

    Response format:
    {
      "data": [
        {"url": "https://...", "b64_json": null},
        ...
      ]
    }
    """
    try:
        # Check if response contains an error
        if "error" in response_data:
            error_msg = response_data.get("error", {})
            if isinstance(error_msg, dict):
                msg = error_msg.get("message", str(error_msg))
                code = error_msg.get("code", "unknown")
                raise RuntimeError(f"API 返回错误 (code={code}): {msg}")
            else:
                raise RuntimeError(f"API 返回错误: {error_msg}")

        data = response_data.get("data", [])
        if not data:
            # Provide more context about what was in the response
            keys = list(response_data.keys())
            raise RuntimeError(f"API 返回 data 为空或缺失。响应包含字段: {keys}")

        images = []
        for item in data:
            url = item.get("url")
            b64_json = item.get("b64_json")

            if url:
                images.append({"type": "image_url", "image_url": {"url": url}})
            elif b64_json:
                images.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_json}"}})

        if not images:
            raise RuntimeError(f"API 返回的 data 中没有 url 或 b64_json。data 内容: {data}")

        return images

    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"images/generations API 返回格式异常：{json.dumps(response_data, ensure_ascii=False)[:500]}") from exc


def extract_images(message: dict) -> list[dict]:
    """
    Extract images from chat/completions API response.

    This is the original format with message.images or message.content.
    """
    images = message.get("images")
    if isinstance(images, list) and images:
        return images

    content = message.get("content")
    if isinstance(content, list):
        content_images = [item for item in content if isinstance(item, dict) and item.get("type") == "image_url"]
        if content_images:
            return content_images

    raise RuntimeError(f"模型返回中未找到生成图片：{json.dumps(message, ensure_ascii=False)}")


def extract_image_url(image_item: dict) -> str:
    image_url = image_item.get("image_url")
    if isinstance(image_url, dict) and isinstance(image_url.get("url"), str):
        return image_url["url"]

    camel_image_url = image_item.get("imageUrl")
    if isinstance(camel_image_url, dict) and isinstance(camel_image_url.get("url"), str):
        return camel_image_url["url"]

    raise RuntimeError(f"图片对象缺少可用 url：{json.dumps(image_item, ensure_ascii=False)}")


def decode_data_url(data_url: str) -> tuple[str, bytes]:
    match = re.fullmatch(r"data:(?P<mime>[-\w.+/]+);base64,(?P<data>.+)", data_url, flags=re.DOTALL)
    if not match:
        raise ValueError("不是合法的 base64 data URL")
    mime = match.group("mime")
    binary = base64.b64decode(match.group("data"))
    return mime, binary


def suffix_from_mime(mime_type: str) -> str:
    guessed = mimetypes.guess_extension(mime_type, strict=False)
    if guessed == ".jpe":
        return ".jpg"
    return guessed or ".png"


def extract_title(prompt_json_text: str) -> str:
    try:
        parsed = json.loads(prompt_json_text)
    except json.JSONDecodeError:
        first_line = prompt_json_text.strip().splitlines()[0] if prompt_json_text.strip() else "image"
        return sanitize_path_segment(first_line[:40])

    title = (
        parsed.get("elements", {})
        .get("title_block", {})
        .get("text", "")
    )
    if isinstance(title, str) and title.strip():
        return sanitize_path_segment(title)
    return "image"


def build_timestamp() -> str:
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def save_response_bundle(output_root: Path, prompt_json_text: str, response_data: dict) -> tuple[Path, list[Path]]:
    timestamp = build_timestamp()
    title = extract_title(prompt_json_text)
    target_dir = output_root / title
    target_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = target_dir / f"prompt {timestamp}.json"
    prompt_path.write_text(prompt_json_text, encoding="utf-8")

    response_path = target_dir / f"response {timestamp}.json"
    response_path.write_text(json.dumps(response_data, ensure_ascii=False, indent=2), encoding="utf-8")

    message = extract_message(response_data)
    images = extract_images(message)

    saved_images: list[Path] = []
    for index, image_item in enumerate(images, start=1):
        image_url = extract_image_url(image_item)
        if image_url.startswith("data:"):
            mime_type, binary = decode_data_url(image_url)
        else:
            try:
                with request.urlopen(image_url, timeout=120) as response:
                    mime_type = response.headers.get_content_type()
                    binary = response.read()
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"下载生成图片失败：HTTP {exc.code} {detail}") from exc
            except error.URLError as exc:
                raise RuntimeError(f"下载生成图片失败：{exc.reason}") from exc

        image_path = target_dir / f"image_{index} {timestamp}{suffix_from_mime(mime_type)}"
        image_path.write_bytes(binary)
        saved_images.append(image_path)

    return target_dir, saved_images


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prompt",
        help="直接传入生图 prompt，支持普通文本或 JSON 字符串",
    )
    parser.add_argument(
        "--prompt-file",
        help="从文件读取生图 prompt，支持 txt / md / json",
    )
    parser.add_argument(
        "--reference-image",
        default=default_reference_image(root),
        help="参考图路径，默认使用 process/styles/OpenAI/ref.webp（若存在）",
    )
    parser.add_argument(
        "--output-root",
        default=str(root / "output" / "image"),
        help="输出根目录，默认 output/image",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenRouter 模型名称",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="4:5",
        help="图片比例，例如 1:1、4:5、16:9、4:1",
    )
    parser.add_argument(
        "--image-size",
        default="1K",
        help="图片尺寸，例如 0.5K、1K、2K、4K",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="API Key（必需）",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="API Base URL",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="单次请求超时时间，单位秒",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.api_key:
        raise SystemExit("缺少 API Key，请传入 --api-key 或设置 IMAGE_API_KEY/OPENROUTER_API_KEY")

    prompt_json_text = load_prompt_json_text(prompt=args.prompt, prompt_file=args.prompt_file)
    output_root = Path(args.output_root).expanduser().resolve()

    reference_image: Path | None = None
    if args.reference_image:
        reference_image = Path(args.reference_image).expanduser().resolve()
        if not reference_image.exists():
            raise FileNotFoundError(f"参考图不存在：{reference_image}")

    user_message = build_user_message(
        prompt_json_text=prompt_json_text,
        reference_image_attached=reference_image is not None,
    )
    print(f"API Base URL：{args.base_url}")

    response_data = call_llm_api(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        user_message=user_message,
        timeout=args.timeout,
        reference_image=reference_image_path,
        aspect_ratio=args.aspect_ratio,
        image_size=args.image_size,
        max_tokens=args.max_tokens,
    )

    target_dir, saved_images = save_response_bundle(
        output_root=output_root,
        prompt_json_text=prompt_json_text,
        response_data=response_data,
    )

    print(f"输出目录：{target_dir}")
    for image_path in saved_images:
        print(f"已写入：{image_path}")
    return 0


# Alias for backward compatibility
call_openrouter = call_llm_api


if __name__ == "__main__":
    sys.exit(main())
