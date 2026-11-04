---
phase: quick-261104-u3f
plan: 01
subsystem: frontend
tags: [centres, i18n, topbar, security, cache-busting]
status: complete
requirements: [quick-261104-u3f]
key-files:
  modified:
    - fp-cercador/frontend/i18n.js
    - fp-cercador/frontend/site.css
    - fp-cercador/frontend/index.html
    - fp-cercador/backend/grau_page.py
    - fp-cercador/backend/tests/test_grau_page.py
    - fp-cercador/frontend/ (14 static pages + admin.html: cache bumps)
decisions:
  - "Language-aware external link via generic data-lang-href attribute handled in i18n.js (no Alpine, no f-string braces in grau_page.py)"
actuals:
  tokens: 20000
  tasks: 3
  commits: 3
plan_head_before: deeb60d00ad133284cc6894106e5956bed95f314
plan_head_after: 83843f1391a803dd7dc97b0859e904b21e10b95d
---

# Quick 261104-u3f: Centres integration follow-ups and dead code

Removed dead centres upsell code, hardened centre website links with `safeHttpUrl()`, and added a language-aware "Centres"/"Centros" topbar link to every page sharing the site.css topbar plus `/grau/<ref>`.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 2f40a3f | chore(frontend): remove unused centres upsell key and separator rule |
| 2 | dc9d219 | fix(centres): only link centre websites with http(s) URLs |
| 3 | 83843f1 | feat(topbar): link to the centres finder from every page |

## What changed

- Task 1: deleted `index.centres.upsell` (CA+ES) from i18n.js and the `.centres-separator` rule from index.html. No remaining references.
- Task 2: all six `centre.url_web` bindings (x-if, :href, negated x-if, in selected and unselected lists) now go through `safeHttpUrl()`. `javascript:`, `data:`, empty or missing values render the centre name as plain text.
- Task 3: i18n.js sets `href = data-lang-href + _lang + '/'` on load; `.topbar-centres` rule moved from index.html to site.css; anchor added after the logo on 14 static pages and in the grau_page.py skeleton (Spanish default text `Centros`); `site.css?v=4` on all 16 pages, `i18n.js?v=20261104b` on all 15, grau_page.py constants matched. New test `test_topbar_enllaca_al_cercador_de_centres` (RED first, then GREEN).

## Verification

- Backend suite (`--ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`): 414 passed. test_grau_page.py: 40 passed (39 + 1 new).
- Task 1, 2 and 3 automated gates all passed (including the node check that `safeHttpUrl` rejects `javascript:`/`data:`/undefined and trims http(s)).
- Browser spot check was not performed.

## Deviations from Plan

None. Plan executed as written. (Only tooling hiccup: `sd` multi-line regex did not match in i18n.js, so the two key lines were removed with Edit instead; same result.)

## Notes for follow-up

- tel: and mailto: anchors in the centres panel left unchanged: the scheme is fixed by the string prefix, so scraped data cannot make them script URLs (T-u3f-02 accepted).
- Out of scope, observation: the FPO course-detail link (~line 4482 in index.html, `curs.centre.web`) forces an `https://` prefix on values that are not http(s), rather than rejecting them.
- Possible cleanup (not done, scope discipline): the comment `/* Auth widget al topbar */` in index.html's inline style block is now left without a rule below it.

## Known Stubs

None.

## Threat Flags

None. No new surface beyond the plan's threat model (outbound `rel="noopener"` link; T-u3f-03 mitigated by the fixed-string gate).

## Self-Check: PASSED

Commits 2f40a3f, dc9d219, 83843f1 exist on master; modified files present; working tree contains only pre-existing unrelated changes (.DS_Store, grausfp-launch/, pt.log) plus this docs directory.
