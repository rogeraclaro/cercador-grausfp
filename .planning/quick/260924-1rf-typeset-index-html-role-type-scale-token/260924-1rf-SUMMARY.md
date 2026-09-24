---
status: complete
quick_id: 260924-1rf
---
# Typeset index.html

The GSD executor failed mid-run (API 429, monthly spend limit) after Task 1. The orchestrator finished the work inline: 9 `--fs-*` role tokens, all font sizes migrated (~65 declarations), `.textpetit` 7.6px/60% -> 11px/100%, compounding em sizes removed, iOS focus-zoom rule (16px on `pointer: coarse`), tabular figures, Google Fonts URL trimmed (DM Sans 300 and Geist Mono 500 dropped, real DM Sans italic added).

Verified in a real browser at 1280/390/320: computed sizes per role, no visible text < 11px, no horizontal overflow, touch inputs >= 16px, italic face loaded, no console errors.

Left as is: `.centres-modal-close` 18px (glyph). Commit: see git log ("style(index): escala tipogràfica...").
