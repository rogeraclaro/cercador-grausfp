# Spike 017 — Disseny de les alertes personalitzades de novetats (F3)

> Generat el 2026-06-16. Fonament de la construcció F3 (plans 028–029).
> Cap d'aquestes decisions implica canvi de codi en aquest pla.

---

## Context

F3 (alertes personalitzades) és la "killer feature" del login: permet a un usuari dir "avisa'm quan surti un grau nou que m'interessi". F1 (login) i F2 (favorits) ja estan en producció. F3 tanca el triangle de retenció.

La infraestructura necessària ja existeix parcialment:
- Taula `alerts` a `backend/migrations/001_initial_schema.sql`
- `compute_changes()` a `backend/history.py` produeix `new_by_grado` i `removed_by_grado`
- `email_service.send_email()` via Brevo SMTP (`backend/email_service.py`)
- `scheduler_service._scheduled_refresh()` és el hook natural post-refresh
- `feed.item_summary()` és reutilitzable com a referència de format de text

---

## Step 1: Model de subscripció (format de `filter_json`)

### Esquema del filtre

La taula `alerts` té `filter_json TEXT NOT NULL`. El camp conté un objecte JSON serialitzat amb els camps de filtre. Tots els camps són opcionals; s'aplica per AND (tots s'han de complir).

```json
{
  "familia": "Informàtica i Comunicacions",
  "grado": "D",
  "nivel": "Superior",
  "texto": "ciberseguretat",
  "alertar_baixes": false
}
```

**Definició de cada camp:**

| Camp | Tipus | Matching | Exemple |
|---|---|---|---|
| `familia` | string | Exacte (case-insensitive) sobre el camp `familia` de l'oferta | `"Sanitat"` |
| `grado` | string | Exacte: `"A"`, `"B"`, `"C"`, `"D"` o `"E"` | `"D"` |
| `nivel` | string | Exacte (case-insensitive) sobre el camp `nivel` de l'oferta | `"Superior"` |
| `texto` | string | Substring NFD+lower sobre la denominació (igual que el cercador) | `"ciberseguretat"` |
| `alertar_baixes` | bool | Si `true`, l'email inclou també les denominacions eliminades | `false` |

**Exemples concrets:**

```json
// Alerta global per a tot Grado A (quan surti qualsevol titulació nova)
{"grado": "A"}

// Alerta per a una família concreta al Grado D
{"familia": "Informàtica i Comunicacions", "grado": "D"}

// Alerta per text lliure (text normalitzat NFD+lower com al cercador)
{"texto": "ciberseguretat"}

// Alerta combinada: família + text
{"familia": "Sanitat", "texto": "infermeria"}

// Alerta amb baixes incloses (explícit)
{"grado": "B", "alertar_baixes": true}
```

### Límit d'alertes per usuari

**Límit recomanat: 10 alertes per usuari.**

Justificació: un usuari típic (orientador, família) rarament necessita més de 5 filtres simultanis. 10 dóna marge generós sense risc d'abús (un usuari amb 10 alertes i 1 enviament setmanal = 10 emails/setmana cap a ell, acceptable). A 100 usuaris actius × 10 alertes = 1.000 enviaments màxim/setmana, dins del límit gratuït de Brevo (300/dia = 2.100/setmana). El límit és simple d'implementar: `COUNT(*) WHERE user_id = ? AND active = 1` abans de `INSERT`.

### Índex a la taula

La taula `alerts` actual no té índexs secundaris. Per a la consulta de dispatching post-refresh (seleccionar totes les alertes actives) és suficient un `SELECT * WHERE active = 1`. Amb centenars d'usuaris SQLite ho resol sense índex. Quan el volum arribi a milers, afegir:

```sql
-- A incloure a la futura migració 002:
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active);
```

No cal nova migració ara; el volum no ho justifica en producció actual.

---

## Step 2: Motor de matching

### Funció `match_alert`

```python
# alerts_service.py (fitxer nou a backend/)

import unicodedata

def _normalize(text: str) -> str:
    """NFD + elimina diacrítics + lowercase. Igual que index.html."""
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('ascii').lower()


def match_alert(filter_dict: dict, changes: dict) -> list[str]:
    """
    Retorna la llista de denominacions noves que encaixen amb el filtre.

    Args:
        filter_dict: El filter_json deserialitzat (dict).
        changes: El retorn de history.compute_changes().

    Returns:
        Llista de denominacions matchejades (buida si cap).
    """
    grado_filter = filter_dict.get("grado")
    familia_filter = filter_dict.get("familia")
    nivel_filter = filter_dict.get("nivel")
    texto_filter = filter_dict.get("texto")

    new_by_grado = changes.get("new_by_grado") or {}

    # 1. Candidats: denominacions noves del grado especificat (o de tots si no hi ha filtre)
    if grado_filter:
        candidates = new_by_grado.get(grado_filter, [])
    else:
        # Sense filtre de grado: totes les noves denominacions
        candidates = [d for denoms in new_by_grado.values() for d in denoms]

    if not candidates:
        return []

    # 2. Filtre per texto (NFD+lower, substring)
    if texto_filter:
        q = _normalize(texto_filter)
        candidates = [d for d in candidates if q in _normalize(d)]

    # 3. Filtre per familia i nivel: requereix metadades (veure nota implementació)
    # Pseudocodi: si candidates porta metadades {denominacio, familia, nivel}:
    # if familia_filter:
    #     fam_q = familia_filter.lower()
    #     candidates = [c for c in candidates if (c.get("familia") or "").lower() == fam_q]
    # if nivel_filter:
    #     niv_q = nivel_filter.lower()
    #     candidates = [c for c in candidates if (c.get("nivel") or "").lower() == niv_q]

    return candidates
```

**Nota d'implementació important**: El filtre per `familia` i `nivel` requereix metadades que `new_by_grado` no porta (només conté llistes de strings de denominacions). El pla 028 haurà de decidir entre:
- **Opció A (recomanada)**: A `history.py`, enriquir `new_by_grado` amb metadades `{grado: [{denominacio, familia, nivel}]}` — canvi mínim a `compute_changes`.
- **Opció B**: A `alerts_service.py`, carregar `ofertes.json` i fer lookup per denominació per obtenir família/nivell.

L'opció A és més neta i evita una lectura de fitxer a cada dispatching.

### Idempotència: `last_sent_at` és suficient

La taula `alerts` té `last_sent_at TEXT`. La lògica d'idempotència és:

```python
# Pseudocodi al dispatcher (a implementar al pla 028)
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
if alert["last_sent_at"] and alert["last_sent_at"][:10] == today:
    continue  # ja enviat avui, skip
```

**No cal una taula addicional de "sent log"**: el refresh és setmanal (un cop per setmana). `last_sent_at` és suficient perquè:
1. La granularitat d'idempotència és "dia actual" — si el scheduler s'executa dues vegades el mateix dia per algun motiu, es fa skip.
2. No hi ha necessitat d'historial d'enviaments (audit trail) en aquesta fase.
3. Una taula de log seria overhead sense valor per al cas d'ús actual.

Si en el futur es volen estadístiques d'obertura o rebots, s'afegirà via Brevo (que ja porta tracking), no via BD local.

### Integració al post-refresh

**Hook natural**: `scheduler_service._scheduled_refresh()`, just AFTER `history.append(result)` (línies ~119-122 de `scheduler_service.py`). El refresh manual des de l'admin (`/api/admin/refresh`) també crida `history.append` — cal afegir el hook als dos llocs.

```python
# scheduler_service.py — pseudocodi d'integració
try:
    history.append(result)
except Exception as exc_h:
    logger.error("Could not write refresh history: %s", exc_h)

# Hook F3: dispatching d'alertes (AFEGIR al pla 028)
try:
    from alerts_service import dispatch_alerts
    dispatch_alerts(result)
except Exception as exc_a:
    logger.error("Could not dispatch alerts: %s", exc_a)
```

`dispatch_alerts(result)` cridarà `compute_changes` internament (o reaprofitarà el que ja ha calculat `history.append`) per obtenir `changes`, iterarà les alertes actives de BD i enviarà els emails.

### Baixes (`removed_by_grado`)

**Recomanació: NO alertar baixes per defecte.**

Justificació: la baixa d'una titulació és notícia negativa i rara. Enviar-la per defecte crearia confusió. L'usuari que vulgui baixes pot activar-ho explícitament amb `"alertar_baixes": true` al `filter_json`. La implementació al motor de matching és simètrica: si `filter_dict.get("alertar_baixes")`, afegir el càlcul sobre `removed_by_grado[grado]` i incloure-les a l'email amb l'epígraf "Titulacions retirades:".

---

## Step 3: L'email

### Freqüència recomanada: digest post-refresh (setmanal)

El refresh és setmanal per disseny del sistema. L'email s'envia just AFTER cada refresh que produeix canvis que encaixen amb el filtre. No hi ha emails entre refreshos. Justificació:
- Evita spam: si hi ha 5 titulacions noves en un refresh, un sol email les consolida.
- La freqüència màxima és la del refresh (1 cop/setmana): no intrusiu.
- L'usuari s'ha subscrit entenent que el sistema fa refreshos setmanals.

### Plantilla text pla

S'usa `email_service.send_email(to, subject, body)` — text pla via Brevo SMTP.

**Assumpte:**
```
Novetats FP — [N] nous ensenyaments que t'interessen ([data])
```
Exemple: `Novetats FP — 3 nous ensenyaments que t'interessen (2026-06-16)`

**Cos:**
```
Hola,

Han aparegut [N] nous ensenyaments de Formació Professional que encaixen
amb la teva alerta "[descripció del filtre]":

  • [denominació 1]
  • [denominació 2]
  • [denominació N]

Consulta els detalls a:
https://grausfp.masellas.info

---
Reps aquest email perquè tens una alerta activa al Cercador FP España.
Per deixar de rebre'l, clica aquí (sense necessitat d'entrar):
https://grausfp.masellas.info/api/alerts/[id]/unsubscribe?token=[tok]

Cercador FP España · grausfp.masellas.info
```

### Mock d'exemple complet

```
De: Cercador FP España <noreply@masellas.info>
Per a: maria.garcia@gmail.com
Assumpte: Novetats FP — 2 nous ensenyaments que t'interessen (2026-06-16)

Hola,

Han aparegut 2 nous ensenyaments de Formació Professional que encaixen
amb la teva alerta "Grado D · Informàtica i Comunicacions":

  • Tècnic Superior en Ciberseguretat en Entorns de les Tecnologies de la Informació
  • Tècnic Superior en Desenvolupament de Videojocs i Realitat Virtual

Consulta els detalls a:
https://grausfp.masellas.info

---
Reps aquest email perquè tens una alerta activa al Cercador FP España.
Per deixar de rebre'l, clica aquí (sense necessitat d'entrar):
https://grausfp.masellas.info/api/alerts/7/unsubscribe?token=e9c3a1f5b8d2c4a6f1e3b7d9...

Cercador FP España · grausfp.masellas.info
```

### Link de baixa sense login

**Format**: `GET /api/alerts/<alert_id>/unsubscribe?token=<tok>`

**Token de baixa:**
- Generat amb `secrets.token_hex(32)` en el moment de crear l'alerta.
- Guardat a la taula `tokens` existent amb `type='alert_unsubscribe'` i `expires_at` a +365 dies (1 any).
- L'endpoint és públic (sense sessió): comprova que el token existeix, és del tipus correcte i no ha caducat; si OK, fa `UPDATE alerts SET active = 0 WHERE id = ?` i esborra el token.
- Retorna redirect a `/?unsubscribed=1` (el frontend pot mostrar un toast).

Usar la taula `tokens` existent (no afegir camp dedicat a `alerts`) manté el patró del codebase (igual que `email_verify` i `password_reset`).

### Volum estimat i límits Brevo

| Escenari | Emails/setmana | Emails/dia (aprox.) |
|---|---|---|
| 100 usuaris × 3 alertes | 300/setmana | 43/dia |
| 500 usuaris × 5 alertes | 2.500/setmana | 357/dia |
| 1.000 usuaris × 5 alertes | 5.000/setmana | 714/dia |

**Límit Brevo gratuït: 300 emails/dia.**

Amb el volum actual del projecte (fase de llançament), 100 usuaris × 3 alertes = 300 emails/setmana, molt per sota del límit diari. **No cal preocupar-se ara.** Quan el projecte superi ~300 usuaris actius, caldrà escalar al pla de pagament de Brevo (Starter ~25€/mes per a 20.000 emails/mes). Afegir un petit `time.sleep(0.1)` entre enviaments al dispatcher per no sobrecarregar Brevo SMTP, però per a centenars d'usuaris no és un problema pràctic.

---

## Step 4: UI de gestió d'alertes

### On viu

Nova pàgina `frontend/alertes.html`, seguint el patró d'`historial.html`: pàgina estàtica amb fetch vanilla, sense frameworks nous. Accessible des del widget d'auth del header (quan l'usuari és autenticat, el menú desplegable mostra "Les meves alertes").

### Estats i fluxos

#### Flux 1: Crear alerta des de la cerca (principal)

A `index.html`, quan hi ha filtres actius (grado, família, o text de cerca) i l'usuari és autenticat, apareix un botó "Desa com a alerta" sota els filtres actius. En clicar:
1. El frontend serialitza els filtres actuals al format `filter_json`.
2. `POST /api/alerts` amb `{"filter_json": {...}}`.
3. Confirmació inline: "Alerta creada. T'avisarem quan surtin nous ensenyaments."
4. Si no autenticat: clic al botó → `showCentresModal()` (el modal de gating ja existent de plans 026–027).

#### Flux 2: Gestió a `alertes.html`

La pàgina mostra la llista d'alertes de l'usuari. Per cada alerta:
- **Descripció llegible** generada al frontend a partir del `filter_json`:
  - `{"grado":"D","familia":"Informàtica i Comunicacions"}` → `"Grado D · Informàtica i Comunicacions"`
  - `{"texto":"ciberseguretat"}` → `"Texto: «ciberseguretat»"`
  - `{"grado":"A"}` → `"Tots els nous Grado A"`
- **Data de creació** (`created_at`).
- **Última notificació** (`last_sent_at`, o "Encara no enviada").
- **Toggle activar/desactivar** (PATCH `/api/alerts/<id>` amb `{"active": true/false}`).
- **Botó esborrar** (DELETE `/api/alerts/<id>`).

#### Flux 3: Usuari no autenticat

- `alertes.html` amb sessió no vàlida → redirigeix a `index.html` (o mostra modal de login).
- Botó "Desa com a alerta" a `index.html` sense sessió → `showCentresModal()`.

### Endpoints REST mínims

```
GET    /api/alerts                          (auth)   → llista d'alertes de l'usuari
POST   /api/alerts                          (auth)   → crear alerta
DELETE /api/alerts/<id>                     (auth)   → esborrar (verifica ownership)
PATCH  /api/alerts/<id>                     (auth)   → toggle active
GET    /api/alerts/<id>/unsubscribe?token=  (públic) → baixa sense login
```

**Detall de POST /api/alerts:**
- Body: `{"filter_json": {...}}`
- Validació: almenys un dels camps (`familia`, `grado`, `nivel`, `texto`) ha d'estar present.
- Validació: `grado` ha de ser un de `A`, `B`, `C`, `D`, `E` si està present.
- Límit: màxim 10 alertes actives per usuari (retorna 429 si superat).
- Genera token de baixa i l'insereix a `tokens` (type='alert_unsubscribe', expires +365 dies).
- Retorna: `{"id": 42, "filter_json": {...}, "active": 1, "created_at": "2026-06-16T..."}`

**Detall de GET /api/alerts:**
- Retorna: `[{"id": 42, "filter_json": {...}, "active": 1, "created_at": "...", "last_sent_at": null}, ...]`
- Ordre: `created_at DESC`.

**Detall de PATCH /api/alerts/<id>:**
- Body: `{"active": false}` (o `true`)
- Verifica ownership: `SELECT id FROM alerts WHERE id = ? AND user_id = ?`

**Detall de GET /api/alerts/<id>/unsubscribe?token=:**
- Públic, sense sessió.
- Comprova `tokens` (type='alert_unsubscribe', no caducat).
- `UPDATE alerts SET active = 0 WHERE id = ?`; esborra el token.
- Redirect a `/?unsubscribed=1`.

---

## Step 5: Relació amb feed.py / notifier.py / F4

### feed.py i `item_summary()`

`feed.item_summary(changes_dict)` genera el resum global de canvis en text pla: "Nous ensenyaments per grado: D: 5, C: 2". Per a les alertes personalitzades, el cos de l'email és diferent: llistat de denominacions específiques matchejades per a AQUEST usuari. No reutilitzar directament `item_summary()` per al cos de l'email d'alerta — el contingut és massa diferent. Sí mantenir el mateix estil: text pla, sense HTML, línies curtes, format de bullet list amb `•`.

### notifier.py (newsletter broadcast) vs F3 (alertes individuals)

**Mecanismes completament independents — no combinar:**

| | `notifier.py` (broadcast) | F3 `alerts_service.py` (individuals) |
|---|---|---|
| Canal | Brevo API — campanyes de marketing | Brevo SMTP — emails transaccionals |
| Destinataris | Llista Brevo completa (tots els subscrits) | Usuari individual (els seus filtres) |
| Contingut | Resum global de tots els canvis | Denominacions específiques matchejades |
| Trigger | Post-refresh si `BREVO_API_KEY` configurat | Post-refresh per a cada alerta activa amb matches |
| Fitxer | `backend/notifier.py` | `backend/alerts_service.py` (nou, pla 028) |
| Idempotència | `data/notifier_state.json` (guid del darrer ítem) | `last_sent_at` a taula `alerts` |
| Baixa | Gestió externa a Brevo | `GET /api/alerts/<id>/unsubscribe?token=` |

**Per què no combinar-los**: la newsletter és opt-in a Brevo (subscripció externa, qualsevol visitant), les alertes F3 són opt-in a l'app (compte registrat, filtre personalitzat). Les baixes funcionen diferent. El contingut és diferent. Fusionar-los crearia acoblament no desitjat i dificultaria l'evolució independent.

### F4 (seguiment de centres) — endoll documentat

Quan F4 s'implementi (post-pla 015 construït), el motor d'alertes s'estén de forma natural:

1. **`filter_json` extensible**: afegir `"centre_ids": [1234, 5678]` al filtre. El motor actual l'ignora (camp desconegut = ignorat). Quan F4 s'implementi, `match_alert` incorpora la nova font.

2. **Nova font de canvis**: `dispatch_alerts(result, centre_changes=None)` — signatura preparada per a F4 des del principi. L'arg `centre_changes` és `None` fins que F4 existeixi.

3. **No cal migrar la taula `alerts`**: `filter_json` és TEXT flexible, els nous camps s'afegeixen sense canvi d'esquema.

4. **Mateixa infraestructura d'email**: `email_service.send_email` per a F3 i F4 — canvi zero al canal d'enviament.

---

## Step 6: Pla de construcció proposat

Donada la taula `alerts` ja existent a `001_initial_schema.sql`, la construcció de F3 es desglossa en dos plans:

### Pla 028 — Backend motor d'alertes (esforç S-M)

**Fitxers nous**: `backend/alerts_service.py`

**Fitxers modificats**: `backend/app.py`, `backend/scheduler_service.py`

**Lliurables**:

1. `alerts_service.py` nou:
   - `_normalize(text)` — NFD+lower (igual que `index.html`)
   - `match_alert(filter_dict, changes)` — retorna llista de denominacions matchejades
   - `build_alert_description(filter_dict)` — genera text llegible del filtre per a l'email
   - `dispatch_alerts(result)` — llegeix alertes actives de BD, crida `match_alert` per cadascuna, envia emails via `email_service.send_email`, actualitza `last_sent_at`

2. `app.py` — endpoints CRUD + unsubscribe:
   - `GET /api/alerts` (auth)
   - `POST /api/alerts` (auth, límit 10, genera token baixa a `tokens`)
   - `DELETE /api/alerts/<id>` (auth, ownership check)
   - `PATCH /api/alerts/<id>` (auth, ownership check)
   - `GET /api/alerts/<id>/unsubscribe?token=` (públic)

3. `scheduler_service.py` — crida `dispatch_alerts` just AFTER `history.append(result)`

4. `app.py` endpoint `/api/admin/refresh` — afegir la mateixa crida `dispatch_alerts`

5. **Tests unitaris** (`backend/tests/test_alerts_service.py`):
   - `test_match_alert_by_grado` — filtre `{"grado": "D"}` matcheja denominació de Grado D
   - `test_match_alert_by_texto_normalized` — filtre `{"texto": "ciberseguretat"}` matcheja "Ciberseguretat en..."
   - `test_match_alert_no_match` — filtre `{"grado": "A"}` retorna `[]` si `new_by_grado` no té "A"
   - `test_match_alert_combined_and` — `{"grado": "D", "texto": "web"}` matcheja intersecció
   - `test_idempotency_skip_if_sent_today` — dispatcher no envia si `last_sent_at` és d'avui

### Pla 029 — Frontend gestió d'alertes (esforç M)

**Fitxers nous**: `frontend/alertes.html`, `frontend/js/alertes.js`

**Fitxers modificats**: `frontend/index.html` (botó "Desa com a alerta")

**Lliurables**:

1. `frontend/alertes.html`:
   - Llista d'alertes de l'usuari (fetch `GET /api/alerts`)
   - Per cada alerta: descripció llegible, data creació, última notificació, toggle actiu/inactiu, botó esborrar
   - Formulari de creació manual (camps: grado, família, texto)
   - Redirect a `index.html` si sessió no vàlida

2. `frontend/js/alertes.js`:
   - `fetchAlerts()`, `createAlert(filterJson)`, `deleteAlert(id)`, `toggleAlert(id, active)`
   - `buildFilterDescription(filterJson)` → text llegible del filtre (lògica simètrica al backend)

3. `frontend/index.html`:
   - Botó "Desa com a alerta" visible quan hi ha filtres actius i usuari autenticat
   - Si no autenticat: `showCentresModal()` (modal de gating existent)

### Primer increment demostrable

**Criteri mínim**: un usuari autenticat crea una alerta `{"grado": "D"}` via `POST /api/alerts`. El proper refresh (manual via `/api/admin/refresh`) detecta noves denominacions de Grado D, crida `dispatch_alerts`, i l'usuari rep un email amb la llista de nouvinguts de Grado D. El link de baixa de l'email desactiva l'alerta sense necessitat de login.

Verificable amb:
```bash
# 1. Crear alerta (autenticat amb cookie de sessió)
curl -X POST https://grausfp.masellas.info/api/alerts \
  -H "Content-Type: application/json" \
  -b "session=<token>" \
  -d '{"filter_json": {"grado": "D"}}'

# 2. Trigger refresh manual
curl -X POST https://grausfp.masellas.info/api/admin/refresh \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# 3. Comprovar inbox del compte registrat
```

---

## Decisions clau (resum executiu)

| Decisió | Opció triada | Justificació |
|---|---|---|
| Format `filter_json` | `{grado, familia, nivel, texto, alertar_baixes}` tots opcionals, AND | Compatible amb taula existent; extensible per a F4 sense migració |
| Límit alertes/usuari | 10 | Suficient per a l'ús real; dins del límit gratuït de Brevo |
| Motor de matching | `match_alert(filter_dict, changes)` a `alerts_service.py` (fitxer nou) | Separat de `notifier.py`; testejable de forma aïllada |
| Idempotència | `last_sent_at` a la taula `alerts` | Suficient per al cicle setmanal; cap taula addicional |
| Alertes de baixes | No per defecte; opt-in via `"alertar_baixes": true` | Evita notificacions negatives no esperades |
| Freqüència | Digest post-refresh (setmanal) | Alineat amb el cicle del sistema; no intrusiu |
| Token de baixa | `tokens` existent (type='alert_unsubscribe', expires +1 any) | Reutilitza el patró del codebase (email_verify, password_reset) |
| Separació broadcast/individual | `notifier.py` (Brevo API) ≠ `alerts_service.py` (Brevo SMTP) | Canals independents; baixes independents; evolució independent |
| Filtre `familia`/`nivel` | Requereix enriquir `new_by_grado` (Opció A, decisió pla 028) | Evita lectura de `ofertes.json` a cada dispatch |
| Hook post-refresh | `scheduler_service._scheduled_refresh` + endpoint admin refresh | Les dues rutes de refresh han d'enviar alertes |
| Endoll F4 | `dispatch_alerts(result, centre_changes=None)` + `filter_json` extensible | Cap canvi a l'esquema quan F4 existeixi |
