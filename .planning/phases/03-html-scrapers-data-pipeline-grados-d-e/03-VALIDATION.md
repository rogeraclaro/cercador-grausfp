---
phase: 3
slug: html-scrapers-data-pipeline-grados-d-e
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `fp-cercador/backend/tests/` (or Wave 0 creates it) |
| **Quick run command** | `cd fp-cercador && python -m pytest backend/tests/test_html_scraper.py -v` |
| **Full suite command** | `cd fp-cercador && python -m pytest backend/tests/ -v` |
| **Estimated runtime** | ~10 seconds (unit) / ~30 seconds (with network) |

---

## Sampling Rate

- **After every task commit:** Run `cd fp-cercador && python -m pytest backend/tests/test_html_scraper.py -v`
- **After every plan wave:** Run `cd fp-cercador && python -m pytest backend/tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | HTML-01 | — | Headers User-Agent/Referer presents | unit | `pytest backend/tests/test_html_scraper.py::test_parse_grado_d_basico -v` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | HTML-02 | — | Family inferred via headers attr | unit | `pytest backend/tests/test_html_scraper.py::test_family_extraction -v` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | HTML-03 | — | HTML_FAMILY_ALIASES maps anomalies | unit | `pytest backend/tests/test_html_scraper.py::test_family_aliases -v` | ❌ W0 | ⬜ pending |
| 3-01-04 | 01 | 1 | HTML-04 | — | Fail fast on network error | unit | `pytest backend/tests/test_html_scraper.py::test_fail_fast -v` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | HTML-05 | — | parse_grado_e returns 36 records | unit | `pytest backend/tests/test_html_scraper.py::test_parse_grado_e -v` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 3 | DATA-01 | — | ofertes.json schema valid (all fields) | unit | `pytest backend/tests/test_pipeline.py::test_ofertes_schema -v` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 3 | DATA-02 | — | IDs unique and sequential A→B→C→D→E | unit | `pytest backend/tests/test_pipeline.py::test_id_sequence -v` | ❌ W0 | ⬜ pending |
| 3-03-03 | 03 | 3 | DATA-03 | — | pipeline.run() includes D/E in by_grado | unit | `pytest backend/tests/test_pipeline.py::test_pipeline_run_all_grados -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `fp-cercador/backend/tests/test_html_scraper.py` — stubs per HTML-01 a HTML-06
- [ ] `fp-cercador/backend/tests/test_pipeline.py` — stubs per DATA-01 a DATA-04 (si no existeix)
- [ ] `fp-cercador/backend/tests/conftest.py` — fixtures compartides (HTML mock responses)
- [ ] `pytest` — si no detectat a l'entorn virtual

*Si pytest ja existeix de la Fase 2: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Recompte real de títols D+E del ministeri | HTML-06 | Requereix xarxa en viu i depèn de l'estat del lloc web | `curl https://www.todofp.es/.../grado-medio.html | grep -c 'id="tit-'` per cada URL |
| "Mantenimiento y Servicios..." titol LOGSE | HTML-03 | Comportament edge-case: 1 sol registre amb família especial | Inspecció manual de ofertes.json per a familia='Desconeguda' o aliàs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
