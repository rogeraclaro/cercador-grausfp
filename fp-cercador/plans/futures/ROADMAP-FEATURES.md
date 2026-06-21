# Roadmap de funcionalitats futures — Cercador FP España

> Document de visió generat el 2026-06-10 (sessió /improve, commit `5dc92a1`),
> aprovat pel propietari: **les 10 funcionalitats seleccionades**. Aquest
> document és la referència; els plans de spike/disseny individuals (016+)
> es generen per onades a mesura que s'ataquen.
>
> **Actualitzat 2026-06-21 (commit `2b4fa22`)**: F1–F9 DONE (F7 ~80%, pla 033
> pendent ~juliol), F10 descartat a curt termini. Afegida secció de
> **Pròximes direccions post-F10** amb les oportunitats A–E identificades.

## Context

El projecte té avui un cercador públic de 12.894 ensenyaments (Graus A–E),
un historial setmanal de canvis amb diff per grau, i tres spikes en cartera
(013 dades extra Grado C, 014 feed RSS, 015 centres per grau). El propietari
té decidit afegir **login d'usuaris** per donar accés a característiques
restringides. Aquest roadmap ordena les 10 funcionalitats aprovades al
voltant d'aquest eix.

Constraints vigents que tot disseny ha de respectar:
- Flask + HTML/CSS/JS vanilla (excepció documentada: Alpine.js a index.html)
- Dependències mínimes (les actuals + stdlib; SQLite i smtplib són stdlib,
  el hashing de contrasenyes ve amb Werkzeug/Flask — el login és viable
  sense dependències noves)
- Cercador fluid; dades pesades sempre en fitxers/endpoints separats

## La taula de referència

| # | Funcionalitat | Descripció | Per a qui / valor | Què aprofita del que ja tens | Dependències | Esforç |
|---|---|---|---|---|---|---|
| F1 | **Comptes d'usuari** (fonament) | Registre/login (email + contrasenya o magic link), sessions, perfil mínim. És infraestructura, no feature visible — però tot el que ve després hi penja. Implica la primera base de dades del projecte (SQLite encaixa amb les constraints) | El propietari — habilita el gating | El backend Flask existent; ADMIN_TOKEN ja marca el patró d'auth | — | L |
| F2 | **Favorits i llistes de graus** | Desar graus a "la meva llista", crear llistes amb nom ("Opcions per al meu fill", "Informàtica a distància"), notes pròpies per grau | Famílies i estudiants que comparen durant setmanes; primera raó simple per registrar-se | El cercador i els `id`/`codigo` estables dels registres | F1 | M |
| F3 | **Alertes personalitzades de novetats** | "Avisa'm quan surti un grau nou de la família X / al grado D / que contingui 'ciberseguretat'". El refresh setmanal ja calcula exactament què és nou; només cal creuar-ho amb les subscripcions i enviar email | Orientadors i gent esperant que s'obri una titulació concreta; la feature retenidora per excel·lència | `compute_changes` (plans 005/006) ja produeix les altes per grau; scheduler ja existeix | F1; lliga amb el feed RSS (pla 014) com a versió anònima | M |
| F4 | **Seguiment de centres d'un grau** | "Segueixo aquest grau: avisa'm quan un centre nou l'anunciï o s'obri a la meva província" — la versió personalitzada de la feature de centres | Qui ja sap QUÈ vol estudiar i espera ON | L'estratègia de snapshots de centres del pla 015 (estats anunciat/vigent/històric) | F1, F3 + pla 015 construït | M |
| F5 | **Itineraris formatius (A→B→C→D)** | La Llei 3/2022 fa els graus **acumulables**: els A i B són parts de certificats C, i els C connecten amb cicles D. Mostrar a cada fitxa "aquest grau forma part de…" i "des d'aquí pots arribar a…", com un mapa de ruta | Diferenciador fort: cap cercador ho mostra bé; or per a orientadors | Els codis ja porten l'estructura (`IFC_A_0123` ↔ família+grado); el registre estatal confirma la relació A/B⊂C | Spike previ per validar el mapeig real dels codis | L |
| F6 | **Cerca per ocupació/sortida professional** | "Vull ser soldador / cuidar gent gran" → graus que hi porten. El SEPE relaciona certificats amb ocupacions (el seu buscador per ocupació ja existeix) | Canvia el punt d'entrada: de "sé el nom del títol" a "sé què vull fer" — el cas real de la majoria | El vessant SEPE ja apareix als spikes 013/015 | Spike de la font SEPE | L |
| F7 | **Observatori de l'oferta FP** | Pàgina pública d'estadístiques: evolució del total per família/grado al llarg del temps, titulacions noves per any, famílies que creixen. Gràfics senzills | SEO i autoritat: contingut que mitjans i orientadors enllacen; la sèrie temporal ja s'acumula sola cada setmana | L'historial de refreshos ÉS la sèrie temporal (encara més net post-pla 006) | Cap (millor post-006) | M |
| F8 | **Exportació per a orientadors** | Exportar una llista/selecció a PDF o CSV amb format presentable per donar a un alumne; enllaç compartible de només-lectura d'una llista | Orientadors de secundària — públic professional que repeteix i prescriu | F2 (llistes); les fitxes todofp ja enllaçades | F1, F2 | M |
| F9 | **Multiidioma (ca/es)** | UI en castellà a més del català. Les dades ja són en castellà; només cal traduir la interfície | Dobla el públic potencial (àmbit estatal) amb cost contingut | Frontend petit (3 pàgines vives post-pla 008) | Cap | S-M |
| F10 | **API pública documentada** | Documentar `/api/ofertes` i el futur `/api/centres` com a API oberta amb token per a usuaris registrats (rate limit). Webs de centres i apps de tercers hi consumirien | Posiciona el projecte com LA font de dades FP consolidades; backlinks | L'API ja existeix — falta documentació, tokens i límits | F1 (tokens) | M |

**Descartades (perquè ningú les re-proposi sense context)**:
- *Mapa geolocalitzat de centres*: valuós, però absorbit dins F4/pla 015 —
  depèn que les fonts donin coordenades; no és feature autònoma.
- *PWA/mode offline*: cost alt, valor marginal per a un cercador de consulta
  puntual.

## El consell de palanca (recomanació del 2026-06-10)

**La seqüència amb més palanca és F1 → F3 → F4, amb F7 en paral·lel.**

Per què:
- **F3 (alertes) és la "killer feature" del login**: reutilitza la maquinària
  de diff que ja existirà (plans 005/006), dona a l'usuari una raó de pes
  per registrar-se des del dia u, i crea l'hàbit de tornar. Un login sense
  F3 és una porta sense res a dins.
- **F4 n'és la continuació natural** quan el pla 015 (centres) estigui
  construït: mateixa infraestructura d'alertes, aplicada a "on" en lloc de
  "què". El valor compost F3+F4 ("t'aviso quan surti el grau I quan
  s'obri un centre a prop") és el que cap competidor té.
- **F7 (observatori) corre en paral·lel sense dependre de res**: és públic,
  barat (la sèrie temporal ja s'acumula sola) i fa feina de màrqueting
  (SEO, enllaços) mentre es construeix la part privada.
- **F9 (multiidioma) és el comodí barat**: S-M, independent, es pot encaixar
  en qualsevol forat.
- **F5 i F6 són els diferenciadors grans** (itineraris i cerca per
  ocupació): valor enorme però necessiten spike propi de fonts abans de
  comprometre-s'hi. Programar-los quan la base (F1–F3) estigui rodada.

### Onades recomanades

```
ONADA 0 (en curs)    : plans 001–012 (sanejament) + spikes 013/014/015
ONADA 1 (públic)     : F7 observatori  ·  F9 multiidioma     [sense login]
ONADA 2 (fonament)   : F1 login                              [spike 016 → construcció]
ONADA 3 (retenció)   : F3 alertes  →  F2 favorits/llistes    [spike 017]
ONADA 4 (compost)    : F4 seguiment de centres (post-015) · F8 exportació (post-F2) · F10 API (post-F1)
ONADA 5 (diferenciar): F5 itineraris · F6 cerca per ocupació [spikes propis]
```

## Estat dels spikes/plans per feature

| Feature | Spike/pla de disseny | Estat |
|---|---|---|
| F1 | plans 023–026 | DONE |
| F2 | plans 028–029 (favorits/llistes) | DONE |
| F3 | plans 028–029 (alertes) | DONE |
| F7 | plans 030–032; pla 033 pendent (~juliol, espera ≥4 setm. dades) | PARCIAL |
| F8 | plans 034–035 (CSV + centres) | DONE |
| F4 | plans 038–039 | TODO — plans generats 2026-06-18 |
| F9 | pendent de generar spike | TODO — independent, esforç S-M |
| F10 | pendent de generar spike | TODO — depèn de F1 ✓ |
| F5 | pendent de generar spike | TODO — necessita spike de fonts (itineraris A→B→C→D) |
| F6 | spike `.planning/spikes/001-003` | DONE 2026-06-20 — font `/pdfPT` validada (C 99,8%, D 100%, E 93%); pendent de planificar implementació |

## Ordre recomanat per als propers plans

> **OBSOLET (F1–F9 DONE).** Vegeu secció «Pròximes direccions post-F10» per a l'ordre actual.

1. ~~**F4** — Seguiment de centres~~ DONE
2. ~~**F9** — Multiidioma ca/es~~ DONE
3. ~~**F10** — API pública documentada~~ DESCARTAT a curt termini
4. ~~**F5** — Itineraris formatius~~ DONE
5. ~~**F6** — Cerca per ocupació/SEPE~~ DONE

---

## Pròximes direccions post-F10

Auditoria de direcció del 2026-06-21 (commit `2b4fa22`). Amb el roadmap F1–F10
completat, aquestes són les oportunitats de major palanca identificades.

| # | Direcció | Valor | Esforç | Pla | Estat |
|---|----------|-------|--------|-----|-------|
| A | **Renovació automàtica d'`ocupaciones.json`** al pipeline (nou endpoint admin + job) | Manteniment dades F6 | S | [049](../049-renovacio-automatica-ocupaciones.md) | TODO |
| B | **Cerca d'ocupació en català** — sinònims CA↔ES + regles de sufix `-ació/-ació→-acion`, `-tat→-dad` | UX / accessibilitat lingüística | S–M | [050](../050-sinonims-ca-es-cerca-ocupacio.md) | TODO |
| C | **SEO: pàgines de grau amb URL pròpia** (`/grau/<codigo>`) — SSR Jinja2, 1.500+ pàgines indexables | Creixement orgànic | L | pendent | — |
| D | **Dashboard d'usuari centralitzat** (`perfil.html`) — favorits + alertes + seguiment en una sola pàgina | Retenció | M | [051](../051-dashboard-perfil-usuari.md) | TODO |
| E | **Analytics bàsiques d'ús** — event log anònim a SQLite (cerques, clics, accions) | Decisió de producte | S–M | pendent | — |

### Evidència per direcció

**A** — `scripts/generate_ocupaciones.py` és d'execució manual (~2-3 min). El
`pipeline.py:run()` no l'inclou. Si el ministeri afegeix titulacions noves (passa
cada trimestre), `ocupaciones.json` queda desactualitzat sense avís.

**B** — Spike 003 (`.planning/spikes/003-reverse-search-feel`) anota explícitament:
«les queries en català retornen 0 resultats sobre dades castellanes». La funció
`_norm_ocup()` a `app.py:797` fa word-boundary match directament sense cap capa
de traducció. Sufixos sistemàtics: `-ació` (CA) ≠ `-acion` (ES), `-itat` ≠ `-idad`,
`-ment` ≠ `-miento/-amiento`, `-atge` ≠ `-aje`.

**C** — Tot el cercador és SPA client-side; Google no indexa cap grau concret.
`/api/ficha-redirect` fa un redirect temporal. 1.500+ graus sense URL indexable
= oportunitat SEO perduda.

**D** — Features d'usuari disperses entre 3 llocs: favorits (inline a `index.html`),
alertes (`alertes.html`), seguiment (`seguiment.html`). No hi ha pàgina de perfil.

**E** — No hi ha cap registre d'ús (cerques, graus visitats, famílies populars).
Sense dades d'ús les decisions de producte es prenen intuïtivament.

### Ordre recomanat

**Ara (curt termini):** A + B — baix cost, manteniment de la qualitat de F6.
**Mig termini:** D — consolida la inversió de F1–F4.
**Inversió:** C — alta palanca SEO si el creixement orgànic és objectiu.
**Quan hi hagi usuaris actius:** E — les analítiques valen quan hi ha mostra.

Quan toqui una feature, demanar `/improve plan <descripció>` per generar el pla corresponent.
