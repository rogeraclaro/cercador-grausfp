# Itinerari visual dels graus A→B→C→D→E — disseny

**Data:** 2026-10-23 · **Estat:** aprovat pel propietari (sessió de *grilling*), pendent d'executar.
**Plans:** 071 (backend), 072 (pàgina + timeline + arbre), 073 (graf), 074 (dades E).
**Maqueta de referència:** https://claude.ai/artifact/8VUN8EBhey4EesvXa19U5d (privada del propietari; tres formes amb l'exemple real `ADG_C_001_3B`).

## La idea, en una frase

Quan tries un grau, veure'l al centre d'un esquema amb **de què està fet** (a l'esquerra) i **cap on porta** (a la dreta), al llarg dels cinc graus A → B → C → D → E.

Els graus del sistema FP (Llei 3/2022) s'encaixen: un B està format per diversos A; un C conté diversos B; un C porta a cicles D (mòduls compartits); un D dona accés a cursos E. Avui això només es veu a trossos (insígnies i llistes al panell de detall del cercador, un sol nivell cada cop).

## Decisions (totes del propietari)

| # | Decisió |
|---|---|
| Públic | Estudiants/famílies **i** orientadors, però pensat sobretot per a l'estudiant: "on soc i cap on puc anar". |
| Direcció | Totes dues alhora: el grau triat al centre, components a l'esquerra, destinacions a la dreta. |
| Forma (ordinador) | **Timeline per columnes** A·B·C·D·E amb línies (forma A de la maqueta) per defecte, i una pestanya **Graf** interactiu (forma C). |
| Forma (mòbil) | **Arbre desplegable** (forma B). Canvi automàtic per amplada (~760 px). A l'ordinador, botó per forçar l'arbre. Al mòbil no s'ofereix el graf. |
| Graf | **Cytoscape.js** vendoritzat a `frontend/vendor/`, carregat només a `itinerari.html`. Excepció explícita a la regla "vanilla + Alpine" (s'ha d'afegir al `CLAUDE.md`). Arrossegar, zoom i **exploració**: doble clic en un node hi afegeix els seus veïns. |
| On | Pàgina pública pròpia `itinerari.html` (URL compartible) **i** al panell de detall del cercador una línia resum `A (4) → B (3) → [C] → D (1)` amb botó "Veure itinerari complet". Accessible des dels graus A, B, C i D (i E quan hi hagi dades). |
| Accés | Pública, sense sessió. |
| Interacció | Clic en un element = **recentrar** la vista en aquell grau. Enllaç separat a la fitxa oficial. |
| Pla antic / nou | Tot junt; els elements LOE porten l'etiqueta "pla antic" com al cercador. No s'amaguen enllaços entre plans. |
| Columnes llargues | Primers 5 elements i "+N més" desplegable; primer els de la mateixa família. |
| Idiomes | CA/ES amb `i18n.js`. Les denominacions surten com les dona el ministeri. |
| Columna E | Amagada fins que el pla 074 aporti la relació D→E. |
| Dades D→E | Scraper de les pàgines de todofp dels cursos d'especialització (secció "Requisitos de acceso"): lligar per enllaç, si no per nom normalitzat, i un fitxer de correspondències manual versionat per als casos en prosa. Els títols no lligats s'avisen a l'admin. |

## Estat actual de les dades (verificat 2026-10-23)

- **A↔B LOMLOE:** pel codi (`FAM_A_NNNN_PP` → `FAM_B_NNNN`), `backend/itinerary.py:76-79,104-107`. **A↔B LOE:** `a_loe_pares.json` (`{UF: [MF,…]}`), molts-a-molts (un A fins a 23 B). Cobertura: 8.726 de 8.730 A tenen B.
- **B↔C LOE:** `bc_loe.json` (`{C: [UC####_N]}`, B `MF####_N` ↔ `UC####_N`), `itinerary.py:60-63`, índex invers `app.py:~1547`. **B↔C LOMLOE:** `bc_lomloe.json`, invers `app.py:~1201-1230`.
- **C LOMLOE→D:** `backend/cd_lomloe.py` (mateixa família i mòduls B compartits; cada enllaç porta `{id, shared, total}`). **C LOE→D:** `ciclos_fp.json` (scraper `/ciclosFP`), entrades `{denominacion, familia, ficha_url}` **sense id de D**.
- **D→C:** no existeix (s'ha d'invertir). **D→E:** no existeix (pla 074).
- Registres D i E: sense `codigo`; s'identifiquen per `id`; tenen `ficha_url` (todofp).
- `/api/itinerari` (`app.py:~1733-1875`) només A/B/C i **un sol nivell**; el frontend no fa servir `children_a`.
- Mides típiques: un B té 2–10 A (mediana 4); un C LOE té 0–15 B (mediana 4); un B LOE és a 1–21 C.
- Volum: A 8.730 · B 2.952 · C 981 · D 195 · E 36 (+2 a todofp).

## Model de dades comú (el defineix el pla 071)

- **Clau de node:** `"{grado}:{codigo}"` per a A/B/C i `"{grado}:{id}"` per a D/E (p. ex. `C:ADG_C_001_3B`, `D:12776`).
- **Node:** `{key, grado, codigo|null, id|null, denominacion, familia, nivel, plan_antiguo, ficha}` on `ficha` és l'enllaç a la fitxa oficial (`/api/ficha-redirect?...` per a A/B/C, `ficha_url` per a D/E).
- **Aresta:** `{from, to, kind}` sempre dirigida "cap amunt" (A→B, B→C, C→D, D→E); `kind` ∈ `ab`, `bc`, `cd`, `de`; les `cd` LOMLOE porten `shared`/`total`.
- **Cadena completa des del focus:** tots els **ascendents** (seguint arestes cap amunt) i tots els **descendents** (cap avall), no els "germans" d'altres branques. L'exploració del graf demana veïns d'un node concret (`depth=1`).

## Fora d'abast

- Xarxa sencera d'una família (massa nodes).
- Graf al mòbil.
- Canviar el cercador més enllà de la línia resum i el botó.
