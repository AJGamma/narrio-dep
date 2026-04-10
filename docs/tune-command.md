# Narrio Tune - Multi-Variant Tuning Pipeline

The `narrio tune` command enables parallel execution of multiple style variants using tmux, providing real-time visibility into the execution process and automatic result presentation.

## Overview

Instead of running variants sequentially (one at a time, waiting for each to complete), the tune command:

1. Creates a tmux session with multiple panes
2. Runs each variant in its own isolated pane
3. Provides a summary window showing overall progress
4. Automatically displays results after completion (if supported)

## Prerequisites

### Required

- **tmux**: Terminal multiplexer for managing multiple panes
  - macOS: `brew install tmux`
  - Ubuntu/Debian: `sudo apt-get install tmux`
  - Fedora/RHEL: `sudo dnf install tmux`

### Optional

- **fzf**: Fuzzy finder for interactive file/style selection
  - macOS: `brew install fzf`
  - Ubuntu/Debian: `sudo apt-get install fzf`

- **kitty terminal**: For in-terminal image display
  - macOS: `brew install --cask kitty`
  - See: https://sw.kovidgoyal.net/kitty/

- **Pillow**: Python library for image display fallback
  - Install: `pip install Pillow`

## Usage

### Non-Interactive Mode

Provide all arguments via command-line flags:

```bash
narrio tune --input path/to/file.md --styles OpenAI,Anthropic,Google
```

### Interactive Mode

Run without arguments to be prompted for input:

```bash
narrio tune
```

The command will:
1. Show available markdown files (with fzf if installed)
2. Let you select the input file
3. Show available styles (with multi-select via fzf if installed)
4. Let you select one or more styles
5. Create and attach to the tmux session

### List Active Sessions

See all active tune sessions:

```bash
narrio tune --list
```

Output example:
```
Active narrio-tune sessions (2):
  - narrio-tune-20260408-143022 (created: 20260408-143022)
  - narrio-tune-20260408-150145 (created: 20260408-150145)
```

### Attach to Existing Session

Reattach to a previously detached session:

```bash
narrio tune --attach narrio-tune-20260408-143022
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--input <path>` | Input file path (markdown file) |
| `--styles <list>` | Comma-separated list of style names (e.g., `OpenAI,Anthropic`) |
| `--no-auto-display` | Skip automatic image display after completion |
| `--attach <name>` | Attach to an existing tmux session |
| `--list` | List all active narrio-tune sessions |

## Tmux Session Layout

### Variants Window (window 0)

Contains multiple panes in a tiled grid layout, with each pane running one style variant:

```
┌─────────────┬─────────────┐
│   OpenAI    │  Anthropic  │
│   (pane 0)  │   (pane 1)  │
├─────────────┼─────────────┤
│   Google    │   Mistral   │
│   (pane 2)  │   (pane 3)  │
└─────────────┴─────────────┘
```

### Summary Window (window 1)

Shows overall session information and navigation help:

```
=== Narrio Multi-Variant Tuning Pipeline ===
Session: narrio-tune-20260408-143022
Input: content/articles/example.md
Variants: 4

Variants running:
  [0] OpenAI: running in pane 0
  [1] Anthropic: running in pane 1
  [2] Google: running in pane 2
  [3] Mistral: running in pane 3

Navigation:
  - Ctrl+b, 0: Switch to variants window
  - Ctrl+b, 1: Switch back to this summary
  - Ctrl+b, d: Detach from session
  - Ctrl+b, arrow keys: Navigate between panes
```

## Tmux Navigation

Common tmux commands (prefix is `Ctrl+b` by default):

| Command | Action |
|---------|--------|
| `Ctrl+b, 0` | Switch to variants window |
| `Ctrl+b, 1` | Switch to summary window |
| `Ctrl+b, arrow keys` | Navigate between panes |
| `Ctrl+b, d` | Detach from session (keeps it running) |
| `Ctrl+b, x` | Kill current pane |
| `Ctrl+b, &` | Kill current window |

## Image Display

After each variant completes, the system attempts to display the generated image automatically (unless `--no-auto-display` is set).

### Display Methods

1. **kitty terminal** (if detected):
   - Uses `kitten icat` for in-terminal image display
   - Detects kitty via `KITTY_LISTEN_ON` or `TERM=xterm-kitty`

2. **PIL fallback** (if kitty not available):
   - Opens image in system's default image viewer
   - Requires Pillow: `pip install Pillow`

3. **Path only** (if neither available):
   - Prints the image file path
   - Suggests installing Pillow

## Session Lifecycle

### Creating a Session

```bash
narrio tune --input article.md --styles OpenAI,Anthropic
```

Output:
```
Creating tmux session: narrio-tune-20260408-143022
Input file: article.md
Styles: OpenAI, Anthropic
Content type: article

Attaching to session 'narrio-tune-20260408-143022'...
[tmux session starts]
```

### Detaching from a Session

Press `Ctrl+b, d` to detach from the session. The variants continue running in the background.

### Reattaching to a Session

```bash
narrio tune --attach narrio-tune-20260408-143022
```

### Cleaning Up

After detaching from a session, you'll be prompted:

```
Session detached.
Clean up this session? (y/n):
```

- Type `y` to kill the session
- Type `n` to keep it running

To manually kill a session:
```bash
tmux kill-session -t narrio-tune-20260408-143022
```

## Examples

### Run 3 variants in parallel

```bash
narrio tune --input research/ai-trends.md --styles OpenAI,Anthropic,Google
```

### Run variants without auto-display

```bash
narrio tune --input article.md --styles OpenAI,Claude --no-auto-display
```

### Check running sessions and reattach

```bash
# List active sessions
narrio tune --list

# Reattach to a specific session
narrio tune --attach narrio-tune-20260408-143022
```

## Troubleshooting

### "Error: tmux is not installed"

Install tmux using your system's package manager:
- macOS: `brew install tmux`
- Ubuntu: `sudo apt-get install tmux`

### "No styles selected" in interactive mode

Make sure you have styles configured in your narrio installation. Check:
```bash
ls ~/.narrio/styles/  # or your configured styles directory
```

### Pane output is not visible

- Switch to the variants window: `Ctrl+b, 0`
- Navigate to the specific pane: `Ctrl+b, arrow keys`
- Check if the command is still running or has completed

### Image display not working

1. Check if you're in a kitty terminal: `echo $TERM`
2. Install Pillow if not available: `pip install Pillow`
3. Use `--no-auto-display` and view images manually

## Advanced Usage

### Custom Content Type

The default content type is `article`. To change it, modify the `run_tuning_pipeline` function call in the code or extend the CLI with a `--content-type` option.

### Parallel Execution Limits

The number of parallel variants is limited only by:
- Your system's resources (CPU, memory)
- Terminal window size (for readable pane layout)

Recommended: 2-6 variants for optimal viewing and performance.

## Related Commands

- `narrio run`: Run a single variant (traditional sequential mode)
- `narrio lab`: Interactive experimentation mode
- `narrio tree`: Multi-variant tree-based execution (alternative approach)

## See Also

- [Technical Design Document](technical-design.md)
- [Narrio Architecture](../README.md)
- [tmux Documentation](https://github.com/tmux/tmux/wiki)
