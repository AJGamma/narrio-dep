## 1. Core Service Implementation

- [x] 1.1 Create `src/narrio/highlight_service.py` with basic module structure
- [x] 1.2 Implement `CONTENT_TYPE_CONFIG` for article and podcast highlight strategies
- [x] 1.3 Add `extract_highlights()` function that loads content and calls LLM API
- [x] 1.4 Implement JSON response parsing and validation for highlight structure
- [x] 1.5 Add content length validation (minimum 1000 words threshold)
- [x] 1.6 Implement position tracking in source content for each highlight

## 2. Prompt Engineering

- [x] 2.1 Create `assets/process/prompt/HighlightExtract.md` base template
- [ ] 2.2 Design article-specific highlight extraction prompt emphasizing insights and counterintuitive claims
- [ ] 2.3 Design podcast-specific highlight extraction prompt emphasizing conversational quotability
- [ ] 2.4 Add prompt criteria for self-contained, context-independent sentences
- [ ] 2.5 Include negative examples in prompt (avoid jargon, pronouns, generic statements)
- [ ] 2.6 Request engagement rationale in prompt to enable quality assessment

## 3. Output Structure

- [x] 3.1 Define JSON schema for `highlights.json` output file
- [x] 3.2 Implement highlight ranking by engagement score (descending order)
- [x] 3.3 Add metadata fields: text, score, rationale, position (chunk_index, paragraph)
- [x] 3.4 Create output directory structure following existing conventions

## 4. CLI Integration

- [x] 4.1 Add `extract-highlights` subcommand to `src/narrio/cli.py`
- [x] 4.2 Add `--extract-highlights` flag to `run` command for integrated pipeline
- [x] 4.3 Add `--model` override parameter for highlight extraction
- [x] 4.4 Implement `--continue-on-error` flag for optional highlight extraction
- [x] 4.5 Add CLI help documentation for new commands and flags

## 5. Pipeline Integration

- [x] 5.1 Update `src/narrio/experiment.py` to call highlight extraction before chunkification
- [x] 5.2 Add conditional logic to skip highlights for content below minimum length
- [x] 5.3 Store `highlights.json` in experiment output directory structure
- [x] 5.4 Ensure highlight extraction failure doesn't block pipeline with `--continue-on-error`

## 6. Configuration and Error Handling

- [x] 6.1 Integrate with existing OpenRouter/LLM configuration infrastructure
- [x] 6.2 Add timeout configuration for highlight extraction API calls
- [x] 6.3 Implement graceful error handling for LLM API failures
- [x] 6.4 Add clear error messages with API response details
- [x] 6.5 Add logging for highlight extraction progress and results

## 7. Testing and Documentation

- [ ] 7.1 Test standalone highlight extraction on sample article content
- [ ] 7.2 Test standalone highlight extraction on sample podcast transcript
- [ ] 7.3 Test integrated pipeline with `--extract-highlights` flag
- [ ] 7.4 Verify short content skips highlight extraction appropriately
- [ ] 7.5 Test error handling with invalid API keys / network failures
- [x] 7.6 Update README.md with highlight extraction usage examples
- [ ] 7.7 Add example `highlights.json` output to documentation

## 8. Prompt Iteration and Quality

- [ ] 8.1 Evaluate initial prompt results on diverse content samples
- [ ] 8.2 Refine prompt based on highlight quality (engaging vs. boring)
- [ ] 8.3 Tune engagement criteria (emotional resonance, surprise factor, quotability)
- [ ] 8.4 Validate highlights are contextually self-contained
- [ ] 8.5 Document prompt design decisions and tuning rationale
