---
status: testing
phase: 07-microanimacions-gsap
source: [07-VERIFICATION.md]
started: 2026-10-28T00:00:00Z
updated: 2026-10-28T00:00:00Z
---

## Current Test

number: 1
name: itinerari.html C→D dashed/dotted links in Safari and Firefox
expected: |
  On a grau C itinerary with C→D links (production), the dashed and dotted connectors draw in and keep their pattern in Safari and Firefox; none disappear or flicker.
awaiting: user response

## Tests

### 1. itinerari.html C→D dashed/dotted links in Safari and Firefox
expected: The SVG-mask draw-in works in Safari and Firefox as in Chrome; dashed/dotted links stay visible with their pattern after the animation.
result: [pending]

### 2. observatori.html bars with real production data
expected: On https://grausfp.es/observatori.html the five "Distribució per grau" bars grow to their correct widths and the numbers count up to the real final values within ~0.5 s.
result: [pending]

### 3. observatori.html in forced-colors (Windows High Contrast)
expected: With forced colors active, no doubled numbers are visible during the count-up (or the overlap is acceptable to the owner).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
