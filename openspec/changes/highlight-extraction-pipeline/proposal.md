## Why

Long-form content like podcasts and articles often lack engaging visual entry points. Users need compelling "thumbnail" content to decide whether to engage with the full piece, but manually selecting highlight quotes is time-consuming and inconsistent. An automated highlight extraction pipeline can surface the most captivating sentences to serve as visual hooks.

## What Changes

- Add a new `highlight_service.py` module that extracts engaging sentences from long-form content
- Create a dedicated prompt template for highlight extraction that identifies attention-grabbing, quotable sentences
- Integrate highlight extraction into the existing pipeline, making it available as an optional preprocessing step
- Store extracted highlights in the experiment output structure alongside chunks and editorial data
- Add CLI support for running highlight extraction independently or as part of the full pipeline

## Capabilities

### New Capabilities
- `highlight-extraction`: Extracts the most engaging sentences from long-form content (articles, podcasts) to use as thumbnails or preview content. Uses LLM-based analysis to identify quotable, attention-grabbing sentences.

### Modified Capabilities
<!-- No existing capabilities are being modified -->

## Impact

- **New files**: `src/narrio/highlight_service.py`, `assets/process/prompt/HighlightExtract.md`
- **Modified files**: `src/narrio/cli.py` (add highlight extraction command), `src/narrio/experiment.py` (integrate highlight step)
- **Dependencies**: Reuses existing OpenRouter/LLM integration infrastructure
- **Output structure**: Adds `highlights.json` to experiment output directories
