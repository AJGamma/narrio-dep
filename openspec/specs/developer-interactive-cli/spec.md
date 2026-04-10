# developer-interactive-cli Specification

## Purpose
TBD - created by archiving change add-prompt-experiment-workbench. Update Purpose after archive.
## Requirements
### Requirement: Developers can run experiments through command-style CLI entry points
The system SHALL provide command-style CLI entry points for running, resuming, inspecting, comparing, and exporting prompt experiments.

#### Scenario: Execute a run non-interactively
- **WHEN** a developer provides the required experiment parameters through CLI arguments
- **THEN** the system starts the requested experiment without requiring interactive prompts

#### Scenario: Resume from an existing run
- **WHEN** a developer invokes a resume-oriented CLI command with a prior workbench run reference
- **THEN** the system starts a new run using the specified resume stage and records the reused artifacts

### Requirement: Developers can configure experiments through an interactive terminal flow
The system SHALL provide an interactive terminal flow that collects experiment parameters without embedding business logic in the interaction layer.

#### Scenario: Collect experiment parameters interactively
- **WHEN** a developer starts the interactive lab command
- **THEN** the system prompts for content type, source input, style, prompt selection, start stage, and execution mode before dispatching the run

#### Scenario: Dispatch interactive selections through shared execution logic
- **WHEN** the interactive flow completes parameter collection
- **THEN** the system invokes the same underlying workflow execution path used by non-interactive commands

### Requirement: Interactive selection prefers fzf with a fallback path
The system SHALL use `fzf` as the preferred selector when available and SHALL fall back to a non-`fzf` terminal prompt when it is not available.

#### Scenario: Use fzf when installed
- **WHEN** a developer starts an interactive command on a machine where `fzf` is available
- **THEN** the system offers list-based selection through `fzf`

#### Scenario: Fall back when fzf is unavailable
- **WHEN** a developer starts an interactive command on a machine where `fzf` is unavailable
- **THEN** the system falls back to a plain terminal selection flow without aborting the command

### Requirement: CLI surfaces workbench outputs for developer inspection
The system SHALL report where the current experiment results were written so that developers can quickly inspect intermediate artifacts.

#### Scenario: Show output paths after run submission
- **WHEN** an experiment run is created
- **THEN** the CLI prints the workbench run path and the known artifact locations or stage directories for inspection

#### Scenario: Show batch run summaries
- **WHEN** a batch experiment finishes
- **THEN** the CLI reports each run status together with its prompt identity and run path

