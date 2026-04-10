#!/usr/bin/env python3
"""Highlight extraction service for Narrio.

Extracts engaging, quotable sentences from long-form content (articles and podcasts)
to use as preview or thumbnail content.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from urllib import error, request

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3.1-flash-image-preview"
DEFAULT_TIMEOUT = 180
MIN_WORD_COUNT = 1000
DEFAULT_MAX_HIGHLIGHTS = 5

CONTENT_TYPE_CONFIG = {
    "article": {
        "default_input": ("input", "article"),
        "default_prompt": ("assets", "prompts", "HighlightExtract.md"),
        "default_output": ("output", "article"),
        "file_label": "文章文件名",
        "content_label": "文章内容",
        "prompt_variant": "article",
    },
    "podcast": {
        "default_input": ("input", "podcast", "transcript"),
        "default_prompt": ("assets", "prompts", "HighlightExtract.md"),
        "default_output": ("output", "podcast"),
        "file_label": "播客文稿文件名",
        "content_label": "播客文稿内容",
        "prompt_variant": "podcast",
    },
}


@dataclass
class Highlight:
    """A single extracted highlight."""
    text: str
    score: float
    rationale: str
    position: dict[str, Any]


@dataclass
class HighlightResult:
    """Result of highlight extraction."""
    highlights: list[Highlight]
    word_count: int
    skipped: bool = False
    skip_reason: str | None = None


def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parents[2]


def sanitize_path_segment(value: str) -> str:
    """Sanitize a string for use as a path segment."""
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return cleaned or "untitled"


def load_text(path: Path) -> str:
    """Load text from a file."""
    return path.read_text(encoding="utf-8").strip()


def count_words(text: str) -> int:
    """Count words in text, treating each Chinese character as a word."""
    # Count Chinese characters (CJK Unified Ideographs) - each char is a word
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    chinese_count = len(chinese_chars)

    # Remove Chinese characters and count remaining words by whitespace
    non_chinese_text = re.sub(r'[\u4e00-\u9fff]', ' ', text)
    non_chinese_words = non_chinese_text.split()
    non_chinese_count = len(non_chinese_words)

    return chinese_count + non_chinese_count


def build_user_message(
    prompt_text: str,
    input_path: Path,
    file_label: str,
    content_label: str,
    content_type: str,
) -> str:
    """Build the user message for the LLM API."""
    input_text = load_text(input_path)

    # Add content type specific instructions
    type_instruction = ""
    if content_type == "article":
        type_instruction = "\n\n请特别关注：\n- 洞察密度高的句子\n- 反直觉的观点\n- 主题句和关键论点\n- 具有启发性的段落"
    elif content_type == "podcast":
        type_instruction = "\n\n请特别关注：\n- 对话中的金句\n- 有情感共鸣的时刻\n- 自然口语化的表达\n- 有叙事吸引力的片段"

    return f"{prompt_text}\n\n{file_label}: {input_path.name}\n\n{content_label}:\n{input_text}{type_instruction}"


def call_llm_api(
    api_key: str,
    base_url: str,
    model: str,
    user_message: str,
    timeout: int,
) -> str:
    """Call the LLM API and return the response content."""
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
    """Extract JSON from LLM response text."""
    fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", response_text, re.IGNORECASE)
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


def parse_highlight(highlight_data: dict[str, Any]) -> Highlight:
    """Parse a single highlight from LLM response data."""
    return Highlight(
        text=highlight_data.get("text", ""),
        score=float(highlight_data.get("score", 0)),
        rationale=highlight_data.get("rationale", ""),
        position=highlight_data.get("position", {}),
    )


def parse_highlights_response(response_text: str) -> list[Highlight]:
    """Parse the LLM response and return a list of Highlights."""
    json_text = extract_json_text(response_text)
    data = json.loads(json_text)

    highlights_data = data.get("highlights", [])
    highlights = []
    for item in highlights_data:
        try:
            highlights.append(parse_highlight(item))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(f"解析单个 highlight 失败：{exc}, 数据：{item}")
            continue

    # Sort by score descending
    highlights.sort(key=lambda h: h.score, reverse=True)
    return highlights


def find_sentence_positions(content: str, highlights: list[Highlight]) -> list[Highlight]:
    """Find and add position information for each highlight in the source content."""
    if not highlights:
        return highlights

    # Split content into sentences (simple approach: split on .!?)
    # This is a simplified version; could be improved with proper sentence tokenization
    sentences = re.split(r'(?<=[.!?])\s+', content)

    result = []
    for highlight in highlights:
        position = highlight.position.copy()

        # Try to find the sentence in the content
        best_match_index = None
        for idx, sentence in enumerate(sentences):
            if highlight.text.strip() in sentence or sentence in highlight.text.strip():
                best_match_index = idx
                break

        if best_match_index is not None:
            # Calculate which paragraph/chunk this sentence belongs to
            # For now, we'll use a simple approach
            position["sentence_index"] = best_match_index
            position["total_sentences"] = len(sentences)

        result.append(Highlight(
            text=highlight.text,
            score=highlight.score,
            rationale=highlight.rationale,
            position=position,
        ))

    return result


def extract_highlights(
    input_path: Path,
    api_key: str,
    base_url: str,
    model: str,
    content_type: str,
    prompt_file: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    min_word_count: int = MIN_WORD_COUNT,
    max_highlights: int = DEFAULT_MAX_HIGHLIGHTS,
) -> HighlightResult:
    """Extract highlights from content.

    Args:
        input_path: Path to the input markdown file
        api_key: API key for LLM
        base_url: Base URL for LLM API
        model: Model name to use
        content_type: "article" or "podcast"
        prompt_file: Optional path to custom prompt file
        timeout: Request timeout in seconds
        min_word_count: Minimum word count to process
        max_highlights: Maximum number of highlights to return

    Returns:
        HighlightResult with extracted highlights
    """
    # Load content
    content = load_text(input_path)
    word_count = count_words(content)

    # Check minimum word count
    if word_count < min_word_count:
        return HighlightResult(
            highlights=[],
            word_count=word_count,
            skipped=True,
            skip_reason=f"内容字数 ({word_count}) 少于最低要求 ({min_word_count})",
        )

    # Load prompt
    if prompt_file is None:
        root = project_root()
        prompt_file = build_default_path(root, content_type, "default_prompt")

    prompt_text = load_text(prompt_file)

    # Add max_highlights instruction to prompt
    max_highlights_instruction = f"\n\n请返回 {max_highlights} 个以内的最佳亮点。"
    full_prompt = prompt_text + max_highlights_instruction

    # Build user message
    config = CONTENT_TYPE_CONFIG[content_type]
    user_message = build_user_message(
        prompt_text=full_prompt,
        input_path=input_path,
        file_label=config["file_label"],
        content_label=config["content_label"],
        content_type=content_type,
    )

    logger.info(f"调用 LLM API 提取亮点，模型：{model}, 内容类型：{content_type}")

    # Call LLM API
    response_text = call_llm_api(
        api_key=api_key,
        base_url=base_url,
        model=model,
        user_message=user_message,
        timeout=timeout,
    )

    # Parse response
    highlights = parse_highlights_response(response_text)

    # Add position information
    highlights = find_sentence_positions(content, highlights)

    # Limit to max_highlights
    highlights = highlights[:max_highlights]

    logger.info(f"成功提取 {len(highlights)} 个亮点")

    return HighlightResult(
        highlights=highlights,
        word_count=word_count,
        skipped=False,
    )


def build_timestamp() -> str:
    """Build a timestamp string for output filenames."""
    from datetime import datetime
    return datetime.now().strftime("%y%m%d-%H%M%S")


def save_highlights_json(
    output_dir: Path,
    input_path: Path,
    result: HighlightResult,
    use_subdir: bool = False,
) -> Path:
    """Save highlights to a JSON file.

    Args:
        output_dir: Base output directory
        input_path: Original input file path (for metadata and subdir name)
        result: Highlight extraction result
        use_subdir: If True, create a subdirectory per input file with timestamp.
                   If False, save directly as highlights.json (for pipeline use).

    Returns:
        Path to the saved highlights.json file
    """
    if use_subdir:
        # Legacy behavior for standalone CLI: create subdir with timestamp
        input_dir = output_dir / sanitize_path_segment(input_path.stem)
        input_dir.mkdir(parents=True, exist_ok=True)
        timestamp = build_timestamp()
        output_path = input_dir / f"highlights {timestamp}.json"
    else:
        # Pipeline behavior: save directly to output_dir as highlights.json
        output_path = output_dir / "highlights.json"

    # Convert to JSON-serializable format
    output_data = {
        "highlights": [
            {
                "text": h.text,
                "score": h.score,
                "rationale": h.rationale,
                "position": h.position,
            }
            for h in result.highlights
        ],
        "word_count": result.word_count,
        "skipped": result.skipped,
        "skip_reason": result.skip_reason,
        "source_file": input_path.name,
    }

    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def build_default_path(root: Path, content_type: str, key: str) -> Path:
    """Build a default path based on content type."""
    parts = CONTENT_TYPE_CONFIG[content_type][key]
    return root.joinpath(*parts)


def iter_markdown_files(input_target: Path) -> list[Path]:
    """Iterate over markdown files in a directory or single file."""
    if input_target.is_file():
        return [input_target]

    if not input_target.exists():
        raise FileNotFoundError(f"输入路径不存在：{input_target}")

    files = sorted(
        path for path in input_target.iterdir()
        if path.is_file() and path.suffix.lower() == ".md"
    )
    if not files:
        raise FileNotFoundError(f"未找到 markdown 文件：{input_target}")
    return files


def resolve_markdown_target(input_path: Path, markdown: str | None) -> Path:
    """Resolve the markdown file path."""
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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="从长文本中提取引人注目的亮点句子"
    )
    parser.add_argument(
        "--content-type",
        choices=sorted(CONTENT_TYPE_CONFIG),
        default="article",
        help="内容类型，默认 article；可选 article 或 podcast",
    )
    parser.add_argument(
        "--input-path",
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
        default=DEFAULT_TIMEOUT,
        help="单次请求超时时间，单位秒",
    )
    parser.add_argument(
        "--min-word-count",
        type=int,
        default=MIN_WORD_COUNT,
        help="最低字数要求，低于此值不提取",
    )
    parser.add_argument(
        "--max-highlights",
        type=int,
        default=DEFAULT_MAX_HIGHLIGHTS,
        help="最多返回的亮点数量",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    if not args.api_key:
        raise SystemExit(
            "缺少 API Key，请传入 --api-key 或设置 TEXT_API_KEY/OPENROUTER_API_KEY"
        )

    root = project_root()
    content_config = CONTENT_TYPE_CONFIG[args.content_type]

    # Resolve paths
    input_path = (
        Path(args.input_path).expanduser().resolve()
        if args.input_path
        else build_default_path(root, args.content_type, "default_input")
    )
    prompt_file = (
        Path(args.prompt_file).expanduser().resolve()
        if args.prompt_file
        else build_default_path(root, args.content_type, "default_prompt")
    )
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else build_default_path(root, args.content_type, "default_output")
    )

    # Resolve markdown target
    markdown_target = resolve_markdown_target(input_path=input_path, markdown=args.markdown)
    markdown_files = iter_markdown_files(markdown_target)

    for markdown_path in markdown_files:
        print(f"处理中：{markdown_path.name}")

        result = extract_highlights(
            input_path=markdown_path,
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            content_type=args.content_type,
            prompt_file=prompt_file,
            timeout=args.timeout,
            min_word_count=args.min_word_count,
            max_highlights=args.max_highlights,
        )

        if result.skipped:
            print(f"跳过 ({result.skip_reason})")
        else:
            output_path = save_highlights_json(
                output_dir=output_root,
                input_path=markdown_path,
                result=result,
                use_subdir=True,
            )
            print(f"已写入：{output_path}")
            print(f"提取了 {len(result.highlights)} 个亮点")

    return 0


if __name__ == "__main__":
    sys.exit(main())
