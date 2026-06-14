# Plan 016b: [OPCIONAL] URL web dels centres

> **Prerequisit**: Pla 016 completat (`centres.json` disponible).
> **Executor instructions**: Pla optatiu — el propietari decideix si executar-lo.
> Cap canvi al pipeline de `ofertes.json`. Només modifica `centres.json`.
> Afegeix el camp `url_web` a cada registre de centre.
> En acabar, actualitza la fila d'aquest pla a `plans/README.md`.

## Status

- **Priority**: P3 (millora de qualitat de dades)
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 016 (centres.json existent)
- **Category**: data-enrichment

## Why this matters

El `centres.json` del pla 016 ja té adreça, telèfon i email per a cada centre.
La URL web permet afegir un enllaç directe al lloc del centre al frontend.
La Font 1 inclou `urlCentro` al detall de cada centre però NO al JSON de la llista,
cosa que requeriria ~12.000 crides extra si es fes per scraping directe de tots.

Aquest pla cobreix la URL web amb un cost mínim gràcies a dues estratègies gratuïtes.

## Estratègia: 3 capes en cascada

### Capa 1 — Derivació del domini de l'email (cost: 0 crides, ~cobertura 60-70%)

```python
GENERIC_DOMAINS = {
    'gmail.com', 'hotmail.com', 'yahoo.com', 'outlook.com',
    # Dominis de conselleries d'educació (no el centre en si):
    'hezkuntza.net', 'edu.gva.es', 'educa.jcyl.es',
    'juntadeandalucia.es', 'xunta.gal', 'educantabria.es',
    'educastur.net', 'caib.es', 'gobiernodecanarias.org',
    'educacion.navarra.es', 'educacion.gob.es', 'larioja.org',
    'educa.madrid.org', 'educarm.es', 'educarex.es',
}

def url_from_email(email):
    if not email or '@' not in email:
        return None
    domain = email.split('@')[1].lower()
    if domain in GENERIC_DOMAINS:
        return None
    return f"https://www.{domain}"
```

**Funciona per a**: centres privats amb domini propi (p. ex. `info@ceaformacion.com` → `www.ceaformacion.com`).
**No funciona per a**: centres públics (usen el domini de la conselleria), centres amb gmail/hotmail.

### Capa 2 — Detall centrorcd per a centres sense URL (cost: ~1.000–3.000 crides)

Els centres públics (`centrorcd=1`) tenen `urlCentro` al seu detall HTML.
Fer-ho només per als centres que la Capa 1 no ha resolt i que siguin de tipus `rcd`.

```python
def fetch_url_centrorcd(cod_ministerio, session):
    url = f"https://registrosfp.educacion.gob.es/.../centrorcd/{cod_ministerio}"
    html = session.get(url).text
    match = re.search(r'id="urlCentro"[^>]*value="([^"]+)"', html)
    return match.group(1) if match else None
```

Rate-limit: 1 req/s. ~2.000 centres × 1s ≈ **~33 min** (vs 3h per a tots).

### Capa 3 — Fallback manual o Google (cost: baix, per als que queden buits)

Per als centres sense URL després de les capes 1 i 2, dos options:
- **Manual**: deixar `url_web: null` i mostrar-ho buit al frontend.
- **Google Custom Search API**: `"{nombre}" "{localidad}" formación profesional` → primer resultat.
  Límit gratuït: 100 queries/dia. Útil com a eina puntual, no per a un refresh automàtic.

**Recomanació**: implementar capes 1 i 2 i deixar la 3 fora d'abast inicial.

## Scope

**In scope**: afegir `url_web` a `centres.json` via les capes 1 i 2.

**Out of scope**: Google/Bing scraping, verificació que la URL és accessible (HEAD request),
modificació de `ofertes.json` o `oferta_centres.json`.

## Steps

### Step 1 — Capa 1: derivació massiva des de l'email

Llegir `centres.json`, aplicar `url_from_email()` a tots els registres.
Comptar quants queden resolts i quants estan buits.

### Step 2 — Capa 2: scraping centrorcd per als buits

Fer bootstrap de sessió a Font 1.
Per a cada centre amb `url_web=null` i `tipo='rcd'`: cridar el detall i extreure `urlCentro`.
Rate-limit 1 req/s. Escriure resultat progressivament (per si s'interromp).

### Step 3 — Actualitzar `centres.json`

Guardar `centres.json` amb el nou camp `url_web` (null si no trobat).
Exemple resultat:
```json
{
  "id": "M010014639G",
  "nombre": "LAUDIOALDE",
  "url_web": "www.cmfp-llodio.com",
  ...
}
```

### Step 4 — Informe de cobertura

Imprimir:
```
Cobertura url_web:
  Capa 1 (email domain): N centres (X%)
  Capa 2 (centrorcd detail): N centres (X%)
  Sense URL: N centres (X%)
```

## Done criteria

- [ ] `centres.json` té el camp `url_web` a tots els registres (null si no disponible)
- [ ] Informe de cobertura imprès
- [ ] Cap canvi a `ofertes.json`, `oferta_centres.json` ni frontend
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- Crides a Font 1 retornen 429/403 → aturar Capa 2, guardar l'estat parcial i informar.
- Menys del 20% de cobertura total → escalar al propietari abans de desplegar (la feature seria poc útil).
