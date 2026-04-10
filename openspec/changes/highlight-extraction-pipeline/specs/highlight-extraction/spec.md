## ADDED Requirements

### Requirement: Extract engaging highlights from content
The system SHALL analyze long-form content and extract 3-5 sentences that are most likely to engage readers as preview or thumbnail content.

#### Scenario: Successful highlight extraction from article
- **WHEN** user runs highlight extraction on an article with >1000 words
- **THEN** system returns JSON with 3-5 highlight sentences ranked by engagement score

#### Scenario: Successful highlight extraction from podcast transcript
- **WHEN** user runs highlight extraction on a podcast transcript
- **THEN** system returns JSON with 3-5 quotable moments optimized for conversational content

#### Scenario: Content too short for meaningful highlights
- **WHEN** user runs highlight extraction on content with <1000 words
- **THEN** system returns warning and empty highlights array

### Requirement: Provide engagement metadata for each highlight
Each extracted highlight SHALL include the text, an engagement score (0-1), rationale for selection, and position information.

#### Scenario: Highlight includes full metadata
- **WHEN** highlight is extracted
- **THEN** result includes `text`, `score`, `rationale`, and `position` fields

#### Scenario: Position tracking enables context retrieval
- **WHEN** highlight position data is present
- **THEN** caller can locate the original sentence in source content

### Requirement: Support both article and podcast content types
The system SHALL adapt highlight extraction strategy based on content type, optimizing for article insight density or podcast conversational flow.

#### Scenario: Article highlights favor insight and counterintuitive claims
- **WHEN** extracting from article content type
- **THEN** selected highlights prioritize surprising facts, topic sentences, and insight density

#### Scenario: Podcast highlights favor quotable conversational moments
- **WHEN** extracting from podcast content type
- **THEN** selected highlights prioritize natural speech patterns, narrative hooks, and emotional resonance

### Requirement: Ensure highlights are contextually self-contained
Selected highlights SHALL be understandable when viewed in isolation without requiring surrounding context.

#### Scenario: Highlight makes sense standalone
- **WHEN** highlight sentence is extracted
- **THEN** sentence can be understood without needing previous or following sentences

#### Scenario: Avoid pronoun-heavy or reference-dependent sentences
- **WHEN** candidate sentence relies heavily on pronouns or contextual references
- **THEN** system deprioritizes or excludes it from final highlights

### Requirement: Provide CLI access to highlight extraction
The system SHALL expose highlight extraction through the CLI as both a standalone command and an integrated pipeline option.

#### Scenario: Standalone highlight extraction
- **WHEN** user runs `narrio extract-highlights --input <file>`
- **THEN** system generates `highlights.json` in output directory

#### Scenario: Integrated pipeline execution
- **WHEN** user runs `narrio run --extract-highlights --markdown <file>`
- **THEN** highlight extraction executes after content loading, before chunkification

#### Scenario: Skip highlights for short content
- **WHEN** integrated pipeline detects content below minimum length
- **THEN** highlight extraction is automatically skipped without error

### Requirement: Store highlights in structured JSON format
Extracted highlights SHALL be persisted in a `highlights.json` file following a defined schema.

#### Scenario: Output file follows schema
- **WHEN** highlights are extracted
- **THEN** output file contains `{"highlights": []}` array with each entry having required fields

#### Scenario: Multiple highlights preserved in order
- **WHEN** multiple highlights are extracted
- **THEN** they are stored in descending order by engagement score

### Requirement: Use configurable LLM models for extraction
Highlight extraction SHALL use the same LLM configuration infrastructure as other services (OpenRouter, model selection, timeout).

#### Scenario: Respects global model configuration
- **WHEN** user has configured a specific model in settings
- **THEN** highlight extraction uses that model

#### Scenario: Supports model override per execution
- **WHEN** user specifies `--model` flag
- **THEN** highlight extraction uses the specified model for that run

### Requirement: Handle LLM failures gracefully
The system SHALL provide clear error messages when highlight extraction fails and allow pipeline to continue if extraction is optional.

#### Scenario: API failure with clear error message
- **WHEN** LLM API call fails
- **THEN** system logs error with API response details and exits cleanly

#### Scenario: Optional extraction failure doesn't block pipeline
- **WHEN** highlight extraction fails in integrated pipeline mode with `--continue-on-error`
- **THEN** pipeline continues to chunkification stage without highlights
