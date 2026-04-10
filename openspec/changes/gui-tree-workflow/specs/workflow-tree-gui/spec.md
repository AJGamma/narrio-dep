## ADDED Requirements

### Requirement: Users can upload article content and create a multi-style run tree in the GUI
The system SHALL provide a GUI flow that allows a user to upload or paste article content and select multiple styles to create a run tree.

#### Scenario: Submit an article and select multiple styles
- **WHEN** a user uploads an article and selects two or more styles in the GUI
- **THEN** the system creates a run tree and starts execution for the selected styles

### Requirement: GUI visualizes the workflow as a tree with node statuses
The GUI SHALL visualize the workflow run as a tree where each node represents an execution boundary and displays its current status.

#### Scenario: Render a run tree with statuses
- **WHEN** a run tree exists for a user submission
- **THEN** the GUI renders nodes and edges for the run tree and shows each node status as queued, running, completed, or failed

### Requirement: GUI updates the tree in real time as steps progress
The GUI SHALL update node status and available artifact links in real time based on the run tree event stream.

#### Scenario: Real-time update while a node completes
- **WHEN** a node transitions from running to completed and produces an artifact
- **THEN** the GUI updates the node status and surfaces the artifact reference without requiring a page refresh

### Requirement: Users can inspect node outputs and logs from the GUI
The GUI SHALL allow users to inspect the outputs and logs associated with a node, including artifact paths and error details when failed.

#### Scenario: Inspect a failed node
- **WHEN** a node is in failed status
- **THEN** the GUI provides access to the failure message and the associated log or event references for that node

### Requirement: Users can rerun a node subtree from the GUI
The GUI SHALL allow users to request a rerun starting from a node boundary and SHALL reflect the rerun as a new branch or new run instance in the tree.

#### Scenario: Rerun a style branch from the GUI
- **WHEN** a user triggers rerun for a style branch node in the GUI
- **THEN** the system starts a rerun and the GUI displays the new branch or run instance and its live status updates
