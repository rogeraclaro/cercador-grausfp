---
phase: 07-microanimacions-gsap
reviewed: 2026-10-28T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - fp-cercador/frontend/motion.js
  - fp-cercador/frontend/index.html
  - fp-cercador/frontend/i18n.js
  - fp-cercador/frontend/observatori.html
  - fp-cercador/frontend/itinerari.html
  - fp-cercador/scripts/motion_smoke.py
  - fp-cercador/scripts/check_motion_static.sh
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-10-28
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

I reviewed the phase-07 diff (`cb8b175..HEAD`) for `motion.js`, the three animated pages, the i18n tick change and the two verification scripts. I also ran both scripts. `check_motion_static.sh` reports 15 ok / 0 failed, and `motion_smoke.py` reports 21 passed / 0 failed. The vendored GSAP file was not reviewed.

I found no critical issues. There is no injection path, no hidden initial state (D-05), and no plugin use. The guard in `motion.js` (matchMedia plus no-op without GSAP) behaves as designed. Alpine's `$watch` callback order (microtask after the `x-for` flush) holds, and `resetPage()` runs on `@input` before the debounced `search` changes, so the row-cascade key is computed against page 1.

The two warnings are about robustness: what happens when an animation builder fails, and a test threshold with too little margin. The info items are minor.

## Warnings

### WR-01: GFPMotion.play() failure path does not undo DOM mutations made by the builder

**File:** `fp-cercador/frontend/motion.js:31-34` (affects `itinerari.html:985-1042` and `observatori.html:371-402`)
**Issue:** The builders mutate the DOM directly, outside tweens, and only register their cleanup by *returning* a function at the very end. In `play()`, if `build` throws, `try/catch` swallows the exception, so the cleanup is never returned and never registered. `c.revert()` then only rewinds tweens.

- In `animateTimeline`, the `t-part` / `t-old` paths get `mask="url(#tlmN)"` and a `<defs>` with a mask is inserted before any later statement can throw. The mask's `reveal` path starts with an inline `stroke-dashoffset:1`. If the builder throws after that (for example at `vm.$refs.tl.querySelectorAll(...)` or `getComputedStyle`), revert restores the reveal path to offset 1. The dashed C→D segments then stay fully masked, which is permanently invisible.
- In `animateBars`, `val.style.color = 'transparent'` is applied before the count tween is created, so a later throw leaves the value text invisible.

This breaks the phase contract that the page behaves exactly as before when the animation fails. The trigger is currently hypothetical, since I found no concrete throwing path today. A future edit to a builder would make it real, and `play()` is the one place that can guarantee the invariant.
**Fix:** Let builders register cleanup as soon as they mutate the DOM, and run it on failure. For example, pass an `onCleanup` registrar:
```js
play: function (name, build) {
  if (!enabled) return false;
  stop(name);
  var failed = false, undo = [];
  var c = gsap.context(function () {
    try { return build(gsap, function (fn) { undo.push(fn); }); }
    catch (e) { failed = true; if (window.console) console.warn('[motion]', e); }
  });
  if (failed) {
    undo.forEach(function (f) { try { f(); } catch (e) { } });
    try { c.revert(); } catch (e) { }
    return false;
  }
  ...
```
Builders would then call `onCleanup(cleanup)` right after creating the DOM state. Alternatively, wrap each builder body in `try { ... } catch (e) { cleanup(); throw e; }`.

### WR-02: Itinerari span assertions leave about 59 ms of margin, which is flaky under load

**File:** `fp-cercador/scripts/motion_smoke.py:501` (used at lines 537 and 690)
**Issue:** The longest real sequence is the last column's stop. It starts at `(4-1)*0.09 + 0.18*0.6 = 0.378 s` and lasts 0.18 s, so it ends at about 0.558 s. `ITIN_SPAN_BUDGET_MS = 617` leaves roughly 59 ms (about 3.5 frames) of slack. The assertion measures wall-clock from the first to the last `requestAnimationFrame` sample that shows an inline style. On a loaded machine, or when a layout pass delays the first sample, the span exceeds 617 ms and the check fails even though the product is correct. It can also pass for the wrong reason, because the sampler only sees styles on frames it manages to run. The `restart-keeps-t0` test depends on the same budget to prove t0 is preserved.
**Fix:** Assert against the timeline's own duration instead of wall-clock. For example, expose or read the GSAP timeline duration and assert `<= 0.6`. If wall-clock is kept, widen the tolerance (for example 800 ms) and let a separate check assert the t0-preservation property directly. A redraw at T+100 ms must finish at about the same absolute time as the original, not 100 ms later.

## Info

### IN-01: Counting-bar value text is hidden with `color: transparent`, which forced-colors mode overrides

**File:** `fp-cercador/frontend/observatori.html:392-393`
**Issue:** The real `.bar-value` text is hidden with `color: transparent` while a visible `aria-hidden` ghost counts up. In Windows forced-colors / High Contrast mode the UA overrides `color`, so the real text becomes visible and overlaps the ghost for about 0.3 s. The effect is cosmetic and short-lived. It is also only partly accessible-by-design: assistive tech keeps the real text, which is intended.
**Fix:** Add `forced-color-adjust: none` to the temporary inline style on `val`. Or skip the ghost approach under `@media (forced-colors: active)`, for example by returning early from `animateBars` when `matchMedia('(forced-colors: active)').matches`.

### IN-02: Smoke runner cleanup and exit-code contract gaps

**File:** `fp-cercador/scripts/motion_smoke.py:22, 95, 781-789`
**Issue:**
- The docstring promises exit code 2 when Chrome cannot start. A missing `playwright` package fails at the top-level `from playwright.sync_api import ...` with an `ImportError` traceback and exit code 1, which looks like a test failure.
- `new_page()` creates a browser context per check but never closes it. Contexts accumulate until `browser.close()` at the end. A check that raises also leaks its context and its `page.on("pageerror")` list.
**Fix:** Wrap the import in `try/except ImportError`, print `ERROR playwright missing`, and return 2. Have `new_page` return the context as well, or track contexts in a list and `close()` them in a `finally` around each `fn(browser, base)`.

### IN-03: Static guard `no-hidden-start-state` is narrow

**File:** `fp-cercador/scripts/check_motion_static.sh:98`
**Issue:** The regex `opacity:\s*0\s*[;}"]` only catches a bare `opacity:0` followed by `;`, `}` or `"`. It misses `opacity: 0.0`, `opacity:0 !important`, `visibility:hidden` starts, and `gsap.set(x, {opacity: 0})` (where `0` is followed by `}` after a space, which does match, but `autoAlpha: 0` does not). D-05 is only partly enforced, and the other rule (`motion-guard`) only checks for the presence of the string `gsap.matchMedia()`. The guards give a false sense of coverage. The smoke tests are what actually prove the behaviour.
**Fix:** Broaden the pattern to `(opacity|autoAlpha)\s*[:=]\s*0(\.0+)?\s*(!important)?\s*[;}",)]` and add `visibility:\s*hidden` for the animated selectors. State in the header that these are heuristics.

---

_Reviewed: 2026-10-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
