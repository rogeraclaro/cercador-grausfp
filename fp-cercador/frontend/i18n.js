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
      'index.tabs.grau':       'Grau',
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
      'index.centres.word':    'centres',
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
      'index.detall.annexe':   'Annexe PDF',
      'index.err.boe.missing': 'URL del BOE no disponible per a aquest certificat.',
      'index.err.boe.fetch':   'Error en obtenir el BOE: ',
      'index.err.watch.unknown': 'Error desconegut',
      'index.err.watch.network': 'Error de xarxa',

      /* ── F5: Itineraris formatius ── */
      'index.itinerari.parent_b_title': 'Part de la unitat de competència: ',
      'index.itinerari.ciclos_d_btn':   'Cicles FP (D)',
      'index.itinerari.ciclos_d_cap':   'Cicles formatius que convaliden aquest certificat:',
      'index.itinerari.ciclos_d_none':  'No hi ha cicles associats.',
      'index.itinerari.ciclos_d_err':   'Error carregant cicles: ',

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
      'index.tabs.grau':       'Grado',
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
      'index.centres.word':    'centros',
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
      'index.detall.annexe':   'Anexo PDF',
      'index.err.boe.missing': 'URL del BOE no disponible para este certificado.',
      'index.err.boe.fetch':   'Error al obtener el BOE: ',
      'index.err.watch.unknown': 'Error desconocido',
      'index.err.watch.network': 'Error de red',

      /* ── F5: Itineraris formatius ── */
      'index.itinerari.parent_b_title': 'Parte de la unidad de competencia: ',
      'index.itinerari.ciclos_d_btn':   'Ciclos FP (D)',
      'index.itinerari.ciclos_d_cap':   'Ciclos formativos que convalidan este certificado:',
      'index.itinerari.ciclos_d_none':  'No hay ciclos asociados.',
      'index.itinerari.ciclos_d_err':   'Error cargando ciclos: ',

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
