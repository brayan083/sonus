# Frontend

## Template System

All templates extend `base.html` which provides:
- Sidebar navigation with active state via `{% if active == 'transcribe' %}` etc.
- Topbar with title block and theme toggle button
- Content area
- Theme.js + per-page script/style blocks

### Templates

| Template | Page | Active |
|----------|------|--------|
| `index.html` | Upload form | `transcribe` |
| `result.html` | Transcription result (polls status) | `transcribe` |
| `history.html` | List of transcriptions | `history` |
| `summarize.html` | Single summary form | `summarize` |
| `summarize_multi.html` | Multi summary form | `summarize` |
| `summary_result.html` | Summary result (polls status) | `summarize` |
| `summary_history.html` | List of summaries | `summaries` |
| `settings.html` | App settings | `settings` |
| `placeholder.html` | Stub for unimplemented pages | — |

## CSS Architecture

- **`base.css`** — Design system: CSS custom properties (variables) for theming, sidebar, topbar, cards, buttons, badges, utility classes
- **`css/pages/*.css`** — Per-page styles

### Theme System

Dark theme is default (`data-theme="dark"` on `<html>`). Light theme via `data-theme="light"`.
Toggle handled by `theme.js` which persists preference in `localStorage`.

### Design Tokens (CSS Variables)

| Category | Variables |
|----------|-----------|
| Backgrounds | `--bg`, `--sidebar`, `--surface`, `--surface2` |
| Borders | `--border`, `--border-subtle` |
| Accent | `--accent` (#7c3aed), `--accent-hover`, `--accent-glow` |
| Colors | `--cyan`, `--fuchsia`, `--green`, `--yellow`, `--red` + dim variants |
| Text | `--text`, `--text-dim`, `--muted` |
| Shadows | `--shadow-sm`, `--shadow-md` |

### Component Classes

- `.card`, `.card-accent` — Content containers
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`, `.btn-sm` — Buttons
- `.badge`, `.badge-cyan`, `.badge-violet`, `.badge-muted` — Status badges
- `.glow-divider` — Gradient line separator
- `.gradient-text` — Purple-to-fuchsia gradient text

## JavaScript

- **`theme.js`** — Theme toggle, localStorage persistence
- **`pages/index.js`** — Upload form, active jobs indicator
- **`pages/result.js`** — Status polling, cancel button, display transcription segments
- **`pages/history.js`** — Selection, delete, rename, navigate to summarize
- **`pages/summary_result.js`** — Summary status polling, markdown rendering

### Polling Pattern

Result pages use `setInterval` to poll status endpoints every 1-2 seconds until status is `"done"` or `"error"`.

## App Branding

- Name: **Sonus**
- Font: Inter (Google Fonts)
- Logo: SVG speech bubble with sound wave lines, purple-to-fuchsia gradient
