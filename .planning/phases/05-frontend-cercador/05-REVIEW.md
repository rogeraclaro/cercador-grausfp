---
phase: 05-frontend-cercador
reviewed: 2026-04-19T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - fp-cercador/frontend/index.html
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Fase 05: Informe de Revisió de Codi

**Revisat:** 2026-04-19
**Profunditat:** standard
**Fitxers revisats:** 1
**Estat:** issues_found

## Resum

S'ha revisat `fp-cercador/frontend/index.html` (407 línies), un SPA d'una sola pàgina que integra HTML, CSS i JavaScript inline amb Alpine.js 3.15.11. El fitxer implementa un cercador de l'oferta FP espanyola amb filtres, paginació clàssica i gestió d'estats (loading / error / ready).

Els requisits de seguretat crítics es compleixen: no hi ha cap `x-html`, tot el contingut de la API es renderitza via `x-text`, no hi ha credencials hardcoded, ni ús de `eval` ni `innerHTML`. L'Alpine CDN usa una versió fixada, no `@latest`.

S'han trobat 2 advertències (cap impedeix el funcionament en dev, però una bloqueja producció) i 2 ítems informatius menors.

## Warnings

### WR-01: `API_BASE` hardcoded a `localhost` — bloquejarà en producció

**Fitxer:** `fp-cercador/frontend/index.html:184`

**Issue:** `const API_BASE = 'http://localhost:5001'` és un valor hardcoded per a entorn de desenvolupament. En producció, el navegador farà les peticions a `localhost` del client (no del servidor), de manera que totes les càrregues de dades fallaran silenciosament (el `catch` posarà `state = 'error'`). A més, `http://` (sense TLS) provocarà bloqueig de contingut mixt si el frontend es serveix per HTTPS.

**Fix:**
```js
// Opció recomanada: URL relativa si backend i frontend comparteixen origen
const API_BASE = '';

// Opció alternativa: detecció d'entorn per hostname
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:5001'
  : '';  // o 'https://domini.produccio.com'
```

---

### WR-02: `buildPagination()` com a mètode ordinari pot causar doble còmput de `filteredRecords` per render

**Fitxer:** `fp-cercador/frontend/index.html:243-260` i `384`

**Issue:** `buildPagination()` és un mètode ordinari (no un getter Alpine). Cada vegada que Alpine re-avalua el template de paginació, el mètode s'executa de nou, i internament invoca `this.totalPages`, que al seu torn accedeix a `this.filteredRecords` (un getter que itera `allRecords` sencer). En el mateix cicle de render, `pagedRecords` (a la taula) accedeix també a `filteredRecords`. En Alpine 3, els getters no es memoritzen entre accessos del mateix cicle, de manera que amb 1.500 registres es fan dues iteracions completes per render. Addicionalment, si `filteredRecords` canviés entre accessos (teòricament impossible en JS monofil, però indicatiu d'un acoblament fràgil), `totalPages` dins `buildPagination` i `pagedRecords` podrien ser inconsistents.

**Fix:** Convertir `buildPagination` a getter per garantir semàntica reactiva consistent i eliminar la crida explícita al template:

```js
// Canviar de mètode a getter
get paginationItems() {
  const c = this.currentPage, m = this.totalPages, delta = 2;
  if (m <= 1) return [];
  const left = c - delta, right = c + delta + 1;
  const range = [], result = [];
  let l;
  for (let i = 1; i <= m; i++) {
    if (i === 1 || i === m || (i >= left && i < right)) range.push(i);
  }
  for (const i of range) {
    if (l) {
      if (i - l === 2) result.push({ type: 'page', n: l + 1 });
      else if (i - l !== 1) result.push({ type: 'ellipsis' });
    }
    result.push({ type: 'page', n: i });
    l = i;
  }
  return result;
}
```

```html
<!-- Canviar al template (línia 384): -->
<template x-for="(item, idx) in paginationItems" :key="idx">
```

## Info

### IN-01: Clau `x-for` de paginació usa `JSON.stringify` — pot col·lisionar en cas d'ellipsis múltiples

**Fitxer:** `fp-cercador/frontend/index.html:384`

**Issue:** `:key="JSON.stringify(item)"` genera la mateixa clau `{"type":"ellipsis"}` per a tots els elements de tipus `ellipsis`. Si l'algorisme de paginació produís dos ellipsis consecutius (situació actual no possible, però fràgil davant canvis futurs a `buildPagination`), Alpine rebria dues claus idèntiques i el DOM diffing podria comportar-se incorrectament. A més, cridar `JSON.stringify` en cada iteració és innecessàriament costós.

**Fix:**
```html
<template x-for="(item, idx) in buildPagination()" :key="idx">
```
La llista de paginació no es reordena, per tant l'index és una clau segura i sense cost de serialització. (Si s'aplica WR-02, usar `paginationItems` en comptes de `buildPagination()`.)

---

### IN-02: Error del `fetch` silenciat completament al `catch` del `init()`

**Fitxer:** `fp-cercador/frontend/index.html:212-214`

**Issue:** El bloc `catch(e)` captura l'error però descarta `e` sense cap registre. En producció el comportament és acceptable (l'usuari veu l'estat d'error), però durant el desenvolupament és impossible distingir si ha fallat la xarxa, el parse JSON, o una excepció de JS al mapping de dades.

**Fix:**
```js
} catch(e) {
  console.error('[cercador] Error carregant catàleg:', e);
  this.state = 'error';
}
```

---

## Verificació de requisits de seguretat (context: XSS prevention)

| Requisit | Resultat |
|---|---|
| Cap `x-html` al fitxer | Confirmat — no apareix en cap lloc |
| Tot contingut de la API renderitzat via `x-text` | Confirmat (línies 364, 368, 369, 370, 371, 391) |
| Cap `eval()`, `innerHTML` ni `dangerouslySetInnerHTML` | Confirmat |
| Cap credencial ni secret hardcoded | Confirmat |
| Alpine CDN amb versió fixada (no `@latest`) | Confirmat — `@3.15.11` |

---

_Revisat: 2026-04-19_
_Revisor: Claude (gsd-code-reviewer)_
_Profunditat: standard_
