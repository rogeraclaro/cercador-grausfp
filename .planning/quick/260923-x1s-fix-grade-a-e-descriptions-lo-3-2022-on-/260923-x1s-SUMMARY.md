---
phase: quick-260923-x1s
plan: 01
subsystem: ui
tags: [i18n, copy, docs, frontend]

requires: []
provides:
  - "Grade A–E table on per-que-grausfp.html (CA/ES) matching LO 3/2022 (BOE-A-2022-5139) instead of the old cycles/microcredentials mapping"
  - "Itinerary feature sentence rewritten to the real A→B→C→D path (acreditació parcial → certificat de competència → certificat professional → cicle formatiu)"
  - "Grau E FAQ answer corrected to state the 36 specialization courses already in the data, with GM/GS access, dropping the 'new modality still deploying' premise"
  - "fonts.html row 2 detail corrected to describe Grado D as cicles formatius and Grado E as cursos d'especialització"
  - "docs/per-que-grausfp.md mirrors all the above"
affects: [per-que-grausfp.html, fonts.html, i18n.js]

actuals:
  tokens: 4966
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - fp-cercador/frontend/i18n.js
    - fp-cercador/frontend/per-que-grausfp.html
    - fp-cercador/frontend/fonts.html
    - fp-cercador/docs/per-que-grausfp.md

key-decisions:
  - "Grade example column keeps the exact Spanish record names as they appear in ofertes.json for both CA and ES, per the plan's Target Copy table."

requirements-completed: [quick-260923-x1s]

duration: 15min
completed: 2026-09-23
status: complete
---

# Quick Task 260923-x1s: Fix grade A–E descriptions (LO 3/2022) Summary

**Corrected the public "Per què GrausFP?" page and fonts.html so the A–E grade table, itinerary sentence, and Grau E FAQ match Ley Orgánica 3/2022 and the app's own data (ofertes.json), in Catalan and Spanish, plus the docs markdown mirror.**

## Performance

- **Duration:** 15min
- **Tasks completed:** 2/2
- **Files changed:** 4

## Accomplishments

- Replaced the ten `perque.grau.{a-e}.{nom,ex}` values in `i18n.js` (CA + ES blocks), the static HTML fallbacks in `per-que-grausfp.html`, and the table rows in `docs/per-que-grausfp.md` with the correct LO 3/2022 grade names (Acreditació parcial de competència, Certificat de competència, Certificat professional, Cicles formatius de grau bàsic/mitjà/superior, Cursos d'especialització) and real example names from the data.
- Rewrote `perque.feat.itineraris.desc` (CA + ES, i18n.js + HTML + docs) to describe the real A→B→C→D path instead of the old Grau Bàsic→Mitjà→Superior→Especialització chain.
- Rewrote `perque.faq.3.q`/`.a` (CA + ES, i18n.js + HTML + docs) to state the 36 specialization courses already in the dataset with GM/GS access, removing the "nova modalitat en desplegament" premise.
- Corrected `fonts.r2.detall` (CA + ES, i18n.js + fonts.html) to describe Grado D as cicles formatius and Grado E as cursos d'especialització.

## Task Execution

**Task 1 (tracer):** Grade table A–E end-to-end (i18n.js CA/ES → HTML fallbacks → docs mirror). Confirmed RED baseline with `verify-copy.cjs grau`, applied the ten key changes across the three files, confirmed GREEN.

**Task 2 (auto):** Itinerary sentence, Grau E FAQ, fonts.html row 2, docs mirror updates for the remaining four keys. Ran full gate (`node --check`, `verify-copy.cjs all`, legacy-copy rg scan) — all passed. Single commit created.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `node --check frontend/i18n.js` — passed.
- `verify-copy.cjs all` — `OK (all): all grade copy checks pass`.
- `rg` scan for legacy phrases (Microcredencial, Grau Bàsic a Grau Mitjà, etc.) in the four touched files — no matches.
- `git show --stat HEAD` — lists exactly the four app files, no unrelated files staged.
- Commit message is exactly `fix(perque): corregeix la definició dels graus A–E segons la LO 3/2022`, no Co-Authored-By or Claude-Session trailer.
- Not pushed, not deployed.

## Self-Check: PASSED

- FOUND: fp-cercador/frontend/i18n.js
- FOUND: fp-cercador/frontend/per-que-grausfp.html
- FOUND: fp-cercador/frontend/fonts.html
- FOUND: fp-cercador/docs/per-que-grausfp.md
- FOUND commit: 584ba22
