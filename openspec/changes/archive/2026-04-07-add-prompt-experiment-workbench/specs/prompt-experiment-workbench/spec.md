## ADDED Requirements

### Requirement: Workbench experiment runs are persisted in a gitignored local directory
The system SHALL persist every prompt experiment under a local gitignored workbench directory organized by content type, combo identity, and run identity so that developers can inspect and reuse intermediate artifacts.

#### Scenario: Create a new run directory for an input combination
- **WHEN** a developer starts an experiment for a selected content type, source input, style, and prompt set
- **THEN** the system creates a unique workbench path under `.narrio/workbench/<content-type>/<combo-id>/runs/<run-id>/`

#### Scenario: Preserve intermediate artifacts for inspection
- **WHEN** a run completes or fails after producing any stage outputs
- **THEN** the system keeps generated manifest, logs, and stage artifacts in the run directory instead of deleting them

### Requirement: Experiment metadata is recorded per run
The system SHALL record run metadata that explains what inputs, assets, models, and resume settings were used for a run.

#### Scenario: Persist run manifest
- **WHEN** a run is initialized
- **THEN** the system writes a manifest containing at least combo id, run id, workflow type, selected source, selected prompts, selected style, selected models, start stage, and step status

#### Scenario: Record reused artifacts during resume
- **WHEN** a run starts from `from-chunk` or `from-editorial`
- **THEN** the manifest records the reused artifact paths and the chosen start stage

### Requirement: Stage restart uses explicit resume boundaries
The system SHALL support resuming from the source, chunk, or editorial stage without implicitly falling back to an earlier stage.

#### Scenario: Resume from chunk
- **WHEN** a developer starts a run with `from-chunk`
- **THEN** the system reuses an existing chunk artifact and runs stylify plus render only

#### Scenario: Resume from editorial
- **WHEN** a developer starts a run with `from-editorial`
- **THEN** the system reuses an existing editorial artifact and runs render only

#### Scenario: Missing resume artifact fails the run
- **WHEN** a developer starts a run from `from-chunk` or `from-editorial` and the required artifact is missing or incompatible
- **THEN** the system fails the run with an explicit error instead of silently rerunning earlier stages

### Requirement: Experiment tasks can run concurrently at the task level
The system SHALL support running multiple experiment tasks concurrently while keeping each individual run sequential by stage.

#### Scenario: Run multiple prompt variants for the same input
- **WHEN** a developer launches an experiment batch with multiple prompt variants
- **THEN** the system can execute those runs concurrently as separate run directories

#### Scenario: Preserve stage ordering within a run
- **WHEN** a single run is executing
- **THEN** the system keeps chunkify, stylify, and render in deterministic stage order for that run
