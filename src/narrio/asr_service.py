#!/usr/bin/env python3
"""ASR (Automatic Speech Recognition) service using Volcengine API.

Transcribes audio files (mp3, wav, m4a, ogg, flac) to markdown transcripts.
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib import error, parse, request

logger = logging.getLogger(__name__)

SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
QUERY_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
DEFAULT_RESOURCE_IDS = ("volc.seedasr.auc", "volc.bigasr.auc")
DEFAULT_UPLOAD_URL = "https://0x0.st"
SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


def iter_audio_files(audio_input: Path) -> list[Path]:
    """Iterate audio files from a file or directory."""
    if audio_input.is_file():
        if audio_input.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
            raise FileNotFoundError(f"不支持的音频格式：{audio_input}")
        return [audio_input]

    if not audio_input.exists():
        raise FileNotFoundError(f"音频路径不存在：{audio_input}")

    files = sorted(
        path for path in audio_input.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES
    )
    if not files:
        raise FileNotFoundError(f"未找到可转录音频：{audio_input}")
    return files


def normalize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Normalize header keys to lowercase."""
    return {key.lower(): value for key, value in headers.items()}


def encode_file_to_base64(audio_path: Path) -> str:
    """Encode audio file to base64 for inline data."""
    return base64.b64encode(audio_path.read_bytes()).decode("utf-8")


def build_header_candidates(
    request_id: str,
    resource_id: str,
    api_key: str,
    app_key: str,
    access_token: str,
) -> list[dict[str, str]]:
    """Build authentication header candidates."""
    base_headers = {
        "Content-Type": "application/json",
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": "-1",
    }
    candidates: list[dict[str, str]] = []
    if api_key:
        candidates.append(base_headers | {"X-Api-Key": api_key})
    if app_key and access_token:
        candidates.append(base_headers | {"X-Api-App-Key": app_key, "X-Api-Access-Key": access_token})
    if not candidates:
        raise ValueError("缺少鉴权信息，请传入 --api-key 或同时传入 --app-key 与 --access-token")
    return candidates


def post_json(url: str, payload: dict[str, object], headers: dict[str, str], timeout: int) -> tuple[dict[str, object], dict[str, str]]:
    """Post JSON request to Volcengine API."""
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_text = response.read().decode("utf-8", errors="replace")
            response_headers = dict(response.headers.items())
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"火山引擎请求失败：HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"火山引擎连接失败：{exc.reason}") from exc

    if not response_text.strip():
        return {}, response_headers

    try:
        return json.loads(response_text), response_headers
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"火山引擎返回格式异常：{response_text}") from exc


def upload_audio_file(audio_path: Path, upload_url: str, timeout: int) -> str:
    """Upload audio file to temporary hosting service."""
    boundary = f"----TraeBoundary{uuid.uuid4().hex}"
    filename = audio_path.name.encode("utf-8", errors="ignore").decode("utf-8")
    mime = "application/octet-stream"
    file_bytes = audio_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = request.Request(upload_url, data=body, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_text = response.read().decode("utf-8", errors="replace").strip()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"音频上传失败：HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"音频上传连接失败：{exc.reason}") from exc

    if not response_text.startswith("http://") and not response_text.startswith("https://"):
        raise RuntimeError(f"上传服务未返回有效 URL：{response_text}")
    return response_text


def build_request_payload(
    audio_path: Path,
    audio_reference: str,
    uid: str,
    language: str | None,
    use_inline_data: bool,
) -> dict[str, object]:
    """Build request payload for ASR API."""
    audio_payload: dict[str, object] = {"format": audio_path.suffix.lower().lstrip(".")}
    if use_inline_data:
        audio_payload["data"] = audio_reference
    else:
        audio_payload["url"] = audio_reference
    if language:
        audio_payload["language"] = language

    return {
        "user": {"uid": uid},
        "audio": audio_payload,
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": True,
            "show_utterances": True,
        },
    }


def submit_task(payload: dict[str, object], headers: dict[str, str], timeout: int) -> tuple[str, dict[str, str]]:
    """Submit transcription task."""
    _, response_headers = post_json(SUBMIT_URL, payload, headers, timeout)
    normalized = normalize_headers(response_headers)
    status_code = normalized.get("x-api-status-code", "")
    if status_code != "20000000":
        raise RuntimeError(f"提交任务失败：status={status_code} headers={json.dumps(response_headers, ensure_ascii=False)}")
    return headers["X-Api-Request-Id"], response_headers


def query_task(task_id: str, headers: dict[str, str], timeout: int) -> tuple[dict[str, object], dict[str, str]]:
    """Query transcription task status."""
    query_headers = dict(headers)
    query_headers.pop("X-Api-Sequence", None)
    query_headers["X-Api-Request-Id"] = task_id
    return post_json(QUERY_URL, {}, query_headers, timeout)


def wait_for_result(task_id: str, headers: dict[str, str], timeout: int, query_interval: float) -> tuple[dict[str, object], dict[str, str]]:
    """Wait for transcription result by polling."""
    while True:
        response_json, response_headers = query_task(task_id=task_id, headers=headers, timeout=timeout)
        normalized = normalize_headers(response_headers)
        status_code = normalized.get("x-api-status-code", "")
        if status_code == "20000000":
            return response_json, response_headers
        if status_code not in {"20000001", "20000002"}:
            raise RuntimeError(
                f"查询任务失败：status={status_code} headers={json.dumps(response_headers, ensure_ascii=False)} body={json.dumps(response_json, ensure_ascii=False)}"
            )
        logger.info("waiting for result: status=%s", status_code)
        time.sleep(query_interval)


def format_timestamp(value: int | float | None) -> str:
    """Format millisecond timestamp to HH:MM:SS."""
    if value is None:
        return ""
    total_seconds = max(int(round(float(value) / 1000)), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_segments(utterances: list[dict[str, object]]) -> str:
    """Format utterances with timestamps as markdown list."""
    lines: list[str] = []
    for utterance in utterances:
        text = str(utterance.get("text", "")).strip()
        if not text:
            continue
        start = format_timestamp(utterance.get("start_time") if isinstance(utterance.get("start_time"), (int, float)) else None)
        end = format_timestamp(utterance.get("end_time") if isinstance(utterance.get("end_time"), (int, float)) else None)
        prefix = f"[{start}-{end}]" if start or end else ""
        lines.append(f"- {prefix} {text}".strip() if prefix else f"- {text}")
    return "\n".join(lines)


def extract_transcript(response_json: dict[str, object]) -> tuple[str, str]:
    """Extract full text and segments from API response."""
    result = response_json.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"返回结果缺少 result 字段：{json.dumps(response_json, ensure_ascii=False)}")
    full_text = result.get("text")
    utterances = result.get("utterances")
    if not isinstance(full_text, str) or not full_text.strip():
        raise RuntimeError(f"返回结果缺少 text 字段：{json.dumps(response_json, ensure_ascii=False)}")
    segment_markdown = format_segments(utterances) if isinstance(utterances, list) else ""
    return full_text.strip(), segment_markdown


def render_markdown(
    audio_path: Path,
    audio_source: str,
    transcript_text: str,
    segment_markdown: str,
    response_headers: dict[str, str],
    response_json: dict[str, object],
    resource_id: str,
    language: str | None,
) -> str:
    """Render transcription result as markdown."""
    headers = normalize_headers(response_headers)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# {audio_path.stem}",
        "",
        f"- 源文件：{audio_path.name}",
        f"- 音频来源：{audio_source}",
        f"- 生成时间：{generated_at}",
        f"- 接口：Volcengine AUC HTTP",
        f"- Resource ID：{resource_id}",
        f"- 语言：{language or 'auto'}",
        f"- 状态码：{headers.get('x-api-status-code', '')}",
    ]
    if headers.get("x-api-message"):
        lines.append(f"- 状态信息：{headers['x-api-message']}")
    if headers.get("x-tt-logid"):
        lines.append(f"- Log ID：{headers['x-tt-logid']}")

    lines.extend(["", "## 全文", "", transcript_text.strip()])

    if segment_markdown:
        lines.extend(["", "## 分段", "", segment_markdown])

    lines.extend(
        [
            "",
            "## 原始返回",
            "",
            "```json",
            json.dumps(response_json, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown(output_dir: Path, audio_path: Path, markdown_text: str) -> Path:
    """Write markdown transcript to file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{audio_path.stem}.md"
    output_path.write_text(markdown_text, encoding="utf-8")
    return output_path


def resolve_resource_ids(resource_id: str) -> tuple[str, ...]:
    """Resolve resource IDs, auto means try both default IDs."""
    if resource_id.strip().lower() == "auto":
        return DEFAULT_RESOURCE_IDS
    return (resource_id,)


def build_public_audio_url(audio_path: Path, public_base_url: str | None, upload_url: str, timeout: int) -> str:
    """Build public audio URL or upload file."""
    if public_base_url:
        return f"{public_base_url.rstrip('/')}/{parse.quote(audio_path.name)}"
    return upload_audio_file(audio_path=audio_path, upload_url=upload_url, timeout=timeout)


def resolve_audio_sources(
    audio_path: Path,
    audio_source_mode: str,
    public_base_url: str | None,
    upload_url: str,
    timeout: int,
) -> list[tuple[str, str, bool]]:
    """Resolve audio sources based on mode: (reference, label, use_inline).

    Returns a list of (audio_reference, label, use_inline_data) tuples to try in order.
    """
    if audio_source_mode == "public-url":
        return [(build_public_audio_url(audio_path, public_base_url, upload_url, timeout), "public-url", False)]
    if audio_source_mode == "upload":
        return [(upload_audio_file(audio_path=audio_path, upload_url=upload_url, timeout=timeout), "upload-url", False)]
    if audio_source_mode == "inline":
        return [(encode_file_to_base64(audio_path), "inline-data", True)]
    if public_base_url:
        return [(build_public_audio_url(audio_path, public_base_url, upload_url, timeout), "public-url", False)]

    # Auto mode: only use inline (don't fallback to upload as many upload services are unreliable)
    # If inline fails, the error will propagate to the user with clear message
    return [
        (encode_file_to_base64(audio_path), "inline-data", True),
    ]


def try_transcription(
    audio_path: Path,
    language: str | None,
    uid: str,
    timeout: int,
    query_interval: float,
    api_key: str,
    app_key: str,
    access_token: str,
    resource_ids: tuple[str, ...],
    audio_reference: str,
    use_inline_data: bool,
) -> tuple[dict[str, object], dict[str, str], str]:
    """Try transcription with multiple resource IDs and auth methods."""
    failures: list[str] = []
    for resource_id in resource_ids:
        request_id = str(uuid.uuid4())
        for headers in build_header_candidates(
            request_id=request_id,
            resource_id=resource_id,
            api_key=api_key,
            app_key=app_key,
            access_token=access_token,
        ):
            try:
                payload = build_request_payload(
                    audio_path=audio_path,
                    audio_reference=audio_reference,
                    uid=uid,
                    language=language,
                    use_inline_data=use_inline_data,
                )
                task_id, submit_headers = submit_task(payload=payload, headers=headers, timeout=timeout)
                logger.info("task submitted: task_id=%s resource_id=%s", task_id, resource_id)
                result_json, query_headers = wait_for_result(
                    task_id=task_id,
                    headers=headers,
                    timeout=timeout,
                    query_interval=query_interval,
                )
                merged_headers = dict(submit_headers)
                merged_headers.update(query_headers)
                return result_json, merged_headers, resource_id
            except RuntimeError as exc:
                failures.append(f"[{resource_id}] {exc}")
                logger.warning("transcription attempt failed: %s", exc)
    raise RuntimeError("；".join(failures))


def transcribe_one_file(
    audio_path: Path,
    output_dir: Path,
    language: str | None,
    uid: str,
    timeout: int,
    query_interval: float,
    api_key: str,
    app_key: str,
    access_token: str,
    resource_ids: tuple[str, ...],
    audio_source_mode: str,
    public_base_url: str | None,
    upload_url: str,
) -> Path:
    """Transcribe one audio file."""
    failures: list[str] = []
    for audio_reference, source_label, use_inline_data in resolve_audio_sources(
        audio_path=audio_path,
        audio_source_mode=audio_source_mode,
        public_base_url=public_base_url,
        upload_url=upload_url,
        timeout=timeout,
    ):
        logger.info("submitting task: audio=%s mode=%s", audio_path.name, source_label)
        print(f"提交任务：{audio_path.name} [{source_label}]")
        try:
            response_json, response_headers, resolved_resource_id = try_transcription(
                audio_path=audio_path,
                language=language,
                uid=uid,
                timeout=timeout,
                query_interval=query_interval,
                api_key=api_key,
                app_key=app_key,
                access_token=access_token,
                resource_ids=resource_ids,
                audio_reference=audio_reference,
                use_inline_data=use_inline_data,
            )
            transcript_text, segment_markdown = extract_transcript(response_json)
            audio_source = audio_reference if not use_inline_data else "inline-data"
            markdown_text = render_markdown(
                audio_path=audio_path,
                audio_source=audio_source,
                transcript_text=transcript_text,
                segment_markdown=segment_markdown,
                response_headers=response_headers,
                response_json=response_json,
                resource_id=resolved_resource_id,
                language=language,
            )
            output_path = write_markdown(output_dir=output_dir, audio_path=audio_path, markdown_text=markdown_text)
            logger.info("transcript written: %s", output_path)
            print(f"已写入：{output_path}")
            return output_path
        except RuntimeError as exc:
            failures.append(f"[{source_label}] {exc}")
            logger.error("transcription failed: %s", exc)

    # All methods failed, provide helpful error message
    error_msg = "所有转录方法都失败了：\n" + "\n".join(failures)

    # Check file size and provide suggestions
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 50:
        error_msg += f"\n\n提示：音频文件较大 ({file_size_mb:.1f} MB)，建议："
        error_msg += "\n  1. 使用 --audio-source-mode public-url（如果你的文件已在公网）"
        error_msg += "\n  2. 压缩音频文件后再试"
        error_msg += "\n  3. 使用其他上传服务（0x0.st 目前不可用）"

    raise RuntimeError(error_msg)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ASR CLI."""
    from .paths import repo_paths

    paths = repo_paths()
    parser = argparse.ArgumentParser(description="Transcribe audio files to markdown using Volcengine ASR")
    parser.add_argument(
        "--audio-input",
        help="音频文件或目录，默认 content/audio/",
    )
    parser.add_argument(
        "--output-dir",
        help="markdown 输出目录，默认 content/transcripts/",
    )
    parser.add_argument(
        "--language",
        help="指定识别语言，例如 zh-CN、en-US；默认自动识别",
    )
    parser.add_argument(
        "--resource-id",
        default="auto",
        help="火山引擎资源 ID，默认 auto，自动尝试 volc.seedasr.auc 与 volc.bigasr.auc",
    )
    parser.add_argument(
        "--uid",
        default="narrio-transcriber",
        help="请求中的 uid",
    )
    parser.add_argument(
        "--public-base-url",
        help="若音频目录已可公网访问，可传公共 URL 前缀，脚本将直接拼接文件名，不再上传",
    )
    parser.add_argument(
        "--upload-url",
        default=DEFAULT_UPLOAD_URL,
        help="临时上传服务地址，默认 https://0x0.st",
    )
    parser.add_argument(
        "--audio-source-mode",
        choices=("auto", "inline", "upload", "public-url"),
        default="auto",
        help="音频来源模式，auto 会优先尝试 inline，再回退到 upload",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="新版控制台 API Key",
    )
    parser.add_argument(
        "--app-key",
        default="",
        help="旧版控制台 App Key",
    )
    parser.add_argument(
        "--access-token",
        default="",
        help="旧版控制台 Access Token",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="单次请求超时时间，单位秒",
    )
    parser.add_argument(
        "--query-interval",
        type=float,
        default=2.0,
        help="查询结果轮询间隔，单位秒",
    )

    args = parser.parse_args(argv)

    # Resolve default paths
    if args.audio_input:
        audio_input = Path(args.audio_input).expanduser().resolve()
    else:
        audio_input = paths.content_root / "audio"

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        output_dir = paths.content_root / "transcripts"

    audio_files = iter_audio_files(audio_input)
    resource_ids = resolve_resource_ids(args.resource_id)

    logger.info("transcription started: files=%d output=%s", len(audio_files), output_dir)

    for audio_path in audio_files:
        transcribe_one_file(
            audio_path=audio_path,
            output_dir=output_dir,
            language=args.language,
            uid=args.uid,
            timeout=args.timeout,
            query_interval=args.query_interval,
            api_key=args.api_key,
            app_key=args.app_key,
            access_token=args.access_token,
            resource_ids=resource_ids,
            audio_source_mode=args.audio_source_mode,
            public_base_url=args.public_base_url,
            upload_url=args.upload_url,
        )

    logger.info("transcription completed: files=%d", len(audio_files))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    sys.exit(main())
