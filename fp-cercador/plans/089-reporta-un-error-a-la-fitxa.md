# Pla 089 — «Reporta un error en aquesta fitxa»

Origen: auditoria 2026-11-14, idea 9 de 9. El propietari la va triar; les decisions tècniques
d'aquest pla són del redactor i es poden discutir abans d'executar-lo.
Executable per un agent sense context, en una sessió nova. Depèn de: 069 (suggeriments), 076
(`ref`), tots DONE. Pla petit.

## Què fa

Des de cada grau (fila desplegada del cercador, itinerari i pàgina pública), un enllaç «Hi ha
un error en aquesta fitxa?» obre el formulari de suggeriments que ja existeix, amb el tipus
«Dades incorrectes» triat i el grau identificat, i a l'administració el comentari arriba amb
un enllaç directe al grau.

## Fets verificats (2026-11-14, no repetir)

- `frontend/feedback.js` munta la pestanya i el diàleg de suggeriments a totes les pàgines
  que el carreguen. Tipus: `error`, `idea`, `data` («Dades incorrectes»), `other`. Envia
  `{kind, message, context: pageContext(), website}` a `POST /api/feedback`. `open()` és
  una funció interna (línia ~139), **no s'exposa** a `window`.
- Taula `feedback` (migració 011): `id, user_id, email, kind, message, context, status,
  admin_note, created_at, updated_at`. `context` és text lliure.
- Backend: `/api/feedback` (~línia 3728 de `backend/app.py`), valida `kind` contra
  `_FEEDBACK_KINDS`, longitud màxima `_FEEDBACK_MAX_CHARS`, límit per IP, i avisa per correu
  a `FEEDBACK_NOTIFY_EMAIL`.
- El panell d'admin té la pestanya «Suggeriments» (`admin.html`).
- Les pàgines públiques `/grau/<ref>` es generen a `backend/grau_page.py::render_grau` i
  carreguen `i18n.js` i `auth.js`; comproveu si carreguen `feedback.js`.
- Fila desplegada del cercador: accions a prop de `.row-share-menu` (`index.html`).

## Disseny

- `feedback.js` exposa `window.grausfpFeedback = { open: function (opts) {…} }`, on `opts`
  pot portar `{kind, ref, label}`. En obrir amb `ref`:
  - es tria el tipus `data`;
  - sobre el camp de text surt «Sobre: *<label>*», que es pot treure amb ✕;
  - el `context` enviat passa a ser un objecte serialitzat que inclou el de la pàgina més
    `ref`.
- Backend: `context` continua sent text. Si arriba un `ref` (camp nou del cos, opcional),
  es valida amb `oferta_ref.REF_RE` i contra el catàleg i es desa en una **columna nova**
  `feedback.oferta_ref` (migració, el número següent lliure). Un `ref` invàlid s'ignora
  (no és motiu per rebutjar el comentari).
- Correu d'avís a l'admin i pestanya «Suggeriments»: quan hi ha `oferta_ref`, mostren la
  denominació del grau i un enllaç a `/grau/<ref>`.
- Punts d'entrada:
  - `index.html`: a la fila desplegada, enllaç discret «Hi ha un error en aquesta fitxa?»;
  - `itinerari.html`: a la capçalera del grau enfocat;
  - `/grau/<ref>`: al peu del contingut. Si la pàgina pública no carrega `feedback.js`,
    carregueu-lo (la pàgina ha de continuar funcionant sense JavaScript: l'enllaç s'afegeix
    amb el script, no al HTML estàtic).
- Si `feedback.js` no ha carregat, l'enllaç no surt.

## Fases

1. Backend: migració, camp `ref`, validació, correu i resposta de la llista d'admin. Tests a
   `tests/test_feedback_api.py`: amb `ref` vàlid, invàlid, inexistent, i sense.
2. `feedback.js`: API pública, etiqueta «Sobre: …», tipus preseleccionat. Comprovar que la
   pestanya normal continua igual.
3. Punts d'entrada a les tres pàgines + `admin.html`.
4. Textos (`fb.about`, `index.report`, ca i es), `?v=` i `I18N_VERSION`.
5. Verificació al navegador, ca i es: reportar des d'una fila, veure-ho a l'admin amb
   l'enllaç al grau; teclat (el focus torna a l'enllaç en tancar el diàleg); 375 px.

## STOP — atura't i pregunta

- No enviïs cap correu real durant les proves.
- No desplegar sense aprovació explícita. Mai reiniciar diumenge 11:10–11:45.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
