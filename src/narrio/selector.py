from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def has_fzf() -> bool:
    return shutil.which("fzf") is not None


def select_one(options: list[str], prompt: str) -> str:
    if not options:
        raise ValueError("没有可选项")
    if has_fzf() and sys.stdin.isatty() and sys.stdout.isatty():
        return _select_with_fzf(options=options, prompt=prompt)
    return _select_with_prompt(options=options, prompt=prompt)


def _select_with_fzf(options: list[str], prompt: str) -> str:
    result = subprocess.run(
        ["fzf", "--prompt", f"{prompt}> "],
        input="\n".join(options),
        text=True,
        capture_output=True,
        check=False,
    )
    selected = result.stdout.strip()
    if result.returncode != 0 or not selected:
        raise RuntimeError("交互选择已取消")
    return selected


def _select_with_prompt(options: list[str], prompt: str) -> str:
    print(prompt)
    for index, option in enumerate(options, start=1):
        print(f"{index}. {option}")
    raw = input("请输入编号: ").strip()
    selected = int(raw)
    if selected < 1 or selected > len(options):
        raise ValueError("编号超出范围")
    return options[selected - 1]


def ask_text(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    raise ValueError("输入不能为空")


def yes_no(prompt: str, default: bool = False) -> bool:
    """Ask a yes/no question and return boolean result."""
    suffix = " [Y/n]" if default else " [y/N]"
    value = input(f"{prompt}{suffix}: ").strip().lower()
    if not value:
        return default
    return value in ("y", "yes", "是", "对")


def select_file_with_mtime(directory: Path, pattern: str, prompt: str) -> str:
    """
    Select a file from directory with modification time display.
    Files are sorted by modification time (newest first).

    Args:
        directory: Directory to search files in
        pattern: Glob pattern (e.g., "*.md")
        prompt: Prompt message

    Returns:
        Selected filename (not full path)
    """
    if not directory.exists():
        raise FileNotFoundError(f"目录不存在：{directory}")

    # Get all matching files with their mtime
    files_with_mtime: list[tuple[Path, float, str]] = []
    for path in directory.glob(pattern):
        if path.is_file():
            mtime = path.stat().st_mtime
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            files_with_mtime.append((path, mtime, mtime_str))

    if not files_with_mtime:
        raise FileNotFoundError(f"在 {directory} 中未找到匹配 {pattern} 的文件")

    # Sort by mtime (newest first)
    files_with_mtime.sort(key=lambda x: x[1], reverse=True)

    # Build display options
    display_options = []
    filename_map = {}  # Map display string to filename

    for path, mtime, mtime_str in files_with_mtime:
        filename = path.name
        # Format: "filename.md    [2024-04-08 18:30:45]"
        display = f"{filename:<40} [{mtime_str}]"
        display_options.append(display)
        filename_map[display] = filename

    # Use existing select_one function
    if has_fzf() and sys.stdin.isatty() and sys.stdout.isatty():
        selected_display = _select_with_fzf(options=display_options, prompt=prompt)
    else:
        selected_display = _select_with_prompt(options=display_options, prompt=prompt)

    # Return just the filename
    return filename_map[selected_display]


def select_audio_file_with_mtime(directory: Path, prompt: str) -> str:
    """
    Select an audio file from directory with modification time display.
    Supports: mp3, wav, m4a, ogg, flac
    """
    if not directory.exists():
        raise FileNotFoundError(f"目录不存在：{directory}")

    # Get all audio files with their mtime
    audio_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
    files_with_mtime: list[tuple[Path, float, str, int]] = []

    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() in audio_extensions:
            mtime = path.stat().st_mtime
            size = path.stat().st_size
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            files_with_mtime.append((path, mtime, mtime_str, size))

    if not files_with_mtime:
        raise FileNotFoundError(f"在 {directory} 中未找到音频文件")

    # Sort by mtime (newest first)
    files_with_mtime.sort(key=lambda x: x[1], reverse=True)

    # Build display options
    display_options = []
    filename_map = {}  # Map display string to filename

    for path, mtime, mtime_str, size in files_with_mtime:
        filename = path.name
        size_mb = size / (1024 * 1024)
        # Format: "filename.mp3    [2024-04-08 18:30:45] (45.2 MB)"
        display = f"{filename:<40} [{mtime_str}] ({size_mb:.1f} MB)"
        display_options.append(display)
        filename_map[display] = filename

    # Use existing select_one function
    if has_fzf() and sys.stdin.isatty() and sys.stdout.isatty():
        selected_display = _select_with_fzf(options=display_options, prompt=prompt)
    else:
        selected_display = _select_with_prompt(options=display_options, prompt=prompt)

    # Return just the filename
    return filename_map[selected_display]

def select_directory_with_mtime(parent_directory: Path, prompt: str) -> str:
    """
    Select a directory from parent_directory with modification time display.
    Directories are sorted by modification time (newest first).

    Args:
        parent_directory: Parent directory to search subdirectories in
        prompt: Prompt message

    Returns:
        Selected directory name (not full path)
    """
    if not parent_directory.exists():
        raise FileNotFoundError(f"目录不存在：{parent_directory}")

    # Get all subdirectories with their mtime
    dirs_with_mtime: list[tuple[Path, float, str]] = []
    for path in parent_directory.iterdir():
        if path.is_dir() and not path.name.startswith('.'):
            mtime = path.stat().st_mtime
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            dirs_with_mtime.append((path, mtime, mtime_str))

    if not dirs_with_mtime:
        raise FileNotFoundError(f"在 {parent_directory} 中未找到子目录")

    # Sort by mtime (newest first)
    dirs_with_mtime.sort(key=lambda x: x[1], reverse=True)

    # Build display options
    display_options = []
    dirname_map = {}  # Map display string to directory name

    for path, mtime, mtime_str in dirs_with_mtime:
        dirname = path.name
        # Format: "dirname    [2024-04-08 18:30:45]"
        display = f"{dirname:<40} [{mtime_str}]"
        display_options.append(display)
        dirname_map[display] = dirname

    # Use existing select_one function
    if has_fzf() and sys.stdin.isatty() and sys.stdout.isatty():
        selected_display = _select_with_fzf(options=display_options, prompt=prompt)
    else:
        selected_display = _select_with_prompt(options=display_options, prompt=prompt)

    # Return just the directory name
    return dirname_map[selected_display]


def select_run_directory(content_type: str, prompt: str) -> str:
    """
    Select a run directory from .narrio/workbench/{content_type} with modification time display.
    Scans all combo directories and their runs, sorted by modification time (newest first).

    Args:
        content_type: Content type (article or podcast)
        prompt: Prompt message

    Returns:
        Selected run directory path relative to project root
    """
    from pathlib import Path

    workbench_dir = Path(".narrio/workbench") / content_type
    if not workbench_dir.exists():
        raise FileNotFoundError(f"工作目录不存在：{workbench_dir}")

    # Scan all combo directories for runs
    run_dirs_with_mtime: list[tuple[str, float, str]] = []

    for combo_dir in workbench_dir.iterdir():
        if not combo_dir.is_dir() or combo_dir.name.startswith('.'):
            continue

        # Check for runs directory
        runs_dir = combo_dir / "runs"
        if not runs_dir.exists() or not runs_dir.is_dir():
            continue

        # Scan all run directories
        for run_dir in runs_dir.iterdir():
            if run_dir.is_dir() and run_dir.name.startswith("run-"):
                mtime = run_dir.stat().st_mtime
                mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                # Store relative path from project root
                rel_path = str(run_dir)
                run_dirs_with_mtime.append((rel_path, mtime, mtime_str))

        # Check for 'latest' symlink
        latest_link = combo_dir / "latest"
        if latest_link.exists():
            mtime = latest_link.stat().st_mtime
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            rel_path = str(latest_link)
            run_dirs_with_mtime.append((rel_path, mtime, mtime_str))

    if not run_dirs_with_mtime:
        raise FileNotFoundError(f"在 {workbench_dir} 中未找到历史运行目录")

    # Sort by mtime (newest first)
    run_dirs_with_mtime.sort(key=lambda x: x[1], reverse=True)

    # Build display options
    display_options = []
    path_map = {}  # Map display string to full path

    for rel_path, mtime, mtime_str in run_dirs_with_mtime:
        # Format: "path/to/run    [2024-04-08 18:30:45]"
        display = f"{rel_path:<80} [{mtime_str}]"
        display_options.append(display)
        path_map[display] = rel_path

    # Use existing select_one function
    if has_fzf() and sys.stdin.isatty() and sys.stdout.isatty():
        selected_display = _select_with_fzf(options=display_options, prompt=prompt)
    else:
        selected_display = _select_with_prompt(options=display_options, prompt=prompt)

    # Return the full relative path
    return path_map[selected_display]
