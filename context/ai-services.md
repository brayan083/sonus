# AI Services

## Transcription (`transcriber.py`)

### Engines

| Engine | Function | Device | Use Case |
|--------|----------|--------|----------|
| OpenAI Whisper (local) | `transcribir()` | MPS (Apple Silicon) or CPU | Legacy, synchronous |
| faster-whisper | `transcribir_stream()` | CPU only (ctranslate2) | Default — streams segments via callback |
| OpenAI Whisper API | `transcribir_api()` | Remote | Cloud option, auto-splits files >24MB |

### Models

Local models (cached in `~/.cache/whisper/`): `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`, `large-v3-turbo`

Default: `large-v3-turbo`. Plus `whisper-api` for OpenAI cloud.

Only locally installed models are shown in the UI (detected by checking `~/.cache/whisper/{name}.pt`).

### Segment Cleaning (`limpiar_segmentos`)

Post-processing pipeline applied to all transcriptions:
1. Merge consecutive segments with identical text
2. Remove short segments (<2s) containing noise words ("x.", "bien.", etc.)
3. Remove segments with empty/punctuation-only text
4. Merge nearby short segments (gap <0.5s, both texts <30 chars)

### Languages

12 supported: es, en, fr, de, pt, it, ja, zh, ko, ru, ar, auto-detect.

## Summarization (`ai_service.py`)

### Providers

| Provider | Function | Config |
|----------|----------|--------|
| Ollama | `summarize_ollama()` | `ollama_url` + `ollama_model` (default: llama3.2) |
| Gemini | `summarize_gemini()` | `gemini_api_key` + `gemini_model` |

### Summary Types

| Key | Label |
|-----|-------|
| `general` | Resumen general |
| `class_notes` | Apuntes de clase |
| `study_guide` | Guía de estudio |
| `combined` | Combinado (resumen + apuntes + guía) |

### Summary Lengths

- `short` — 2-3 paragraphs
- `medium` — 3-6 paragraphs
- `detailed` — Full development with context

### Gemini Models Available

- `gemini-2.0-flash` — Fast, economical
- `gemini-2.0-flash-lite` — Faster, cheaper
- `gemini-2.5-flash-preview-05-20` — Better quality
- `gemini-2.5-pro-preview-05-06` — Maximum quality

### Prompt Structure

All prompts include a style guide enforcing:
- `##` / `###` headings for sections
- Full paragraphs over bullet lists
- Bullet lists only for short enumerations
- Natural, article-like writing style
