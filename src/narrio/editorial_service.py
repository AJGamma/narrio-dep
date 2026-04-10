#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib import error, request


DEFAULT_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3.1-flash-image-preview"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 12000
TIMESTAMP_FORMAT = "%y%m%d-%H%M%S"
ALT_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sanitize_path_segment(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return cleaned or "untitled"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_json_text(path: Path) -> str:
    data = json.loads(load_text(path))
    return json.dumps(data, ensure_ascii=False, indent=2)


def resolve_markdown_path(article_input: Path, markdown: str) -> Path:
    candidate = Path(markdown).expanduser()
    if candidate.exists():
        return candidate.resolve()

    nested_candidate = article_input / markdown
    if nested_candidate.exists():
        return nested_candidate.resolve()

    if candidate.suffix.lower() != ".md":
        named_candidate = article_input / f"{markdown}.md"
        if named_candidate.exists():
            return named_candidate.resolve()

    raise FileNotFoundError(f"未找到指定 markdown：{markdown}")


def resolve_article_dir_name(article_input: Path, markdown: str) -> str:
    markdown_path = resolve_markdown_path(article_input=article_input, markdown=markdown)
    return sanitize_path_segment(markdown_path.stem)


def resolve_style_file(styles_root: Path, style: str) -> Path:
    candidate = Path(style).expanduser()
    paths_to_try: list[Path] = []

    if candidate.is_absolute():
        paths_to_try.extend(
            [
                candidate,
                candidate / "style.json",
            ]
        )
    else:
        paths_to_try.extend(
            [
                candidate,
                candidate / "style.json",
                styles_root / candidate,
                styles_root / candidate / "style.json",
            ]
        )
        if candidate.suffix.lower() != ".json":
            paths_to_try.append(styles_root / f"{style}.json")

    for path in paths_to_try:
        if path.exists() and path.is_file():
            return path.resolve()

    raise FileNotFoundError(f"未找到指定 style：{style}")


def resolve_style_label(styles_root: Path, style_file: Path) -> str:
    try:
        relative_path = style_file.relative_to(styles_root)
    except ValueError:
        relative_path = style_file

    if style_file.name.lower() == "style.json":
        label_source = relative_path.parent.name or style_file.parent.name
    else:
        label_source = relative_path.stem or style_file.stem

    return sanitize_path_segment(label_source).replace(" ", "-")


def parse_timestamp_value(value: str) -> datetime:
    for fmt in (TIMESTAMP_FORMAT, ALT_TIMESTAMP_FORMAT):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间戳：{value}")


def extract_timestamp_value(value: str) -> str | None:
    match = re.search(r"(\d{6,8}-\d{6})", value)
    if not match:
        return None
    return match.group(1)


def find_latest_chunk_file(output_root: Path, article_dir_name: str) -> Path:
    article_dir = output_root / article_dir_name
    if not article_dir.exists():
        raise FileNotFoundError(f"未找到文章输出目录：{article_dir}")

    chunk_candidates: list[tuple[datetime, Path]] = []
    for path in article_dir.iterdir():
        if path.is_file() and path.suffix.lower() == ".json" and path.stem.startswith("chunk "):
            timestamp = extract_timestamp_value(path.stem)
            if timestamp:
                chunk_candidates.append((parse_timestamp_value(timestamp), path))
            continue

        fallback_chunk_file = path / "chunk.json"
        if path.is_dir() and fallback_chunk_file.exists():
            timestamp = extract_timestamp_value(path.name)
            if timestamp:
                chunk_candidates.append((parse_timestamp_value(timestamp), fallback_chunk_file))

    chunk_candidates.sort(key=lambda item: item[0], reverse=True)
    if not chunk_candidates:
        raise FileNotFoundError(f"未找到 chunk.json：{article_dir}")
    return chunk_candidates[0][1]


def build_user_message(chunk_file: Path, style_file: Path, redsoul_file: Path, stylify_file: Path) -> str:
    parts = [
        load_json_text(chunk_file),
        load_json_text(style_file),
        load_text(redsoul_file),
        load_text(stylify_file),
    ]
    return "\n\n---\n\n".join(parts)


def call_llm_api(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    timeout: int,
    temperature: float,
    max_tokens: int,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": user_message,
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
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

    try:
        data = json.loads(response_text)
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"API 返回格式异常：{response_text}") from exc


def extract_json_text(response_text: str) -> str:
    fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", response_text, flags=re.IGNORECASE)
    candidates = [block.strip() for block in fenced_blocks if block.strip()]
    stripped = response_text.strip()
    if stripped:
        candidates.append(stripped)

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

        for index, char in enumerate(candidate):
            if char not in "[{":
                continue
            try:
                _, end = decoder.raw_decode(candidate[index:])
                fragment = candidate[index:index + end].strip()
                json.loads(fragment)
                return fragment
            except json.JSONDecodeError:
                continue

    raise ValueError(f"模型返回内容不是可解析 JSON：{response_text}")


def resolve_chunk_timestamp(chunk_file: Path) -> str:
    timestamp = extract_timestamp_value(chunk_file.stem)
    if timestamp:
        return parse_timestamp_value(timestamp).strftime(TIMESTAMP_FORMAT)

    timestamp = extract_timestamp_value(chunk_file.parent.name)
    if timestamp:
        return parse_timestamp_value(timestamp).strftime(TIMESTAMP_FORMAT)

    raise ValueError(f"未能从 chunk 文件提取时间戳：{chunk_file}")


def resolve_editorial_output_dir(chunk_file: Path) -> Path:
    if chunk_file.name == "chunk.json":
        return chunk_file.parent.parent
    return chunk_file.parent


def save_editorial_debug_markdown(chunk_file: Path, style_label: str, user_message: str) -> Path:
    timestamp = resolve_chunk_timestamp(chunk_file)
    output_dir = resolve_editorial_output_dir(chunk_file)
    output_path = output_dir / f"Editorial-debug-{style_label}-{timestamp}.md"
    output_path.write_text(user_message, encoding="utf-8")
    return output_path


def save_editorial_json(chunk_file: Path, style_label: str, json_text: str) -> Path:
    parsed = json.loads(json_text)
    timestamp = resolve_chunk_timestamp(chunk_file)
    output_dir = resolve_editorial_output_dir(chunk_file)
    output_path = output_dir / f"Editorial-{style_label}-{timestamp}.json"
    output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--article-input",
        default=str(root / "input" / "article"),
        help="markdown 文章目录，默认 input/article",
    )
    parser.add_argument(
        "--markdown",
        required=True,
        help="指定要处理的 markdown，可传文件名、去掉 .md 的名称或完整路径",
    )
    parser.add_argument(
        "--chunk-root",
        default=str(root / "output" / "article"),
        help="chunk 输出根目录，默认 output/article",
    )
    parser.add_argument(
        "--style-root",
        default=str(root / "process" / "styles"),
        help="style 根目录，默认 process/styles",
    )
    parser.add_argument(
        "--style",
        required=True,
        help="指定 style，可传目录名、style.json 路径或完整路径",
    )
    parser.add_argument(
        "--redsoul-file",
        default=str(root / "process" / "prompt" / "RedSoul.md"),
        help="RedSoul 提示词文件路径",
    )
    parser.add_argument(
        "--stylify-file",
        default=str(root / "process" / "prompt" / "stylify.md"),
        help="stylify 提示词文件路径",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenRouter 模型名称",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="显式传给 OpenRouter 的 temperature",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="显式传给 OpenRouter 的 max_tokens",
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
        default=180,
        help="单次请求超时时间，单位秒",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.api_key:
        raise SystemExit("缺少 API Key，请传入 --api-key 或设置 TEXT_API_KEY/OPENROUTER_API_KEY")

    article_input = Path(args.article_input).expanduser().resolve()
    chunk_root = Path(args.chunk_root).expanduser().resolve()
    styles_root = Path(args.style_root).expanduser().resolve()
    redsoul_file = Path(args.redsoul_file).expanduser().resolve()
    stylify_file = Path(args.stylify_file).expanduser().resolve()

    article_dir_name = resolve_article_dir_name(article_input=article_input, markdown=args.markdown)
    chunk_file = find_latest_chunk_file(output_root=chunk_root, article_dir_name=article_dir_name)
    style_file = resolve_style_file(styles_root=styles_root, style=args.style)
    style_label = resolve_style_label(styles_root=styles_root, style_file=style_file)

    print(f"markdown：{args.markdown}")
    print(f"chunk：{chunk_file}")
    print(f"style：{style_file}")
    print(f"temperature：{args.temperature}")
    print(f"max_tokens：{args.max_tokens}")

    user_message = build_user_message(
        chunk_file=chunk_file,
        style_file=style_file,
        redsoul_file=redsoul_file,
        stylify_file=stylify_file,
    )
    debug_output_path = save_editorial_debug_markdown(
        chunk_file=chunk_file,
        style_label=style_label,
        user_message=user_message,
    )
    response_text = call_llm_api(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        user_message=user_message,
        timeout=args.timeout,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    json_text = extract_json_text(response_text)
    output_path = save_editorial_json(chunk_file=chunk_file, style_label=style_label, json_text=json_text)
    print(f"debug：{debug_output_path}")
    print(f"已写入：{output_path}")
    return 0


# Alias for backward compatibility
call_openrouter = call_llm_api


if __name__ == "__main__":
    sys.exit(main())
