---
name: whisper-bray-frontend
description: >
  Design system and frontend development guide for the Whisper Bray Flask transcription app.
  USE THIS SKILL whenever the user asks to change, improve, add, or redesign any UI element,
  template, page, component, color, style, or visual aspect of the Whisper Bray app.
  Trigger on prompts like: "cambia el diseño", "mejora la UI", "agrega un componente",
  "nueva pantalla", "actualiza los colores", "hazlo más moderno", or any request that involves
  touching app/templates/ or visual/CSS changes in this project.
---

# Whisper Bray — Frontend Design System

## Project context

Flask app that transcribes audio/video using Whisper. Templates are Jinja2 files in `app/templates/`, all extending `base.html`. There is no build step — styles live in `<style>` blocks within each template. No external CSS frameworks.

Template structure:
- `base.html` — layout shell: sidebar + topbar + content area. All CSS variables and shared component styles live here.
- `index.html` — upload page (`active='transcribe'`)
- `result.html` — polling + transcription display (`active=` not set)
- `history.html` — list of past transcriptions
- `placeholder.html` — stub for future pages

**Rule: any change to the design system (colors, typography, shared components) must be made in `base.html`. Page-specific styles go in `{% block head %}` of each template.**

---

## Color Palette — Vibrant Dark Theme

The app uses a dark theme. These are the canonical CSS variables. Always use these variable names — never hardcode hex values in new styles.

```css
:root {
  /* Backgrounds */
  --bg:         #0a0f1e;   /* near-black with blue undertone */
  --sidebar:    #0d1426;   /* slightly lighter sidebar */
  --surface:    #111827;   /* card / panel background */
  --surface2:   #1a2235;   /* elevated surface, hover states */

  /* Borders */
  --border:     #1e2d45;
  --border-subtle: #162030;

  /* Accent — Electric Violet (primary action) */
  --accent:        #7c3aed;   /* violet-600 */
  --accent-hover:  #6d28d9;   /* violet-700 */
  --accent-glow:   rgba(124, 58, 237, 0.25);

  /* Secondary accent — Cyan (highlights, badges, active states) */
  --cyan:       #06b6d4;
  --cyan-dim:   rgba(6, 182, 212, 0.15);

  /* Tertiary — Fuchsia (decorative, gradients) */
  --fuchsia:    #d946ef;
  --fuchsia-dim: rgba(217, 70, 239, 0.12);

  /* Success / warning / error */
  --green:      #10b981;
  --green-dim:  rgba(16, 185, 129, 0.12);
  --yellow:     #f59e0b;
  --red:        #ef4444;
  --red-dim:    rgba(239, 68, 68, 0.10);

  /* Text */
  --text:       #e2e8f0;
  --text-dim:   #94a3b8;
  --muted:      #475569;
}
```

### Color usage rules

- Primary actions (main CTA button, active nav indicator): `--accent` (violet)
- Informational highlights, timestamps, badges with counts: `--cyan`
- Decorative elements, gradient endpoints, special callouts: `--fuchsia`
- Never use more than 2 accent colors on the same screen
- Gradients: always go from `--accent` → `--fuchsia` or `--accent` → `--cyan` (diagonal or horizontal, never vertical on text)

---

## Typography

Font stack: `'Inter', system-ui, -apple-system, sans-serif` — add Inter from Google Fonts in `base.html` head if not already present.

| Use                | Size       | Weight | Color        |
|--------------------|------------|--------|--------------|
| Page title (h1)    | 1.5rem     | 700    | `--text`     |
| Section heading    | 1rem       | 600    | `--text`     |
| Label / uppercase  | 0.7rem     | 600    | `--muted`    |
| Body               | 0.875rem   | 400    | `--text`     |
| Small / meta       | 0.8rem     | 400    | `--text-dim` |
| Monospace (times)  | 0.82rem    | 400    | `--text-dim` |

---

## Component Catalogue

When building or modifying UI, use these components as the foundation. Update the catalogue here if a new reusable component is added to `base.html`.

### Buttons

```html
<!-- Primary -->
<button class="btn btn-primary">⬆️ Acción</button>

<!-- Secondary -->
<button class="btn btn-secondary">Ver historial</button>

<!-- Ghost (for inline/text actions) -->
<button class="btn btn-ghost">Cancelar</button>
```

CSS to add to `base.html` for `btn-ghost`:
```css
.btn-ghost { background: transparent; color: var(--text-dim); border: 1px solid var(--border); }
.btn-ghost:hover { background: var(--surface2); color: var(--text); }
```

### Cards

```html
<!-- Standard card -->
<div class="card"> ... </div>

<!-- Accented card (use for featured/important content) -->
<div class="card card-accent"> ... </div>
```

CSS for `card-accent`:
```css
.card-accent {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent-glow), 0 4px 24px var(--accent-glow);
}
```

### Badges

```html
<span class="badge badge-cyan">Nuevo</span>
<span class="badge badge-violet">Activo</span>
<span class="badge badge-muted">Pronto</span>
```

CSS to add to `base.html`:
```css
.badge {
  display: inline-flex; align-items: center;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem; font-weight: 600;
}
.badge-cyan    { background: var(--cyan-dim); color: var(--cyan); }
.badge-violet  { background: var(--accent-glow); color: #a78bfa; }
.badge-muted   { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }
```

### Gradient text (use sparingly for headings/highlights)

```css
.gradient-text {
  background: linear-gradient(135deg, var(--accent), var(--fuchsia));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

### Subtle glow divider

```css
.glow-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  margin: 1.5rem 0;
  opacity: 0.4;
}
```

### Stat card

```html
<div class="stat-card">
  <span>Segmentos</span>
  <strong>142</strong>
</div>
```

CSS update (replace existing `.stat-card` in `result.html`):
```css
.stat-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.9rem 1.25rem;
  min-width: 110px;
}
.stat-card span { color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; display: block; margin-bottom: 0.35rem; }
.stat-card strong { font-size: 1.3rem; font-weight: 700; color: var(--cyan); }
```

---

## Sidebar design rules

The sidebar must always:
- Use a thin left border on the active item in `--accent` color
- Show `--cyan` for the active item's icon (not the entire text)
- Use `badge-cyan` for counts, `badge-muted` for "Pronto" labels
- Never add background images or gradients to the sidebar itself

Active item CSS (already in `base.html`, reference only):
```css
.sidebar-item.active { color: var(--text); background: rgba(124,58,237,0.1); }
.sidebar-item.active::before { background: var(--accent); }
```

---

## Spacing system

Use multiples of 4px. Prefer these Tailwind-equivalent values:
- `0.25rem` (4px) — micro gap
- `0.5rem` (8px) — tight spacing
- `0.75rem` (12px) — compact
- `1rem` (16px) — default
- `1.5rem` (24px) — section spacing
- `2rem` (32px) — page padding
- `3rem` (48px) — large section gap

---

## Interaction & animation

Keep animations subtle and fast:
```css
/* Standard transition */
transition: background 0.15s, color 0.15s, border-color 0.15s, box-shadow 0.15s;

/* Loading spinner — use the existing .spinner class from result.html */

/* Hover glow on interactive cards */
.card-interactive:hover {
  border-color: var(--border);
  box-shadow: 0 0 0 1px var(--border), 0 8px 32px rgba(0,0,0,0.3);
  transform: translateY(-1px);
  transition: transform 0.15s, box-shadow 0.15s;
}
```

Never use transitions longer than 0.3s. No bounce animations.

---

## Page layout patterns

### Two-column (used in index.html)
```html
<div style="display:grid; grid-template-columns: 1fr 280px; gap: 1.5rem; max-width: 860px;">
  <div class="card"><!-- main --></div>
  <div class="card"><!-- sidebar info --></div>
</div>
```

### Single column with max-width
```html
<div style="max-width: 860px;">...</div>
```

### Stats row
```html
<div style="display:flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem;">
  <div class="stat-card">...</div>
</div>
```

---

## Step-by-step: how to make a UI change

1. **Identify scope** — is this a change to the shared layout/design system (`base.html`) or page-specific?
2. **Check the component catalogue above** — use existing components before inventing new ones.
3. **Use CSS variables** — never hardcode colors.
4. **Place styles correctly** — shared → `base.html` `<style>`, page-specific → `{% block head %}` of the template.
5. **Test the active state** — when adding/modifying nav items, verify the `active` class logic in the template.
6. **Preserve the Jinja2 blocks** — never remove `{% block title %}`, `{% block topbar %}`, `{% block head %}`, `{% block content %}`.
7. **Check all templates** — if you changed `base.html`, quickly scan the other templates to confirm nothing broke visually.

---

## Anti-patterns to avoid

- Do NOT use Tailwind class names (no build step)
- Do NOT add external CSS framework imports unless explicitly asked
- Do NOT hardcode colors — always use `var(--token-name)`
- Do NOT add `!important` unless debugging a very specific override
- Do NOT use `position: fixed` for content (the layout already handles overflow)
- Do NOT make the sidebar wider than 240px or narrower than 200px
- Do NOT put `<style>` tags inside `{% block content %}` — use `{% block head %}` instead
