# Phase 7: Microanimacions GSAP - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-28
**Phase:** 07-microanimacions-gsap
**Areas discussed:** Result rows, Alert modal vs toast, Duration exception, Phase scope, Itinerari surfaces

Pre-decided by owner in the request: GSAP exception in CLAUDE.md, vendored core only, license check, per-page loading, gsap.matchMedia() for reduced motion, works without GSAP, 150–250 ms, nothing delays results/interaction.

---

## Result rows — trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Search + filters | Cascade when result set changes by text (post-debounce) or filter | ✓ |
| Also on pagination | Pages 2, 3… also cascade | |
| Also on initial load | First paint also cascades | |

## Result rows — motion

| Option | Description | Selected |
|--------|-------------|----------|
| Fade + y 8px, 20 ms stagger | opacity 0.4→1, y 8→0, 180 ms expo.out, ≈360 ms total | ✓ |
| Fade only, 15 ms | opacity 0.4→1, 150 ms | |
| Table clip-path | inset 100%→0 in 200 ms, no per-row stagger | |

## Alert modal vs toast

| Option | Description | Selected |
|--------|-------------|----------|
| Keep modal + animate ✓ | scale 0.96→1 + ✓ pop in --path-ink | ✓ |
| Convert to toast | Slide-in toast as in video, auto-dismiss | |
| Only the ✓ | No modal entrance change | |

## Duration exception

| Option | Description | Selected |
|--------|-------------|----------|
| Bounded exception | Each tween 150–250 ms; sequence ≤ 600 ms | ✓ |
| Strict 250 ms total | No sequence > 250 ms | |
| As in video | 700 ms draws, 1 s counters | |

## Phase scope

| Option | Description | Selected |
|--------|-------------|----------|
| One phase, plans per page | P1 GSAP+index, P2 observatori, P3 itinerari | ✓ |
| Only index.html now | Rest deferred | |
| index + observatori | Itinerari deferred | |

## Itinerari surfaces

| Option | Description | Selected |
|--------|-------------|----------|
| Timeline SVG only | Graf unchanged, tree no animation | ✓ |
| Timeline + Graf | Graf via Cytoscape ele.animate() | |
| Timeline + Graf + Tree | Plus tree branch cascade | |

## Claude's Discretion

- Interrupting in-flight cascade on new query (kill previous).
- Shared helper shape, Alpine change-detection mechanism, exact eases from composition vocabulary, `?v=` cache busting.

## Deferred Ideas

- Cytoscape Graf animation; tree branch cascade; alert-as-toast.
