# RootCause design system

The visual identity carries through the pitch deck, the live demo app,
and the full React frontend — same tokens everywhere, defined once in
`frontend/src/index.css` (`:root` custom properties).

## Color

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0e0b08` | Page background |
| `--panel` | `#17130e` | Cards |
| `--panel-border` | `#2c2419` | Card/input borders |
| `--text` | `#f4f1ea` | Primary text |
| `--text-dim` | `#9e988e` | Secondary text, labels |
| `--gold` | `#f2b84b` | Accent, CTAs, links, "weak" status |
| `--green` | `#7cc576` | "Mastered" status |
| `--red` | `#e2705f` | Errors, "fail" feedback |
| `--gray` | `#6b665d` | "Unseen" status |

Status color is never the only signal — every status also carries a
text label (`mastered`/`weak`/`unseen`) so it doesn't rely on color
perception alone (WCAG 1.4.1).

## Typography

- **Headings:** Instrument Serif (italic for emphasis words — "Root*Cause*",
  "*it works*") — matches the pitch deck exactly.
- **Body/UI:** Inter, 400/500/600/700.
- Scale: 11px (labels, uppercase, letter-spacing 0.08em) → 13–14px (body) →
  18–22px (section headers) → 28–38px (hero/brand).

## Spacing & shape

- Cards: 14px border radius, 20–24px padding, 14–16px gap between cards.
- Buttons/pills: fully rounded (999px), so primary/secondary/ghost are
  distinguishable by fill vs. outline vs. transparent, not just color.
- 8px spacing grid throughout (gaps, margins all multiples of 2/4/8).

## Components (all in `frontend/src/components/` + shared styles in `index.css`)

| Component | Pattern |
|---|---|
| `.card` | The one container primitive — every section is a card |
| `.pill` / `.badge` | Status/achievement chips, color + text, never color alone |
| `.progress-tile` | Colored left border (green/gold/gray) by mastery status |
| `button.primary` / `.cta` | Filled gold — the one primary action per screen |
| `button.ghost` | Outlined/transparent — secondary actions |
| `.feedback.pass` / `.feedback.fail` | Result banners, color + icon-equivalent text |
| `ConceptMap` | SVG, nodes sized/colored by mastery, positioned by prerequisite depth |

## Accessibility

- Sticky header stays usable at all viewport widths; nav wraps on mobile.
- All interactive elements are real `<button>`/`<a>` tags, never a `<div onClick>`
  with no keyboard path.
- Color is always paired with text (status pills, feedback banners).
- Voice input (Teach-Back) degrades to a clear text message, never a
  silent failure, on browsers without `SpeechRecognition`.
- **Known gap:** focus-visible outlines aren't custom-styled yet (relying
  on browser defaults) and no components have been run through an
  automated contrast checker — do that before calling this
  WCAG-compliant rather than WCAG-inspired.

## UX principles this app actually follows

1. **Every async action gets a response** — pass/fail banners, error
   banners, empty states ("No progress yet…", "Nothing left to queue
   up") — never a silent no-op.
2. **One primary action per screen** — the gold filled button is always
   the one thing you're meant to do next.
3. **Status is never a dead end** — a "weak" result always has a next
   step attached (a button, a related concept, a diagnosis chain).
