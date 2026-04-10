#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib import error, request
import logging

from .image_service import (
    DEFAULT_BASE_URL as IMAGE_DEFAULT_BASE_URL,
    DEFAULT_MODEL as IMAGE_DEFAULT_MODEL,
    build_user_message,
    call_llm_api,
    call_images_api,
    decode_data_url,
    extract_image_url,
    extract_images,
    extract_images_from_generations,
    extract_message,
    project_root,
    suffix_from_mime,
)


FIXED_ASPECT_RATIO = "3:4"
FIXED_IMAGE_SIZE = "1K"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_MODEL = IMAGE_DEFAULT_MODEL
DEFAULT_BASE_URL = IMAGE_DEFAULT_BASE_URL
REQUEST_RETRY_COUNT = 3
REQUEST_RETRY_DELAY = 2  # seconds
EDITORIAL_PATTERN = re.compile(r"^Editorial-(?P<style>.+)-(?P<timestamp>\d{6,8}-\d{6})$")

logger = logging.getLogger("narrio")

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def resolve_existing_path(path_value: str, root: Path) -> Path:
    candidate = Path(path_value).expanduser()
    paths_to_try: list[Path] = []

    if candidate.is_absolute():
        paths_to_try.append(candidate)
    else:
        paths_to_try.extend(
            [
                candidate,
                root / candidate,
            ]
        )

    for path in paths_to_try:
        if path.exists():
            return path.resolve()

    raise FileNotFoundError(f"未找到文件：{path_value}")


def load_editorial_pages(editorial_path: Path) -> list[dict[str, object]]:
    data = json.loads(editorial_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError(f"Editorial 文件必须是非空数组：{editorial_path}")

    pages: list[dict[str, object]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Editorial 第 {index} 项不是对象：{editorial_path}")
        pages.append(item)
    return pages


def parse_page_selection(page_values: list[str]) -> set[int]:
    selected_pages: set[int] = set()
    for raw_value in page_values:
        for part in raw_value.split(","):
            value = part.strip()
            if not value:
                continue
            if "-" in value:
                start_text, end_text = value.split("-", 1)
                start = int(start_text.strip())
                end = int(end_text.strip())
                if end < start:
                    raise ValueError(f"页码范围不合法：{value}")
                selected_pages.update(range(start, end + 1))
                continue
            selected_pages.add(int(value))
    return selected_pages


def resolve_style_label(editorial_path: Path) -> str:
    match = EDITORIAL_PATTERN.fullmatch(editorial_path.stem)
    if not match:
        raise ValueError(f"无法从 Editorial 文件名中解析 style：{editorial_path.name}")
    return match.group("style")


def resolve_reference_image(style_root: Path, style_label: str, override: str | None) -> Path:
    if override:
        reference_path = Path(override).expanduser()
        if not reference_path.is_absolute():
            reference_path = style_root.parent.parent / reference_path
        reference_path = reference_path.resolve()
        if not reference_path.exists() or not reference_path.is_file():
            raise FileNotFoundError(f"参考图不存在：{reference_path}")
        return reference_path

    style_dir = style_root / style_label
    if not style_dir.exists() or not style_dir.is_dir():
        raise FileNotFoundError(f"未找到 style 目录：{style_dir}")

    candidates = sorted(path for path in style_dir.glob("ref.*") if path.is_file())
    if not candidates:
        raise FileNotFoundError(f"未找到参考图，期望路径类似：{style_dir / 'ref.*'}")
    return candidates[0].resolve()


def build_page_prompt(page_data: dict[str, object], imagegen_prompt: str, style_json: str | None = None) -> str:
    page_prompt = json.dumps(page_data, ensure_ascii=False, indent=2)
    base_message = build_user_message(
        prompt_json_text=page_prompt,
        reference_image_attached=True,
    )
    extra_instruction = imagegen_prompt.strip()
    if not extra_instruction:
        return base_message
    # 替换 {{style_json}} 占位符为实际的 style.json 内容
    if style_json:
        extra_instruction = extra_instruction.replace("{{style_json}}", style_json)
    return f"{base_message}\n\n附加要求：\n{extra_instruction}"


def extract_page_number(page_data: dict[str, object], fallback_index: int) -> int:
    page_number = page_data.get("page", fallback_index)
    if not isinstance(page_number, int):
        raise ValueError(f"page 字段必须是整数：{json.dumps(page_data, ensure_ascii=False)}")
    return page_number


def download_image_binary(image_item: dict[str, object], timeout: int) -> tuple[str, bytes]:
    image_url = extract_image_url(image_item)
    if image_url.startswith("data:"):
        return decode_data_url(image_url)

    try:
        with request.urlopen(image_url, timeout=timeout) as response:
            mime_type = response.headers.get_content_type()
            binary = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"下载生成图片失败：HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"下载生成图片失败：{exc.reason}") from exc

    return mime_type, binary


def convert_to_png(source_path: Path, target_path: Path) -> None:
    try:
        subprocess.run(
            ["sips", "-s", "format", "png", str(source_path), "--out", str(target_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("当前系统缺少 sips，无法把生成结果转换成 PNG") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip()
        raise RuntimeError(f"图片转换 PNG 失败：{detail}") from exc


def prepare_reference_image(reference_image: Path) -> tuple[Path, Path | None]:
    if reference_image.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        return reference_image, None

    temp_dir = Path(tempfile.mkdtemp(prefix="redimagegen-ref-"))
    converted_path = temp_dir / "reference.png"
    convert_to_png(source_path=reference_image, target_path=converted_path)
    return converted_path, temp_dir


def write_output_image(binary: bytes, mime_type: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if mime_type == "image/png":
        output_path.write_bytes(binary)
        return

    source_suffix = suffix_from_mime(mime_type)
    temp_source_path = output_path.with_name(f"{output_path.stem}.source{source_suffix}")
    temp_source_path.write_bytes(binary)
    try:
        convert_to_png(source_path=temp_source_path, target_path=output_path)
    finally:
        if temp_source_path.exists():
            temp_source_path.unlink()


def should_retry_request(error_message: str) -> bool:
    retry_markers = [
        "Remote end closed connection without response",
        "API 连接失败",
        "API 连接异常",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "HTTP 429",
        "HTTP 500",
        "HTTP 502",
        "HTTP 503",
        "HTTP 504",
    ]
    normalized = error_message.lower()
    return any(marker.lower() in normalized for marker in retry_markers)


def generate_page_image(
    page_data: dict[str, object],
    page_number: int,
    article_dir: Path,
    imagegen_prompt: str,
    reference_image: Path,
    api_key: str,
    base_url: str,
    model: str,
    timeout: int,
    max_tokens: int,
    style_json: str | None = None,
    api_format: str = "chat/completions",
) -> Path:
    prompt_text = build_page_prompt(page_data=page_data, imagegen_prompt=imagegen_prompt, style_json=style_json)
    logger.debug(f"生成提示词：{prompt_text}")
    retry_messages = [
        prompt_text,
        (
            f"{prompt_text}\n\n"
            "上一次返回了非图片结果。请直接生成图片，不要拒绝，不要解释，不要输出纯文本，"
            "必须返回 1 张最终图片。"
        ),
        (
            f"{prompt_text}\n\n"
            "这是一项正常的杂志内页视觉设计任务，内容不涉及受限主题。"
            "请仅返回图片结果，并确保版式中的文字清晰可读。"
        ),
    ]

    last_error: Exception | None = None
    mime_type = ""
    binary = b""
    for user_message in retry_messages:
        response_data: dict[str, object] | None = None

        # Choose API format
        if api_format == "images/generations":
            # images/generations format - simpler, no modalities retry
            for attempt in range(1, REQUEST_RETRY_COUNT + 1):
                try:
                    response_data = call_images_api(
                        api_key=api_key,
                        base_url=base_url,
                        model=model,
                        prompt=user_message,
                        timeout=timeout,
                        reference_image=reference_image,
                        aspect_ratio=FIXED_ASPECT_RATIO,
                        image_size=FIXED_IMAGE_SIZE,
                        n=1,
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    print(f"第 {page_number} 页第 {attempt} 次 API 调用失败: {exc}")
                    if attempt < REQUEST_RETRY_COUNT:
                        time.sleep(REQUEST_RETRY_DELAY)
                    continue
        else:
            # chat/completions format - with modalities retry
            for modalities in (["image", "text"], ["image"]):
                for attempt in range(1, REQUEST_RETRY_COUNT + 1):
                    try:
                        response_data = call_llm_api(
                            api_key=api_key,
                            base_url=base_url,
                            model=model,
                            user_message=user_message,
                            timeout=timeout,
                            reference_image=reference_image,
                            aspect_ratio=FIXED_ASPECT_RATIO,
                            image_size=FIXED_IMAGE_SIZE,
                            max_tokens=max_tokens,
                            modalities=modalities,
                        )
                        break
                    except RuntimeError as exc:
                        message = str(exc)
                        if 'No endpoints found that support the requested output modalities: image, text' in message:
                            if modalities == ["image"]:
                                raise
                            break
                        if attempt >= REQUEST_RETRY_COUNT or not should_retry_request(message):
                            raise
                        print(f"第 {page_number} 页第 {attempt} 次请求失败，准备重试：{message}")
                        time.sleep(min(attempt, 3))
                if response_data is not None:
                    break

        try:
            if response_data is None:
                # If we have a last_error from API call, re-raise it with more context
                if last_error:
                    raise RuntimeError(f"API 调用失败，所有重试均失败") from last_error
                else:
                    raise RuntimeError("模型请求未返回响应")

            # Extract images based on API format
            if api_format == "images/generations":
                image_items = extract_images_from_generations(response_data)
            else:
                message = extract_message(response_data)
                image_items = extract_images(message)

            mime_type, binary = download_image_binary(image_items[0], timeout=timeout)
            last_error = None
            break
        except RuntimeError as exc:
            # Log the actual error for debugging
            error_detail = str(exc)
            response_summary = json.dumps(response_data, ensure_ascii=False)[:500] if response_data else "null"
            print(f"第 {page_number} 页图片提取失败: {error_detail}")
            print(f"API 响应摘要: {response_summary}")
            last_error = RuntimeError(
                f"第 {page_number} 页生成失败。错误: {error_detail}\n原始响应："
                f"{json.dumps(response_data, ensure_ascii=False)}"
            )

    if last_error is not None:
        raise last_error

    output_path = article_dir / f"{page_number}.png"
    write_output_image(binary=binary, mime_type=mime_type, output_path=output_path)
    return output_path


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--editorial",
        required=True,
        help="Editorial JSON 路径，可传相对路径或绝对路径",
    )
    parser.add_argument(
        "--prompt-file",
        default=str(root / "process" / "prompt" / "ImageGen.md"),
        help="ImageGen 提示词文件，默认 process/prompt/ImageGen.md",
    )
    parser.add_argument(
        "--style-root",
        default=str(root / "process" / "styles"),
        help="style 根目录，默认 process/styles",
    )
    parser.add_argument(
        "--reference-image",
        help="手动指定参考图路径；未传时按 Editorial 文件名解析 style 并寻找 ref.*",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="模型名称",
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
        help="单页生图超时时间，单位秒",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="限制单页请求的最大输出 tokens，默认 1024",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只校验 Editorial、Prompt 与参考图解析结果，不实际调用模型",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在的输出图片；未传时自动跳过已有页面",
    )
    parser.add_argument(
        "--pages",
        action="append",
        default=[],
        help="只生成指定页，可传 5、6 或 5,6 或 5-6，可重复传入",
    )
    return parser.parse_args()


def main() -> int:
    root = project_root()
    args = parse_args()

    api_key = args.api_key
    base_url = args.base_url
    editorial_path = resolve_existing_path(args.editorial, root=root)
    prompt_file = resolve_existing_path(args.prompt_file, root=root)
    style_root = resolve_existing_path(args.style_root, root=root)
    if not style_root.is_dir():
        raise NotADirectoryError(f"style 根目录不是目录：{style_root}")

    imagegen_prompt = load_text(prompt_file)
    pages = load_editorial_pages(editorial_path)
    cover_page_number = extract_page_number(pages[0], fallback_index=0) if pages else 1
    selected_pages = parse_page_selection(args.pages)
    style_label = resolve_style_label(editorial_path)
    reference_image = resolve_reference_image(
        style_root=style_root,
        style_label=style_label,
        override=args.reference_image,
    )
    prepared_reference_image, reference_temp_dir = prepare_reference_image(reference_image)
    article_dir = editorial_path.parent

    print(f"Editorial：{editorial_path}")
    print(f"Style：{style_label}")
    print(f"参考图：{reference_image}")
    if prepared_reference_image != reference_image:
        print(f"上传参考图：{prepared_reference_image}")
    print(f"输出目录：{article_dir}")
    print(f"页数：{len(pages)}")
    if selected_pages:
        print(f"指定页：{sorted(selected_pages)}")
    print(f"固定比例：{FIXED_ASPECT_RATIO}")
    print(f"固定尺寸：{FIXED_IMAGE_SIZE}")
    print(f"max_tokens：{args.max_tokens}")

    if args.dry_run:
        for index, page_data in enumerate(pages):
            page_number = extract_page_number(page_data, fallback_index=index)
            if selected_pages and page_number not in selected_pages:
                continue
            output_path = article_dir / f"{page_number}.png"
            if page_number == cover_page_number:
                ref_name = prepared_reference_image.name
            else:
                ref_name = f"{cover_page_number}.png (封面图)"
            print(f"[DRY RUN] page {page_number} -> {output_path} (参考图: {ref_name})")
        return 0

    if not api_key:
        raise SystemExit("缺少 API Key，请传入 --api-key 或设置 IMAGE_API_KEY/OPENROUTER_API_KEY")

    try:
        for index, page_data in enumerate(pages):
            page_number = extract_page_number(page_data, fallback_index=index)
            if selected_pages and page_number not in selected_pages:
                continue
            output_path = article_dir / f"{page_number}.png"
            if output_path.exists() and not args.overwrite:
                print(f"跳过已存在：{output_path}")
                continue

            if page_number == cover_page_number:
                current_ref = prepared_reference_image
            else:
                cover_path = article_dir / f"{cover_page_number}.png"
                if cover_path.exists():
                    current_ref = cover_path
                else:
                    print(f"警告：找不到封面图 {cover_path}，将回退使用默认参考图")
                    current_ref = prepared_reference_image

            output_path = generate_page_image(
                page_data=page_data,
                page_number=page_number,
                article_dir=article_dir,
                imagegen_prompt=imagegen_prompt,
                reference_image=current_ref,
                api_key=api_key,
                base_url=base_url,
                model=args.model,
                timeout=args.timeout,
                max_tokens=args.max_tokens,
            )
            print(f"已写入：{output_path}")
    finally:
        if reference_temp_dir and reference_temp_dir.exists():
            for path in sorted(reference_temp_dir.glob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
            reference_temp_dir.rmdir()

    return 0


if __name__ == "__main__":
    sys.exit(main())
