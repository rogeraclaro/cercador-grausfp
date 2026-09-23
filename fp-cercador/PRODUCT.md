# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

In priority order:

1. **Students** choosing Vocational Training (FP) studies — frequently on mobile, often unsure of the official name of the programme they want.
2. **Guidance counsellors (orientadors)** — using the tool live in sessions with students to show what exists and the path between levels.
3. **Educators and heads of studies** — sector-wide overviews, following other centres, exporting results (CSV) for reports and planning.

## Product Purpose

GrausFP is a single, instant search engine for the entire Spanish Vocational Training offer (Grados A–E under Ley Orgánica 3/2022), plus FPO courses from the SOC (Catalonia). It replaces scattered ministry pages, PDFs and regional sites with one filterable view by grade, professional family, level, region and free text. Success: a user finds the right programme — and the path to it — without leaving the site or reading a PDF.

## Positioning

The only tool that combines, in one place: all grades A–E together, search by occupation (job outcome → programmes), training itineraries A→B→C→D, automatic alerts on new offer, and centre follow-up. All data comes from official sources (todofp.es, BOE, ministry search engines, SOC) and is refreshed automatically.

## Operating Context

- Anonymous use covers search and consultation; registration (email or Google) unlocks favourites, alerts, centre follow-up and CSV export.
- Each result links to its official ministry fiche.
- Counsellors use it during face-to-face guidance sessions; students often on phones.
- Transactional email (alerts, notifications) is delivered via Brevo.
- Surfaces: search (`index.html`, with name / occupation / FPO modes), profile, alerts, centre follow-up, observatory (charts), data sources, changelog, marketing page ("Per què GrausFP?"), auth pages, admin.

## Capabilities and Constraints

- Stack: Flask backend (scrapers + API), static frontend in vanilla HTML/CSS/JS. Alpine.js 3.x (vendored, no CDN) is the only accepted frontend library; no other frameworks.
- Search filters the full catalogue (~12,900 records) instantly in the browser; results render paginated at 200 rows per page.
- Bilingual UI: Catalan and Spanish, switchable instantly (`i18n.js`).
- Responsive; deployed on a VPS (CloudPanel, Ubuntu 24.04).
- Terminology: "Grado A–E", "família professional", "itinerari", "fitxa oficial", "FPO".

## Brand Commitments

- Name: **GrausFP** (project name "Cercador FP España").
- Free, non-profit, oriented to public educational service. No paid tiers planned.
- Voice: direct, plain-language, helpful to non-experts; Catalan and Spanish on equal footing.

## Evidence on Hand

- Real, official catalogue data (thousands of records) and the observatory's live charts.
- Marketing copy: `docs/per-que-grausfp.md` / `frontend/per-que-grausfp.html`, including the comparison against ministry, buscadorcertificados and regional sites.
- No testimonials, usage figures, user counts or press exist. Do not fabricate any.

## Product Principles

1. **Official truth first** — every record traces back to an official source; never paraphrase data into claims it does not make.
2. **Instant** — results respond as you type, across the whole system at once.
3. **Paths, not just items** — show where a programme comes from and leads to, and which jobs it serves.
4. **Free to consult** — searching never requires an account; registration only adds follow-up tools.
5. **Two languages, one product** — Catalan and Spanish are equal; no untranslated literals.
