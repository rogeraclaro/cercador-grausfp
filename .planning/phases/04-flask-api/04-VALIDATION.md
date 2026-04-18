---
phase: 4
slug: flask-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (ja instal·lat com a dep de dev) |
| **Config file** | cap (pytest descobreix automàticament `tests/`) |
| **Quick run command** | `cd fp-cercador/backend && python3 -m pytest tests/test_api.py -q` |
| **Full suite command** | `cd fp-cercador/backend && python3 -m pytest -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd fp-cercador/backend && python3 -m pytest tests/test_api.py -q`
- **After every plan wave:** Run `cd fp-cercador/backend && python3 -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | API-07 | — | N/A | unit | `pytest tests/test_api.py::test_health -x` | ❌ Wave 0 | ⬜ pending |
| 4-01-02 | 01 | 1 | API-01 | — | N/A | unit | `pytest tests/test_api.py::test_ofertes_200 -x` | ❌ Wave 0 | ⬜ pending |
| 4-01-03 | 01 | 1 | API-02 | — | N/A | unit | `pytest tests/test_api.py::test_ofertes_503 -x` | ❌ Wave 0 | ⬜ pending |
| 4-01-04 | 01 | 1 | API-08 | — | CORS headers presents | unit | `pytest tests/test_api.py::test_cors_headers -x` | ❌ Wave 0 | ⬜ pending |
| 4-02-01 | 02 | 1 | API-03 | T-04-01 | started immediatament | unit | `pytest tests/test_api.py::test_refresh_started -x` | ❌ Wave 0 | ⬜ pending |
| 4-02-02 | 02 | 1 | API-04 | T-04-02 | 401 token incorrecte | unit | `pytest tests/test_api.py::test_refresh_401 -x` | ❌ Wave 0 | ⬜ pending |
| 4-02-03 | 02 | 1 | API-05 | T-04-03 | 409 si procés en curs | unit | `pytest tests/test_api.py::test_refresh_409 -x` | ❌ Wave 0 | ⬜ pending |
| 4-02-04 | 02 | 1 | API-06 | — | estat complet retornat | unit | `pytest tests/test_api.py::test_refresh_status -x` | ❌ Wave 0 | ⬜ pending |
| 4-02-05 | 02 | 1 | API-09 | T-04-04 | token de .env, no hardcoded | unit | `pytest tests/test_api.py::test_admin_token_from_env -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `fp-cercador/backend/tests/test_api.py` — 9 tests nous (API-01 a API-09)
- [ ] Fixture `autouse` per resetejar `_state` entre tests (evita contaminació d'estat del thread)

*Infrastructure existent cobreix tot; només cal el nou fitxer de tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Thread real d'scraping s'executa en background | API-03 | Comportament real del thread difícil de testar sense sleep/race | Llançar `POST /api/admin/refresh` i verificar que la resposta arriba abans que el pipeline acabi (~45s) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
