---
phase: 1
slug: project-setup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest tests/ -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | PROJ-01 | — | N/A | file check | `test -d fp-cercador/backend && test -d fp-cercador/frontend` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | PROJ-02 | — | N/A | install | `pip install -r requirements.txt --dry-run` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | PROJ-03 | — | .env excluded | file check | `grep -q '\.env' fp-cercador/.gitignore` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_setup.py` — stubs per PROJ-01, PROJ-02, PROJ-03
- [ ] pytest instal·lat si no detectat

*Si cap: "La infraestructura existent cobreix tots els requisits de la fase."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| .env.example visible i documenta ADMIN_TOKEN | PROJ-03 | Verificació visual de documentació | Obrir .env.example i confirmar que ADMIN_TOKEN apareix amb comentari explicatiu |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
