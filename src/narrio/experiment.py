from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import os
import shutil
import time
import typing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ._services import chunkify, extract_highlights, red_image, stylify
from .paths import prompt_file, repo_paths, source_candidates, sources_dir, styles_root
from .selector import yes_no
from .workbench import START_STAGE_TO_STEP, STAGES, append_event, build_combo_id, build_run_id, combo_dir, make_run_paths, prompt_fingerprint, read_json, sanitize, write_json

logger = logging.getLogger("narrio")


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{seconds / 60:.1f}m"



def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def source_input_dir(content_type: str) -> Path:
    return sources_dir(content_type)


def default_chunk_prompt(content_type: str) -> Path:
    if content_type == "article":
        return prompt_file("ArticleChunkify.md")
    if content_type == "podcast":
        return prompt_file("PodcastChunkify.md")
    raise ValueError(f"不支持的内容类型：{content_type}")


def default_stylify_prompt() -> Path:
    return prompt_file("stylify.md")


def default_redsoul_prompt() -> Path:
    return prompt_file("RedSoul.md")


def default_image_prompt() -> Path:
    return prompt_file("ImageGen.md")


def resolve_markdown_path(content_type: str, markdown: str) -> Path:
    errors: list[Exception] = []
    for candidate_root in source_candidates(content_type):
        try:
            return chunkify.resolve_markdown_target(candidate_root, markdown)
        except FileNotFoundError as exc:
            errors.append(exc)
    raise FileNotFoundError(str(errors[-1]) if errors else f"未找到指定 markdown：{markdown}")


def resolve_audio_path(audio_file: str) -> Path:
    """Resolve audio file path from various sources."""
    from . import asr_service

    # Try direct path
    audio_path = Path(audio_file).expanduser().resolve()
    if audio_path.exists() and audio_path.is_file():
        if audio_path.suffix.lower() in asr_service.SUPPORTED_AUDIO_SUFFIXES:
            return audio_path
        raise ValueError(f"不支持的音频格式：{audio_path.suffix}")

    # Try content/audio directory
    audio_dir = repo_paths().content_root / "audio"
    candidate = audio_dir / audio_file
    if candidate.exists() and candidate.is_file():
        if candidate.suffix.lower() in asr_service.SUPPORTED_AUDIO_SUFFIXES:
            return candidate
        raise ValueError(f"不支持的音频格式：{candidate.suffix}")

    raise FileNotFoundError(f"未找到音频文件：{audio_file}")


def resolve_prompt_path(path_value: str | None, default_path: Path) -> Path:
    if path_value:
        return Path(path_value).expanduser().resolve()
    return default_path.resolve()


@dataclass(frozen=True)
class PromptOverrides:
    chunk_prompt: str | None = None
    stylify_prompt: str | None = None
    redsoul_prompt: str | None = None
    image_prompt: str | None = None
    label: str | None = None

    def resolved(self, content_type: str) -> dict[str, Path]:
        return {
            "chunk_prompt": resolve_prompt_path(self.chunk_prompt, default_chunk_prompt(content_type)),
            "stylify_prompt": resolve_prompt_path(self.stylify_prompt, default_stylify_prompt()),
            "redsoul_prompt": resolve_prompt_path(self.redsoul_prompt, default_redsoul_prompt()),
            "image_prompt": resolve_prompt_path(self.image_prompt, default_image_prompt()),
        }


@dataclass(frozen=True)
class ModelOverrides:
    chunk_model: str = chunkify.DEFAULT_MODEL
    editorial_model: str = stylify.DEFAULT_MODEL
    image_model: str = red_image.DEFAULT_MODEL


@dataclass(frozen=True)
class ExperimentRequest:
    content_type: str
    markdown: str
    style: str = "OpenAI"
    start_stage: str = "from-source"
    prompts: PromptOverrides = PromptOverrides()
    models: ModelOverrides = ModelOverrides()
    timeout: int = 180
    image_timeout: int = 300
    max_tokens: int = stylify.DEFAULT_MAX_TOKENS
    image_max_tokens: int = red_image.DEFAULT_MAX_TOKENS
    temperature: float = stylify.DEFAULT_TEMPERATURE
    text_api_key: str = ""
    image_api_key: str = ""
    text_base_url: str = ""
    image_base_url: str = ""
    image_api_format: str = "images/generations"  # "chat/completions" or "images/generations"
    dry_run: bool = False
    reuse_from_run: str | None = None
    render_workers: int | None = None  # 并行渲染 worker 数，None 表示自动（max(剩余页数，5)）
    extract_highlights: bool | None = None  # None=自动（article跳过，podcast使用），True=强制，False=跳过
    highlight_model: str | None = None
    continue_on_error: bool = False
    max_pages: int | None = None  # 图片生成数量上限，None 表示全部生成
    run_name: str | None = None  # 用户指定的运行名称
    # ASR transcribe options
    audio_file: str | None = None  # 音频文件路径（如果从音频开始）
    asr_api_key: str | None = None  # 火山引擎 API Key
    asr_app_key: str | None = None  # 火山引擎 App Key
    asr_access_token: str | None = None  # 火山引擎 Access Token
    asr_language: str | None = None  # ASR 语言
    asr_audio_source_mode: str = "auto"  # 音频来源模式
    asr_public_base_url: str | None = None  # 公网音频 URL 前缀
    asr_upload_url: str = "https://0x0.st"  # 临时上传服务
    progress_callback: typing.Callable[[str, int], None] | None = None  # 进度回调，参数为 (stage, progress)


def prompt_label(request: ExperimentRequest, prompt_paths: dict[str, Path]) -> str:
    if request.prompts.label:
        return request.prompts.label
    parts = [path.name for path in prompt_paths.values()]
    return sanitize("-".join(parts))[:64]


def build_manifest(request: ExperimentRequest, source_path: Path, combo_id: str, run_id: str, prompt_paths: dict[str, Path], run_dir: Path) -> dict:
    content_hash = hashlib.sha1(source_path.read_bytes()).hexdigest()
    return {
        "combo_id": combo_id,
        "run_id": run_id,
        "workflow_type": request.content_type,
        "status": "running",
        "created_at": now_iso(),
        "selection": {
            "markdown": request.markdown,
            "style": request.style,
            "prompt_label": prompt_label(request, prompt_paths),
        },
        "source": {
            "path": str(source_path),
            "content_hash": content_hash,
        },
        "resume": {
            "start_stage": request.start_stage,
            "reused_artifacts": [],
        },
        "assets": {
            "chunk_prompt": str(prompt_paths["chunk_prompt"]),
            "stylify_prompt": str(prompt_paths["stylify_prompt"]),
            "redsoul_prompt": str(prompt_paths["redsoul_prompt"]),
            "image_prompt": str(prompt_paths["image_prompt"]),
            "style": request.style,
        },
        "models": {
            "chunk_model": request.models.chunk_model,
            "editorial_model": request.models.editorial_model,
            "image_model": request.models.image_model,
        },
        "paths": {
            "run_dir": str(run_dir),
        },
        "steps": {
            stage: {"status": "pending"} for stage in STAGES
        },
    }


def save_manifest(manifest: dict, path: Path) -> None:
    write_json(path, manifest)


def mark_step(manifest: dict, path: Path, step: str, status: str, detail: str | None = None) -> None:
    manifest["steps"][step]["status"] = status
    manifest["steps"][step]["updated_at"] = now_iso()
    if detail:
        manifest["steps"][step]["detail"] = detail
    save_manifest(manifest, path)


def log_event(path: Path, event: str, **payload: object) -> None:
    append_event(path, {"ts": now_iso(), "event": event, **payload})


def write_selection_files(paths, request: ExperimentRequest, source_path: Path, prompt_paths: dict[str, Path], combo_id: str, run_id: str) -> None:
    write_json(
        paths.meta_dir / "selection.json",
        {
            "content_type": request.content_type,
            "markdown": request.markdown,
            "style": request.style,
            "combo_id": combo_id,
            "last_run_id": run_id,
        },
    )
    write_json(
        paths.meta_dir / "params.json",
        {
            "start_stage": request.start_stage,
            "prompt_paths": {key: str(value) for key, value in prompt_paths.items()},
            "models": {
                "chunk_model": request.models.chunk_model,
                "editorial_model": request.models.editorial_model,
                "image_model": request.models.image_model,
            },
        },
    )
    normalized_path = paths.source_dir / "normalized.md"
    normalized_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")


def resolve_resume_paths(request: ExperimentRequest) -> Path | None:
    # Stages that start from the beginning don't need resume paths
    if request.start_stage in ("from-audio", "from-source"):
        return None
    # For resume stages (from-chunk, from-editorial), require reuse_from_run
    if request.reuse_from_run:
        return Path(request.reuse_from_run).expanduser().resolve()
    raise ValueError("从中间阶段重跑时必须显式提供 --reuse-from-run")


def copy_resume_artifacts(request: ExperimentRequest, resume_run_dir: Path | None, paths, manifest: dict) -> None:
    # Stages that start from the beginning don't need to copy artifacts
    if request.start_stage in ("from-audio", "from-source"):
        return
    if resume_run_dir is None:
        raise FileNotFoundError("缺少可复用运行目录")
    if request.start_stage == "from-chunk":
        source_path = resume_run_dir / "chunk" / "chunk.json"
        if not source_path.exists():
            raise FileNotFoundError(f"缺少 chunk 中间产物：{source_path}")
        shutil.copy2(source_path, paths.chunk_dir / "chunk.json")
        manifest["resume"]["reused_artifacts"].append(str(source_path))
        return
    source_path = resume_run_dir / "editorial" / "editorial.json"
    if not source_path.exists():
        raise FileNotFoundError(f"缺少 editorial 中间产物：{source_path}")
    shutil.copy2(source_path, paths.editorial_dir / "editorial.json")
    manifest["resume"]["reused_artifacts"].append(str(source_path))


def run_transcribe_stage(request: ExperimentRequest, audio_path: Path, paths, manifest: dict) -> Path:
    """Run ASR transcription stage and return the path to the generated markdown."""
    from . import asr_service

    logger.info("transcription started: audio=%s", audio_path.name)
    log_event(paths.events_path, "transcribe.started", audio=str(audio_path))
    mark_step(manifest, paths.manifest_path, "transcribe", "running")

    # Use ASR API keys from request (must be provided via config or CLI args)
    asr_api_key = request.asr_api_key or ""
    asr_app_key = request.asr_app_key or ""
    asr_access_token = request.asr_access_token or ""

    try:
        # Transcribe audio file
        output_path = asr_service.transcribe_one_file(
            audio_path=audio_path,
            output_dir=paths.transcribe_dir,
            language=request.asr_language,
            uid="narrio-run",
            timeout=request.timeout,
            query_interval=2.0,
            api_key=asr_api_key,
            app_key=asr_app_key,
            access_token=asr_access_token,
            resource_ids=asr_service.resolve_resource_ids("auto"),
            audio_source_mode=request.asr_audio_source_mode,
            public_base_url=request.asr_public_base_url,
            upload_url=request.asr_upload_url,
        )

        logger.info("transcription completed: output=%s", output_path)
        mark_step(manifest, paths.manifest_path, "transcribe", "completed")
        log_event(paths.events_path, "transcribe.completed", output=str(output_path))
        return output_path

    except Exception as exc:
        logger.exception("transcription failed: %s", exc)
        mark_step(manifest, paths.manifest_path, "transcribe", "failed", detail=str(exc))
        log_event(paths.events_path, "transcribe.failed", error=str(exc))
        raise


def convert_highlights_to_chunk(highlights_path: Path, chunk_output_path: Path) -> None:
    """Convert highlights.json to chunk.json format for direct use in editorial stage.

    For podcast mode, highlights are used directly as content chunks without chunkify.
    """
    highlights_data = read_json(highlights_path)

    # Convert highlights to chunk format - each highlight becomes a chunk
    chunks = []
    for idx, highlight in enumerate(highlights_data.get("highlights", []), start=1):
        chunks.append({
            "page": idx,
            "title": f"亮点 {idx}",
            "content": highlight["text"],
        })

    write_json(chunk_output_path, chunks)
    logger.info("converted highlights to chunk format: %d chunks created", len(chunks))


def run_highlight_stage(request: ExperimentRequest, source_path: Path, paths, manifest: dict) -> None:
    """Run highlight extraction stage."""
    logger.info("highlight extraction started: source=%s", source_path.name)
    log_event(paths.events_path, "highlight.started", source=str(source_path))
    mark_step(manifest, paths.manifest_path, "highlight", "running")

    highlight_model = request.highlight_model or request.models.chunk_model
    base_url = request.text_base_url or extract_highlights.DEFAULT_BASE_URL

    try:
        result = extract_highlights.extract_highlights(
            input_path=source_path,
            api_key=request.text_api_key,
            base_url=base_url,
            model=highlight_model,
            content_type=request.content_type,
            timeout=request.timeout,
        )

        if result.skipped:
            logger.info("highlight extraction skipped: %s", result.skip_reason)
            mark_step(manifest, paths.manifest_path, "highlight", "skipped", detail=result.skip_reason)
            log_event(paths.events_path, "highlight.skipped", reason=result.skip_reason)
        else:
            output_path = extract_highlights.save_highlights_json(
                output_dir=paths.highlight_dir,
                input_path=source_path,
                result=result,
            )
            logger.info("highlight extraction completed: %d highlights saved to %s", len(result.highlights), output_path)
            mark_step(manifest, paths.manifest_path, "highlight", "completed")
            log_event(paths.events_path, "highlight.completed", output=str(output_path), count=len(result.highlights))
    except Exception as exc:
        logger.exception("highlight extraction failed: %s", exc)
        if request.continue_on_error:
            mark_step(manifest, paths.manifest_path, "highlight", "failed", detail=str(exc))
            log_event(paths.events_path, "highlight.failed", error=str(exc))
        else:
            raise


def run_chunk_stage(request: ExperimentRequest, source_path: Path, prompt_paths: dict[str, Path], paths, manifest: dict) -> None:
    if request.progress_callback:
        request.progress_callback("chunkify", 0)
    config = chunkify.CONTENT_TYPE_CONFIG[request.content_type]
    prompt_text = chunkify.load_text(prompt_paths["chunk_prompt"])
    user_message = chunkify.build_user_message(prompt_text, source_path, config["file_label"], config["content_label"])
    (paths.chunk_dir / "request.txt").write_text(user_message, encoding="utf-8")
    (paths.snapshots_dir / "chunk-input.txt").write_text(user_message, encoding="utf-8")
    logger.info(
        "chunkify started: model=%s timeout=%ss source=%s prompt=%s",
        request.models.chunk_model,
        request.timeout,
        source_path.name,
        prompt_paths["chunk_prompt"].name,
    )
    logger.info("chunkify request saved: %s", paths.chunk_dir / "request.txt")
    log_event(paths.events_path, "chunkify.started", source=str(source_path))
    mark_step(manifest, paths.manifest_path, "chunkify", "running")
    started_at = time.monotonic()
    base_url = request.text_base_url or chunkify.DEFAULT_BASE_URL
    response_text = chunkify.call_llm_api(
        api_key=request.text_api_key,
        base_url=base_url,
        model=request.models.chunk_model,
        user_message=user_message,
        timeout=request.timeout,
    )
    elapsed = time.monotonic() - started_at
    logger.info("chunkify model response received: elapsed=%s", format_duration(elapsed))
    (paths.chunk_dir / "response.txt").write_text(response_text, encoding="utf-8")
    json_text = chunkify.extract_json_text(response_text)
    parsed = json.loads(json_text)
    write_json(paths.chunk_dir / "chunk.json", parsed)
    logger.info("chunkify output written: %s", paths.chunk_dir / "chunk.json")
    mark_step(manifest, paths.manifest_path, "chunkify", "completed")
    log_event(paths.events_path, "chunkify.completed", output=str(paths.chunk_dir / "chunk.json"))
    if request.progress_callback:
        request.progress_callback("chunkify", 100)


def run_stylify_stage(request: ExperimentRequest, prompt_paths: dict[str, Path], paths, manifest: dict) -> None:
    if request.progress_callback:
        request.progress_callback("stylify", 0)
    chunk_file = paths.chunk_dir / "chunk.json"
    if not chunk_file.exists():
        raise FileNotFoundError(f"缺少 chunk 产物：{chunk_file}")
    style_root = styles_root().resolve()
    style_file = stylify.resolve_style_file(style_root, request.style)
    logger.info(
        "stylify started: model=%s timeout=%ss chunk=%s style=%s redsoul=%s stylify_prompt=%s",
        request.models.editorial_model,
        request.timeout,
        chunk_file,
        style_file,
        prompt_paths["redsoul_prompt"].name,
        prompt_paths["stylify_prompt"].name,
    )
    user_message = stylify.build_user_message(
        chunk_file=chunk_file,
        style_file=style_file,
        redsoul_file=prompt_paths["redsoul_prompt"],
        stylify_file=prompt_paths["stylify_prompt"],
    )
    (paths.editorial_dir / "request.md").write_text(user_message, encoding="utf-8")
    (paths.snapshots_dir / "editorial-input.md").write_text(user_message, encoding="utf-8")
    logger.info("stylify request saved: %s", paths.editorial_dir / "request.md")
    manifest["assets"]["style_file"] = str(style_file)
    manifest["assets"]["style_label"] = stylify.resolve_style_label(style_root, style_file)
    save_manifest(manifest, paths.manifest_path)
    log_event(paths.events_path, "stylify.started", chunk=str(chunk_file))
    mark_step(manifest, paths.manifest_path, "stylify", "running")
    started_at = time.monotonic()
    base_url = request.text_base_url or stylify.DEFAULT_BASE_URL
    response_text = stylify.call_llm_api(
        api_key=request.text_api_key,
        base_url=base_url,
        model=request.models.editorial_model,
        user_message=user_message,
        timeout=request.timeout,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    elapsed = time.monotonic() - started_at
    logger.info("stylify model response received: elapsed=%s", format_duration(elapsed))
    (paths.editorial_dir / "response.txt").write_text(response_text, encoding="utf-8")
    json_text = stylify.extract_json_text(response_text)
    parsed = json.loads(json_text)
    write_json(paths.editorial_dir / "editorial.json", parsed)
    logger.info("stylify output written: %s", paths.editorial_dir / "editorial.json")
    mark_step(manifest, paths.manifest_path, "stylify", "completed")
    log_event(paths.events_path, "stylify.completed", output=str(paths.editorial_dir / "editorial.json"))
    if request.progress_callback:
        request.progress_callback("stylify", 100)


def run_render_stage(request: ExperimentRequest, prompt_paths: dict[str, Path], paths, manifest: dict) -> dict:
    """Run render stage and return render info.

    Returns:
        dict with keys: total_pages, generated_pages, failed_pages
    """
    if request.progress_callback:
        request.progress_callback("render", 0)
    editorial_path = paths.editorial_dir / "editorial.json"
    if not editorial_path.exists():
        raise FileNotFoundError(f"缺少 editorial 产物：{editorial_path}")
    pages = red_image.load_editorial_pages(editorial_path)
    total_pages = len(pages)

    # 根据 max_pages 限制页面数量
    original_count = len(pages)
    if request.max_pages is not None and request.max_pages > 0:
        pages = pages[:request.max_pages]
        if len(pages) < original_count:
            logger.info("render pages limited: original=%s max_pages=%s actual=%s",
                       original_count, request.max_pages, len(pages))

    imagegen_prompt = red_image.load_text(prompt_paths["image_prompt"])
    style_label = manifest["assets"].get("style_label") or sanitize(request.style)

    # 读取 style.json 内容
    style_root = styles_root().resolve()
    style_file = stylify.resolve_style_file(style_root, request.style)
    style_json = style_file.read_text(encoding="utf-8")

    reference_image = red_image.resolve_reference_image(styles_root().resolve(), style_label, None)
    prepared_reference_image, reference_temp_dir = red_image.prepare_reference_image(reference_image)
    logger.debug("reference image prepared: original=%s prepared=%s", reference_image, prepared_reference_image)
    logger.info(
        "render started: model=%s timeout=%ss pages=%s style=%s reference=%s",
        request.models.image_model,
        request.image_timeout,
        len(pages),
        style_label,
        reference_image,
    )
    manifest["assets"]["reference_image"] = str(reference_image)
    save_manifest(manifest, paths.manifest_path)
    log_event(paths.events_path, "render.started", editorial=str(editorial_path))
    mark_step(manifest, paths.manifest_path, "render", "running")

    cover_page_number = red_image.extract_page_number(pages[0], fallback_index=0)

    # 分离封面页和其他页
    cover_page = None
    other_pages: list[dict] = []
    for index, page_data in enumerate(pages):
        page_number = red_image.extract_page_number(page_data, fallback_index=index)
        if page_number == cover_page_number:
            cover_page = page_data
        else:
            other_pages.append(page_data)

    # 保存所有页面的输入快照
    for page_data in pages:
        page_number = red_image.extract_page_number(page_data, fallback_index=pages.index(page_data))
        write_json(paths.snapshots_dir / f"render-input-page-{page_number}.json", page_data)

    # 确定并发 worker 数
    max_workers = 10  # 上限
    if request.render_workers is not None:
        max_workers = request.render_workers
    else:
        # 自动模式：使用剩余页数和上限的较小值
        max_workers = min(len(other_pages), max_workers) if other_pages else 1

    render_results = {"success": [], "failed": []}

    try:
        # 阶段 1: 串先生成封面图
        if cover_page is not None:
            logger.info("render cover page started: page=%s", cover_page_number)
            started_at = time.monotonic()
            base_url = request.image_base_url or red_image.DEFAULT_BASE_URL
            red_image.generate_page_image(
                page_data=cover_page,
                page_number=cover_page_number,
                article_dir=paths.render_dir,
                imagegen_prompt=imagegen_prompt,
                reference_image=prepared_reference_image,
                api_key=request.image_api_key,
                base_url=base_url,
                model=request.models.image_model,
                timeout=request.image_timeout,
                max_tokens=request.image_max_tokens,
                style_json=style_json,
                api_format=request.image_api_format,
            )
            elapsed = time.monotonic() - started_at
            logger.info("render cover page completed: page=%s elapsed=%s", cover_page_number, format_duration(elapsed))
            render_results["success"].append(cover_page_number)
            if request.progress_callback:
                completed = len(render_results["success"]) + len(render_results["failed"])
                request.progress_callback("render", int((completed / len(pages)) * 100))

        # 阶段 2: 并发生成其他页面
        if other_pages:
            logger.info("render parallel started: pages=%s workers=%s", len(other_pages), max_workers)

            def generate_single_page(page_data: dict, page_number: int, ref_path: Path) -> tuple[int, bool, str | None]:
                """单个页面生成函数，返回 (页码，是否成功，错误信息)"""
                try:
                    started_at = time.monotonic()
                    base_url = request.image_base_url or red_image.DEFAULT_BASE_URL
                    red_image.generate_page_image(
                        page_data=page_data,
                        page_number=page_number,
                        article_dir=paths.render_dir,
                        imagegen_prompt=imagegen_prompt,
                        reference_image=ref_path,
                        api_key=request.image_api_key,
                        base_url=base_url,
                        model=request.models.image_model,
                        timeout=request.image_timeout,
                        max_tokens=request.image_max_tokens,
                        style_json=style_json,
                        api_format=request.image_api_format,
                    )
                    elapsed = time.monotonic() - started_at
                    logger.info("render page completed: [%s/%s] page=%s elapsed=%s",
                              len(render_results["success"]) + 1, len(other_pages), page_number, format_duration(elapsed))
                    return (page_number, True, None)
                except Exception as e:
                    logger.error("render page failed: page=%s error=%s", page_number, str(e))
                    return (page_number, False, str(e))

            # 使用 ThreadPoolExecutor 并发
            cover_path = paths.render_dir / f"{cover_page_number}.png"
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_page = {}
                for page_data in other_pages:
                    page_number = red_image.extract_page_number(page_data, fallback_index=0)
                    # 使用封面图作为参考（如果存在）
                    current_ref = cover_path if cover_path.exists() else prepared_reference_image
                    future = executor.submit(generate_single_page, page_data, page_number, current_ref)
                    future_to_page[future] = page_number

                # 收集结果
                for future in concurrent.futures.as_completed(future_to_page):
                    page_number, success, error = future.result()
                    if success:
                        render_results["success"].append(page_number)
                    else:
                        render_results["failed"].append((page_number, error))
                    if request.progress_callback:
                        completed = len(render_results["success"]) + len(render_results["failed"])
                        request.progress_callback("render", int((completed / len(pages)) * 100))

            # 记录失败页面
            if render_results["failed"]:
                failed_pages = [(pn, err) for pn, err in render_results["failed"]]
                logger.warning("render failed pages: %s", [pn for pn, _ in failed_pages])

    finally:
        if reference_temp_dir and reference_temp_dir.exists():
            for path in sorted(reference_temp_dir.glob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
            reference_temp_dir.rmdir()

    # 输出统计
    success_count = len(render_results["success"])
    failed_count = len(render_results["failed"])
    logger.info("render completed: total=%s success=%s failed=%s", total_pages, success_count, failed_count)

    if failed_count > 0:
        logger.warning("render completed with %s failed page(s): %s", failed_count, [pn for pn, _ in render_results["failed"]])

    mark_step(manifest, paths.manifest_path, "render", "completed")
    log_event(paths.events_path, "render.completed", output=str(paths.render_dir), success=success_count, failed=failed_count)
    logger.info("render completed: output_dir=%s", paths.render_dir)

    if request.progress_callback:
        request.progress_callback("render", 100)

    return {
        "total_pages": total_pages,
        "generated_pages": success_count,
        "failed_pages": failed_count,
    }


def _maybe_ask_continue_render(
    request: ExperimentRequest,
    render_info: dict,
    paths,
    prompt_paths: dict[str, Path],
    manifest: dict,
) -> None:
    """Ask user whether to continue generating remaining pages if max_pages was used.

    Only asks when:
    - max_pages was specified and less than total pages
    - Not in dry_run mode
    - Running interactively (not in batch mode)
    """
    total = render_info["total_pages"]
    generated = render_info["generated_pages"]

    # Check if max_pages limited the render
    if request.max_pages is None or request.max_pages <= 0:
        return
    if request.max_pages >= total:
        return
    if generated < request.max_pages:
        # Some pages failed, don't ask yet
        return

    remaining = total - generated
    if remaining <= 0:
        return

    # Ask user
    print(f"\n已完成 {generated}/{total} 张图片的生成，剩余 {remaining} 张图片未生成")

    # Only wrap the yes_no call in try/except to catch non-interactive mode
    try:
        continue_choice = yes_no("是否继续生成剩余图片", default=True)
        logger.info("yes_no returned: %s", continue_choice)
    except (EOFError, OSError, KeyboardInterrupt) as e:
        # Non-interactive mode (e.g., batch mode) or user interrupted, skip asking
        logger.info("non-interactive mode detected or interrupted, skipping continue prompt: %s", e)
        # User interrupted or non-interactive: treat as "decline to continue" and save manifest
        return

    if continue_choice:
        logger.info("user requested to continue generating remaining pages: %s", remaining)
        # Continue generating remaining pages
        try:
            _continue_render_remaining_pages(request, prompt_paths, paths, manifest, remaining)
            logger.info("finished continuing render")
        except Exception as e:
            logger.exception("error during continue render: %s", e)
    else:
        logger.info("user declined to continue generating remaining pages")


def _continue_render_remaining_pages(
    request: ExperimentRequest,
    prompt_paths: dict[str, Path],
    paths,
    manifest: dict,
    remaining_count: int,
) -> None:
    """Continue rendering remaining pages from where we left off."""
    editorial_path = paths.editorial_dir / "editorial.json"
    pages = red_image.load_editorial_pages(editorial_path)

    # Get already generated pages
    render_dir = paths.render_dir
    generated_page_numbers = set()
    generated_png_files = []
    for png_file in render_dir.glob("*.png"):
        try:
            # Extract page number from filename (e.g., "1.png", "2.png")
            page_num = int(png_file.stem)
            generated_page_numbers.add(page_num)
            generated_png_files.append((page_num, png_file))
        except ValueError:
            continue

    # Determine cover page (first generated page or first page in editorial)
    cover_page_number = red_image.extract_page_number(pages[0], fallback_index=0)
    cover_path = paths.render_dir / f"{cover_page_number}.png"

    # Filter remaining pages
    remaining_pages = []
    for page_data in pages:
        page_number = red_image.extract_page_number(page_data, fallback_index=pages.index(page_data))
        if page_number not in generated_page_numbers:
            remaining_pages.append((page_data, page_number))

    if not remaining_pages:
        logger.info("no remaining pages to generate")
        return

    logger.info("continuing render: %s remaining pages", len(remaining_pages))

    # Load prompts and style
    imagegen_prompt = red_image.load_text(prompt_paths["image_prompt"])
    style_label = manifest["assets"].get("style_label") or sanitize(request.style)
    style_root = styles_root().resolve()
    style_file = stylify.resolve_style_file(style_root, request.style)
    style_json = style_file.read_text(encoding="utf-8")

    try:
        for page_data, page_number in remaining_pages:
            try:
                logger.info("rendering remaining page: %s", page_number)
                # Use cover image as reference if it exists (either generated before or in this continuation)
                current_ref = cover_path if cover_path.exists() else None
                if current_ref is None:
                    # If no cover exists, generate one page first to use as reference
                    logger.warning("no cover image found, cannot continue render properly")
                    continue
                red_image.generate_page_image(
                    page_data=page_data,
                    page_number=page_number,
                    article_dir=paths.render_dir,
                    imagegen_prompt=imagegen_prompt,
                    reference_image=current_ref,
                    api_key=request.image_api_key,
                    base_url=request.image_base_url or red_image.DEFAULT_BASE_URL,
                    model=request.models.image_model,
                    timeout=request.image_timeout,
                    max_tokens=request.image_max_tokens,
                    style_json=style_json,
                    api_format=request.image_api_format,
                )
                logger.info("rendered remaining page: %s", page_number)
            except Exception as e:
                logger.error("failed to render remaining page %s: %s", page_number, e)
    finally:
        pass  # No temp dir cleanup needed since we're not preparing reference image

    logger.info("completed rendering remaining pages")


def execute_experiment(request: ExperimentRequest) -> dict:
    # Determine initial source path (audio or markdown)
    if request.start_stage == "from-audio":
        if not request.audio_file:
            raise ValueError("从音频开始时必须提供 --audio-file")
        audio_path = resolve_audio_path(request.audio_file)
        # Use audio filename as source name for combo_id
        source_name = audio_path.stem
        initial_source_path = audio_path
    elif request.start_stage in ("from-chunk", "from-editorial"):
        # For resume scenarios, get source info from the reuse_from_run manifest
        if not request.reuse_from_run:
            raise ValueError("从中间阶段恢复时必须提供 reuse_from_run")
        reuse_run_dir = Path(request.reuse_from_run).expanduser().resolve()
        reuse_manifest_path = reuse_run_dir / "manifest.json"
        if not reuse_manifest_path.exists():
            raise FileNotFoundError(f"未找到历史运行的 manifest：{reuse_manifest_path}")
        reuse_manifest = read_json(reuse_manifest_path)
        # Extract source name from the original manifest
        original_markdown = reuse_manifest.get("selection", {}).get("markdown", "unknown.md")
        source_name = Path(original_markdown).stem
        # Try to find the actual source file from the previous run
        source_candidates = [
            reuse_run_dir / "source" / "normalized.md",
            reuse_run_dir / "source" / original_markdown,
        ]
        initial_source_path = None
        for candidate in source_candidates:
            if candidate.exists():
                initial_source_path = candidate
                break
        if initial_source_path is None:
            # Fallback: use original source path from manifest if it still exists
            original_source_path = Path(reuse_manifest.get("source", {}).get("path", ""))
            if original_source_path.exists():
                initial_source_path = original_source_path
            else:
                raise FileNotFoundError(f"未找到源文件，尝试过：{source_candidates}")
    else:
        source_path = resolve_markdown_path(request.content_type, request.markdown)
        source_name = source_path.stem
        initial_source_path = source_path

    prompt_paths = request.prompts.resolved(request.content_type)
    combo_id = build_combo_id(
        request.content_type,
        source_name,
        request.style,
        prompt_fingerprint(list(prompt_paths.values())),
    )
    run_id = build_run_id(request.run_name)
    paths = make_run_paths(request.content_type, combo_id, run_id)
    manifest = build_manifest(request, initial_source_path, combo_id, run_id, prompt_paths, paths.run_dir)

    # For non-audio starts, write selection files normally
    if request.start_stage != "from-audio":
        write_selection_files(paths, request, initial_source_path, prompt_paths, combo_id, run_id)

    save_manifest(manifest, paths.manifest_path)
    log_event(paths.events_path, "run.created", combo_id=combo_id, run_id=run_id)
    logger.info("run created: run_id=%s combo_id=%s run_dir=%s", run_id, combo_id, paths.run_dir)
    logger.info("events log: %s", paths.events_path)
    if request.dry_run:
        manifest["status"] = "dry_run"
        save_manifest(manifest, paths.manifest_path)
        log_event(paths.events_path, "run.dry_run")
        logger.info("dry_run: manifest written: %s", paths.manifest_path)
        return {
            "combo_id": combo_id,
            "run_id": run_id,
            "run_dir": str(paths.run_dir),
            "status": "dry_run",
        }
    try:
        logger.info("resolving resume paths: start_stage=%s reuse_from_run=%s audio_file=%s",
                   request.start_stage, request.reuse_from_run, request.audio_file)
        reuse_run_dir = resolve_resume_paths(request)
        logger.info("resume_run_dir resolved: %s", reuse_run_dir)
        copy_resume_artifacts(request, reuse_run_dir, paths, manifest)
        logger.info("artifacts copied successfully")
        save_manifest(manifest, paths.manifest_path)
        start_step = START_STAGE_TO_STEP[request.start_stage]
        logger.info("pipeline start: start_stage=%s content_type=%s extract_highlights=%s",
                   request.start_stage, request.content_type, request.extract_highlights)

        # Handle transcribe stage (if starting from audio)
        if start_step == "transcribe":
            # Run ASR transcription
            transcript_path = run_transcribe_stage(request, initial_source_path, paths, manifest)
            # Update source_path to use the transcribed markdown
            source_path = transcript_path
            # Write selection files after transcription
            write_selection_files(paths, request, source_path, prompt_paths, combo_id, run_id)
            # Continue to next stages
            start_step = "chunkify"
        else:
            # For non-transcribe starts, source_path is already set
            source_path = initial_source_path

        # Determine whether to use highlights based on extract_highlights and content_type
        use_highlights = False
        skip_chunkify = False

        if start_step == "chunkify":
            if request.extract_highlights is None:
                # Auto mode: podcast uses highlights and skips chunkify, article uses chunkify
                if request.content_type == "podcast":
                    use_highlights = True
                    skip_chunkify = True
                    logger.info("auto mode: podcast will use highlights, skip chunkify")
                else:
                    logger.info("auto mode: article will use chunkify, skip highlights")
            elif request.extract_highlights is True:
                # Explicit mode: run highlights, then chunkify
                use_highlights = True
                skip_chunkify = False
                logger.info("explicit mode: will run both highlights and chunkify")
            # If extract_highlights is False: skip highlights, use chunkify (default behavior)

        # Execute pipeline based on determined flow
        if start_step == "chunkify":
            if use_highlights:
                # Run highlight extraction
                run_highlight_stage(request, source_path, paths, manifest)

                if skip_chunkify:
                    # Convert highlights to chunk format and skip chunkify
                    highlights_path = paths.highlight_dir / "highlights.json"
                    if highlights_path.exists():
                        convert_highlights_to_chunk(highlights_path, paths.chunk_dir / "chunk.json")
                        logger.info("using highlights as chunks, skipped chunkify stage")
                        mark_step(manifest, paths.manifest_path, "chunkify", "skipped",
                                detail="using highlights instead")
                    else:
                        logger.warning("highlights.json not found, falling back to chunkify")
                        run_chunk_stage(request, source_path, prompt_paths, paths, manifest)
                else:
                    # Run chunkify normally after highlights
                    run_chunk_stage(request, source_path, prompt_paths, paths, manifest)
            else:
                # Normal flow: run chunkify
                run_chunk_stage(request, source_path, prompt_paths, paths, manifest)

            run_stylify_stage(request, prompt_paths, paths, manifest)
            render_info = run_render_stage(request, prompt_paths, paths, manifest)
        elif start_step == "stylify":
            run_stylify_stage(request, prompt_paths, paths, manifest)
            render_info = run_render_stage(request, prompt_paths, paths, manifest)
        else:
            render_info = run_render_stage(request, prompt_paths, paths, manifest)

        # 检查是否需要询问继续生成剩余图片
        _maybe_ask_continue_render(request, render_info, paths, prompt_paths, manifest)

        manifest["status"] = "completed"
        manifest["completed_at"] = now_iso()
        save_manifest(manifest, paths.manifest_path)
        log_event(paths.events_path, "run.completed")
        logger.info("run completed: run_id=%s", run_id)
        return {
            "combo_id": combo_id,
            "run_id": run_id,
            "run_dir": str(paths.run_dir),
            "status": "completed",
        }
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        manifest["failed_at"] = now_iso()
        save_manifest(manifest, paths.manifest_path)
        log_event(paths.events_path, "run.failed", error=str(exc))
        logger.exception("run failed: run_id=%s error=%s", run_id, exc)
        raise


def execute_batch(requests: list[ExperimentRequest], max_workers: int) -> list[dict]:
    if max_workers <= 1:
        return [execute_experiment(request) for request in requests]
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(execute_experiment, request): request for request in requests}
        for future in concurrent.futures.as_completed(future_map):
            request = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    {
                        "combo_id": request.markdown,
                        "run_id": "failed",
                        "run_dir": "",
                        "status": f"failed: {exc}",
                    }
                )
    return sorted(results, key=lambda item: item["run_id"])


def list_sources(content_type: str) -> list[str]:
    input_dir = source_input_dir(content_type)
    return sorted(path.name for path in input_dir.glob("*.md"))


def list_styles() -> list[str]:
    root = styles_root()
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir())


def list_prompt_candidates(content_type: str) -> dict[str, list[str]]:
    return {
        "chunk_prompt": [str(default_chunk_prompt(content_type))],
        "stylify_prompt": [str(default_stylify_prompt())],
        "redsoul_prompt": [str(default_redsoul_prompt())],
        "image_prompt": [str(default_image_prompt())],
    }


def find_run_dir(run_path: str) -> Path:
    candidate = Path(run_path).expanduser().resolve()
    manifest_path = candidate / "manifest.json"
    if manifest_path.exists():
        return candidate
    raise FileNotFoundError(f"未找到运行目录：{candidate}")


def inspect_run(run_path: str) -> dict:
    run_dir = find_run_dir(run_path)
    return read_json(run_dir / "manifest.json")


def export_run(run_path: str, export_root: str | None = None) -> dict:
    run_dir = find_run_dir(run_path)
    manifest = read_json(run_dir / "manifest.json")
    content_type = manifest.get("workflow_type") or manifest.get("selection", {}).get("content_type") or "article"
    combo_id = manifest.get("combo_id") or "unknown-combo"
    run_id = manifest.get("run_id") or run_dir.name

    exports_base = Path(export_root).expanduser().resolve() if export_root else repo_paths().exports_root.resolve()
    target_dir = exports_base / sanitize(content_type) / sanitize(combo_id) / sanitize(run_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    render_dir = run_dir / "render"
    for path in sorted(render_dir.glob("*")) if render_dir.exists() else []:
        if not path.is_file():
            continue
        shutil.copy2(path, target_dir / path.name)
        copied.append(path.name)

    for name in ("manifest.json",):
        source = run_dir / name
        if source.exists() and source.is_file():
            shutil.copy2(source, target_dir / name)
            copied.append(name)

    return {
        "export_dir": str(target_dir),
        "copied": sorted(set(copied)),
        "status": "ok",
    }


def compare_combo(content_type: str, combo_id: str) -> list[dict]:
    combo_root = combo_dir(content_type, combo_id)
    runs_dir = combo_root / "runs"
    if not runs_dir.exists():
        raise FileNotFoundError(f"未找到组合目录：{combo_root}")
    results: list[dict] = []
    for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
        manifest = read_json(run_dir / "manifest.json")
        results.append(
            {
                "run_id": manifest["run_id"],
                "status": manifest["status"],
                "prompt_label": manifest["selection"]["prompt_label"],
                "run_dir": str(run_dir),
            }
        )
    return results
