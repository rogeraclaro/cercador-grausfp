---
phase: 5
slug: frontend-cercador
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-19
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Cap framework automatitzat — HTML estàtic + Alpine.js via CDN |
| **Config file** | N/A — verificació manual al navegador |
| **Quick run command** | Obrir `fp-cercador/frontend/index.html` amb Flask corrent |
| **Full suite command** | Checklist manual complet (veure baix) |
| **Estimated runtime** | ~5 minuts (checklist manual) |

---

## Sampling Rate

- **After every task commit:** Obrir el navegador i verificar que la funcionalitat de la tasca funciona
- **After every plan wave:** Executar el checklist manual complet
- **Before `/gsd-verify-work`:** Tot el checklist ha d'estar en verd
- **Max feedback latency:** 5 minuts

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | SRCH-01 | — | N/A | manual | Escriure "ADG" al cercador; verificar filtratge per codi | ✅ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | SRCH-02 | — | N/A | manual | Seleccionar Grado B; verificar que tots els resultats son Grado B | ✅ W0 | ⬜ pending |
| 5-01-03 | 01 | 1 | SRCH-03 | — | N/A | manual | Obrir dropdown Família; verificar 30 opcions (29 + "Totes") | ✅ W0 | ⬜ pending |
| 5-01-04 | 01 | 1 | SRCH-04 | — | N/A | manual | Seleccionar Nivell=1; verificar 0 resultats Grado A | ✅ W0 | ⬜ pending |
| 5-01-05 | 01 | 1 | SRCH-05 | — | N/A | manual | Carregar pàgina; comptador ha de mostrar 7.244 (hideOld=true per defecte) | ✅ W0 | ⬜ pending |
| 5-01-06 | 01 | 1 | SRCH-06 | — | N/A | manual | Verificar 5 columnes en ordre: Denominació, Codi, Família, Grado, Nivell | ✅ W0 | ⬜ pending |
| 5-01-07 | 01 | 1 | SRCH-07 | — | N/A | manual | Desactivar hideOld; verificar badges "Pla antic" a files plan_antiguo=true | ✅ W0 | ⬜ pending |
| 5-01-08 | 01 | 1 | SRCH-08 | — | N/A | manual | Escriure text; verificar que el comptador s'actualitza en temps real | ✅ W0 | ⬜ pending |
| 5-01-09 | 01 | 1 | SRCH-09* | — | N/A | manual | DevTools Elements: comptar `<tr>` a `<tbody>`; mai >50 | ✅ W0 | ⬜ pending |
| 5-01-10 | 01 | 1 | SRCH-10 | — | N/A | manual | Aturar Flask; recarregar; verificar banner 503 sense botó retry | ✅ W0 | ⬜ pending |

*SRCH-09 revisat: "sense paginació" → paginació clàssica 50/pàg (D-02)

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No hi ha framework de tests frontend a configurar. La fase comença directament amb la implementació de `fp-cercador/frontend/index.html`. Les verificacions son manuals al navegador.

*Existing infrastructure covers all phase requirements (manual browser testing).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cerca en temps real per text | SRCH-01 | UI interactiva, Alpine.js reactiu | Escriure "ADG"; verificar files; escriure "administracio" (sense accent); trobar "Administración" |
| Dropdown Grado filtra | SRCH-02 | UI interactiva | Seleccionar "B"; verificar que tots els resultats son Grado B |
| Dropdown Família pobla dinàmicament | SRCH-03 | UI interactiva, dades del JSON | Obrir dropdown; comptar opcions (30 incl. "Totes") |
| Dropdown Nivell exclou Grado A | SRCH-04 | Comportament de dades (nivel=null) | Grado=Tots, Nivell=1 → 0 Grado A visibles |
| Checkbox activat per defecte | SRCH-05 | Estat inicial UI | Carregar pàgina → comptador 7.244 (no 12.374) |
| Badge "Pla antic" a cel·la Denominació | SRCH-07 | Inspecció visual | Desactivar hideOld; verificar badge apareix al costat del nom |
| Paginació clàssica amb ellipsis | D-02 | UI interactiva | Navegar a pàgina ~124/145; verificar "1 ... 122 123 [124] 125 126 ... 145" |
| Estat buit distinct de 503 | D-12 | Distinció visual | Escriure "ZZZZZZZ" → missatge dins taula; aturar Flask → banner diferent |
| Màx 50 `<tr>` al DOM | SRCH-09 | DevTools | DevTools Elements: comptar `<tr>` a `<tbody>` en qualsevol pàgina |
| Un únic fetch per sessió | D-03 | DevTools Network | Verificar un sol GET /api/ofertes a la pestanya Network |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
