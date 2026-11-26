---
version: 1
slug: "frontend-com-funciona-html"
primary_target: "frontend/com-funciona.html"
related_targets: []
---

# Surface brief — frontend/com-funciona.html

Scope: one public page, unlinked for now (noindex). Visitor mode: **Read**.
Audience: curious visitors, guidance counsellors, institutions. Job: understand where GrausFP's data comes from, how it is kept fresh, what happens during a search, what happens when a source is wrong, and what is stored about them. Action: go to the search, or on to the project page.
Proof/content: real figures from the 2026-11-26 refresh (12,989 grade records; 7,557 SEPE specialties; ~950 FPO courses; 13 sources), real examples (SSCE22, IFCD0025, a Grau D cycle), real corrections (20 certificate durations, 399 false UC links). No usage numbers, no testimonials.
Constraints: vanilla HTML/CSS/JS, no GSAP on this page, inline SVG, Catalan only in this first version, prefers-reduced-motion respected, inherits DESIGN.md ("The Official Register").

## Direction contract

THESIS: The page is a set of plain questions a visitor would actually ask, each answered by a diagram you can operate. It refuses the feature-card grid and the "how it works in 3 steps" strip.

OWN-WORLD: Warm paper, near-black ink, 1px seam rules and 2px ink rules, serif display questions set very large, mono only for official codes and measures. Diagrams are ink line drawings on paper; one full-bleed ink band carries the weekly refresh. Tints only where a record has a status.

STORY: The visitor learns that every record traces to an official source, that the register is re-read every week and survives failures, that a search runs over grades and specialties at once, and that errors in sources are corrected in the open. They leave trusting the data and open the search.

FIRST VIEWPORT: Left, the page title as one large serif line and a two-sentence lead; right, a "follow a record" path (source → read → check → register → screen) already drawn, with three real records to choose from; choosing one lights its own route. No hero metric.

FORM: Reader's questions as the spine (index 5 of the ranked list, the dealt lead), with "follow one record" (index 1) as the signature interaction and the week timeline (index 4) as the answer to the freshness question. Seed key 2e6de1d6 (degraded roll: no challengers).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
