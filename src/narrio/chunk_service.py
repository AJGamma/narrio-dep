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
TIMESTAMP_FORMAT = "%y%m%d-%H%M%S"
CONTENT_TYPE_CONFIG = {
    "article": {
        "default_input": ("input", "article"),
        "default_prompt": ("process", "prompt", "ArticleChunkify.md"),
        "default_output": ("output", "article"),
        "file_label": "文章文件名",
        "content_label": "文章内容",
    },
    "podcast": {
        "default_input": ("input", "podcast", "transcript"),
        "default_prompt": ("process", "prompt", "PodcastChunkify.md"),
        "default_output": ("output", "podcast"),
        "file_label": "播客文稿文件名",
        "content_label": "播客文稿内容",
    },
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sanitize_path_segment(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return cleaned or "untitled"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_user_message(prompt_text: str, input_path: Path, file_label: str, content_label: str) -> str:
    input_text = load_text(input_path)
    return f"{prompt_text}\n\n{file_label}：{input_path.name}\n\n{content_label}：\n{input_text}"


def call_llm_api(api_key: str, base_url: str, model: str, user_message: str, timeout: int) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": user_message,
            }
        ],
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


# Alias for backward compatibility
call_openrouter = call_llm_api


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


def build_timestamp() -> str:
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def save_chunk_json(output_root: Path, input_path: Path, json_text: str) -> Path:
    timestamp = build_timestamp()
    input_dir = output_root / sanitize_path_segment(input_path.stem)
    input_dir.mkdir(parents=True, exist_ok=True)

    parsed = json.loads(json_text)
    output_path = input_dir / f"chunk {timestamp}.json"
    output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def iter_markdown_files(input_target: Path) -> list[Path]:
    if input_target.is_file():
        return [input_target]

    if not input_target.exists():
        raise FileNotFoundError(f"输入路径不存在：{input_target}")

    files = sorted(path for path in input_target.iterdir() if path.is_file() and path.suffix.lower() == ".md")
    if not files:
        raise FileNotFoundError(f"未找到 markdown 文件：{input_target}")
    return files


def resolve_markdown_target(input_path: Path, markdown: str | None) -> Path:
    if not markdown:
        return input_path

    candidate = Path(markdown).expanduser()
    if candidate.exists():
        return candidate.resolve()

    if candidate.suffix.lower() != ".md":
        named_candidate = input_path / f"{markdown}.md"
        if named_candidate.exists():
            return named_candidate.resolve()

    nested_candidate = input_path / markdown
    if nested_candidate.exists():
        return nested_candidate.resolve()

    raise FileNotFoundError(f"未找到指定 markdown：{markdown}")


def build_default_path(root: Path, content_type: str, key: str) -> Path:
    parts = CONTENT_TYPE_CONFIG[content_type][key]
    return root.joinpath(*parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--content-type",
        choices=sorted(CONTENT_TYPE_CONFIG),
        default="article",
        help="内容类型，默认 article；可选 article 或 podcast",
    )
    parser.add_argument(
        "--article-input",
        "--input-path",
        dest="input_path",
        help="markdown 文件或目录，默认根据 --content-type 自动选择",
    )
    parser.add_argument(
        "--markdown",
        help="指定只解析某一个 markdown，可传文件名、文件名去掉 .md 后的名称，或完整路径",
    )
    parser.add_argument(
        "--prompt-file",
        help="提示词文件路径，默认根据 --content-type 自动选择",
    )
    parser.add_argument(
        "--output-root",
        help="输出根目录，默认根据 --content-type 自动选择",
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
        default=180,
        help="单次请求超时时间，单位秒",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.api_key:
        raise SystemExit("缺少 API Key，请传入 --api-key 或在 .narrio.yaml 中配置")

    root = project_root()
    content_config = CONTENT_TYPE_CONFIG[args.content_type]
    input_path = Path(args.input_path).expanduser().resolve() if args.input_path else build_default_path(root, args.content_type, "default_input")
    prompt_file = Path(args.prompt_file).expanduser().resolve() if args.prompt_file else build_default_path(root, args.content_type, "default_prompt")
    output_root = Path(args.output_root).expanduser().resolve() if args.output_root else build_default_path(root, args.content_type, "default_output")

    prompt_text = load_text(prompt_file)
    markdown_target = resolve_markdown_target(input_path=input_path, markdown=args.markdown)
    markdown_files = iter_markdown_files(markdown_target)

    for markdown_path in markdown_files:
        print(f"处理中：{markdown_path.name}")
        user_message = build_user_message(
            prompt_text=prompt_text,
            input_path=markdown_path,
            file_label=content_config["file_label"],
            content_label=content_config["content_label"],
        )
        response_text = call_llm_api(
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            user_message=user_message,
            timeout=args.timeout,
        )
        json_text = extract_json_text(response_text)
        output_path = save_chunk_json(output_root=output_root, input_path=markdown_path, json_text=json_text)
        print(f"已写入：{output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
