from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .paths import repo_paths


WORKBENCH_ROOT = repo_paths().workbench_root
STAGES = ("transcribe", "highlight", "chunkify", "stylify", "render")
START_STAGE_TO_STEP = {
    "from-audio": "transcribe",
    "from-source": "chunkify",
    "from-chunk": "stylify",
    "from-editorial": "render",
}


@dataclass(frozen=True)
class RunPaths:
    combo_dir: Path
    run_dir: Path
    meta_dir: Path
    source_dir: Path
    transcribe_dir: Path
    highlight_dir: Path
    chunk_dir: Path
    editorial_dir: Path
    render_dir: Path
    snapshots_dir: Path
    logs_dir: Path
    latest_link: Path
    manifest_path: Path
    events_path: Path


def sanitize(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("-_")
    return cleaned or "untitled"


def short_hash(parts: list[str]) -> str:
    digest = hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()
    return digest[:8]


def build_combo_id(content_type: str, source_name: str, style_name: str, prompt_fingerprint: str) -> str:
    base = sanitize(Path(source_name).stem)[:32]
    style = sanitize(style_name)[:24]
    return f"{sanitize(content_type)}-{base}-{style}-{prompt_fingerprint}"


def build_run_id(run_name: str | None = None, include_timestamp: bool = True) -> str:
    """Build run ID with optional user-provided name and timestamp.

    Args:
        run_name: Optional user-provided name. If None, uses 'run' as default.
        include_timestamp: Whether to append timestamp to the name.

    Returns:
        Run ID in format: {name}-{MMDD-HHMMSS} (no year in timestamp)
        If include_timestamp is False, returns just the sanitized name.
    """
    timestamp = datetime.now().strftime('%m%d-%H%M%S')
    if run_name:
        sanitized_name = sanitize(run_name)
        if include_timestamp:
            # If the run_name already ends with a timestamp pattern, don't add it again
            import re
            timestamp_pattern = r'-\d{4}-\d{6}$'  # -MMDD-HHMMSS
            if re.search(timestamp_pattern, sanitized_name):
                return sanitized_name
            return f"{sanitized_name}-{timestamp}"
        return sanitized_name
    if include_timestamp:
        return f"run-{timestamp}"
    return "run"


def prompt_fingerprint(paths: list[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        resolved = path.expanduser().resolve()
        parts.append(str(resolved))
        if resolved.exists():
            parts.append(hashlib.sha1(resolved.read_bytes()).hexdigest())
    return short_hash(parts)


def combo_dir(content_type: str, combo_id: str) -> Path:
    return WORKBENCH_ROOT / sanitize(content_type) / combo_id


def make_run_paths(content_type: str, combo_id: str, run_id: str) -> RunPaths:
    root = combo_dir(content_type=content_type, combo_id=combo_id)
    run_dir = root / "runs" / run_id
    paths = RunPaths(
        combo_dir=root,
        run_dir=run_dir,
        meta_dir=root / "meta",
        source_dir=run_dir / "source",
        transcribe_dir=run_dir / "transcribe",
        highlight_dir=run_dir / "highlight",
        chunk_dir=run_dir / "chunk",
        editorial_dir=run_dir / "editorial",
        render_dir=run_dir / "render",
        snapshots_dir=run_dir / "snapshots",
        logs_dir=run_dir / "logs",
        latest_link=root / "latest",
        manifest_path=run_dir / "manifest.json",
        events_path=run_dir / "logs" / "events.jsonl",
    )
    for directory in (
        WORKBENCH_ROOT / sanitize(content_type),
        paths.combo_dir,
        paths.meta_dir,
        paths.run_dir,
        paths.source_dir,
        paths.transcribe_dir,
        paths.highlight_dir,
        paths.chunk_dir,
        paths.editorial_dir,
        paths.render_dir,
        paths.snapshots_dir,
        paths.logs_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    _refresh_latest_link(paths.latest_link, paths.run_dir)
    return paths


def _refresh_latest_link(link_path: Path, target_path: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    try:
        link_path.symlink_to(target_path.relative_to(link_path.parent))
    except OSError:
        link_path.write_text(str(target_path), encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def append_event(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\n")
