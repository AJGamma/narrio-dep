## ADDED Requirements

### Requirement: System can create a workflow run tree for one source with multiple style branches
The system SHALL accept a single article source input together with a list of selected styles and SHALL create a workflow run tree that branches by style after the chunkify stage.

#### Scenario: Create a new run tree for an uploaded article and selected styles
- **WHEN** a client submits article content (or a content reference) with a style list
- **THEN** the system creates a new run tree identifier and initializes nodes for source, chunkify, and one stylify+render branch per style

### Requirement: System can return the current run tree graph state
The system SHALL provide a query API that returns the run tree as an explicit graph structure including nodes, edges, statuses, and known artifact references.

#### Scenario: Fetch run tree state for rendering
- **WHEN** a client requests the run tree state by run tree identifier
- **THEN** the system returns a graph containing node identifiers, edge relationships, node status, and artifact paths if available

### Requirement: System provides a real-time event stream for run tree updates
The system SHALL provide a real-time event stream for a run tree so that clients can update visualization without polling.

#### Scenario: Subscribe to run tree updates
- **WHEN** a client subscribes to the run tree event stream
- **THEN** the system emits incremental events containing at least node identifier, event type, timestamp, and updated status or artifact references

### Requirement: System supports node-level rerun from an explicit stage boundary
The system SHALL allow clients to request a rerun starting from an explicit stage boundary and SHALL persist the rerun as a new run instance or branch without overwriting the prior artifacts.

#### Scenario: Rerun a style branch from chunk boundary
- **WHEN** a client requests rerun for a stylify/render branch starting from `from-chunk`
- **THEN** the system creates a new run instance for that branch, reuses the required chunk artifact, and executes stylify plus render for the selected style

### Requirement: System rejects rerun requests when required resume artifacts are missing
The system SHALL fail a rerun request when the required upstream artifact for the chosen resume boundary is missing or incompatible.

#### Scenario: Rerun from editorial boundary without editorial artifact
- **WHEN** a client requests rerun starting from `from-editorial` but the referenced editorial artifact does not exist
- **THEN** the system returns an explicit failure and does not fall back to rerunning earlier stages
