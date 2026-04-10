## 1. Core Infrastructure

- [x] 1.1 Create `src/narrio/tune.py` module with basic CLI entry point
- [x] 1.2 Add `narrio tune` command to existing CLI framework (if applicable)
- [x] 1.3 Implement tmux availability check with clear error message

## 2. Tmux Session Management

- [x] 2.1 Implement tmux session creation with unique naming (`narrio-tune-<timestamp>`)
- [x] 2.2 Implement dynamic pane layout based on style count
- [x] 2.3 Implement variant execution in isolated pane shells
- [x] 2.4 Implement summary window creation and status tracking

## 3. Interactive CLI Flow

- [x] 3.1 Implement `--input` and `--styles` argument parsing
- [x] 3.2 Implement fzf-based file selection with plain prompt fallback
- [x] 3.3 Implement multi-select style selection (comma-separated or interactive)
- [x] 3.4 Implement non-interactive mode (all flags provided, no prompts)

## 4. Image Display Integration

- [x] 4.1 Implement kitty detection (via `KITTY_LISTEN_ON` and `TERM`)
- [x] 4.2 Implement `kitten icat` integration for image display
- [x] 4.3 Implement Python PIL fallback for non-kitty terminals
- [x] 4.4 Implement `--no-auto-display` flag to skip auto-display

## 5. Session Lifecycle Management

- [x] 5.1 Implement session cleanup on successful completion
- [x] 5.2 Implement `--attach <session-name>` for manual session attachment
- [x] 5.3 Implement `--list` to show active narrio-tune sessions
- [x] 5.4 Implement real-time status updates in summary window

## 6. Testing & Documentation

- [ ] 6.1 Write unit tests for tmux session management functions
- [ ] 6.2 Write integration tests for full multi-variant pipeline
- [x] 6.3 Add usage documentation to `docs/` directory
- [x] 6.4 Add tmuxifier configuration example (optional)
