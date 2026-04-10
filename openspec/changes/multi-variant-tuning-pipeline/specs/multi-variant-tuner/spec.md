# multi-variant-tuner Specification

## Purpose

Defines the multi-variant parallel execution pipeline that enables developers to run multiple style variants concurrently via tmux, with real-time output visibility and automatic result presentation.

## Requirements

### Requirement: Multi-variant session orchestration
The system SHALL create and manage a tmux session with multiple panes, where each pane runs a single style variant of the input file.

#### Scenario: Create tmux session with dynamic pane layout
- **WHEN** a user provides an input file path and a list of styles (e.g., `--styles OpenAI,Anthropic,Google`)
- **THEN** the system creates a tmux session named `narrio-tune-<timestamp>` with a grid of panes (one per style)

#### Scenario: Execute variant in isolated pane
- **WHEN** a pane is created for a style variant
- **THEN** the system runs the single-variant execution command in that pane with isolated environment variables

#### Scenario: Handle tmux not installed
- **WHEN** the system detects tmux is not available
- **THEN** it aborts with a clear error message and installation instructions

### Requirement: Real-time output aggregation
The system SHALL maintain a summary window that aggregates the status of all running variants.

#### Scenario: Display variant status in summary window
- **WHEN** variants are running
- **THEN** the summary window shows each variant's status: `pending`, `running`, `done`, or `failed`

#### Scenario: Update status on variant completion
- **WHEN** a variant completes
- **THEN** the summary window updates that variant's status and displays the output artifact path

### Requirement: Interactive input collection
The system SHALL provide an interactive CLI flow that collects the input file path and style selections from the user.

#### Scenario: Collect input file path interactively
- **WHEN** the user runs `narrio tune` without arguments
- **THEN** the system prompts for the input file path with fzf-based file selection (or plain prompt fallback)

#### Scenario: Collect multiple styles interactively
- **WHEN** the user provides styles via `--styles` flag
- **THEN** the system accepts comma-separated style names
- **WHEN** no `--styles` flag is provided
- **THEN** the system prompts for style selection with multi-select support

#### Scenario: Support non-interactive mode
- **WHEN** the user provides both `--input` and `--styles` flags
- **THEN** the system skips all interactive prompts and starts the tmux session immediately

### Requirement: Post-run image presentation
The system SHALL automatically display the generated image after each variant completes.

#### Scenario: Display image with kitten icat
- **WHEN** a variant completes and kitty is detected (via `KITTY_LISTEN_ON` or `TERM=kitty`)
- **THEN** the system runs `kitten icat <image-path>` in the corresponding pane

#### Scenario: Fallback to Python PIL display
- **WHEN** a variant completes but kitty is not available
- **THEN** the system uses Python PIL to open the image in the system's default image viewer

#### Scenario: Handle missing image output
- **WHEN** a variant completes but no image was generated
- **THEN** the system displays an error message and the log path for debugging

### Requirement: Session cleanup and recovery
The system SHALL provide mechanisms to clean up completed sessions and recover from interruptions.

#### Scenario: Auto-cleanup on successful completion
- **WHEN** all variants complete successfully and the user confirms
- **THEN** the system kills the tmux session after displaying final results

#### Scenario: Manual session attachment
- **WHEN** a user wants to inspect a completed or interrupted session
- **THEN** the system supports `narrio tune --attach <session-name>` to reattach to an existing tmux session

#### Scenario: List active sessions
- **WHEN** a user runs `narrio tune --list`
- **THEN** the system lists all active `narrio-tune-*` tmux sessions with their creation time and variant count
