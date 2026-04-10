from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    cursor = (start or Path(__file__)).resolve()
    if cursor.is_file():
        cursor = cursor.parent
    for parent in [cursor, *cursor.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return cursor


REPO_ROOT = find_repo_root()


@dataclass(frozen=True)
class RepoPaths:
    repo_root: Path
    assets_root: Path
    content_root: Path
    exports_root: Path
    workbench_root: Path


def repo_paths(repo_root: Path | None = None) -> RepoPaths:
    root = (repo_root or REPO_ROOT).resolve()
    return RepoPaths(
        repo_root=root,
        assets_root=root / "assets",
        content_root=root / "content",
        exports_root=root / "exports",
        workbench_root=root / ".narrio" / "workbench",
    )


def sources_dir(content_type: str, root: Path | None = None) -> Path:
    paths = repo_paths(root)
    if content_type == "article":
        return paths.content_root / "sources" / "article"
    if content_type == "podcast":
        return paths.content_root / "transcripts"
    raise ValueError(f"不支持的内容类型：{content_type}")


def source_candidates(content_type: str, root: Path | None = None) -> list[Path]:
    paths = repo_paths(root)
    if content_type == "article":
        return [paths.content_root / "sources" / "article"]
    if content_type == "podcast":
        return [paths.content_root / "transcripts"]
    raise ValueError(f"不支持的内容类型：{content_type}")


def prompts_root(root: Path | None = None) -> Path:
    paths = repo_paths(root)
    return paths.assets_root / "prompts"


def prompt_file(filename: str, root: Path | None = None) -> Path:
    paths = repo_paths(root)
    return paths.assets_root / "prompts" / filename


def styles_root(root: Path | None = None) -> Path:
    paths = repo_paths(root)
    return paths.assets_root / "styles"


def style_dir(style_label: str, root: Path | None = None) -> Path:
    return styles_root(root) / style_label


def reference_image_candidates(style_label: str, root: Path | None = None) -> list[Path]:
    base = style_dir(style_label, root)
    candidates: list[Path] = []
    for suffix in (".png", ".webp", ".jpg", ".jpeg"):
        candidates.append(base / f"ref{suffix}")
    candidates.append(base / "ref.png")
    return candidates
