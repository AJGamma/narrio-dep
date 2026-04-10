## Context

Narrio currently processes long-form content through three stages (Chunkify → Stylify → Render), but lacks a mechanism to generate compelling preview content. The highlight extraction pipeline will add a preprocessing capability that identifies quotable, engaging sentences from the source material.

The existing architecture uses service modules (`chunk_service.py`, `editorial_service.py`, etc.) that follow a consistent pattern:
- Load prompts from `assets/process/prompt/*.md`
- Call LLM API via `call_llm_api()` with standardized message formatting
- Extract and parse JSON responses
- Store results in experiment output directories

## Goals / Non-Goals

**Goals:**
- Create a reusable highlight extraction service following existing architectural patterns
- Design a prompt that reliably identifies attention-grabbing, quotable sentences
- Enable standalone execution and integration into the full pipeline
- Support both article and podcast content types
- Output structured data (JSON) compatible with downstream rendering

**Non-Goals:**
- Image generation for highlights (use existing render capabilities)
- Real-time extraction (batch processing only)
- Multi-language support beyond what the underlying LLM provides
- Highlight ranking or A/B testing infrastructure

## Decisions

### 1. Service Architecture
**Decision**: Create `highlight_service.py` following the same pattern as `chunk_service.py`

**Rationale**: 
- Maintains consistency with existing codebase
- Reuses proven LLM integration patterns
- Easy for developers familiar with other services to understand
- Minimal new abstractions needed

**Alternatives considered**:
- Integrate into `chunk_service.py` → Rejected: Different responsibility, should be decoupled
- Create a generic "analysis" service → Rejected: Over-engineering for single use case

### 2. Prompt Design Strategy
**Decision**: Create a dedicated `HighlightExtract.md` prompt that emphasizes criteria for "engaging" content

**Rationale**:
- Prompt quality is explicitly identified as critical by the user
- Dedicated prompt file allows iteration without code changes
- Can specify clear criteria: emotional resonance, surprise, quotability, context independence

**Key prompt elements**:
- Request 3-5 highlight candidates ranked by engagement potential
- Specify length constraints (e.g., 1-2 sentences, 100-200 characters)
- Include negative criteria (avoid jargon, don't pick first/last sentences, ensure standalone clarity)
- Request rationale for each selection to enable prompt tuning

### 3. Output Format
**Decision**: JSON structure with array of highlights, each containing `text`, `score`, `rationale`, `position`

```json
{
  "highlights": [
    {
      "text": "The extracted sentence",
      "score": 0.95,
      "rationale": "Why this is engaging",
      "position": {
        "chunk_index": 2,
        "paragraph": 3
      }
    }
  ]
}
```

**Rationale**:
- Enables programmatic selection of top highlight
- Position tracking helps with context display
- Rationale aids prompt debugging and quality assessment

### 4. Pipeline Integration
**Decision**: Optional preprocessing step, executed after content loading but before chunkification

**Rationale**:
- Highlights work on full source text, not chunked content
- Can be skipped for short content (add length threshold)
- Independence from chunk boundaries prevents artificial constraints

**Alternatives considered**:
- Extract from chunks → Rejected: May miss highlights split across boundaries
- Post-editorial extraction → Rejected: Editorial JSON format is restrictive

### 5. Content Type Support
**Decision**: Unified implementation with content-type-specific prompt variants

**Rationale**:
- Articles and podcasts have different engagement patterns
- Podcasts: conversational, quotable moments, narrative hooks
- Articles: insight density, topic sentences, counterintuitive claims
- Single service with prompt switching via config (similar to `CONTENT_TYPE_CONFIG`)

## Risks / Trade-offs

**[Risk] LLM may select technically accurate but boring sentences** → Mitigation: Emphasize "surprising" and "emotional resonance" in prompt; include negative examples

**[Risk] Selected highlights lack context when viewed standalone** → Mitigation: Prompt instructs to prefer self-contained sentences; include surrounding context in output for optional display

**[Risk] Long content may exceed context window** → Mitigation: Add content truncation strategy (first/middle/last sampling); document token limits per model

**[Trade-off] Additional API call increases cost/latency** → Acceptable: Highlights are high-value for user engagement; can be cached and reused

**[Trade-off] Subjective definition of "engaging"** → Acceptable: Start with prompt-based heuristics; can iterate based on user feedback

## Migration Plan

Not applicable (new feature, no existing data to migrate).

Deployment strategy:
1. Add `highlight_service.py` and prompt template
2. Integrate into CLI as `--extract-highlights` flag
3. Update experiment workflow to optionally run highlight extraction
4. Document usage in README

Rollback: Simply remove flag/don't call service. No breaking changes.

## Open Questions

- Should we extract multiple highlights or just the single best one? → Start with 3-5, let caller select
- What's the minimum content length where highlight extraction makes sense? → Suggest 1000 words, make configurable
- Should highlights be embedded in editorial JSON or separate file? → Separate `highlights.json` for modularity
