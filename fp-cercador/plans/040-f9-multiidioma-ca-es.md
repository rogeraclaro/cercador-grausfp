# Pla 040 — F9 Multiidioma CA/ES

**Commit de referència:** `66c500a`
**Generat:** 2026-06-18
**Estat:** DONE — commit `8cea11c` a branca `worktree-agent-a24abde7fa7f3f668` (pendent de merge)

---

## Context i objectiu

Afegir castellà (es) com a segon idioma de la interfície. Les dades del
catàleg ja són en castellà; cal traduir els textos de la UI. L'idioma triat
es desa a `localStorage` i es recorda entre sessions. Un selector CA / ES
apareix a la topbar de totes les pàgines.

**Decisió d'arquitectura (presa pel propietari):**
Estratègia A1 — un sol fitxer `frontend/i18n.js` amb un diccionari hardcoded
(`const TRANSLATIONS = { ca: {...}, es: {...} }`). Es carrega síncronament
al `<head>` de cada pàgina, exposa `window.t(key)` i `window.setLang(lang)`.
Cap framework i18n extern, cap fetch async, sense dependències noves.

---

## Pàgines en abast

| Fitxer | Contingut |
|--------|-----------|
| `frontend/i18n.js` | NOU: diccionari + runtime |
| `frontend/auth.js` | Strings d'autenticació al widget topbar |
| `frontend/alertes.js` | Strings de la gestió d'alertes |
| `frontend/index.html` | Cercador principal (Alpine.js) |
| `frontend/alertes.html` | Gestió d'alertes (HTML estàtic + `alertes.js`) |
| `frontend/seguiment.html` | Seguiment de centres (HTML + JS inline) |
| `frontend/login.html` | Formulari login (HTML + JS inline) |
| `frontend/register.html` | Formulari registre (HTML + JS inline) |
| `frontend/forgot-password.html` | Formulari contrasenya oblidada (HTML + JS inline) |
| `frontend/reset-password.html` | Formulari nova contrasenya (HTML + JS inline) |
| `frontend/observatori.html` | Observatori FP (HTML + JS inline) |
| `frontend/historial.html` | Historial d'actualitzacions (HTML + JS inline) |
| `frontend/politica-privacitat.html` | Política de privacitat |

**Exclosos d'aquest pla:** `admin.html` (interfície interna).

---

## STOP conditions

- Si en qualsevol pàgina trobes un string en JS que interacciona amb
  l'API (missatge d'error del servidor, text del `data.error`) i NO surt
  del codi de l'app sinó de la resposta JSON del backend, NO el tradueixes
  ni el passes per `t()`. Deixa'l com a `data.error` directe.
- Si Alpine.js deixa de funcionar al fer els canvis a `index.html`, ATURA't
  i reporta. No segueixis amb les altres pàgines.

---

## Pas 1 — Crear `frontend/i18n.js`

Crea el fitxer nou `frontend/i18n.js` amb exactament el contingut següent.
**NO modifiquis cap altra cosa en aquest pas.**

```js
(function () {
  var TRANSLATIONS = {
    ca: {
      /* ── Topbar / auth widget ── */
      'nav.greeting':        'Hola, {email}',
      'nav.logout':          'Sortir',
      'nav.login':           'Entra',
      'nav.register':        "Registra't",
      'nav.lang.ca':         'CA',
      'nav.lang.es':         'ES',

      /* ── Topbar logos (per a <title> de pàgina) ── */
      'page.title.index':    'Cercador Graus FP',
      'page.title.alertes':  'Les meves alertes — Cercador Graus FP',
      'page.title.seguiment':'Seguiment de centres — Cercador Graus FP',
      'page.title.login':    'Inicia sessió — Cercador Graus FP',
      'page.title.register': 'Crea un compte — Cercador Graus FP',
      'page.title.forgot':   'Restablir contrasenya — Cercador Graus FP',
      'page.title.reset':    'Nova contrasenya — Cercador Graus FP',
      'page.title.obs':      "Observatori de l'oferta FP — Cercador Graus FP",
      'page.title.historial':'Historial — Cercador Graus FP',
      'page.title.privacitat':'Política de privacitat — Cercador Graus FP',

      /* ── auth.js — toast ── */
      'auth.verified.toast': '✓ Compte verificat. Ja pots iniciar sessió.',

      /* ── index.html — hero ── */
      'index.hero.h1.line1':   'Formació',
      'index.hero.h1.line2':   'Professional',
      'index.hero.sub':        "Explora els graus disponibles a l'estat espanyol",
      'index.search.placeholder': 'Cerca per denominació o codi...',
      'index.search.label':    'Cerca',

      /* ── index.html — grau tabs ── */
      'index.tabs.all':        'Tots els graus',
      'index.tabs.aria':       'Filtre per grau',

      /* ── index.html — filter bar ── */
      'index.filter.label':    'Filtrar per:',
      'index.filter.allFam':   'Totes les famílies',
      'index.filter.allNiv':   'Tots els nivells',
      'index.filter.niv1':     'Nivell 1',
      'index.filter.niv2':     'Nivell 2',
      'index.filter.niv3':     'Nivell 3',
      'index.filter.all':      "Veure'ls tots",
      'index.filter.hideOld':  'Ocultar pla antic',
      'index.filter.onlyOld':  'Només pla antic',
      'index.filter.favs':     'Favorits',
      'index.btn.alerts':      'Veure alertes',
      'index.btn.saveAlert':   '🔔 Desa com a alerta',
      'index.btn.exportCsv':   '↓ Exporta CSV',
      'index.btn.clearFilters':'Esborrar filtres ×',

      /* ── index.html — states ── */
      'index.loading':         'Carregant dades del catàleg FP...',
      'index.error':           "⚠️ Les dades del catàleg no estan disponibles. Contacteu l'administrador del sistema.",
      'index.results.zero':    'Cap resultat coincideix amb els filtres aplicats',
      'index.results.one':     '1 resultat trobat',
      'index.results.many':    '{n} resultats trobats',

      /* ── index.html — taula ── */
      'index.col.nom':         'Denominació',
      'index.col.codi':        'Codi',
      'index.col.fam':         'Família professional',
      'index.col.grau':        'Grau',
      'index.col.niv':         'Nivell',
      'index.table.caption':   'Resultats del cercador de Graus FP',
      'index.table.empty':     'Cap resultat coincideix amb els filtres aplicats.',
      'index.fav.add':         'Afegeix als favorits',
      'index.fav.remove':      'Treu dels favorits',
      'index.badge.old':       'Pla antic',
      'index.centres.count':   '{n} centres',

      /* ── index.html — centres panel ── */
      'index.centres.placeholder': 'Cerca centre o població…',
      'index.centres.loading': 'Carregant centres…',
      'index.centres.all.ccaa': 'Totes',
      'index.centres.watch':   'Seguir centres',
      'index.centres.watching':'Seguint centres →',
      'index.centres.saved':   '✓ Seguiment desat!',
      'index.centres.maxSel':  'Màxim 5 centres seleccionats',
      'index.centres.upsell':  "Registra't per a veure'ls tots",
      'index.centres.more':    '... i {n} centres més',
      'index.centres.empty':   'Cap centre trobat per a aquesta comunitat.',

      /* ── index.html — CSV export ── */
      'csv.header.codi':       'Codi',
      'csv.header.denom':      'Denominació',
      'csv.header.fam':        'Família',
      'csv.header.grau':       'Grau',
      'csv.header.niv':        'Nivell',
      'csv.header.old':        'Pla antic',
      'csv.header.centres':    'Centres seleccionats',
      'index.btn.exportTitle': 'Exporta {n} registres a CSV',

      /* ── index.html — paginació ── */
      'pagination.aria':       'Paginació de resultats',
      'pagination.showing':    'Mostrant {start}–{end} de {total}',
      'pagination.prev':       '← Anterior',
      'pagination.next':       'Següent →',
      'pagination.page':       'Pàgina {n}',

      /* ── index.html — modals ── */
      'modal.alert.ok':        '✓ Alerta desada correctament',
      'modal.alert.sub':       "Rebràs un email quan hi hagi nous ensenyaments que encaixin amb els teus filtres.",
      'modal.alert.view':      'Veure les meves alertes',
      'modal.alert.continue':  'Continuar cercant',
      'modal.alert.close':     'Tancar',
      'modal.gate.msg':        "Registra't o entra amb el teu usuari per a accedir a tota la informació",
      'modal.gate.register':   'Registrar-me',
      'modal.gate.later':      'Ara no',
      'modal.gate.login':      'Entrar',

      /* ── index.html — errors inline JS ── */
      'index.err.boe.missing': 'URL del BOE no disponible per a aquest certificat.',
      'index.err.boe.fetch':   'Error en obtenir el BOE: ',
      'index.err.watch.unknown': 'Error desconegut',
      'index.err.watch.network': 'Error de xarxa',

      /* ── index.html — footer ── */
      'index.footer.historial':'Historial d\'actualitzacions',
      'index.footer.obs':      'Observatori',

      /* ── alertes.html ── */
      'alertes.hero.h1':       'Les meves',
      'alertes.hero.h1.em':    'alertes',
      'alertes.hero.sub':      "Rebràs un email quan apareguin nous ensenyaments que encaixin amb els teus filtres",
      'alertes.footer.back':   '← Tornar al cercador',

      /* ── alertes.js ── */
      'alertes.loading':       'Carregant alertes...',
      'alertes.login.required':"Cal <a href=\"login.html\">iniciar sessió</a> per veure les teves alertes.",
      'alertes.error':         'Error carregant les alertes.',
      'alertes.empty':         "Encara no tens cap alerta configurada.<br>Aplica filtres al cercador i clica \"Desa com a alerta\".",
      'alertes.col.filter':    'Filtre',
      'alertes.col.created':   'Creada',
      'alertes.col.sent':      'Darrer enviament',
      'alertes.col.state':     'Estat',
      'alertes.state.active':  'Activa',
      'alertes.state.inactive':'Inactiva',
      'alertes.filter.niv':    'Nivell ',
      'alertes.filter.all':    'Tots els nous ensenyaments',
      'alertes.err.toggle':    'Error canviant estat: ',
      'alertes.confirm.delete':"Elimines aquesta alerta?",
      'alertes.err.delete':    'Error eliminant alerta: ',
      'alertes.aria.delete':   'Eliminar alerta',

      /* ── seguiment.html ── */
      'seguiment.hero.h1':     'Seguiment de centres',
      'seguiment.hero.sub':    "Rebràs un email quan apareguin nous centres que impartiran els ensenyaments que segueixes.",
      'seguiment.loading':     'Carregant seguiments…',
      'seguiment.empty':       "Encara no segueixes cap ensenyament.<br>Obre el panell de centres d'un ensenyament al <a href=\"index.html\">cercador</a> i clica \"Seguir centres\".",
      'seguiment.col.ens':     'Ensenyament',
      'seguiment.col.prov':    'Província',
      'seguiment.col.created': 'Creat',
      'seguiment.col.sent':    'Darrer enviament',
      'seguiment.col.state':   'Estat',
      'seguiment.state.active':'Actiu',
      'seguiment.state.inactive':'Inactiu',
      'seguiment.all.prov':    'Totes',
      'seguiment.err.delete':  'Error eliminant el seguiment: ',
      'seguiment.err.toggle':  'Error canviant estat: ',
      'seguiment.error':       'Error carregant els seguiments.',
      'seguiment.footer.back': '← Tornar al cercador',
      'seguiment.footer.alerts':'Les meves alertes',
      'seguiment.footer.priv': 'Política de privacitat',

      /* ── login.html ── */
      'login.h1':              'Inicia sessió',
      'login.pw.label':        'Contrasenya',
      'login.btn.submit':      'Entra',
      'login.btn.submitting':  'Entrant…',
      'login.link.forgot':     'Has oblidat la contrasenya?',
      'login.link.register':   "Sense compte? Registra't",
      'login.msg.verified':    'Compte verificat correctament. Ja pots entrar.',
      'login.err.default':     'Error en iniciar sessió.',
      'login.err.network':     'Error de connexió. Torna-ho a intentar.',

      /* ── register.html ── */
      'register.h1':           'Crea un compte',
      'register.pw.label':     'Contrasenya',
      'register.pw2.label':    'Confirma la contrasenya',
      'register.pw.placeholder':  'Mínim 8 caràcters',
      'register.pw2.placeholder': 'Repeteix la contrasenya',
      'register.gdpr':         "He llegit i accepto la <a href=\"politica-privacitat.html\" target=\"_blank\">política de privacitat</a>. Autoritzo el tractament del meu email per a l'autenticació i, si ho sol·licito, per rebre alertes personalitzades.",
      'register.btn.submit':   'Crea el compte',
      'register.btn.submitting':'Creant compte…',
      'register.link.login':   'Ja tens compte? Inicia sessió',
      'register.msg.ok':       'Compte creat. Revisa el teu email per verificar-lo.',
      'register.err.pw.match': 'Les contrasenyes no coincideixen.',
      'register.err.default':  'Error en crear el compte.',
      'register.err.network':  'Error de connexió. Torna-ho a intentar.',

      /* ── forgot-password.html ── */
      'forgot.h1':             'Restablir contrasenya',
      'forgot.subtitle':       "Introdueix el teu email i t'enviarem un link per restablir la contrasenya.",
      'forgot.btn.submit':     'Envia el link',
      'forgot.btn.submitting': 'Enviant…',
      'forgot.link.back':      'Torna a Inicia sessió',
      'forgot.msg.ok':         "Si l'email existeix, rebràs un missatge en breus.",
      'forgot.err.network':    'Error de connexió. Torna-ho a intentar.',

      /* ── reset-password.html ── */
      'reset.h1':              'Nova contrasenya',
      'reset.pw.label':        'Nova contrasenya',
      'reset.pw2.label':       'Confirma la contrasenya',
      'reset.pw.placeholder':  'Mínim 8 caràcters',
      'reset.pw2.placeholder': 'Repeteix la contrasenya',
      'reset.btn.submit':      'Desa la contrasenya',
      'reset.btn.submitting':  'Desant…',
      'reset.link.back':       'Torna a Inicia sessió',
      'reset.err.invalid.token':"Enllaç invàlid o caducat. Sol·licita un nou link de restabliment.",
      'reset.err.pw.match':    'Les contrasenyes no coincideixen.',
      'reset.err.pw.short':    'La contrasenya ha de tenir almenys 8 caràcters.',
      'reset.msg.ok':          'Contrasenya actualitzada correctament.',
      'reset.err.default':     'Error en desar la contrasenya.',
      'reset.err.network':     'Error de connexió. Torna-ho a intentar.',

      /* ── observatori.html ── */
      'obs.hero.h1':           "Observatori<br><em>de l'oferta FP</em>",
      'obs.hero.sub':          'Evolució setmanal del catàleg de Formació Professional espanyol',
      'obs.stat.total.label':  'Titulacions actives',
      'obs.stat.graus.label':  'Graus (A–E)',
      'obs.stat.date.label':   'Darrera actualització',
      'obs.section.evolution': 'Evolució del total de titulacions',
      'obs.section.dist':      'Distribució per grau',
      'obs.section.novetats':  'Darreres novetats',
      'obs.loading':           'Carregant dades...',
      'obs.loading.short':     'Carregant...',
      'obs.few.data':          'Poques dades per mostrar una tendència (mínim 2 refreshos).',
      'obs.novetats.empty':    'Sense novetats recents',
      'obs.novetats.no.detail':'Sense denominacions detallades',
      'obs.footer.note':       'Font: Ministerio de Educación, FP.es (todofp.es). Actualitzat automàticament cada setmana.',
      'obs.footer.historial':  "← Veure l'historial complet",

      /* ── historial.html ── */
      'hist.hero.h1':          "Historial<br><em>d'actualitzacions</em>",
      'hist.hero.sub':         'Registre de les darreres actualitzacions del catàleg FP',
      'hist.loading':          'Carregant historial...',
      'hist.empty':            "Encara no hi ha cap actualització registrada.",
      'hist.col.num':          '#',
      'hist.col.date':         'Data',
      'hist.col.total':        'Total',
      'hist.col.changes':      'Canvis',
      'hist.changes.first':    'Primer registre',
      'hist.changes.none':     'Sense canvis',
      'hist.changes.added':    '+ Nous ({n})',
      'hist.changes.removed':  '− Eliminats ({n})',
      'hist.footer.back':      '← Tornar al cercador',
      'hist.footer.obs':       'Observatori',

      /* ── politica-privacitat.html ── */
      'priv.h1':               'Política de privacitat',
      'priv.badge':            'Text provisional — es completarà abans del llançament públic',
      'priv.footer.back':      '← Tornar al cercador',
    },

    es: {
      /* ── Topbar / auth widget ── */
      'nav.greeting':        'Hola, {email}',
      'nav.logout':          'Salir',
      'nav.login':           'Entrar',
      'nav.register':        'Regístrate',
      'nav.lang.ca':         'CA',
      'nav.lang.es':         'ES',

      /* ── Títols de pàgina ── */
      'page.title.index':    'Buscador Grados FP',
      'page.title.alertes':  'Mis alertas — Buscador Grados FP',
      'page.title.seguiment':'Seguimiento de centros — Buscador Grados FP',
      'page.title.login':    'Iniciar sesión — Buscador Grados FP',
      'page.title.register': 'Crear cuenta — Buscador Grados FP',
      'page.title.forgot':   'Restablecer contraseña — Buscador Grados FP',
      'page.title.reset':    'Nueva contraseña — Buscador Grados FP',
      'page.title.obs':      'Observatorio de la oferta FP — Buscador Grados FP',
      'page.title.historial':'Historial — Buscador Grados FP',
      'page.title.privacitat':'Política de privacidad — Buscador Grados FP',

      /* ── auth.js — toast ── */
      'auth.verified.toast': '✓ Cuenta verificada. Ya puedes iniciar sesión.',

      /* ── index.html — hero ── */
      'index.hero.h1.line1':   'Formación',
      'index.hero.h1.line2':   'Profesional',
      'index.hero.sub':        'Explora los grados disponibles en el estado español',
      'index.search.placeholder': 'Buscar por denominación o código...',
      'index.search.label':    'Buscar',

      /* ── index.html — grau tabs ── */
      'index.tabs.all':        'Todos los grados',
      'index.tabs.aria':       'Filtro por grado',

      /* ── index.html — filter bar ── */
      'index.filter.label':    'Filtrar por:',
      'index.filter.allFam':   'Todas las familias',
      'index.filter.allNiv':   'Todos los niveles',
      'index.filter.niv1':     'Nivel 1',
      'index.filter.niv2':     'Nivel 2',
      'index.filter.niv3':     'Nivel 3',
      'index.filter.all':      'Ver todos',
      'index.filter.hideOld':  'Ocultar plan antiguo',
      'index.filter.onlyOld':  'Solo plan antiguo',
      'index.filter.favs':     'Favoritos',
      'index.btn.alerts':      'Ver alertas',
      'index.btn.saveAlert':   '🔔 Guardar como alerta',
      'index.btn.exportCsv':   '↓ Exportar CSV',
      'index.btn.clearFilters':'Borrar filtros ×',

      /* ── index.html — states ── */
      'index.loading':         'Cargando datos del catálogo FP...',
      'index.error':           '⚠️ Los datos del catálogo no están disponibles. Contacte al administrador del sistema.',
      'index.results.zero':    'Ningún resultado coincide con los filtros aplicados',
      'index.results.one':     '1 resultado encontrado',
      'index.results.many':    '{n} resultados encontrados',

      /* ── index.html — taula ── */
      'index.col.nom':         'Denominación',
      'index.col.codi':        'Código',
      'index.col.fam':         'Familia profesional',
      'index.col.grau':        'Grado',
      'index.col.niv':         'Nivel',
      'index.table.caption':   'Resultados del buscador de Grados FP',
      'index.table.empty':     'Ningún resultado coincide con los filtros aplicados.',
      'index.fav.add':         'Añadir a favoritos',
      'index.fav.remove':      'Quitar de favoritos',
      'index.badge.old':       'Plan antiguo',
      'index.centres.count':   '{n} centros',

      /* ── index.html — centres panel ── */
      'index.centres.placeholder': 'Buscar centro o población…',
      'index.centres.loading': 'Cargando centros…',
      'index.centres.all.ccaa': 'Todas',
      'index.centres.watch':   'Seguir centros',
      'index.centres.watching':'Siguiendo centros →',
      'index.centres.saved':   '✓ Seguimiento guardado!',
      'index.centres.maxSel':  'Máximo 5 centros seleccionados',
      'index.centres.upsell':  'Regístrate para verlos todos',
      'index.centres.more':    '... y {n} centros más',
      'index.centres.empty':   'No se encontraron centros para esta comunidad.',

      /* ── index.html — CSV export ── */
      'csv.header.codi':       'Código',
      'csv.header.denom':      'Denominación',
      'csv.header.fam':        'Familia',
      'csv.header.grau':       'Grado',
      'csv.header.niv':        'Nivel',
      'csv.header.old':        'Plan antiguo',
      'csv.header.centres':    'Centros seleccionados',
      'index.btn.exportTitle': 'Exportar {n} registros a CSV',

      /* ── index.html — paginació ── */
      'pagination.aria':       'Paginación de resultados',
      'pagination.showing':    'Mostrando {start}–{end} de {total}',
      'pagination.prev':       '← Anterior',
      'pagination.next':       'Siguiente →',
      'pagination.page':       'Página {n}',

      /* ── index.html — modals ── */
      'modal.alert.ok':        '✓ Alerta guardada correctamente',
      'modal.alert.sub':       'Recibirás un email cuando haya nuevas enseñanzas que coincidan con tus filtros.',
      'modal.alert.view':      'Ver mis alertas',
      'modal.alert.continue':  'Continuar buscando',
      'modal.alert.close':     'Cerrar',
      'modal.gate.msg':        'Regístrate o entra con tu usuario para acceder a toda la información',
      'modal.gate.register':   'Registrarme',
      'modal.gate.later':      'Ahora no',
      'modal.gate.login':      'Entrar',

      /* ── index.html — errors inline JS ── */
      'index.err.boe.missing': 'URL del BOE no disponible para este certificado.',
      'index.err.boe.fetch':   'Error al obtener el BOE: ',
      'index.err.watch.unknown': 'Error desconocido',
      'index.err.watch.network': 'Error de red',

      /* ── index.html — footer ── */
      'index.footer.historial':'Historial de actualizaciones',
      'index.footer.obs':      'Observatorio',

      /* ── alertes.html ── */
      'alertes.hero.h1':       'Mis',
      'alertes.hero.h1.em':    'alertas',
      'alertes.hero.sub':      'Recibirás un email cuando aparezcan nuevas enseñanzas que coincidan con tus filtros',
      'alertes.footer.back':   '← Volver al buscador',

      /* ── alertes.js ── */
      'alertes.loading':       'Cargando alertas...',
      'alertes.login.required':"Es necesario <a href=\"login.html\">iniciar sesión</a> para ver tus alertas.",
      'alertes.error':         'Error al cargar las alertas.',
      'alertes.empty':         "Todavía no tienes ninguna alerta configurada.<br>Aplica filtros en el buscador y haz clic en \"Guardar como alerta\".",
      'alertes.col.filter':    'Filtro',
      'alertes.col.created':   'Creado',
      'alertes.col.sent':      'Último envío',
      'alertes.col.state':     'Estado',
      'alertes.state.active':  'Activa',
      'alertes.state.inactive':'Inactiva',
      'alertes.filter.niv':    'Nivel ',
      'alertes.filter.all':    'Todas las nuevas enseñanzas',
      'alertes.err.toggle':    'Error al cambiar estado: ',
      'alertes.confirm.delete':'¿Eliminar esta alerta?',
      'alertes.err.delete':    'Error al eliminar la alerta: ',
      'alertes.aria.delete':   'Eliminar alerta',

      /* ── seguiment.html ── */
      'seguiment.hero.h1':     'Seguimiento de centros',
      'seguiment.hero.sub':    'Recibirás un email cuando aparezcan nuevos centros que impartirán las enseñanzas que sigues.',
      'seguiment.loading':     'Cargando seguimientos…',
      'seguiment.empty':       "Todavía no sigues ninguna enseñanza.<br>Abre el panel de centros de una enseñanza en el <a href=\"index.html\">buscador</a> y haz clic en \"Seguir centros\".",
      'seguiment.col.ens':     'Enseñanza',
      'seguiment.col.prov':    'Provincia',
      'seguiment.col.created': 'Creado',
      'seguiment.col.sent':    'Último envío',
      'seguiment.col.state':   'Estado',
      'seguiment.state.active':'Activo',
      'seguiment.state.inactive':'Inactivo',
      'seguiment.all.prov':    'Todas',
      'seguiment.err.delete':  'Error al eliminar el seguimiento: ',
      'seguiment.err.toggle':  'Error al cambiar estado: ',
      'seguiment.error':       'Error al cargar los seguimientos.',
      'seguiment.footer.back': '← Volver al buscador',
      'seguiment.footer.alerts':'Mis alertas',
      'seguiment.footer.priv': 'Política de privacidad',

      /* ── login.html ── */
      'login.h1':              'Iniciar sesión',
      'login.pw.label':        'Contraseña',
      'login.btn.submit':      'Entrar',
      'login.btn.submitting':  'Entrando…',
      'login.link.forgot':     '¿Has olvidado la contraseña?',
      'login.link.register':   '¿Sin cuenta? Regístrate',
      'login.msg.verified':    'Cuenta verificada correctamente. Ya puedes entrar.',
      'login.err.default':     'Error al iniciar sesión.',
      'login.err.network':     'Error de conexión. Inténtalo de nuevo.',

      /* ── register.html ── */
      'register.h1':           'Crear una cuenta',
      'register.pw.label':     'Contraseña',
      'register.pw2.label':    'Confirmar contraseña',
      'register.pw.placeholder':  'Mínimo 8 caracteres',
      'register.pw2.placeholder': 'Repite la contraseña',
      'register.gdpr':         "He leído y acepto la <a href=\"politica-privacitat.html\" target=\"_blank\">política de privacidad</a>. Autorizo el tratamiento de mi email para la autenticación y, si lo solicito, para recibir alertas personalizadas.",
      'register.btn.submit':   'Crear la cuenta',
      'register.btn.submitting':'Creando cuenta…',
      'register.link.login':   '¿Ya tienes cuenta? Iniciar sesión',
      'register.msg.ok':       'Cuenta creada. Revisa tu email para verificarla.',
      'register.err.pw.match': 'Las contraseñas no coinciden.',
      'register.err.default':  'Error al crear la cuenta.',
      'register.err.network':  'Error de conexión. Inténtalo de nuevo.',

      /* ── forgot-password.html ── */
      'forgot.h1':             'Restablecer contraseña',
      'forgot.subtitle':       'Introduce tu email y te enviaremos un enlace para restablecer la contraseña.',
      'forgot.btn.submit':     'Enviar el enlace',
      'forgot.btn.submitting': 'Enviando…',
      'forgot.link.back':      'Volver a Iniciar sesión',
      'forgot.msg.ok':         'Si el email existe, recibirás un mensaje en breve.',
      'forgot.err.network':    'Error de conexión. Inténtalo de nuevo.',

      /* ── reset-password.html ── */
      'reset.h1':              'Nueva contraseña',
      'reset.pw.label':        'Nueva contraseña',
      'reset.pw2.label':       'Confirmar contraseña',
      'reset.pw.placeholder':  'Mínimo 8 caracteres',
      'reset.pw2.placeholder': 'Repite la contraseña',
      'reset.btn.submit':      'Guardar contraseña',
      'reset.btn.submitting':  'Guardando…',
      'reset.link.back':       'Volver a Iniciar sesión',
      'reset.err.invalid.token':'Enlace inválido o caducado. Solicita un nuevo enlace de restablecimiento.',
      'reset.err.pw.match':    'Las contraseñas no coinciden.',
      'reset.err.pw.short':    'La contraseña debe tener al menos 8 caracteres.',
      'reset.msg.ok':          'Contraseña actualizada correctamente.',
      'reset.err.default':     'Error al guardar la contraseña.',
      'reset.err.network':     'Error de conexión. Inténtalo de nuevo.',

      /* ── observatori.html ── */
      'obs.hero.h1':           'Observatorio<br><em>de la oferta FP</em>',
      'obs.hero.sub':          'Evolución semanal del catálogo de Formación Profesional español',
      'obs.stat.total.label':  'Titulaciones activas',
      'obs.stat.graus.label':  'Grados (A–E)',
      'obs.stat.date.label':   'Última actualización',
      'obs.section.evolution': 'Evolución del total de titulaciones',
      'obs.section.dist':      'Distribución por grado',
      'obs.section.novetats':  'Últimas novedades',
      'obs.loading':           'Cargando datos...',
      'obs.loading.short':     'Cargando...',
      'obs.few.data':          'Pocos datos para mostrar una tendencia (mínimo 2 refrescos).',
      'obs.novetats.empty':    'Sin novedades recientes',
      'obs.novetats.no.detail':'Sin denominaciones detalladas',
      'obs.footer.note':       'Fuente: Ministerio de Educación, FP.es (todofp.es). Actualizado automáticamente cada semana.',
      'obs.footer.historial':  '← Ver el historial completo',

      /* ── historial.html ── */
      'hist.hero.h1':          'Historial<br><em>de actualizaciones</em>',
      'hist.hero.sub':         'Registro de las últimas actualizaciones del catálogo FP',
      'hist.loading':          'Cargando historial...',
      'hist.empty':            'Todavía no hay ninguna actualización registrada.',
      'hist.col.num':          '#',
      'hist.col.date':         'Fecha',
      'hist.col.total':        'Total',
      'hist.col.changes':      'Cambios',
      'hist.changes.first':    'Primer registro',
      'hist.changes.none':     'Sin cambios',
      'hist.changes.added':    '+ Nuevos ({n})',
      'hist.changes.removed':  '− Eliminados ({n})',
      'hist.footer.back':      '← Volver al buscador',
      'hist.footer.obs':       'Observatorio',

      /* ── politica-privacitat.html ── */
      'priv.h1':               'Política de privacidad',
      'priv.badge':            'Texto provisional — se completará antes del lanzamiento público',
      'priv.footer.back':      '← Volver al buscador',
    }
  };

  var _lang = localStorage.getItem('lang') || 'ca';
  var _dict = TRANSLATIONS[_lang] || TRANSLATIONS['ca'];

  function _resolve(key) {
    return _dict[key] !== undefined ? _dict[key] : (TRANSLATIONS['ca'][key] || key);
  }

  window.t = function (key, vars) {
    var str = _resolve(key);
    if (!vars) return str;
    return str.replace(/\{(\w+)\}/g, function (_, k) { return vars[k] != null ? vars[k] : ''; });
  };

  window.getLang = function () { return _lang; };

  window.setLang = function (newLang) {
    localStorage.setItem('lang', newLang);
    location.reload();
  };

  /* Actualitza lang HTML i title de forma síncrona (head ja parsejat) */
  document.documentElement.lang = _lang;
  var titleEl = document.querySelector('title[data-i18n]');
  if (titleEl) titleEl.textContent = _resolve(titleEl.getAttribute('data-i18n'));

  /* Aplica traduccions als elements amb data-i18n un cop carregat el DOM */
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      if (el.tagName === 'TITLE') return; /* ja fet síncronament */
      var key = el.getAttribute('data-i18n');
      var html = _resolve(key);
      if (html !== key) el.innerHTML = html; /* permet HTML en els valors */
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      el.placeholder = _resolve(el.getAttribute('data-i18n-placeholder'));
    });
    document.querySelectorAll('[data-i18n-aria]').forEach(function (el) {
      el.setAttribute('aria-label', _resolve(el.getAttribute('data-i18n-aria')));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      el.title = _resolve(el.getAttribute('data-i18n-title'));
    });

    /* Actualitza lang selector visual */
    document.querySelectorAll('.lang-btn').forEach(function (btn) {
      btn.classList.toggle('lang-btn--active', btn.dataset.lang === _lang);
    });
  });
})();
```

**Verificació del pas 1:**
```
ls -la frontend/i18n.js  # ha d'existir
node -e "require('./frontend/i18n.js')" 2>&1 | head -5
# no ha de donar errors (el require fallarà per window/localStorage però no errors de sintaxi greus;
# millor: obrir la consola del browser i verificar que window.t('nav.login') retorna 'Entra')
```

---

## Pas 2 — CSS del selector d'idioma (snippet comú)

Afegeix el CSS següent a **cada pàgina HTML** dins del bloc `<style>` existent,
just abans del `</style>` de tancament. És el mateix snippet per a totes les pàgines.

```css
/* ── Lang selector ── */
.lang-selector { display: flex; align-items: center; gap: 2px; margin-left: 16px; }
.lang-btn {
  font-size: 11px; font-weight: 700; font-family: inherit;
  padding: 3px 8px; border-radius: 3px; cursor: pointer;
  background: transparent; border: 1px solid rgba(255,255,255,0.3);
  color: rgba(255,255,255,0.6); letter-spacing: 0.04em;
  transition: background 0.15s, color 0.15s;
}
.lang-btn:hover { background: rgba(255,255,255,0.12); color: var(--white); }
.lang-btn--active { background: rgba(255,255,255,0.18); color: var(--white); border-color: rgba(255,255,255,0.6); }
```

---

## Pas 3 — Afegir `i18n.js` i selector a totes les pàgines

Per a **cada pàgina** de la llista, cal fer dues coses:

### 3A — Carregar `i18n.js` primer

A cada pàgina, afegeix `<script src="i18n.js"></script>` com a **primera línia**
just dins del `<head>`, abans de qualsevol altre `<script>`.

- A les pàgines que ja tenen `<script src="auth.js"></script>`, `i18n.js` va **abans**.
- A `index.html`, va avant de l'script inline de l'Alpine component.

### 3B — Selector d'idioma a la topbar

Localitza el `<div class="topbar-inner">` (o `<nav>` / `<header>` equivalent) de
cada pàgina. Insereix el selector **just abans del tancament** del `topbar-inner`,
però **abans** del `<div id="auth-widget">` si n'hi ha (o al final si no n'hi ha).

Snippet del selector (idèntic a totes les pàgines):
```html
<div class="lang-selector" aria-label="Language selector">
  <button class="lang-btn" data-lang="ca" onclick="setLang('ca')">CA</button>
  <button class="lang-btn" data-lang="es" onclick="setLang('es')">ES</button>
</div>
```

A `index.html`, el topbar-inner no té un `id="auth-widget"` perquè `auth.js`
el gestiona extern. El selector va just abans del `<div id="auth-widget">`.

A les pàgines d'autenticació (`login.html`, `register.html`, `forgot-password.html`,
`reset-password.html`, `politica-privacitat.html`), el topbar **no té** `auth-widget`.
El selector va al final del `topbar-inner`.

---

## Pas 4 — Actualitzar `auth.js`

Substitueix el contingut actual de `frontend/auth.js` per aquest:

```js
(function () {
  var API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:5001' : '';

  async function initAuth() {
    var widget = document.getElementById('auth-widget');
    if (!widget) return;
    try {
      var res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
      if (res.ok) {
        var data = await res.json();
        widget.innerHTML =
          '<span class="auth-greeting">' + t('nav.greeting', { email: escHtml(data.email) }) + '</span>' +
          '<button class="auth-btn auth-btn--logout" id="btn-logout">' + t('nav.logout') + '</button>';
        document.getElementById('btn-logout').addEventListener('click', logout);
      } else {
        showGuestButtons(widget);
      }
    } catch (_) {
      showGuestButtons(widget);
    }
  }

  function showGuestButtons(widget) {
    widget.innerHTML =
      '<a class="auth-btn" href="login.html">' + t('nav.login') + '</a>' +
      '<a class="auth-btn auth-btn--primary" href="register.html">' + t('nav.register') + '</a>';
  }

  async function logout() {
    await fetch(API_BASE + '/api/auth/logout', { method: 'POST', credentials: 'include' });
    window.location.reload();
  }

  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function showVerifiedToast() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('verified') !== '1') return;
    history.replaceState(null, '', window.location.pathname);
    var toast = document.createElement('div');
    toast.textContent = t('auth.verified.toast');
    Object.assign(toast.style, {
      position: 'fixed', top: '24px', left: '50%',
      transform: 'translateX(-50%)',
      background: '#2e7d32', color: '#fff',
      padding: '12px 24px', borderRadius: '8px',
      fontSize: '15px', fontWeight: '500',
      boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
      zIndex: '9999', opacity: '0',
      transition: 'opacity 0.3s ease',
    });
    document.body.appendChild(toast);
    requestAnimationFrame(function () { toast.style.opacity = '1'; });
    setTimeout(function () {
      toast.style.opacity = '0';
      setTimeout(function () { toast.remove(); }, 300);
    }, 5000);
  }

  document.addEventListener('DOMContentLoaded', function () { initAuth(); showVerifiedToast(); });
})();
```

**Nota:** `t()` és global (definit per `i18n.js`, que es carrega primer).

---

## Pas 5 — Actualitzar `alertes.js`

Substitueix el contingut de `frontend/alertes.js` per aquest:

```js
(function () {
  var API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:5001' : '';

  var LOCALE = getLang() === 'ca' ? 'ca-ES' : 'es-ES';

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  function buildFilterDescription(filter) {
    var parts = [];
    if (filter.grado)           parts.push('Grado ' + filter.grado);
    if (filter.familia)         parts.push(filter.familia);
    if (filter.nivel != null)   parts.push(t('alertes.filter.niv') + filter.nivel);
    if (filter.texto)           parts.push('Texto: «' + filter.texto + '»');
    return parts.length ? parts.join(' · ') : t('alertes.filter.all');
  }

  async function fetchAlerts() {
    var res = await fetch(API_BASE + '/api/alerts', { credentials: 'include' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  async function createAlert(filterDict) {
    var res = await fetch(API_BASE + '/api/alerts', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filter_json: filterDict })
    });
    if (!res.ok) {
      var err = await res.json().catch(function () { return {}; });
      throw new Error(err.error || 'HTTP ' + res.status);
    }
    return res.json();
  }

  async function deleteAlert(id) {
    var res = await fetch(API_BASE + '/api/alerts/' + id, {
      method: 'DELETE', credentials: 'include'
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
  }

  async function toggleAlert(id, active) {
    var res = await fetch(API_BASE + '/api/alerts/' + id, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: active })
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  function renderAlerts(alerts) {
    var main = document.getElementById('main-content');
    if (!alerts.length) {
      main.innerHTML = '<p class="empty-state">' + t('alertes.empty') + '</p>';
      return;
    }
    var rows = alerts.map(function (a) {
      var filter = JSON.parse(a.filter_json || '{}');
      var desc = buildFilterDescription(filter);
      var active = a.active === 1 || a.active === true;
      var lastSent = a.last_sent_at
        ? new Date(a.last_sent_at).toLocaleDateString(LOCALE)
        : '—';
      var created = a.created_at
        ? new Date(a.created_at).toLocaleString(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '—';
      return '<tr>' +
        '<td class="col-desc">' + esc(desc) + '</td>' +
        '<td class="col-created">' + esc(created) + '</td>' +
        '<td class="col-sent">' + esc(lastSent) + '</td>' +
        '<td class="col-active">' +
          '<button class="toggle-btn ' + (active ? 'toggle-btn--active' : 'toggle-btn--inactive') + '"' +
          ' data-id="' + a.id + '" data-active="' + (active ? '1' : '0') + '">' +
          (active ? t('alertes.state.active') : t('alertes.state.inactive')) +
          '</button>' +
        '</td>' +
        '<td class="col-actions">' +
          '<button class="delete-btn" data-id="' + a.id + '" aria-label="' + t('alertes.aria.delete') + '">✕</button>' +
        '</td>' +
        '</tr>';
    }).join('');

    main.innerHTML =
      '<div class="table-wrap">' +
      '<table class="results-table">' +
      '<thead><tr>' +
        '<th scope="col">' + t('alertes.col.filter') + '</th>' +
        '<th scope="col" class="col-created">' + t('alertes.col.created') + '</th>' +
        '<th scope="col" class="col-sent">' + t('alertes.col.sent') + '</th>' +
        '<th scope="col" class="col-active">' + t('alertes.col.state') + '</th>' +
        '<th scope="col" class="col-actions"></th>' +
      '</tr></thead>' +
      '<tbody>' + rows + '</tbody>' +
      '</table></div>';

    main.querySelectorAll('.toggle-btn').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        var id = parseInt(btn.dataset.id);
        var currentActive = btn.dataset.active === '1';
        btn.disabled = true;
        try {
          await toggleAlert(id, !currentActive);
          await load();
        } catch (e) {
          btn.disabled = false;
          alert(t('alertes.err.toggle') + e.message);
        }
      });
    });

    main.querySelectorAll('.delete-btn').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        if (!confirm(t('alertes.confirm.delete'))) return;
        var id = parseInt(btn.dataset.id);
        btn.disabled = true;
        try {
          await deleteAlert(id);
          await load();
        } catch (e) {
          btn.disabled = false;
          alert(t('alertes.err.delete') + e.message);
        }
      });
    });
  }

  async function load() {
    var main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>' + t('alertes.loading') + '</p></div>';
    try {
      var res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
      if (!res.ok) {
        main.innerHTML = '<p class="empty-state">' + t('alertes.login.required') + '</p>';
        return;
      }
      var alerts = await fetchAlerts();
      renderAlerts(alerts);
    } catch (e) {
      main.innerHTML = '<p class="empty-state" style="color:#991b1b;">' + t('alertes.error') + '</p>';
    }
  }

  document.addEventListener('DOMContentLoaded', load);
})();
```

---

## Pas 6 — `index.html`

### 6A — `<title>`

Canvia:
```html
<title>Cercador Graus FP</title>
```
Per:
```html
<title data-i18n="page.title.index">Cercador Graus FP</title>
```

### 6B — Ordre de scripts al `<head>`

L'ordre ha de quedar:
```html
<script src="i18n.js"></script>          <!-- NOU — primer de tot -->
<script src="auth.js"></script>          <!-- ja existia, LÍNEA 1011 aprox -->
<script>                                 <!-- l'inline d'Alpine: document.addEventListener('alpine:init', ...) -->
  ...
</script>
<script defer src="vendor/alpinejs-3.15.11.min.js"></script>
```

### 6C — Hero

```html
<!-- Abans: -->
<h1>Formació<br><em>Professional</em></h1>
<p class="hero-sub">Explora els graus disponibles a l'estat espanyol</p>
<input ... placeholder="Cerca per denominació o codi...">

<!-- Després: -->
<h1><span data-i18n="index.hero.h1.line1">Formació</span><br><em data-i18n="index.hero.h1.line2">Professional</em></h1>
<p class="hero-sub" data-i18n="index.hero.sub">Explora els graus disponibles a l'estat espanyol</p>
<label for="search" class="sr-only" data-i18n="index.search.label">Cerca</label>
<input type="search" id="search" x-model.debounce.250ms="search" @input="resetPage()"
  data-i18n-placeholder="index.search.placeholder"
  placeholder="Cerca per denominació o codi..." autocomplete="off">
```

### 6D — Grau tabs

```html
<!-- Abans: -->
<div class="grau-tabs" role="tablist" aria-label="Filtre per grau">
  <button ...>Tots els graus</button>

<!-- Després: -->
<div class="grau-tabs" role="tablist" data-i18n-aria="index.tabs.aria" aria-label="Filtre per grau">
  <button ... x-text="filterGrado === '' ? t('index.tabs.all') : ''">
```

Nota: el botó "Tots els graus" usa `x-text` per accedir a `t()`. Substitueix:
```html
<button :class="{ active: filterGrado === '' }" @click="filterGrado=''; resetPage()">Tots els graus</button>
```
Per:
```html
<button :class="{ active: filterGrado === '' }" @click="filterGrado=''; resetPage()" x-text="t('index.tabs.all')"></button>
```

El `<template x-for>` que genera "Grau X" es deixa igual (les lletres A–E són iguals en tots dos idiomes i el mot "Grau" és en les dades).

### 6E — Filter bar

Per a cada element del filter bar, afegeix `data-i18n` o canvia el text inline. Taula de canvis:

| Element original | Canvi |
|-----------------|-------|
| `<span class="filter-bar-label">Filtrar per:</span>` | `<span class="filter-bar-label" data-i18n="index.filter.label">Filtrar per:</span>` |
| `<option value="">Totes les famílies</option>` | `<option value="" data-i18n="index.filter.allFam">Totes les famílies</option>` |
| `<option value="">Tots els nivells</option>` | `<option value="" data-i18n="index.filter.allNiv">Tots els nivells</option>` |
| `<option value="1">Nivell 1</option>` | `<option value="1" data-i18n="index.filter.niv1">Nivell 1</option>` |
| `<option value="2">Nivell 2</option>` | `<option value="2" data-i18n="index.filter.niv2">Nivell 2</option>` |
| `<option value="3">Nivell 3</option>` | `<option value="3" data-i18n="index.filter.niv3">Nivell 3</option>` |
| `Veure'ls tots` (radio label) | `<label ...><input ...> <span data-i18n="index.filter.all">Veure'ls tots</span></label>` |
| `Ocultar pla antic` (radio label) | `<span data-i18n="index.filter.hideOld">Ocultar pla antic</span>` |
| `Només pla antic` (radio label) | `<span data-i18n="index.filter.onlyOld">Només pla antic</span>` |
| `Favorits` (checkbox label) | `<span data-i18n="index.filter.favs">Favorits</span>` (wrap the text in a span) |
| `<a href="alertes.html" ...>Veure alertes</a>` | `<a ... data-i18n="index.btn.alerts">Veure alertes</a>` |
| `🔔 Desa com a alerta` (button, Alpine `:text`) | `x-text="t('index.btn.saveAlert')"` (esborra el text literal) |
| `↓ Exporta CSV` (button, Alpine `:title`) | `x-text="t('index.btn.exportCsv')"` i `:title="t('index.btn.exportTitle', {n: filteredCount})"` |
| `Esborrar filtres ×` (button, Alpine) | `x-text="t('index.btn.clearFilters')"` |

### 6F — States (loading / error)

```html
<!-- Abans: -->
<p>Carregant dades del catàleg FP...</p>
<!-- Dins del div x-show="state === 'loading'" -->

<!-- Després: -->
<p x-text="t('index.loading')"></p>
```

```html
<!-- Abans: -->
<div x-show="state === 'error'" ...>
  ⚠️ Les dades del catàleg no estan disponibles. Contacteu l'administrador del sistema.
</div>

<!-- Després: -->
<div x-show="state === 'error'" ... x-text="t('index.error')"></div>
```

### 6G — Results count

```html
<!-- Abans: -->
x-text="filteredCount === 0 ? 'Cap resultat coincideix amb els filtres aplicats' : (filteredCount === 1 ? '1 resultat trobat' : filteredCount + ' resultats trobats')"

<!-- Després: -->
x-text="filteredCount === 0 ? t('index.results.zero') : (filteredCount === 1 ? t('index.results.one') : t('index.results.many', {n: filteredCount}))"
```

### 6H — Capçaleres de taula (th)

```html
<!-- Cada th: substitueix el text literal pel patró: -->
<th scope="col" class="sortable col-nom" ...>
  <span data-i18n="index.col.nom">Denominació</span>
  <span class="sort-indicator" ...></span>
</th>
```
Fes el mateix per `index.col.codi`, `index.col.fam`, `index.col.grau`, `index.col.niv`.

La `<caption class="sr-only">`:
```html
<caption class="sr-only" data-i18n="index.table.caption">Resultats del cercador de Graus FP</caption>
```

La fila buida:
```html
<td colspan="5" x-text="t('index.table.empty')"></td>
```

### 6I — Badges i botons dins de les files

```html
<!-- badge-old: -->
<span x-show="row.plan_antiguo" class="badge-old" x-text="t('index.badge.old')">Pla antic</span>

<!-- badge-centres (ja usa x-text): -->
<span class="badge-centres" @click.stop="toggleCentres(row)"
  x-text="centres_count(row) + ' ' + (centres_count(row) === 1 ? t('index.centres.count', {n:''}).replace('{n} ','') : t('index.centres.count', {n: centres_count(row)}).replace(centres_count(row)+'','')).trim()">
```

Simplifica: com que el diccionari conté `'index.centres.count': '{n} centres'`, usa directament:
```html
x-text="t('index.centres.count', {n: centres_count(row)})"
```

<!-- Fav button titles: -->
```html
:title="favorites.has(row.id) ? t('index.fav.remove') : t('index.fav.add')"
```

### 6J — Panel de centres

Taula de canvis del panel de centres:

| Element | Canvi |
|---------|-------|
| `placeholder="Cerca centre o població…"` | `data-i18n-placeholder="index.centres.placeholder"` |
| `Carregant centres…` (div) | `x-text="t('index.centres.loading')"` |
| `'Totes'` a `this.centresCCAA[row.id] = 'Totes'` (JS inline) | `this.centresCCAA[row.id] = t('index.centres.all.ccaa')` |
| El botó watch (ternari `x-text`) | Vegeu nota |
| `'Registra't per a veure'ls tots'` (a) | `data-i18n="index.centres.upsell"` |
| `'... i {n} centres més'` (p) | `x-text="t('index.centres.more', {n: centresFiltrats(row).length - 50})"` |
| `'Cap centre trobat per a aquesta comunitat.'` (p) | `x-text="t('index.centres.empty')"` |
| Checkbox title `'Màxim 5 centres seleccionats'` | `":title"` amb `t('index.centres.maxSel')` |
| Checkbox title `'Marca ' + sc(...)` | mantenir igual (nom propi del centre) |
| Checkbox title `'Treu ' + sc(...) + ' de la selecció'` | mantenir igual (nom propi) |

Botó watch — substitueix el ternari `x-text` existent per:
```html
x-text="watchedOfertaKeys.has(row.codigo || String(row.id))
  ? (watchSaved[row.codigo || String(row.id)] ? t('index.centres.saved') : t('index.centres.watching'))
  : t('index.centres.watch')"
```

### 6K — Errors en JS inline de `index.html`

Al bloc `<script>` inline (Alpine component), localitza:

```js
this.watchSaveError = err.error || 'Error desconegut';
// → canvia per:
this.watchSaveError = err.error || t('index.err.watch.unknown');

this.watchSaveError = 'Error de xarxa';
// → canvia per:
this.watchSaveError = t('index.err.watch.network');

alert('URL del BOE no disponible per a aquest certificat.');
// → canvia per:
alert(t('index.err.boe.missing'));

alert('Error en obtenir el BOE: ' + e.message);
// → canvia per:
alert(t('index.err.boe.fetch') + e.message);
```

### 6L — `exportCSV()` — capçaleres

```js
// Abans:
const headers = ['Codi', 'Denominació', 'Família', 'Grau', 'Nivell', 'Pla antic', 'Centres seleccionats'];

// Després:
const headers = [
  t('csv.header.codi'), t('csv.header.denom'), t('csv.header.fam'),
  t('csv.header.grau'), t('csv.header.niv'), t('csv.header.old'), t('csv.header.centres')
];
```

### 6M — Paginació

```html
<!-- aria-label: -->
<nav class="pagination" data-i18n-aria="pagination.aria" aria-label="Paginació de resultats" ...>

<!-- info de paginació: -->
x-text="t('pagination.showing', {start: paginationStart, end: paginationEnd, total: filteredCount})"

<!-- botons prev/next: -->
<button @click="goToPage(currentPage - 1)" ... x-text="t('pagination.prev')"></button>
<button @click="goToPage(currentPage + 1)" ... x-text="t('pagination.next')"></button>

<!-- aria-label pàgina: -->
:aria-label="t('pagination.page', {n: item.n})"
```

### 6N — Modals

```html
<!-- Modal alerta desada — OK: -->
<p class="centres-modal-msg" style="color:#166534;" data-i18n="modal.alert.ok">✓ Alerta desada correctament</p>
<p style="..." data-i18n="modal.alert.sub">Rebràs un email...</p>
<a href="alertes.html" class="centres-modal-btn centres-modal-btn--primary" data-i18n="modal.alert.view">Veure les meves alertes</a>
<button ... data-i18n="modal.alert.continue">Continuar cercant</button>

<!-- Modal alerta desada — error (close button): -->
<button ... data-i18n="modal.alert.close">Tancar</button>

<!-- Modal gating: -->
<p class="centres-modal-msg" data-i18n="modal.gate.msg">Registra't o entra...</p>
<a href="register.html" ... data-i18n="modal.gate.register">Registrar-me</a>
<button ... data-i18n="modal.gate.later">Ara no</button>
<a href="login.html" ... data-i18n="modal.gate.login">Entrar</a>
```

### 6O — Footer

```html
<a href="historial.html" ... data-i18n="index.footer.historial">Historial d'actualitzacions</a>
<a href="observatori.html" ... data-i18n="index.footer.obs">Observatori</a>
```

---

## Pas 7 — `alertes.html`

### 7A — `<title>`
```html
<title data-i18n="page.title.alertes">Les meves alertes — Cercador Graus FP</title>
```

### 7B — Hero
```html
<h1><span data-i18n="alertes.hero.h1">Les meves</span><br><em data-i18n="alertes.hero.h1.em">alertes</em></h1>
<p class="hero-sub" data-i18n="alertes.hero.sub">Rebràs un email...</p>
```

### 7C — Footer
```html
<a href="index.html" data-i18n="alertes.footer.back">← Tornar al cercador</a>
```

### 7D — Carregar `i18n.js` al head

Afegeix `<script src="i18n.js"></script>` **abans** de `<script src="auth.js"></script>`.

---

## Pas 8 — `seguiment.html`

### 8A — `<title>`
```html
<title data-i18n="page.title.seguiment">Seguiment de centres — Cercador Graus FP</title>
```

### 8B — Hero
```html
<h1 data-i18n="seguiment.hero.h1">Seguiment de centres</h1>
<p class="hero-sub" data-i18n="seguiment.hero.sub">Rebràs un email...</p>
```

### 8C — Loading inicial
```html
<span data-i18n="seguiment.loading">Carregant seguiments…</span>
```

### 8D — Footer
```html
<a href="index.html" data-i18n="seguiment.footer.back">← Tornar al cercador</a>
<a href="alertes.html" data-i18n="seguiment.footer.alerts">Les meves alertes</a>
<a href="politica-privacitat.html" data-i18n="seguiment.footer.priv">Política de privacitat</a>
```

### 8E — JS inline (seguiment.html)

Localitza el `<script>` inline al final del `<body>`. Canvia:

```js
// Missatge buit:
main.innerHTML = '<p class="empty-state">Encara no segueixes cap ensenyament.<br>'
  + 'Obre el panell de centres d\'un ensenyament al <a href="index.html">cercador</a>'
  + ' i clica "Seguir centres".</p>';
// → canvia per:
main.innerHTML = '<p class="empty-state">' + t('seguiment.empty') + '</p>';

// Capçaleres de taula:
'<th>Ensenyament</th>'        → '<th>' + t('seguiment.col.ens') + '</th>'
'<th class="col-prov">Província</th>' → '<th class="col-prov">' + t('seguiment.col.prov') + '</th>'
'<th class="col-created">Creat</th>'  → '<th class="col-created">' + t('seguiment.col.created') + '</th>'
'<th class="col-sent">Darrer enviament</th>' → '<th class="col-sent">' + t('seguiment.col.sent') + '</th>'
'<th class="col-active">Estat</th>'   → '<th class="col-active">' + t('seguiment.col.state') + '</th>'

// Botó toggle (dins rows.map):
w.active ? 'Actiu' : 'Inactiu'
// → canvia per:
w.active ? t('seguiment.state.active') : t('seguiment.state.inactive')

// Província "Totes":
w.provincia_filter ? esc(w.provincia_filter) : '<span style="color:var(--warm)">' + t('seguiment.all.prov') + '</span>'

// A handleToggle (btn.textContent):
btn.textContent = updated.active ? t('seguiment.state.active') : t('seguiment.state.inactive');

// Errors:
alert('Error eliminant el seguiment: ' + e.message)  → alert(t('seguiment.err.delete') + e.message)
alert('Error canviant estat: ' + e.message)           → alert(t('seguiment.err.toggle') + e.message)
document.getElementById('main-content').innerHTML =
  '<p class="empty-state">Error carregant els seguiments.</p>'
// → canvia per:
'<p class="empty-state">' + t('seguiment.error') + '</p>'

// Loading div initial (a la funció de load async):
main.innerHTML = '<div class="loading-state"><div class="spinner"></div><span>' + t('seguiment.loading') + '</span></div>';
```

### 8F — `<script src="i18n.js">` al head

Afegeix abans de `<script src="auth.js"></script>`.

---

## Pas 9 — `login.html`

### 9A — `<title>`
```html
<title data-i18n="page.title.login">Inicia sessió — Cercador Graus FP</title>
```

### 9B — HTML estàtic
```html
<h1 data-i18n="login.h1">Inicia sessió</h1>
<label for="password" data-i18n="login.pw.label">Contrasenya</label>
<button type="submit" id="btn-submit" data-i18n="login.btn.submit">Entra</button>
<a href="forgot-password.html" data-i18n="login.link.forgot">Has oblidat la contrasenya?</a>
```

Per al segon auth-link (`Sense compte? Registra't`), com que té text mixt, envolta els parts:
```html
<p class="auth-links"><span data-i18n="login.link.register">Sense compte? <a href="register.html">Registra't</a></span></p>
```
(El diccionari conté `"login.link.register": "Sense compte? <a href=\"register.html\">Registra't</a>"` — però com que la traducció canvia el contingut del link, el més simple és tenir-ho en dos `data-i18n` separats o incloure l'HTML al diccionari; el diccionari ja inclou el link en el string. El `i18n.js` usa `innerHTML` per a tots els elements, per tant funciona directament.)

**Alternativa simplificada** (recomanada): usa `innerHTML = t(key)` (que és el que fa `i18n.js` per defecte), i al diccionari el string `login.link.register` ja té el `<a>` incrustat. No cal fer res especial.

### 9C — JS inline

```js
// Missatge de compte verificat:
if (new URLSearchParams(window.location.search).get('verified') === '1') {
  showMsg(t('login.msg.verified'), 'ok');
}

// btn.textContent = 'Entrant…'  → t('login.btn.submitting')
// btn.textContent = 'Entra'     → t('login.btn.submit')
// showMsg(data.error || 'Error en iniciar sessió.', 'error')  → t('login.err.default')
// showMsg('Error de connexió. Torna-ho a intentar.', 'error') → t('login.err.network')
```

### 9D — `<script src="i18n.js">` al head

Afegeix com a primera línia del `<head>` (abans del `<link>` de Google Fonts fins i tot és acceptable, però mínim ha d'anar ABANS de l'`<script>` inline que usa `t()`).

---

## Pas 10 — `register.html`

### 10A — `<title>`
```html
<title data-i18n="page.title.register">Crea un compte — Cercador Graus FP</title>
```

### 10B — HTML estàtic
```html
<h1 data-i18n="register.h1">Crea un compte</h1>
<label for="password" data-i18n="register.pw.label">Contrasenya</label>
<input ... data-i18n-placeholder="register.pw.placeholder" placeholder="Mínim 8 caràcters">
<label for="password2" data-i18n="register.pw2.label">Confirma la contrasenya</label>
<input ... data-i18n-placeholder="register.pw2.placeholder" placeholder="Repeteix la contrasenya">
<!-- label GDPR: -->
<label for="gdpr-consent" data-i18n="register.gdpr">He llegit i accepto la <a ...>política de privacitat</a>...</label>
<button type="submit" id="btn-submit" data-i18n="register.btn.submit">Crea el compte</button>
<p class="auth-links" data-i18n="register.link.login">Ja tens compte? <a href="login.html">Inicia sessió</a></p>
```

### 10C — JS inline

```js
// btn.textContent = 'Creant compte…' → t('register.btn.submitting')
// btn.textContent = 'Crea el compte' → t('register.btn.submit')
// showMsg('Les contrasenyes no coincideixen.', 'error') → t('register.err.pw.match')
// showMsg('Compte creat...', 'ok') → t('register.msg.ok')
// showMsg(data.error || 'Error en crear el compte.', 'error') → t('register.err.default')
// showMsg('Error de connexió...', 'error') → t('register.err.network')
```

---

## Pas 11 — `forgot-password.html`

### 11A — `<title>`
```html
<title data-i18n="page.title.forgot">Restablir contrasenya — Cercador Graus FP</title>
```

### 11B — HTML estàtic
```html
<h1 data-i18n="forgot.h1">Restablir contrasenya</h1>
<p class="subtitle" data-i18n="forgot.subtitle">Introdueix el teu email...</p>
<button type="submit" id="btn-submit" data-i18n="forgot.btn.submit">Envia el link</button>
<a href="login.html" data-i18n="forgot.link.back">Torna a Inicia sessió</a>
```

### 11C — JS inline
```js
// btn.textContent = 'Enviant…'       → t('forgot.btn.submitting')
// btn.textContent = 'Envia el link'  → t('forgot.btn.submit')
// showMsg("Si l'email existeix...", 'ok') → t('forgot.msg.ok')
// showMsg('Error de connexió...', 'error') → t('forgot.err.network')
```

---

## Pas 12 — `reset-password.html`

### 12A — `<title>`
```html
<title data-i18n="page.title.reset">Nova contrasenya — Cercador Graus FP</title>
```

### 12B — HTML estàtic
```html
<h1 data-i18n="reset.h1">Nova contrasenya</h1>
<label for="password" data-i18n="reset.pw.label">Nova contrasenya</label>
<input ... data-i18n-placeholder="reset.pw.placeholder" placeholder="Mínim 8 caràcters">
<label for="password2" data-i18n="reset.pw2.label">Confirma la contrasenya</label>
<input ... data-i18n-placeholder="reset.pw2.placeholder" placeholder="Repeteix la contrasenya">
<button type="submit" id="btn-submit" data-i18n="reset.btn.submit">Desa la contrasenya</button>
<a href="login.html" data-i18n="reset.link.back">Torna a Inicia sessió</a>
```

### 12C — JS inline
```js
// showMsg('Enllaç invàlid...', 'error')    → t('reset.err.invalid.token')
// showMsg('Les contrasenyes...', 'error')  → t('reset.err.pw.match')
// showMsg('La contrasenya ha...', 'error') → t('reset.err.pw.short')
// btn.textContent = 'Desant…'             → t('reset.btn.submitting')
// btn.textContent = 'Desa la contrasenya' → t('reset.btn.submit')
// showMsg('Contrasenya actualitzada...', 'ok') → t('reset.msg.ok')
// showMsg(data.error || 'Error en desar...', 'error') → t('reset.err.default')
// showMsg('Error de connexió...', 'error') → t('reset.err.network')
```

---

## Pas 13 — `observatori.html`

### 13A — `<title>`
```html
<title data-i18n="page.title.obs">Observatori de l'oferta FP — Cercador Graus FP</title>
```

### 13B — Hero
```html
<h1 data-i18n="obs.hero.h1">Observatori<br><em>de l'oferta FP</em></h1>
<p class="hero-sub" data-i18n="obs.hero.sub">Evolució setmanal...</p>
```

Nota: el valor del diccionari `obs.hero.h1` conté `<br><em>...</em>` — `i18n.js` usa `innerHTML` per tots els elements, per tant el HTML s'aplica correctament.

### 13C — Stats strip
```html
<span class="stat-label" data-i18n="obs.stat.total.label">Titulacions actives</span>
<span class="stat-value">5</span><span class="stat-label" data-i18n="obs.stat.graus.label">Graus (A–E)</span>
<span class="stat-label" data-i18n="obs.stat.date.label">Darrera actualització</span>
```

### 13D — Seccions
```html
<h2 data-i18n="obs.section.evolution">Evolució del total de titulacions</h2>
<h2 data-i18n="obs.section.dist">Distribució per grau</h2>
<h2 data-i18n="obs.section.novetats">Darreres novetats</h2>
<div class="loading-state" ... data-i18n="obs.loading">Carregant dades...</div>
<div class="loading-state" data-i18n="obs.loading.short">Carregant...</div>
```

### 13E — Footer
```html
<p class="footer-note" data-i18n="obs.footer.note">Font: Ministerio...</p>
<a href="historial.html" data-i18n="obs.footer.historial">← Veure l'historial complet</a>
```

### 13F — JS inline (observatori.html)

```js
// formatDate: canvia 'ca-ES' per getLang() === 'ca' ? 'ca-ES' : 'es-ES'
function formatDate(iso) {
  var locale = getLang() === 'ca' ? 'ca-ES' : 'es-ES';
  var d = new Date(iso);
  return d.toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// renderBarChart: 'Grau ${g}' → el text ja és vàlid en castellà (Grau/Grado difereix)
// La barra usa 'Grau ${g}' — substitueix per:
'<span class="bar-label">Grau ' + g + '</span>'
// → deixa'l igual: "Grau A/B/C..." és terminologia tècnica usada per ambdós idiomes
// (la llei espanyola els anomena "Grado A/B/C..."; en català és "Grau A/B/C...")
// Pots fer: getLang() === 'ca' ? 'Grau ' : 'Grado ' però és opcional. Decideix tu.

// val.toLocaleString('ca-ES') → val.toLocaleString(getLang() === 'ca' ? 'ca-ES' : 'es-ES')

// renderNovetats:
'<li class="empty-state">Sense novetats recents</li>'
// → '<li class="empty-state">' + t('obs.novetats.empty') + '</li>'

// '<span style="color:var(--warm);font-size:12px">Sense denominacions detallades</span>'
// → '<span ...>' + t('obs.novetats.no.detail') + '</span>'

// renderLineChart:
loading.textContent = 'Poques dades per mostrar una tendència (mínim 2 refreshos).';
// → loading.textContent = t('obs.few.data');
```

### 13G — `<script src="i18n.js">` al head

Afegeix AVANT de `<script src="auth.js"></script>`.

---

## Pas 14 — `historial.html`

### 14A — `<title>`
```html
<title data-i18n="page.title.historial">Historial — Cercador Graus FP</title>
```

### 14B — Hero
```html
<h1 data-i18n="hist.hero.h1">Historial<br><em>d'actualitzacions</em></h1>
<p class="hero-sub" data-i18n="hist.hero.sub">Registre de les darreres actualitzacions...</p>
```

### 14C — Loading initial
```html
<p data-i18n="hist.loading">Carregant historial...</p>
```

### 14D — Footer
```html
<a href="index.html" data-i18n="hist.footer.back">← Tornar al cercador</a>
<a href="observatori.html" ... data-i18n="hist.footer.obs">Observatori</a>
```

### 14E — JS inline (historial.html)

```js
// formatDate: canvia 'ca-ES' per:
var locale = getLang() === 'ca' ? 'ca-ES' : 'es-ES';
return d.toLocaleString(locale, { ... });

// Empty state:
main.innerHTML = '<p class="empty-state">Encara no hi ha cap actualització registrada.</p>';
// → '<p class="empty-state">' + t('hist.empty') + '</p>'

// Capçaleres de taula (gradoCols i la fila de th):
// La variable gradoCols genera les columnes per grau: 'Grau ${g}' — deixa igual (terminologia tècnica)
// Les columnes fixes:
'<th class="col-date" scope="col">Data</th>'     → '<th...>' + t('hist.col.date') + '</th>'
'<th class="col-total" scope="col">Total</th>'   → t('hist.col.total')
'<th class="col-changes" scope="col">Canvis</th>'→ t('hist.col.changes')
// El '#' (col-num) es deixa igual

// renderNovetats (strings de canvis):
'<span class="first-entry">Primer registre</span>'   → t('hist.changes.first')
'<span class="no-changes">Sense canvis</span>'       → t('hist.changes.none')
'+ Nous (${added.length})'   → t('hist.changes.added', {n: added.length})
'− Eliminats (${removed.length})' → t('hist.changes.removed', {n: removed.length})
```

### 14F — `<script src="i18n.js">` al head

Afegeix AVANT de `<script src="auth.js"></script>`.

---

## Pas 15 — `politica-privacitat.html`

### 15A — `<title>`
```html
<title data-i18n="page.title.privacitat">Política de privacitat — Cercador Graus FP</title>
```

### 15B — HTML estàtic
```html
<h1 data-i18n="priv.h1">Política de privacitat</h1>
<span class="provisional-badge" data-i18n="priv.badge">Text provisional...</span>
```

El cos del text legal (paràgrafs, llista, etc.) es deixa en català perquè la pàgina
porta un badge de "text provisional". No cal traduir el cos fins que s'escrigui el
text definitiu.

### 15C — Footer

Localitza el footer/link de tornada (si n'hi ha) i afegeix `data-i18n="priv.footer.back"`.

### 15D — `<script src="i18n.js">` al head

Afegeix com a primer script del `<head>`.

---

## Criteris de finalització (done criteria)

Executa les comprovacions següents. Totes han de passar:

### Verificació manual al browser

1. Obre `index.html` al browser local (`python3 -m http.server 8080` a `frontend/`).
2. Comprova que en català (per defecte) tots els textos es mostren correctament.
3. Fes clic a "ES". La pàgina es recarrega. Comprova:
   - La topbar mostra "Buscar por denominación o código..." al placeholder
   - El botó actiu del selector és "ES"
   - Els grau tabs mostren "Todos los grados"
   - Les capçaleres de taula mostren "Denominación", "Código", etc.
4. Torna a "CA". Comprova que tot és en català.
5. Tanca el browser i torna a obrir `index.html`. Ha de recordar l'últim idioma triat.
6. Obre `alertes.html`, `seguiment.html`, `login.html`, `register.html`, `observatori.html`, `historial.html`, `politica-privacitat.html`:
   - Cada pàgina mostra el selector CA/ES a la topbar.
   - Cada pàgina usa l'idioma desat a `localStorage`.
7. A `login.html` en castellà: comprova que el missatge d'error ("Error al iniciar sesión.") és en castellà.
8. A `alertes.html` sense login: comprova que el missatge "Es necesario iniciar sesión..." és en castellà quan l'idioma és ES.

### Verificació de localStorage

```js
// A la consola del browser:
localStorage.setItem('lang', 'es');
location.reload();
// → Pàgina en castellà

localStorage.setItem('lang', 'ca');
location.reload();
// → Pàgina en català

localStorage.removeItem('lang');
location.reload();
// → Pàgina en català (per defecte)
```

### Verificació de `window.t()`

```js
// A la consola del browser (amb lang=ca):
window.t('nav.login')       // → "Entra"
window.t('nav.logout')      // → "Sortir"
window.t('index.results.many', {n: 42})  // → "42 resultats trobats"

// Amb lang=es:
window.t('nav.login')       // → "Entrar"
window.t('index.results.many', {n: 42})  // → "42 resultados encontrados"
```

### Verificació que Alpine segueix funcionant

```
# Obre index.html, espera que es carregui, i comprova:
# 1. La taula de resultats es renderitza amb dades
# 2. Els filtres funcionen
# 3. El botó "Exporta CSV" genera un fitxer CSV
# 4. El modal de centres s'obre
```

---

## Notes de manteniment

- Per afegir un nou string traduïble en una pàgina futura: afegeix la clau als dos
  blocs (`ca` i `es`) de `TRANSLATIONS` a `i18n.js`, i usa `data-i18n="la.clau"` al HTML
  o `t('la.clau')` al JS.
- Per corregir una traducció: edita una sola línia a `i18n.js`.
- Per afegir un tercer idioma: afegeix un tercer bloc `gl: {...}` a `TRANSLATIONS`
  i un tercer botó al `lang-selector`.
- El fitxer `i18n.js` és l'únic arxiu de referència per a traduccions.
  **No hi ha cap altra font de veritat.**
