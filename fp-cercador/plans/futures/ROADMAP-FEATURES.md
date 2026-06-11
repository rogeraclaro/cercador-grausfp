# Roadmap de funcionalitats futures — Cercador FP España

> Document de visió generat el 2026-06-10 (sessió /improve, commit `5dc92a1`),
> aprovat pel propietari: **les 10 funcionalitats seleccionades**. Aquest
> document és la referència; els plans de spike/disseny individuals (016+)
> es generen per onades a mesura que s'ataquen.

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
| F1 | `plans/016-spike-login-fonament.md` | TODO |
| F3 | `plans/017-spike-alertes-novetats.md` | TODO |
| F7 | `plans/018-spike-observatori-oferta.md` | TODO |
| F2, F4, F5, F6, F8, F9, F10 | pendents de generar (per onades; demanar a /improve quan toqui) | — |

Quan una onada s'acosti, generar els spikes que faltin amb el mateix patró
(013–018) i afegir-los aquí i a `plans/README.md`.
