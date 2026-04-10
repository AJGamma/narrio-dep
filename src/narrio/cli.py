from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from .config import load_config
from .experiment import (
    ExperimentRequest,
    ModelOverrides,
    PromptOverrides,
    compare_combo,
    execute_batch,
    execute_experiment,
    export_run,
    inspect_run,
    list_sources,
    list_styles,
)
from .selector import (
    ask_text,
    select_one,
    yes_no,
    select_file_with_mtime,
    select_audio_file_with_mtime,
    select_directory_with_mtime,
    select_run_directory,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="narrio")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    add_request_args(run_parser)
    run_parser.add_argument("--batch-file", help="JSON 文件，内容为实验请求数组")
    run_parser.add_argument(
        "--max-workers", type=int, default=1, help="并发实验 worker 数"
    )
    run_parser.add_argument(
        "--render-workers",
        type=int,
        default=None,
        help="并行渲染 worker 数，默认自动（剩余页数和 5 的较小值）",
    )

    def parse_extract_highlights(value):
        """Parse extract-highlights argument: true/false/1/0/yes/no"""
        if value is None:
            return None
        v = value.lower().strip()
        if v in ("true", "1", "yes"):
            return True
        elif v in ("false", "0", "no"):
            return False
        else:
            raise argparse.ArgumentTypeError(
                f"Invalid value for --extract-highlights: {value}"
            )

    run_parser.add_argument(
        "--extract-highlights",
        nargs="?",
        const=True,
        default=None,
        type=parse_extract_highlights,
        help="提取亮点：不指定时根据content_type自动决定（article跳过，podcast使用），显式指定true/false强制开启/关闭",
    )
    run_parser.add_argument(
        "--highlight-model", help="用于亮点提取的模型，默认使用 chunk-model"
    )
    run_parser.add_argument(
        "--continue-on-error", action="store_true", help="亮点提取失败时继续流程"
    )
    run_parser.add_argument(
        "--max-pages", type=int, default=None, help="图片生成数量上限，默认全部生成"
    )
    run_parser.add_argument(
        "--name", help="为本次运行指定名称，将用于生成中间文件目录名"
    )

    resume_parser = subparsers.add_parser("resume")
    add_request_args(resume_parser, include_start_stage=False)
    resume_parser.add_argument("--reuse-from-run", required=True, help="历史运行目录")
    resume_parser.add_argument(
        "--start-stage",
        choices=["from-chunk", "from-editorial"],
        default="from-chunk",
        help="恢复起始阶段",
    )
    resume_parser.add_argument(
        "--render-workers", type=int, default=None, help="并行渲染 worker 数"
    )
    resume_parser.add_argument(
        "--name", help="为本次运行指定名称，将用于生成中间文件目录名"
    )

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("run_path", help="运行目录")

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("run_path", help="运行目录")
    export_parser.add_argument("--export-root", help="导出根目录，默认 exports/")

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument(
        "--content-type", choices=["article", "podcast"], required=True
    )
    compare_parser.add_argument("--combo-id", required=True)

    lab_parser = subparsers.add_parser("lab")
    lab_parser.add_argument("--api-key", default="")
    lab_parser.add_argument("--dry-run", action="store_true")

    # Highlight extraction command
    highlight_parser = subparsers.add_parser("extract-highlights")
    highlight_parser.add_argument(
        "--content-type", choices=["article", "podcast"], default="article"
    )
    highlight_parser.add_argument("--input-path", help="输入文件或目录路径")
    highlight_parser.add_argument("--markdown", help="指定单个 markdown 文件")
    highlight_parser.add_argument("--prompt-file", help="提示词文件路径")
    highlight_parser.add_argument("--output-root", help="输出根目录")
    highlight_parser.add_argument("--model", help="使用的模型")
    highlight_parser.add_argument("--api-key", default="")
    highlight_parser.add_argument("--base-url", default="")
    highlight_parser.add_argument("--timeout", type=int, default=180)
    highlight_parser.add_argument("--min-word-count", type=int, default=1000)
    highlight_parser.add_argument("--max-highlights", type=int, default=5)
    highlight_parser.add_argument(
        "--continue-on-error", action="store_true", help="错误时继续，不中断流程"
    )

    # Tune command - multi-variant parallel pipeline
    tune_parser = subparsers.add_parser(
        "tune", help="Run multiple style variants in parallel using tmux"
    )
    tune_parser.add_argument(
        "--input", help="Input file path (if not provided, will prompt interactively)"
    )
    tune_parser.add_argument(
        "--styles",
        help="Comma-separated list of styles (e.g., 'OpenAI,Anthropic,Google')",
    )
    tune_parser.add_argument(
        "--no-auto-display",
        action="store_true",
        help="Skip automatic image display after completion",
    )
    tune_parser.add_argument(
        "--attach", metavar="SESSION_NAME", help="Attach to an existing tmux session"
    )
    tune_parser.add_argument(
        "--list", action="store_true", help="List all active narrio-tune sessions"
    )

    # Transcribe command - ASR for audio files
    transcribe_parser = subparsers.add_parser(
        "transcribe",
        help="Transcribe audio files (mp3, wav, etc.) to markdown using Volcengine ASR",
    )
    transcribe_parser.add_argument(
        "--audio-input", help="音频文件或目录，默认 content/audio/"
    )
    transcribe_parser.add_argument(
        "--output-dir", help="markdown 输出目录，默认 content/transcripts/"
    )
    transcribe_parser.add_argument(
        "--language", help="指定识别语言，例如 zh-CN、en-US；默认自动识别"
    )
    transcribe_parser.add_argument(
        "--resource-id", default="auto", help="火山引擎资源 ID，默认 auto"
    )
    transcribe_parser.add_argument(
        "--uid", default="narrio-transcriber", help="请求中的 uid"
    )
    transcribe_parser.add_argument(
        "--public-base-url", help="若音频已可公网访问，传入公共 URL 前缀"
    )
    transcribe_parser.add_argument(
        "--upload-url", default="https://0x0.st", help="临时上传服务地址"
    )
    transcribe_parser.add_argument(
        "--audio-source-mode",
        choices=("auto", "inline", "upload", "public-url"),
        default="auto",
        help="音频来源模式",
    )
    transcribe_parser.add_argument("--api-key", default="", help="火山引擎 API Key")
    transcribe_parser.add_argument("--app-key", default="", help="火山引擎 App Key")
    transcribe_parser.add_argument(
        "--access-token", default="", help="火山引擎 Access Token"
    )
    transcribe_parser.add_argument(
        "--timeout", type=int, default=600, help="单次请求超时时间，单位秒"
    )
    transcribe_parser.add_argument(
        "--query-interval", type=float, default=2.0, help="查询结果轮询间隔，单位秒"
    )

    # Scrape command - test URL content fetching
    scrape_parser = subparsers.add_parser(
        "scrape", help="Scrape content from a URL for testing"
    )
    scrape_parser.add_argument("--url", required=True, help="URL to scrape")
    scrape_parser.add_argument(
        "--output", "-o", help="Output file path (default: print to terminal)"
    )
    scrape_parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format: text (human-readable), json (structured), markdown (article)",
    )
    scrape_parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information including headers and metadata",
    )

    return parser


def add_request_args(
    parser: argparse.ArgumentParser, include_start_stage: bool = True
) -> None:
    parser.add_argument(
        "--content-type", choices=["article", "podcast"], default="article"
    )

    # Input source: audio or markdown (mutually exclusive in practice, but both optional)
    parser.add_argument(
        "--audio-file",
        help="音频文件路径（从音频开始，自动设置 --start-stage from-audio）",
    )
    parser.add_argument("--markdown", help="markdown 文件名或路径")

    parser.add_argument("--style", default="OpenAI")
    if include_start_stage:
        parser.add_argument(
            "--start-stage",
            choices=["from-audio", "from-source", "from-chunk", "from-editorial"],
            default="from-source",
            help="起始阶段：from-audio=从音频转录开始，from-source=从markdown开始",
        )

    # ASR options (only used when starting from audio)
    parser.add_argument("--asr-api-key", default="", help="火山引擎 API Key")
    parser.add_argument("--asr-app-key", default="", help="火山引擎 App Key")
    parser.add_argument("--asr-access-token", default="", help="火山引擎 Access Token")
    parser.add_argument("--asr-language", help="ASR 识别语言，例如 zh-CN、en-US")
    parser.add_argument(
        "--asr-audio-source-mode",
        choices=("auto", "inline", "upload", "public-url"),
        default="auto",
        help="音频来源模式",
    )
    parser.add_argument("--asr-public-base-url", help="公网音频 URL 前缀")
    parser.add_argument(
        "--asr-upload-url", default="https://0x0.st", help="临时上传服务地址"
    )

    parser.add_argument("--chunk-prompt")
    parser.add_argument("--stylify-prompt")
    parser.add_argument("--redsoul-prompt")
    parser.add_argument("--image-prompt")
    parser.add_argument("--prompt-label")
    parser.add_argument("--chunk-model")
    parser.add_argument("--editorial-model")
    parser.add_argument("--image-model")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--dry-run", action="store_true")


def request_from_namespace(args: argparse.Namespace) -> ExperimentRequest:
    # Load config from YAML (required)
    config = load_config()

    defaults = ModelOverrides()
    prompts = PromptOverrides(
        chunk_prompt=args.chunk_prompt,
        stylify_prompt=args.stylify_prompt,
        redsoul_prompt=args.redsoul_prompt,
        image_prompt=args.image_prompt,
        label=args.prompt_label,
    )

    # Use config with optional CLI overrides
    models = ModelOverrides(
        chunk_model=args.chunk_model or config.text_api.model,
        editorial_model=args.editorial_model or config.text_api.model,
        image_model=args.image_model or config.image_api.model,
    )
    text_api_key = args.api_key or config.text_api.api_key
    image_api_key = config.image_api.api_key
    text_base_url = config.text_api.base_url
    image_base_url = config.image_api.base_url
    image_api_format = config.image_api.format

    # Determine start_stage based on audio_file
    audio_file = getattr(args, "audio_file", None)
    markdown = getattr(args, "markdown", "")
    start_stage = args.start_stage

    if audio_file:
        # If audio file is provided, force start_stage to from-audio
        start_stage = "from-audio"
        # Use audio filename as markdown name (will be replaced after transcription)
        if not markdown:
            markdown = Path(audio_file).stem + ".md"
    elif not markdown:
        raise ValueError("必须提供 --markdown 或 --audio-file 参数")

    # Get ASR credentials from config or CLI args
    asr_api_key = getattr(args, "asr_api_key", None) or (
        config.asr_api.api_key if config and config.asr_api else None
    )
    asr_app_key = getattr(args, "asr_app_key", None) or (
        config.asr_api.app_key if config and config.asr_api else None
    )
    asr_access_token = getattr(args, "asr_access_token", None) or (
        config.asr_api.access_token if config and config.asr_api else None
    )
    asr_language = getattr(args, "asr_language", None) or (
        config.asr_api.language if config and config.asr_api else None
    )

    return ExperimentRequest(
        content_type=args.content_type,
        markdown=markdown,
        style=args.style,
        start_stage=start_stage,
        prompts=prompts,
        models=models,
        text_api_key=text_api_key,
        image_api_key=image_api_key,
        text_base_url=text_base_url,
        image_base_url=image_base_url,
        image_api_format=image_api_format,
        dry_run=args.dry_run,
        reuse_from_run=getattr(args, "reuse_from_run", None),
        render_workers=getattr(args, "render_workers", None),
        extract_highlights=getattr(args, "extract_highlights", None),
        highlight_model=getattr(args, "highlight_model", None),
        continue_on_error=getattr(args, "continue_on_error", False),
        max_pages=getattr(args, "max_pages", None),
        run_name=getattr(args, "name", None),
        # ASR options (prefer config, then CLI args, then env vars)
        audio_file=audio_file,
        asr_api_key=asr_api_key,
        asr_app_key=asr_app_key,
        asr_access_token=asr_access_token,
        asr_language=asr_language,
        asr_audio_source_mode=getattr(args, "asr_audio_source_mode", "auto"),
        asr_public_base_url=getattr(args, "asr_public_base_url", None),
        asr_upload_url=getattr(args, "asr_upload_url", "https://0x0.st"),
    )


def request_from_payload(payload: dict, api_key: str) -> ExperimentRequest:
    # Load config as fallback for missing payload values
    try:
        config = load_config()
    except (FileNotFoundError, ValueError):
        config = None

    defaults = ModelOverrides()
    prompts = PromptOverrides(
        chunk_prompt=payload.get("chunk_prompt"),
        stylify_prompt=payload.get("stylify_prompt"),
        redsoul_prompt=payload.get("redsoul_prompt"),
        image_prompt=payload.get("image_prompt"),
        label=payload.get("prompt_label"),
    )

    # Use config values as defaults if available
    if config:
        models = ModelOverrides(
            chunk_model=payload.get("chunk_model") or config.text_api.model,
            editorial_model=payload.get("editorial_model") or config.text_api.model,
            image_model=payload.get("image_model") or config.image_api.model,
        )
        text_api_key = (
            payload.get("text_api_key")
            or payload.get("api_key")
            or api_key
            or config.text_api.api_key
        )
        image_api_key = payload.get("image_api_key") or config.image_api.api_key
        text_base_url = payload.get("text_base_url") or config.text_api.base_url
        image_base_url = payload.get("image_base_url") or config.image_api.base_url
        image_api_format = payload.get("image_api_format") or config.image_api.format
    else:
        models = ModelOverrides(
            chunk_model=payload.get("chunk_model", defaults.chunk_model),
            editorial_model=payload.get("editorial_model", defaults.editorial_model),
            image_model=payload.get("image_model", defaults.image_model),
        )
        text_api_key = payload.get("text_api_key") or payload.get("api_key", api_key)
        image_api_key = payload.get("image_api_key", "")
        text_base_url = payload.get("text_base_url", "")
        image_base_url = payload.get("image_base_url", "")
        image_api_format = payload.get("image_api_format", "images/generations")

    # Handle extract_highlights: None means auto, True/False are explicit
    extract_highlights = payload.get("extract_highlights", None)
    if extract_highlights is not None and not isinstance(extract_highlights, bool):
        extract_highlights = None  # Ensure only None, True, or False

    return ExperimentRequest(
        content_type=payload.get("content_type", "article"),
        markdown=payload["markdown"],
        style=payload.get("style", "OpenAI"),
        start_stage=payload.get("start_stage", "from-source"),
        prompts=prompts,
        models=models,
        text_api_key=text_api_key,
        image_api_key=image_api_key,
        text_base_url=text_base_url,
        image_base_url=image_base_url,
        image_api_format=image_api_format,
        dry_run=payload.get("dry_run", False),
        reuse_from_run=payload.get("reuse_from_run"),
        render_workers=payload.get("render_workers"),
        extract_highlights=extract_highlights,
        highlight_model=payload.get("highlight_model"),
        continue_on_error=payload.get("continue_on_error", False),
        max_pages=payload.get("max_pages"),
    )


def interactive_request(api_key: str, dry_run: bool) -> ExperimentRequest:
    from .paths import sources_dir, repo_paths
    from .config import load_config

    # Load config from .narrio.yaml
    config = load_config()

    # Step 1: Select content type
    content_type = select_one(["article", "podcast"], "选择内容类型")

    # Step 2: Select starting point (audio, markdown, or resume from stage)
    start_options = [
        "from-audio (从音频文件开始)",
        "from-source (从 markdown 文件开始)",
        "from-chunk (从已有 chunk 恢复)",
        "from-editorial (从已有 editorial 恢复)",
    ]
    if content_type == "article":
        # Article doesn't support audio
        start_options = start_options[1:]

    start_choice = select_one(start_options, "选择起始阶段")
    start_stage = start_choice.split(" ")[
        0
    ]  # Extract "from-audio", "from-source", etc.

    # Initialize variables
    audio_file = None
    markdown = None
    reuse_from_run = None

    # Step 3: Select input file based on start_stage
    if start_stage == "from-audio":
        # Select audio file
        audio_dir = repo_paths().content_root / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        try:
            audio_file = select_audio_file_with_mtime(audio_dir, "选择音频文件")
            # Generate markdown name from audio filename
            markdown = Path(audio_file).stem + ".md"
        except FileNotFoundError as e:
            print(f"错误: {e}")
            print(f"请将音频文件放到 {audio_dir} 目录")
            raise

    elif start_stage == "from-source":
        # Select markdown file with mtime
        source_dir = sources_dir(content_type)
        source_dir.mkdir(parents=True, exist_ok=True)
        try:
            markdown = select_file_with_mtime(source_dir, "*.md", "选择输入文件")
        except FileNotFoundError as e:
            print(f"错误: {e}")
            print(f"请将 markdown 文件放到 {source_dir} 目录")
            raise

    else:
        # Resume from existing run - use interactive selector
        try:
            reuse_from_run = select_run_directory(content_type, "选择历史运行目录")
            # Validate path exists
            reuse_path = Path(reuse_from_run).expanduser().resolve()
            if not reuse_path.exists():
                print(f"\n错误: 目录不存在: {reuse_path}")
                print(f"请检查路径是否正确\n")
                raise FileNotFoundError(f"目录不存在: {reuse_path}")
        except FileNotFoundError as e:
            print(f"\n错误: {e}")
            print(f"提示: 如果要从头开始，请选择 'from-source' 或 'from-audio'\n")
            raise

        # Still need a markdown name (will be ignored)
        markdown = "resume.md"

    # Step 4: Select style (with modification time)
    from .paths import styles_root

    styles_dir = styles_root()
    try:
        style = select_directory_with_mtime(styles_dir, "选择 style")
    except FileNotFoundError:
        print("警告: 未找到 style 定义，使用默认 OpenAI")
        style = "OpenAI"

    # Step 5: Advanced options
    chunk_prompt = ask_optional_path("chunk prompt 覆盖路径")
    stylify_prompt = ask_optional_path("stylify prompt 覆盖路径")
    redsoul_prompt = ask_optional_path("redsoul prompt 覆盖路径")
    image_prompt = ask_optional_path("image prompt 覆盖路径")
    prompt_label = ask_text("实验标签", "interactive")
    render_workers_str = ask_optional_text("并行渲染 worker 数 (上限 5)")
    render_workers = int(render_workers_str) if render_workers_str else None

    # Step 6: Run name
    run_name = ask_run_name()

    # Step 7: Highlight options
    extract_choice = select_one(
        ["auto", "yes", "no"],
        "是否提取高亮语句（auto=根据类型自动决定，yes=强制，no=跳过）",
    )
    if extract_choice == "auto":
        extract_highlights = None
    elif extract_choice == "yes":
        extract_highlights = True
    else:
        extract_highlights = False

    # Step 8: Max pages
    max_pages_str = ask_optional_text("图片生成数量上限")
    max_pages = int(max_pages_str) if max_pages_str else None

    # Build request using config from .narrio.yaml
    return ExperimentRequest(
        content_type=content_type,
        markdown=markdown,
        style=style,
        start_stage=start_stage,
        prompts=PromptOverrides(
            chunk_prompt=chunk_prompt,
            stylify_prompt=stylify_prompt,
            redsoul_prompt=redsoul_prompt,
            image_prompt=image_prompt,
            label=prompt_label,
        ),
        models=ModelOverrides(
            chunk_model=config.text_api.model,
            editorial_model=config.text_api.model,
            image_model=config.image_api.model,
        ),
        text_api_key=api_key or config.text_api.api_key,
        image_api_key=config.image_api.api_key,
        text_base_url=config.text_api.base_url,
        image_base_url=config.image_api.base_url,
        image_api_format=config.image_api.format,
        dry_run=dry_run,
        reuse_from_run=reuse_from_run,
        render_workers=render_workers,
        extract_highlights=extract_highlights,
        max_pages=max_pages,
        run_name=run_name,
        audio_file=audio_file,
        # ASR options from config (if available)
        asr_api_key=config.asr_api.api_key if config.asr_api else None,
        asr_app_key=config.asr_api.app_key if config.asr_api else None,
        asr_access_token=config.asr_api.access_token if config.asr_api else None,
        asr_language=config.asr_api.language if config.asr_api else None,
    )


def ask_optional_text(prompt: str) -> str | None:
    raw = input(f"{prompt}（留空表示默认）: ").strip()
    return raw or None


def ask_optional_path(prompt: str) -> str | None:
    raw = input(f"{prompt}（留空表示默认）: ").strip()
    return raw or None


def ask_run_name() -> str | None:
    """Ask user for a custom run name interactively.

    The default name is auto-generated with timestamp (MMDD-HHMMSS format).
    User can modify it or leave empty to use the default.

    Returns:
        User-provided name or None to use default auto-generated name.
    """
    default_name = f"run-{datetime.now().strftime('%m%d-%H%M%S')}"
    raw = input(f"运行名称（留空使用默认：{default_name}）: ").strip()
    # If user leaves it empty, return None to use default
    # If user provides input, return it (they can modify the default)
    return raw or None


def print_run_result(result: dict) -> None:
    print(f"run_id: {result['run_id']}")
    print(f"status: {result['status']}")
    print(f"combo_id: {result['combo_id']}")
    print(f"run_dir: {result['run_dir']}")


def configure_logging() -> None:
    raw_level = os.getenv("NARRIO_LOG_LEVEL", "INFO").upper().strip()
    level = getattr(logging, raw_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        if args.batch_file:
            payloads = json.loads(
                Path(args.batch_file).expanduser().resolve().read_text(encoding="utf-8")
            )
            requests = [request_from_payload(item, args.api_key) for item in payloads]
            results = execute_batch(requests, max_workers=args.max_workers)
            for result in results:
                print(json.dumps(result, ensure_ascii=False))
            return 0
        result = execute_experiment(request_from_namespace(args))
        print_run_result(result)
        return 0

    if args.command == "resume":
        result = execute_experiment(request_from_namespace(args))
        print_run_result(result)
        return 0

    if args.command == "inspect":
        print(json.dumps(inspect_run(args.run_path), ensure_ascii=False, indent=2))
        return 0

    if args.command == "export":
        result = export_run(args.run_path, export_root=args.export_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "compare":
        print(
            json.dumps(
                compare_combo(args.content_type, args.combo_id),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "lab":
        result = execute_experiment(interactive_request(args.api_key, args.dry_run))
        print_run_result(result)
        return 0

    # Highlight extraction command
    if args.command == "extract-highlights":
        return handle_extract_highlights(args)

    # Tune command
    if args.command == "tune":
        return handle_tune(args)

    # Transcribe command
    if args.command == "transcribe":
        return handle_transcribe(args)

    # Scrape command
    if args.command == "scrape":
        return handle_scrape(args)

    raise ValueError(f"未知命令：{args.command}")


def handle_extract_highlights(args) -> int:
    """Handle extract-highlights command."""
    from .highlight_service import main as extract_main

    try:
        # Build argv for the highlight service
        argv = [
            "--content-type",
            args.content_type,
            "--model",
            args.model,
            "--api-key",
            args.api_key,
            "--base-url",
            args.base_url,
            "--timeout",
            str(args.timeout),
            "--min-word-count",
            str(args.min_word_count),
            "--max-highlights",
            str(args.max_highlights),
        ]

        if args.input_path:
            argv.extend(["--input-path", args.input_path])
        if args.markdown:
            argv.extend(["--markdown", args.markdown])
        if args.prompt_file:
            argv.extend(["--prompt-file", args.prompt_file])
        if args.output_root:
            argv.extend(["--output-root", args.output_root])

        return extract_main(argv)
    except Exception as exc:
        if args.continue_on_error:
            print(f"提取亮点失败 (已忽略): {exc}")
            return 0
        raise


def handle_tune(args) -> int:
    """Handle tune command."""
    from .tune import main as tune_main

    # Build argv for the tune module
    argv = []

    if args.input:
        argv.extend(["--input", args.input])
    if args.styles:
        argv.extend(["--styles", args.styles])
    if args.no_auto_display:
        argv.append("--no-auto-display")
    if args.attach:
        argv.extend(["--attach", args.attach])
    if args.list:
        argv.append("--list")

    return tune_main(argv)


def handle_scrape(args) -> int:
    """Handle scrape command - fetch and parse content from a URL."""
    import asyncio
    import httpx
    import json

    from .ssr_service import get_scraper

    url = args.url
    output_path = args.output
    output_format = args.format
    debug = args.debug

    # Temporarily reduce logging for cleaner output
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("narrio.ssr_service").setLevel(logging.WARNING)

    print(f"Scraping content from: {url}")

    try:
        # Run async scraping
        scraper = get_scraper()
        result = asyncio.run(scraper.scrape_url(url))

        # Format output
        if output_format == "json":
            output_content = json.dumps(result, ensure_ascii=False, indent=2)
        elif output_format == "markdown":
            output_content = format_markdown_output(result)
        else:  # text
            output_content = format_text_output(result, debug=debug)

        # Output to file or terminal
        if output_path:
            from pathlib import Path

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(output_content, encoding="utf-8")
            print(f"Content saved to: {output_path}")
        else:
            print("\n" + "=" * 60 + "\n")
            print(output_content)

        return 0

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.reason_phrase}")
        if debug:
            print(f"Response headers: {dict(e.response.headers)}")
            print(f"Response body: {e.response.text[:500]}...")
        return 1

    except httpx.TimeoutException as e:
        print(f"Timeout: Request timed out after 30 seconds")
        if debug:
            print(f"Details: {e}")
        return 1

    except httpx.RequestError as e:
        print(f"Request Error: {str(e)}")
        if debug:
            print(f"Details: {e}")
        return 1

    except FileNotFoundError as e:
        print(f"Dependency Error: beautifulsoup4 is not installed")
        print("Install with: pip install beautifulsoup4")
        return 1

    except Exception as e:
        print(f"Error: {str(e)}")
        if debug:
            import traceback

            traceback.print_exc()
        return 1


def format_text_output(data: dict, debug: bool = False) -> str:
    """Format scraped data as human-readable text."""
    lines = [
        f"Title: {data['title']}",
        f"URL: {data['url']}",
        f"Cover Image: {data['cover']}",
        "",
        "--- Content Preview ---",
        "",
        data["content"][:2000] + ("..." if len(data["content"]) > 2000 else ""),
    ]

    if debug:
        lines.extend(
            [
                "",
                "--- Debug Info ---",
                f"Content Length: {len(data['content'])} characters",
                f"Title Length: {len(data['title'])} characters",
            ]
        )

    return "\n".join(lines)


def format_markdown_output(data: dict) -> str:
    """Format scraped data as Markdown article."""
    return f"""# {data['title']}

![Cover Image]({data['cover']})

**Source URL:** {data['url']}

---

{data['content']}
"""


def handle_transcribe(args) -> int:
    """Handle transcribe command."""
    from .asr_service import main as asr_main

    # Build argv for the ASR service
    argv = []

    if args.audio_input:
        argv.extend(["--audio-input", args.audio_input])
    if args.output_dir:
        argv.extend(["--output-dir", args.output_dir])
    if args.language:
        argv.extend(["--language", args.language])
    if args.resource_id:
        argv.extend(["--resource-id", args.resource_id])
    if args.uid:
        argv.extend(["--uid", args.uid])
    if args.public_base_url:
        argv.extend(["--public-base-url", args.public_base_url])
    if args.upload_url:
        argv.extend(["--upload-url", args.upload_url])
    if args.audio_source_mode:
        argv.extend(["--audio-source-mode", args.audio_source_mode])
    if args.api_key:
        argv.extend(["--api-key", args.api_key])
    if args.app_key:
        argv.extend(["--app-key", args.app_key])
    if args.access_token:
        argv.extend(["--access-token", args.access_token])
    argv.extend(["--timeout", str(args.timeout)])
    argv.extend(["--query-interval", str(args.query_interval)])

    return asr_main(argv)
