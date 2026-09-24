---
name: GrausFP
description: One instant search across the entire Spanish Vocational Training offer, set like a printed public register.
colors:
  ink: "#1c1410"
  umber: "#755f51"
  parchment: "#f5ece2"
  seam: "#e8ddd4"
  paper: "#fdf8f2"
  white: "#ffffff"
  faded-ink: "#8a7060"
  ink-soft: "#3a2c24"
  success-tint: "#dcfce7"
  success-ink: "#166534"
  success-edge: "#bbf7d0"
  amber-tint: "#fef3c7"
  amber-ink: "#92400e"
  alert-tint: "#fef2f2"
  alert-edge: "#fecaca"
  alert-ink: "#991b1b"
  heart-red: "#c62828"
  pathway-tint: "#e8f4e8"
  pathway-ink: "#2a6e2a"
typography:
  display:
    fontFamily: "'DM Serif Display', serif"
    fontSize: "48px"
    fontWeight: 400
    lineHeight: 1.05
  title:
    fontFamily: "'DM Serif Display', serif"
    fontSize: "20px"
    fontWeight: 400
    letterSpacing: "-0.3px"
  display-sm:
    fontFamily: "'DM Serif Display', serif"
    fontSize: "30px"
    fontWeight: 400
    lineHeight: 1.05
  lead:
    fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "15px"
    fontWeight: 400
  body:
    fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "14px"
    fontWeight: 400
  input:
    fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "16px"
    fontWeight: 400
  body-small:
    fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "13px"
    fontWeight: 400
  label:
    fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.07em"
  mono:
    fontFamily: "'Geist Mono', monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  hairline: "2px"
  tag: "3px"
  control: "4px"
  field: "6px"
  pill: "12px"
spacing:
  gutter: "48px"
  gutter-mobile: "16px"
  cell-y: "13px"
  cell-x: "16px"
components:
  search-input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "14px 18px 14px 50px"
    typography: "{typography.body}"
  mode-toggle:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "8px 20px"
  mode-toggle-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "5px 12px"
  button-secondary-hover:
    backgroundColor: "{colors.seam}"
  topbar-button:
    backgroundColor: "transparent"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
    padding: "5px 14px"
  topbar-button-primary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
  select:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "5px 12px"
  badge-new:
    backgroundColor: "{colors.success-tint}"
    textColor: "{colors.success-ink}"
    rounded: "{rounded.tag}"
    padding: "1px 6px"
  badge-old-plan:
    backgroundColor: "{colors.amber-tint}"
    textColor: "{colors.amber-ink}"
    rounded: "{rounded.tag}"
    padding: "2px 6px"
  badge-centres:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  badge-centres-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
  table-header:
    backgroundColor: "{colors.parchment}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: "11px 16px"
---

# Design System: GrausFP

## Overview

**Creative North Star: "The Official Register"**

GrausFP looks like a public catalogue printed on warm paper: cream stock, near-black ink, a serif masthead and plain, dense tables. The whole visual system exists to make official data feel trustworthy and easy to consult. There is no decoration competing with the records. Hierarchy comes from ink weight, rules and type contrast, not from colour or depth.

The surface is compact and meant for scanning. Body text is 14px, secondary text 13px, and results sit in a full-width table with uppercase column headers over a heavy ink rule. The dark top bar works as a masthead. Beneath it, a serif headline and one large, ink-bordered search field make the only real invitation on the page. Everything after that is register: tabs, filters, rows.

Colour is used sparingly and always to say something. The warm neutrals carry the page. Small tinted tags mark the status of a record (new plan, old plan, pathway), and red is reserved for favourites and errors.

**Key Characteristics:**
- Warm paper background with near-black warm ink; no pure greys in the core palette.
- A serif (DM Serif Display) only for the masthead and page headline; DM Sans for everything else; Geist Mono for official codes.
- Heavy 2px ink rules and borders give structure; shadows are almost absent.
- Small, tight radii (2–6px); the only pill shape is the centres badge.
- Dense, scannable tables with uppercase micro-labels.

## Colors

A warm, paper-and-ink neutral system with a handful of small, semantic tints.

### Primary
- **Register Ink** (`ink`): the masthead band, all primary text, active tabs, the active mode button, the search field's border and the heavy rule under the table header. It is the brand colour: authority comes from ink, not from a hue.

### Links
Links are Register Ink with an Umber underline (2px offset) that darkens to Ink on hover. There is no link hue: a link reads as ink that can be followed. List-style links (centre names) stay un-underlined at rest and underline on hover.

### Neutral
- **Umber** (`umber`): secondary text. Hero subtitle, family and level columns, result counts, official codes, filter labels, link underlines, and the focus outline. Tuned to pass AA on Paper (5.7:1) and Parchment (5.1:1).
- **Parchment** (`parchment`): the filter bar, table header, row hover and favourite-row highlight, and informational notes.
- **Seam** (`seam`): 1px borders and row dividers; hover state for secondary buttons.
- **Paper** (`paper`): page background.
- **White** (`white`): raised working surfaces: search field, tabs bar, table body, selects, secondary buttons; text on ink.
- **Faded Ink** (`faded-ink`): placeholder text, the resting favourite heart and decorative icon strokes (4.6:1 on white).
- **Soft Ink** (`ink-soft`): hover step for filled ink buttons.

### Semantic tints
- **New plan / success** (`success-tint`, `success-ink`, `success-edge`): the "NOU" badge and the active follow-centre button.
- **Old plan** (`amber-tint`, `amber-ink`): the old-plan (LOE) badge.
- **Pathway** (`pathway-tint`, `pathway-ink`): itinerary B badges.
- **Alert** (`alert-tint`, `alert-edge`, `alert-ink`): error and warning banners.
- **Heart Red** (`heart-red`): the favourite heart and the favourites filter, nothing else (4.8:1 on Parchment).

### Named Rules
**The Ink Carries Authority Rule.** Emphasis comes from Register Ink: weight, a heavier rule, or an inverted ink block. Never introduce a bright brand hue to make something "primary".

**The Tint Means Status Rule.** Every tinted tag (green, amber, pathway green) states a fact about a record. A tint without a meaning is not allowed.

## Typography

**Display Font:** DM Serif Display (with serif)
**Body Font:** DM Sans (with -apple-system, BlinkMacSystemFont, sans-serif)
**Label/Mono Font:** Geist Mono (with monospace), for official codes only

**Character:** A bookish, high-contrast serif gives the masthead the voice of a printed register. The neutral grotesque underneath keeps every record plain and readable.

### Hierarchy
- **Display** (400, 48px, line-height 1.05; 30px under 768px): the page headline in the hero. One per page.
- **Title** (400, 20px, -0.3px tracking): the GrausFP wordmark in the top bar.
- **Body** (400–500, 14px): default text, tabs, mode buttons; programme names in the table at weight 500. The search field uses 16px so iOS does not zoom.
- **Lead** (400, 15px; 14px under 768px): the hero subtitle and occupation card titles.
- **Input** (400, 16px): search and, on touch devices, every select and text field, so iOS Safari never zooms on focus.
- **Body Small** (400, 13px): filters, family column, counts, secondary buttons. It is the most common size in the product.
- **Label** (600, 11px, 0.07em, uppercase): table column headers and small status badges. Also the "partial accreditation of" note beside programme names, in Umber at full opacity.
- **Mono** (400, 12px): official programme codes, in Umber.

### Named Rules
**The Role Scale Rule.** Every font size is a `--fs-*` token (`display`, `display-sm`, `title`, `lead`, `body`, `small`, `label`, `mono`, `input`). No `em` or `rem` sizes that compound inside other sized elements, and no visible text under 11px.

**The One Serif Rule.** The serif appears only in the wordmark and page headlines. Tables, controls and badges are always set in DM Sans.

## Layout

The layout is a single full-width column of stacked bands: the ink masthead (52px tall), the hero with the search field, the grade tabs bar, the parchment filter bar, then the results table. Every band uses the same 48px horizontal gutter; the search field is capped at 640px. Under 768px the gutter becomes 16px, the headline drops to 30px, the filter bar stacks vertically and the grade tabs scroll horizontally. Table cells use 13px × 16px padding. All results render in one list with no pagination.

## Elevation & Depth

The system is flat. Depth is expressed with bands of colour (ink masthead, white working surfaces on paper, parchment bars) and with rules, not shadows. The only shadow belongs to modal dialogs, which float over a dimmed backdrop.

### Shadow Vocabulary
- **Modal lift** (`box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18)`): the shared modal pattern (`.centres-modal`) only.

### Named Rules
**The Rules Not Shadows Rule.** Separation between regions comes from a 1px Seam border or a 2px Ink rule. Shadows are reserved for surfaces that float above the page.

## Shapes

Corners are small and utilitarian: 2px on the results table, 3px on tags and language buttons, 4px on selects and secondary buttons, 6px on the search field and mode buttons. Borders do the structural work. Primary controls use a 2px Register Ink stroke; secondary controls use a 1px Seam stroke. The centres badge (12px radius) is the only pill shape, and the heart icon the only circular one.

## Components

### Search Field
The front door of the product: a white field with a 2px Register Ink border, 6px radius, a leading search icon, 16px text and Faded Ink placeholder. Focus adds a 2px Umber outline offset by 2px.

### Mode Toggle
Search modes (name / occupation / FPO) are outlined ink buttons: 2px Ink border, 6px radius, 14px weight-500 text. Hover adds a 5% black wash; the active mode inverts to Ink with white text.

### Grade Tabs
A white bar of text tabs in Umber. The active tab switches to Ink, weight 600, with a 2.5px Ink underline. Colour and underline transitions take 0.15s.

### Buttons
- **Secondary** (documents, follow-centre): white fill, 1px Seam border, 4px radius, 12px text; hover fills with Seam or Parchment. The active follow state switches to the success tint.
- **Top bar buttons** (auth): transparent with a translucent white border on the Ink band; the primary one is filled white with Ink text. Language buttons (CA/ES) are 11px bold uppercase chips on the same band.
- **Favourite heart:** hidden until the row is hovered, grey at rest, Heart Red when hovered or active.

### Filters
A Parchment bar with an Umber label and white selects (1px Seam border, 4px radius, 13px). Focus uses the shared Umber outline.

### Results Table (signature)
The heart of the register. White body inside a 1px Seam frame, with a Parchment header row closed by a 2px Ink rule. Headers are uppercase 11px labels. Rows are divided by Seam hairlines and wash to Parchment on hover. The name column is weight 500 in Ink. Family and level sit in Umber, and codes in Umber Geist Mono. Grade and level columns are centred. Sortable headers show a faint arrow that turns solid when active.

### Status Badges
Small inline tags beside programme names: "NOU" (success tint, 10px bold uppercase), old plan (amber tint, 11px bold), itinerary B (pathway tint), and the centres count (an Ink outline pill on white that inverts to solid Ink on hover, the same vocabulary as the mode toggle).

## Do's and Don'ts

### Do:
- **Do** define tokens once, in `frontend/site.css` (linked by every page before its own `<style>`), and use them for every colour: core (`--dark`, `--warm`, `--warm2`, `--border`, `--bg`, `--white`, `--faded`, `--ink-soft`) and semantic (`--ok-*`, `--amber-*`, `--alert-*`, `--path-*`, `--heart`, `--scrim`).
- **Do** build hierarchy with Register Ink: weight 500–600, a 2px Ink rule, or an inverted Ink block.
- **Do** keep 13–14px DM Sans as the working size and reserve the serif for the wordmark and headline.
- **Do** use the shared focus treatment: `outline: 2px solid var(--warm); outline-offset: 2px`.
- **Do** keep the 48px / 16px gutter consistent across every band.

### Don't:
- **Don't** introduce a link or accent hue (the old `#1a73e8` blue was removed on purpose); new accents come from the warm neutrals or an existing semantic tint.
- **Don't** introduce cool greys (`#666`, `#888`, `#ccc`); use Umber, Seam or Faded Ink instead.
- **Don't** add shadows to cards, rows or bars; shadows belong only to floating modals.
- **Don't** use emoji as icons. Icons are inline SVG, 2px round stroke, `currentColor` (heart, bell, phone share one vocabulary).
- **Don't** rely on a middle dot to separate wrapped meta items; use flex `gap`, so a separator never lands at the start of a line.
- **Don't** use tinted badges decoratively; every tint must mark a real record status.
- **Don't** round corners beyond 6px except for the existing centres pill.
