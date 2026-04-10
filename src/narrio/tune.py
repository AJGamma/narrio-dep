"""Multi-variant parallel tuning pipeline using tmux."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def is_inside_tmux() -> bool:
    """Check if currently running inside a tmux session."""
    return os.getenv("TMUX") is not None


def check_tmux_available() -> bool:
    """Check if tmux is installed and available."""
    try:
        subprocess.run(["tmux", "-V"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_tmux_command(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """
    Run a tmux command, handling nested tmux sessions properly.

    When running inside an existing tmux session, we need to unset the TMUX
    environment variable to allow creating a new independent session.
    """
    env = kwargs.pop("env", None)
    if env is None:
        env = os.environ.copy()

    # Unset TMUX variable to allow nested session creation
    if "TMUX" in env:
        env["TMUX"] = ""

    return subprocess.run(cmd, env=env, **kwargs)


def build_tune_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the tune command."""
    parser = argparse.ArgumentParser(
        prog="narrio tune",
        description="Run multiple style variants in parallel using tmux",
    )

    parser.add_argument(
        "--input",
        help="Input file path (if not provided, will prompt interactively)",
    )

    parser.add_argument(
        "--styles",
        help="Comma-separated list of styles (e.g., 'OpenAI,Anthropic,Google')",
    )

    parser.add_argument(
        "--no-auto-display",
        action="store_true",
        help="Skip automatic image display after completion",
    )

    parser.add_argument(
        "--attach",
        metavar="SESSION_NAME",
        help="Attach to an existing tmux session",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all active narrio-tune sessions",
    )

    return parser


def list_active_sessions() -> list[str]:
    """List all active narrio-tune tmux sessions."""
    try:
        result = run_tmux_command(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            check=True,
        )
        sessions = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return [s for s in sessions if s.startswith("narrio-tune-")]
    except subprocess.CalledProcessError:
        return []


def cleanup_session(session_name: str) -> int:
    """Kill a tmux session."""
    try:
        run_tmux_command(["tmux", "kill-session", "-t", session_name], check=True)
        print(f"Session '{session_name}' has been cleaned up")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to clean up session '{session_name}': {e}")
        return 1


def attach_to_session(session_name: str) -> int:
    """Attach to an existing tmux session."""
    try:
        run_tmux_command(["tmux", "attach-session", "-t", session_name], check=True)

        # After detaching, offer to clean up the session
        print("\nSession detached.")
        cleanup_choice = input("Clean up this session? (y/n): ").strip().lower()
        if cleanup_choice == "y":
            return cleanup_session(session_name)
        else:
            print(f"Session '{session_name}' is still active.")
            print(f"To reattach: narrio tune --attach {session_name}")
            print(f"To list sessions: narrio tune --list")

        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to attach to session '{session_name}': {e}")
        return 1


def handle_list_sessions() -> int:
    """Handle --list flag."""
    sessions = list_active_sessions()
    if not sessions:
        print("No active narrio-tune sessions found")
        return 0

    print(f"Active narrio-tune sessions ({len(sessions)}):")
    for session in sessions:
        # Extract timestamp from session name
        try:
            timestamp = session.replace("narrio-tune-", "")
            print(f"  - {session} (created: {timestamp})")
        except Exception:
            print(f"  - {session}")

    return 0


def generate_session_name() -> str:
    """Generate a unique session name with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"narrio-tune-{timestamp}"


def calculate_pane_layout(num_styles: int) -> list[str]:
    """
    Calculate optimal pane split commands for given number of styles.
    Returns a list of tmux split-window commands.
    """
    if num_styles == 1:
        return []
    elif num_styles == 2:
        # Vertical split: | |
        return ["split-window -h"]
    elif num_styles == 3:
        # One on left, two stacked on right
        return [
            "split-window -h",  # Split horizontally first
            "split-window -v",  # Split right pane vertically
        ]
    elif num_styles == 4:
        # 2x2 grid
        return [
            "split-window -h",  # Split horizontally
            "split-window -v",  # Split top-right vertically
            "select-pane -t 0",  # Select top-left
            "split-window -v",  # Split top-left vertically
        ]
    else:
        # For 5+ styles, create a flexible grid layout
        # Start with horizontal splits, then vertical splits for each column
        commands = []
        cols = min(3, (num_styles + 1) // 2)  # Max 3 columns
        rows = (num_styles + cols - 1) // cols  # Calculate needed rows

        # Create columns (horizontal splits)
        for i in range(cols - 1):
            commands.append("split-window -h")

        # Create rows in each column (vertical splits)
        for col in range(cols):
            pane_count_in_col = min(rows, num_styles - col * rows)
            if pane_count_in_col > 1:
                commands.append(f"select-pane -t {col}")
                for _ in range(pane_count_in_col - 1):
                    commands.append("split-window -v")

        return commands


def execute_variant_in_pane(
    session_name: str,
    pane_index: int,
    input_file: str,
    style: str,
    content_type: str = "article",
) -> int:
    """Execute a single variant in a specific tmux pane."""
    try:
        # Build the narrio run command
        # Format: narrio run --content-type article --markdown <file> --style <style>
        # Quote the filename to handle spaces
        command = f'narrio run --content-type {content_type} --markdown "{input_file}" --style {style}'

        # Send command to the specific pane
        run_tmux_command(
            [
                "tmux",
                "send-keys",
                "-t",
                f"{session_name}.{pane_index}",
                command,
                "Enter",
            ],
            check=True,
        )

        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to execute variant in pane {pane_index}: {e}")
        return 1


def setup_summary_window(session_name: str, styles: list[str], input_file: str) -> int:
    """Set up the summary window with initial status display and monitoring script."""
    try:
        # Create a monitoring script that watches pane activity
        monitor_script = f'''
#!/bin/bash
# Real-time status monitor for narrio tune session

clear
echo "=== Narrio Multi-Variant Tuning Pipeline ==="
echo "Session: {session_name}"
echo "Input: {input_file}"
echo "Variants: {len(styles)}"
echo ""
echo "Variants:"
'''

        for idx, style in enumerate(styles):
            monitor_script += f'echo "  [{idx}] {style}"\n'

        monitor_script += '''
echo ""
echo "Monitoring status... (press Ctrl+C to stop)"
echo ""

# Monitor loop
while true; do
    echo "---"
    date "+%H:%M:%S"

    # Check each pane's activity
'''

        for idx, style in enumerate(styles):
            monitor_script += f'''
    # Check pane {idx} ({style})
    if tmux list-panes -t {session_name}:0 -F '#{{pane_index}}' 2>/dev/null | grep -q "^{idx}$"; then
        # Get last line from pane
        last_line=$(tmux capture-pane -t {session_name}.{idx} -p | tail -1)
        echo "  [{idx}] {style}: $last_line"
    fi
'''

        monitor_script += '''

    sleep 5
done
'''

        # Send the monitoring script to the summary window
        # For simplicity, just show static info for now
        summary_lines = [
            "=== Narrio Multi-Variant Tuning Pipeline ===",
            f"Session: {session_name}",
            f"Input: {input_file}",
            f"Variants: {len(styles)}",
            "",
            "Variants running:",
        ]

        for idx, style in enumerate(styles):
            summary_lines.append(f"  [{idx}] {style}: running in pane {idx}")

        summary_lines.extend([
            "",
            "Navigation:",
            "  - Ctrl+b, 0: Switch to variants window",
            "  - Ctrl+b, 1: Switch back to this summary",
            "  - Ctrl+b, d: Detach from session",
            "  - Ctrl+b, arrow keys: Navigate between panes",
            "",
            "Commands:",
            f"  - Reattach: narrio tune --attach {session_name}",
            "  - List sessions: narrio tune --list",
            "",
            "Note: Check individual panes for detailed output.",
        ])

        # Write summary to the summary window
        for line in summary_lines:
            escaped_line = line.replace("'", "'\\''")
            run_tmux_command(
                [
                    "tmux",
                    "send-keys",
                    "-t",
                    session_name,
                    f"echo '{escaped_line}'",
                    "Enter",
                ],
                check=True,
            )

        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to set up summary window: {e}")
        return 1


def create_tmux_session(session_name: str, styles: list[str], input_file: str, content_type: str = "article") -> int:
    """Create a tmux session with multi-pane layout for parallel variant execution."""
    try:
        # Create new detached session with first window
        run_tmux_command(
            ["tmux", "new-session", "-d", "-s", session_name, "-n", "variants"],
            check=True,
        )

        # Give tmux a moment to initialize (helps prevent timing issues)
        import time
        time.sleep(0.1)

        # Create pane layout based on number of styles
        layout_commands = calculate_pane_layout(len(styles))
        for cmd in layout_commands:
            full_cmd = ["tmux"] + cmd.split() + ["-t", session_name]
            run_tmux_command(full_cmd, check=True)

        # Balance the panes for equal sizing
        if len(styles) > 1:
            run_tmux_command(
                ["tmux", "select-layout", "-t", session_name, "tiled"],
                check=True,
            )

        # Execute each variant in its corresponding pane
        for pane_idx, style in enumerate(styles):
            execute_variant_in_pane(session_name, pane_idx, input_file, style, content_type)

        # Create summary window
        run_tmux_command(
            ["tmux", "new-window", "-t", session_name, "-n", "summary"],
            check=True,
        )

        # Set up summary window with initial status
        setup_summary_window(session_name, styles, input_file)

        # Select summary window to show user the status
        run_tmux_command(
            ["tmux", "select-window", "-t", f"{session_name}:1"],
            check=True,
        )

        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to create tmux session: {e}")
        return 1


def check_fzf_available() -> bool:
    """Check if fzf is installed and available."""
    try:
        subprocess.run(["fzf", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def find_markdown_files(base_path: str = ".") -> list[str]:
    """Find all markdown files in the given directory."""
    import glob as file_glob

    patterns = [
        f"{base_path}/**/*.md",
        f"{base_path}/**/*.markdown",
    ]

    files = []
    for pattern in patterns:
        files.extend(file_glob.glob(pattern, recursive=True))

    return sorted(set(files))


def select_file_with_fzf(files: list[str]) -> str | None:
    """Use fzf to select a file from the list."""
    try:
        result = subprocess.run(
            ["fzf", "--prompt", "Select input file: ", "--height", "40%"],
            input="\n".join(files),
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # User cancelled or fzf error
        return None


def select_file_interactive() -> str | None:
    """Interactively select an input file."""
    # Find markdown files in current directory and subdirectories
    files = find_markdown_files()

    if not files:
        print("No markdown files found in current directory")
        file_path = input("Enter input file path: ").strip()
        return file_path if file_path else None

    # Try fzf first, fall back to plain prompt
    if check_fzf_available():
        print(f"Found {len(files)} markdown files. Use fzf to select:")
        selected = select_file_with_fzf(files)
        if selected:
            return selected
        print("Selection cancelled")
        return None
    else:
        # Plain prompt fallback
        print(f"Found {len(files)} markdown files:")
        for idx, file in enumerate(files[:10], 1):
            print(f"  {idx}. {file}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")

        file_path = input("\nEnter file path or number (1-10): ").strip()

        # Check if input is a number
        if file_path.isdigit():
            idx = int(file_path) - 1
            if 0 <= idx < min(10, len(files)):
                return files[idx]
            print("Invalid number")
            return None

        return file_path if file_path else None


def get_available_styles() -> list[str]:
    """Get list of available styles from the experiment module."""
    try:
        from .experiment import list_styles
        return list_styles()
    except ImportError:
        return []


def select_styles_with_fzf(styles: list[str]) -> list[str] | None:
    """Use fzf to select multiple styles."""
    try:
        result = subprocess.run(
            [
                "fzf",
                "--multi",
                "--prompt",
                "Select styles (Tab to select multiple, Enter to confirm): ",
                "--height",
                "40%",
            ],
            input="\n".join(styles),
            text=True,
            capture_output=True,
            check=True,
        )
        selected = [s.strip() for s in result.stdout.strip().split("\n") if s.strip()]
        return selected if selected else None
    except subprocess.CalledProcessError:
        # User cancelled or fzf error
        return None


def select_styles_interactive() -> list[str] | None:
    """Interactively select styles."""
    styles = get_available_styles()

    if not styles:
        print("No styles found")
        styles_input = input("Enter comma-separated style names: ").strip()
        if not styles_input:
            return None
        return [s.strip() for s in styles_input.split(",") if s.strip()]

    # Try fzf first for multi-select, fall back to plain prompt
    if check_fzf_available():
        print(f"Found {len(styles)} available styles. Use fzf to select (Tab for multi-select):")
        selected = select_styles_with_fzf(styles)
        if selected:
            return selected
        print("Selection cancelled")
        return None
    else:
        # Plain prompt fallback
        print(f"Available styles: {', '.join(styles)}")
        styles_input = input("Enter comma-separated style names: ").strip()
        if not styles_input:
            return None

        selected = [s.strip() for s in styles_input.split(",") if s.strip()]

        # Validate selected styles
        invalid = [s for s in selected if s not in styles]
        if invalid:
            print(f"Warning: Unknown styles: {', '.join(invalid)}")
            proceed = input("Continue anyway? (y/n): ").strip().lower()
            if proceed != "y":
                return None

        return selected


def parse_styles(styles_arg: str | None) -> list[str] | None:
    """Parse comma-separated styles argument."""
    if not styles_arg:
        return None
    return [s.strip() for s in styles_arg.split(",") if s.strip()]


def run_tuning_pipeline(
    input_file: str,
    styles: list[str],
    content_type: str = "article",
    no_auto_display: bool = False,
) -> int:
    """Run the multi-variant tuning pipeline."""
    # Generate unique session name
    session_name = generate_session_name()

    print(f"Creating tmux session: {session_name}")
    print(f"Input file: {input_file}")
    print(f"Styles: {', '.join(styles)}")
    print(f"Content type: {content_type}")
    print()

    # Create tmux session and execute variants
    result = create_tmux_session(session_name, styles, input_file, content_type)
    if result != 0:
        return result

    # Attach to the session
    print(f"Attaching to session '{session_name}'...")
    print("Use 'Ctrl+b d' to detach from the session.")
    print(f"To reattach later: narrio tune --attach {session_name}")
    print()

    try:
        run_tmux_command(["tmux", "attach-session", "-t", session_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to attach to session: {e}")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for tune command."""
    parser = build_tune_parser()
    args = parser.parse_args(argv)

    # Handle --list flag
    if args.list:
        return handle_list_sessions()

    # Handle --attach flag
    if args.attach:
        return attach_to_session(args.attach)

    # Check tmux availability
    if not check_tmux_available():
        print("Error: tmux is not installed or not available in PATH")
        print("\nInstallation instructions:")
        print("  - macOS: brew install tmux")
        print("  - Ubuntu/Debian: sudo apt-get install tmux")
        print("  - Fedora/RHEL: sudo dnf install tmux")
        return 1

    # Notify user if running inside tmux
    if is_inside_tmux():
        print("Note: Running inside an existing tmux session. Creating independent session...")
        print()

    # Parse input and styles from arguments
    input_file = args.input
    styles = parse_styles(args.styles)

    # Check if we have all required arguments for non-interactive mode
    if input_file and styles:
        # Non-interactive mode: all arguments provided
        return run_tuning_pipeline(
            input_file=input_file,
            styles=styles,
            no_auto_display=args.no_auto_display,
        )

    # Interactive mode: collect missing arguments
    print("=== Narrio Multi-Variant Tuning Pipeline ===\n")

    # Get input file if not provided
    if not input_file:
        input_file = select_file_interactive()
        if not input_file:
            print("Error: No input file selected")
            return 1

    # Get styles if not provided
    if not styles:
        styles = select_styles_interactive()
        if not styles:
            print("Error: No styles selected")
            return 1

    # Run the tuning pipeline
    return run_tuning_pipeline(
        input_file=input_file,
        styles=styles,
        no_auto_display=args.no_auto_display,
    )


if __name__ == "__main__":
    sys.exit(main())
