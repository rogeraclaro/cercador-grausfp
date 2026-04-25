# Phase 6: Admin Panel - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-04-25
**Phase:** 06-admin-panel
**Areas discussed:** Recàrrega de cookies, Refresh periòdic, Instruccions de cookies, Visual i layout

---

## Recàrrega de cookies

| Opció | Descripció | Seleccionat |
|-------|------------|-------------|
| Reload al pipeline | `load_dotenv(override=True)` a `pipeline.run()`, sense restart | ✓ |
| Restart automàtic | `systemctl restart` després de guardar, requereix script extern | |

**Elecció:** Reload al pipeline
**Notes:** Evita el problema de "el servei es mata a si mateix". Més net i senzill.

---

## Refresh periòdic

| Opció | Descripció | Seleccionat |
|-------|------------|-------------|
| APScheduler des de l'admin | Configurable desde UI, guarda config en JSON | ✓ |
| Instruccions cron | Sense codi nou, manual via SSH | |
| Sense refresh automàtic | Deferir a V2 | |

**Interval:** Personalitzable (dia de setmana + hora HH:MM)

---

## Instruccions de cookies

| Opció | Descripció | Seleccionat |
|-------|------------|-------------|
| Inline sempre visible | Instruccions sempre visibles sota el camp | |
| Collapsible / acordió | Expandible "Com obtenir les cookies?" | ✓ |

**Camp cookies:** L'operador enganxa ja retallat (JSESSIONID + __Host-todofp.es)

---

## Visual i layout

| Opció | Descripció | Seleccionat |
|-------|------------|-------------|
| Mateix estil que index.html | DM Sans, warm palette, topbar fosc | ✓ |
| Estil funcional mínim | Blanc, tipografia sistema | |

**Seccions seleccionades:** Refresh manual + estat, Gestió de cookies, Refresh periòdic

---

## Deferred Ideas

- Historial d'execucions
- Notificació email quan falla
