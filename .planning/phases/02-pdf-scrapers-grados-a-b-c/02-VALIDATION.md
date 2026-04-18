---
phase: 2
slug: pdf-scrapers-grados-a-b-c
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/test_scrapers.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_scrapers.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | PDF-01 | — | Descàrrega amb headers correctes | unit | `python -m pytest tests/test_pipeline.py::test_download_headers -x -q` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | PDF-02 | — | Skip pàgines 1–5 cobertura/intro | unit | `python -m pytest tests/test_pdf_scraper.py::test_skip_intro_pages -x -q` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | PDF-03 | — | Camps correctes per registre | unit | `python -m pytest tests/test_pdf_scraper.py::test_record_fields -x -q` | ❌ W0 | ⬜ pending |
| 2-01-04 | 01 | 1 | PDF-04 | — | Familia derivada de PREFIX_MAP | unit | `python -m pytest tests/test_pdf_scraper.py::test_familia_prefix_map -x -q` | ❌ W0 | ⬜ pending |
| 2-01-05 | 01 | 1 | PDF-05 | — | Nivel derivat del sufix (Grado C) | unit | `python -m pytest tests/test_pdf_scraper.py::test_nivel_suffix -x -q` | ❌ W0 | ⬜ pending |
| 2-01-06 | 01 | 1 | PDF-06 | — | plan_antiguo detectat correctament | unit | `python -m pytest tests/test_pdf_scraper.py::test_plan_antiguo -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scrapers.py` — stubs per PDF-01 a PDF-06
- [ ] `tests/conftest.py` — fixtures compartides (PDFs de mostra, registres de prova)
- [ ] `pip install pytest` — si no hi ha framework detectat

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Descàrrega real des de todofp.es | PDF-01 | Requereix xarxa real + 403 si no hi ha headers | `python scraper/download.py` i verificar que els 3 fitxers es creen |
| Volum ~12.144 registres | PDF-03 | Nombre exacte depèn del PDF oficial | Executar scraper complet i `wc -l` al JSON output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
