## 1. Foundations

- [x] 1.1 Define run tree identifiers, node identifiers, and status enums compatible with existing workbench/run concepts
- [x] 1.2 Define run tree persistence layout under `.narrio/workbench/` (tree root, branch runs, manifests, events) without breaking existing CLI runs
- [x] 1.3 Add a lightweight event schema for node updates that can be appended to JSONL and replayed into current tree state

## 2. Execution Orchestration

- [x] 2.1 Implement “one source + multiple styles” orchestration that forks into independent branch runs after chunkify
- [x] 2.2 Implement explicit rerun entry points for `from-source`, `from-chunk`, and `from-editorial` boundaries for a selected branch
- [x] 2.3 Ensure rerun creates a new run instance/branch and never overwrites prior artifacts

## 3. API Layer (workflow-tree-api)

- [x] 3.1 Add an ASGI service module exposing create-run-tree and get-run-tree endpoints returning graph-shaped data
- [x] 3.2 Add a WebSocket endpoint that streams incremental node events for a run tree
- [x] 3.3 Add an API endpoint to request node-level rerun and validate required resume artifacts
- [x] 3.4 Add API error responses that surface explicit failure reasons without implicit fallback execution

## 4. GUI Layer (workflow-tree-gui)

- [x] 4.1 Build a GUI page to upload/paste article content and select multiple styles to create a run tree
- [x] 4.2 Render the run tree as a visual tree/graph with node status styling and branch grouping
- [x] 4.3 Implement real-time updates in the GUI by subscribing to the run tree event stream
- [x] 4.4 Add node inspection UI for artifacts and failure details, including links/paths to workbench outputs
- [x] 4.5 Add node actions to trigger rerun from a selected boundary and visualize the new branch/run instance

## 5. Integration & Packaging

- [x] 5.1 Add project dependencies and script entry points for running the GUI server locally
- [x] 5.2 Ensure GUI and CLI reuse shared execution logic and produce compatible manifests/events
- [x] 5.3 Add minimal end-to-end smoke tests for run tree creation, event streaming, and rerun request validation
