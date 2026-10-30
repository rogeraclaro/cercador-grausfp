# Estat del projecte — per reprendre des d'un altre ordinador

Última actualització: 2026-10-30. Producció: https://grausfp.es (VPS `contabo`) a `ebf76dc`.

## Com reprendre

1. `git clone https://github.com/rogeraclaro/cercador-grausfp.git`. El projecte és a `fp-cercador/`; l'arrel
   del git és la carpeta pare.
2. Les dades (`fp-cercador/backend/data/*.json`) **no són al git**. Cal copiar-les del VPS:
   `scp contabo:/home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/{ofertes,c_modulos,d_modulos,bc_lomloe}.json fp-cercador/backend/data/`
3. El `.env` tampoc no és al git (ADMIN_TOKEN, SMTP, Google OAuth…): copiar-lo a mà del VPS.
4. Tests: `cd fp-cercador/backend && python3 -m pytest tests -q --deselect tests/test_pipeline.py::test_ce_acces_falla_conserva_fitxer_anterior`
   (547 verds el 2026-10-30; aquest test ja fallava abans del pla 078).
5. Local: `python3 app.py` (port 5001) i `python3 -m http.server 8765` dins `frontend/`.

## Deploy (sempre amb l'aprovació explícita del propietari)

`git push cercador-grausfp master`, i després
`ssh contabo 'cd /home/masellas-grausfp/htdocs/grausfp.masellas.info && git pull --ff-only'`.
- Si toca el backend: `systemctl restart fp-cercador`. **Mai diumenge 11:10–11:45**, que és quan corre el
  refresc setmanal.
- Si es canvien textos: apujar `i18n.js?v=` a `index.html` (ara `20261030c`).
- Commits: conventional commits, sense atribució d'IA.

## Fet els darrers dies (tot desplegat)

| Què | Commits | Detall |
|---|---|---|
| Botó "Compartir" a cada fila desplegada del cercador | — | `index.html`; sempre al final de la línia |
| Pla 078 — tots els mòduls dels C LOMLOE (també els sense Grau B) | 0525eb9…ee4dda4 | `c_modulos.json`, notes art. 58.3 / neutra / altra família, recompte C→D |
| Pla 079 — 11 mòduls que 10 fitxes todofp ometen, completats amb el BOE | 0ed38f2…a09712c | `_C_MODULOS_BOE_AFEGITS`, `_C_MODULOS_NO_AL_DECRET` (IMA_C_001_4B 0266) |
| Pla 080 — els 400 C auditats contra el seu decret del BOE | f63b5f1…ebf76dc | `--discover` (sumari diari del BOE), RD individuals i de títol; nota `uc_sense_b` |

Detall i proves: `plans/078-*.md`, `plans/079-*.md`, `plans/080-*.md` i `plans/outputs/audit_c_modulos_boe.md`.
Tornar a fer l'auditoria: `python3 scripts/audit_c_modulos_boe.py [--discover] --cache DIR --data DIR`.
La primera vegada, `--discover` triga ~20 min; després va de la memòria cau.

## Pendent

### Dels plans 078–080 (C LOMLOE)
- **SEA_C_004_5B i SEA_C_006_5B, mòdul 1782.** Probablement associat a UC1970_2 (PRL en incendis
  forestals), però el decret de grup (RD 211/2025) no té taula mòdul↔UC. Mantenen la nota de l'art.
  58.3 fins que hi hagi prova. Si se'n troba, s'afegeixen a `_C_MODULOS_UC_SENSE_B` (`backend/app.py`).
- **Avisar el ministeri** (decisió del propietari):
  - les 11 fitxes todofp incompletes (taula a `plans/079-*.md`);
  - el forat del catàleg HOT_C_003_5B → HOT_B_0178;
  - els 36 "catàleg de més" (inofensius).
- **Automatitzar la detecció.** Executar `--discover` quan aparegui un C nou al catàleg; ara és manual.
  Sense aquest pas, un C nou queda sense auditar.
- **Tests:** `test_refs_api.py` i `test_grau_page.py` no aïllen `C_MODULOS_PATH` (passen igualment).
  `test_ce_acces_falla_conserva_fitxer_anterior` falla des d'abans del 078.

### Fora del git a la carpeta arrel (no pujat; cal decidir-ho)
- `grausfp-launch/`: projecte de vídeo (128 MB, amb `.env` propi). No s'ha pujat perquè té un `.env` i
  pesa molt.
- `pt.log`: buit.

### Pendents anteriors (de la memòria de Claude; verificar-ne l'estat abans de fer-hi res)
- Pla 033 (observatori), previst per a ~juliol.
- Canvi de domini: `SITE_URL`, Search Console i Google OAuth.
- Pla 053: preferències d'email (TODO).
- Pla 064: UI de l'FPO extern (PIMEC/Foment). El 063 (backend) és fet.
- Política de privacitat "provisional", lligada al registre GDPR.
