"""
grau_page.py — Pàgines públiques per grau i família, sitemap i robots (Pla 077).

Funcions pures: reben el registre (o la llista de registres) i les dades ja
carregades i retornen text. La càrrega dels índexs i la memòria cau són a app.py.

El contingut és en castellà (decisió del propietari, 2026-10-26): és l'idioma en
què busca la gent de tot Espanya. La barra superior i el peu els tradueix
i18n.js com a la resta del web.

Seguretat: tot text que ve de les dades passa per _e() (html.escape) o, dins el
JSON-LD, per _json_ld() (sense <, > ni & literals). Les adreces es construeixen
amb quote() i també s'escapen. Mai s'hi posa el nom d'un centre ni l'enllaç
directe a la fitxa oficial (tanca de login).
"""
import html
import json
from urllib.parse import quote

# Versions dels recursos compartits: les mateixes que a les subpàgines (fonts.html).
I18N_VERSION = '20261026c'
SITE_CSS_VERSION = '3'
FOOTER_VERSION = '2'
FEEDBACK_VERSION = '3'

STATIC_PAGES = ['/', '/per-que-grausfp.html', '/fonts.html', '/observatori.html',
                '/historial.html', '/families']

GRADOS = ('A', 'B', 'C', 'D', 'E')

GRADO_NOM = {
    'A': 'Acreditación parcial de competencia',
    'B': 'Certificado de competencia',
    'C': 'Certificado profesional',
    'D': 'Ciclo formativo',
    'E': 'Curso de especialización',
}

GRADO_NOM_PLURAL = {
    'A': 'Acreditaciones parciales de competencia',
    'B': 'Certificados de competencia',
    'C': 'Certificados profesionales',
    'D': 'Ciclos formativos',
    'E': 'Cursos de especialización',
}

# Mateixa explicació que a per-que-grausfp.html (perque.grau.*) i a la Llei Orgànica 3/2022.
GRADO_TEXT = {
    'A': ('Un Grado A es una acreditación parcial de competencia: una formación corta que '
          'acredita una parte concreta de una competencia profesional. Varios Grados A forman '
          'un Grado B (certificado de competencia), así que se pueden ir sumando hasta completarlo.'),
    'B': ('Un Grado B es un certificado de competencia: acredita una competencia profesional '
          'completa. Se puede cursar de una vez o sumando los Grados A que lo forman, y a su vez '
          'forma parte de uno o varios certificados profesionales (Grado C).'),
    'C': ('Un Grado C es un certificado profesional: reúne varios certificados de competencia '
          '(Grado B) y prepara para trabajar en una ocupación concreta. Los módulos que comparte '
          'con un ciclo formativo (Grado D) se pueden convalidar si después quieres seguir estudiando.'),
    'D': ('Un Grado D es un ciclo formativo de grado básico, medio o superior. Conduce a un título '
          'oficial (Técnico Básico, Técnico o Técnico Superior) e incluye formación en empresa.'),
    'E': ('Un Grado E es un curso de especialización: complementa un ciclo formativo de grado medio '
          'o superior y profundiza en un campo concreto. Para acceder hace falta un título de '
          'Formación Profesional relacionado.'),
}

PLAN_ANTIGUO_TEXT = ('Es del plan antiguo, anterior a la Ley Orgánica 3/2022. Sigue vigente hasta '
                     'que el ministerio lo sustituya por la versión del plan nuevo.')
PLAN_ANTIGUO_TEXT_C = ('Es del plan antiguo: un antiguo certificado de profesionalidad. Sigue vigente '
                       'hasta que un nuevo real decreto lo sustituya y, mientras tanto, se ofrece '
                       'dentro del Grado C.')

NIVEL_D = {1: 'Grado básico', 2: 'Grado medio', 3: 'Grado superior'}

# Títol de les llistes de l'itinerari segons el grau de la pàgina (veïns directes).
PREVIS_TITOL = {
    'B': 'Grados A que lo forman',
    'C': 'Grados B que lo forman',
    'D': 'Certificados profesionales con módulos en común',
}
SEGUENTS_TITOL = {
    'A': 'Forma parte de',
    'B': 'Forma parte de',
    'C': 'Puedes continuar con',
    'D': 'Da acceso a',
}

PROVIDER = {'@type': 'Organization',
            'name': 'Ministerio de Educación, Formación Profesional y Deportes',
            'sameAs': 'https://www.todofp.es'}

_MINUSCULES = {'y', 'e', 'de', 'del', 'la', 'las', 'los', 'el', 'i', "d'"}


def _e(value) -> str:
    """Text escapat per a HTML (contingut i atributs)."""
    return html.escape('' if value is None else str(value), quote=True)


def _q(ref: str) -> str:
    return quote(ref, safe='~')


def grau_path(ref: str) -> str:
    return f'/grau/{_q(ref)}'


def _json_ld(data: dict) -> str:
    """JSON per a <script type="application/ld+json">: sense <, > ni & que tanquin l'etiqueta."""
    return (json.dumps(data, ensure_ascii=False)
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))


def nom_ccaa(ccaa: str) -> str:
    """'CASTILLA Y LEÓN' → 'Castilla y León'; 'CASTILLA-LA MANCHA' → 'Castilla-La Mancha'."""
    words = []
    for i, word in enumerate((ccaa or '').lower().split()):
        if i and word in _MINUSCULES:
            words.append(word)
        else:
            words.append('-'.join(p[:1].upper() + p[1:] for p in word.split('-')))
    return ' '.join(words)


def nivel_label(rec: dict) -> str | None:
    grado, nivel = rec.get('grado'), rec.get('nivel')
    if grado in ('A', 'B', 'C') and nivel in (1, 2, 3):
        return f'Nivel {nivel}'
    if grado == 'D':
        return NIVEL_D.get(nivel)
    if grado == 'E':
        den = rec.get('denominacion') or ''
        if '(Acceso GM)' in den:
            return 'Acceso desde grado medio'
        if '(Acceso GS)' in den:
            return 'Acceso desde grado superior'
    return None


# ---------------------------------------------------------------------------
# Esquelet comú (barra superior, peu, site.css, i18n.js)
# ---------------------------------------------------------------------------

_CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: var(--fs-body); color: var(--dark); background: var(--bg); }
    a { color: var(--dark); text-decoration: underline; text-decoration-color: var(--warm);
      text-underline-offset: 2px; }
    a:hover { text-decoration-color: var(--dark); }
    .crumbs { padding: 16px 48px 0; font-size: var(--fs-small); color: var(--warm); }
    .crumbs a { color: var(--warm); }
    .crumbs span[aria-hidden] { margin: 0 6px; }
    .hero { border-bottom: 2px solid var(--dark); padding: 16px 48px 28px; }
    .hero .eyebrow { font-size: var(--fs-label); font-weight: 600; letter-spacing: 0.07em;
      text-transform: uppercase; color: var(--warm); margin-bottom: 8px; }
    .hero h1 { font-family: 'DM Serif Display', serif; font-size: var(--fs-display); font-weight: 400;
      line-height: 1.05; margin-bottom: 14px; overflow-wrap: anywhere; max-width: 28ch; }
    .hero .hero-sub { font-size: var(--fs-lead); color: var(--warm); }
    .tags { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
    .tag { display: inline-block; font-size: var(--fs-small); padding: 2px 8px; border: 1px solid var(--border);
      border-radius: 3px; background: var(--white); color: var(--dark); text-decoration: none; }
    a.tag:hover { background: var(--warm2); }
    .tag-code { font-family: 'Geist Mono', ui-monospace, monospace; font-size: var(--fs-mono); }
    .badge-old { display: inline-block; font-size: var(--fs-label); font-weight: 700; padding: 2px 6px;
      border-radius: 3px; background: var(--amber-bg); color: var(--amber-ink); white-space: nowrap; }
    .content { padding: 32px 48px 80px; max-width: 980px; }
    .content > p, .content section > p { line-height: 1.7; max-width: 75ch; color: var(--ink-soft);
      margin-bottom: 12px; }
    .content .lead { font-size: var(--fs-lead); }
    .content h2 { font-family: 'DM Serif Display', serif; font-size: 26px; font-weight: 400;
      margin: 40px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
    .content h3 { font-size: var(--fs-body); font-weight: 600; margin: 20px 0 8px; }
    .list { list-style: none; display: flex; flex-direction: column; gap: 6px; max-width: 75ch; }
    .list li { line-height: 1.5; color: var(--ink-soft); }
    .list .code { font-family: 'Geist Mono', ui-monospace, monospace; font-size: var(--fs-mono);
      color: var(--warm); margin-right: 6px; }
    .list .g { font-size: var(--fs-label); font-weight: 600; color: var(--warm); margin-left: 6px;
      white-space: nowrap; }
    .ocup { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; max-width: 75ch; }
    .ocup li { font-size: var(--fs-small); padding: 3px 8px; border: 1px solid var(--border);
      border-radius: 3px; background: var(--white); }
    .ccaa { border-collapse: collapse; margin: 4px 0 16px; min-width: 280px; font-size: var(--fs-small);
      background: var(--white); border: 1px solid var(--border); }
    .ccaa th, .ccaa td { text-align: left; padding: 6px 12px; border-bottom: 1px solid var(--border); }
    .ccaa td.n { text-align: right; font-variant-numeric: tabular-nums; }
    .ccaa thead th { background: var(--warm2); font-size: var(--fs-label); text-transform: uppercase;
      letter-spacing: 0.07em; }
    .btns { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 4px; }
    .btn { display: inline-block; padding: 7px 14px; border: 2px solid var(--dark); border-radius: 4px;
      background: var(--white); color: var(--dark); font-size: var(--fs-small); font-weight: 600;
      text-decoration: none; }
    .btn:hover { background: var(--warm2); }
    .note { font-size: var(--fs-small); color: var(--warm) !important; }
    .src { margin-top: 48px; font-size: var(--fs-small); color: var(--warm) !important; }
    .fam-list { columns: 2 280px; column-gap: 32px; list-style: none; }
    .fam-list li { break-inside: avoid; padding: 4px 0; }
    .fam-list .n { color: var(--warm); font-size: var(--fs-small); margin-left: 4px; }
    @media (max-width: 768px) {
      .crumbs { padding: 12px 16px 0; }
      .hero { padding: 12px 16px 20px; }
      .hero h1 { font-size: var(--fs-display-sm); }
      .content { padding: 20px 16px 48px; }
      .content h2 { font-size: 22px; margin-top: 32px; }
      .ccaa { min-width: 0; width: 100%; }
    }
"""


def _shell(*, title: str, description: str, canonical: str | None, body: str,
           site_url: str, head_extra: str = '', noindex: bool = False) -> str:
    """Pàgina completa. title/description/canonical arriben sense escapar."""
    meta = [
        f'<title>{_e(title)}</title>',
        f'<meta name="description" content="{_e(description)}">',
    ]
    if noindex:
        meta.append('<meta name="robots" content="noindex">')
    if canonical:
        meta.append(f'<link rel="canonical" href="{_e(canonical)}">')
        meta.append(f'<meta property="og:url" content="{_e(canonical)}">')
    meta += [
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="GrausFP">',
        '<meta property="og:locale" content="es_ES">',
        f'<meta property="og:title" content="{_e(title)}">',
        f'<meta property="og:description" content="{_e(description)}">',
        f'<meta property="og:image" content="{_e(site_url)}/og-image-es.png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    head = '\n  '.join(meta)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <base href="/">
  {head}
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=DM+Serif+Display:ital@0;1&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/site.css?v={SITE_CSS_VERSION}">
  <style>{_CSS}  </style>
  {head_extra}
  <script src="/i18n.js?v={I18N_VERSION}"></script>
  <script src="/auth.js"></script>
</head>

<body>

  <header class="topbar">
    <div class="topbar-inner">
      <a href="/index.html" class="topbar-logo">GrausFP</a>
      <div id="auth-widget"></div>
      <div class="lang-selector" aria-label="Language selector">
        <button class="lang-btn" data-lang="ca" onclick="setLang('ca')">CA</button>
        <button class="lang-btn" data-lang="es" onclick="setLang('es')">ES</button>
      </div>
    </div>
  </header>

{body}

  <footer class="site-footer" id="site-footer"></footer>
  <script src="/footer.js?v={FOOTER_VERSION}"></script>
  <script src="/feedback.js?v={FEEDBACK_VERSION}"></script>

</body>
</html>
"""


def _crumbs(items) -> str:
    """items: [(text, href | None)]; l'últim sense enllaç."""
    parts = []
    for text, href in items:
        parts.append(f'<a href="{_e(href)}">{_e(text)}</a>' if href else _e(text))
    sep = ' <span aria-hidden="true">›</span> '
    return f'  <nav class="crumbs" aria-label="Ruta">{sep.join(parts)}</nav>\n'


def _fmt_date(iso: str | None) -> str:
    """'2026-10-26' → '26/10/2026'."""
    if not iso or len(iso) != 10:
        return ''
    return f'{iso[8:10]}/{iso[5:7]}/{iso[0:4]}'


def _node_li(node: dict) -> str:
    """Element de llista amb enllaç a la pàgina d'un altre grau."""
    old = ' <span class="badge-old">Plan antiguo</span>' if node.get('plan_antiguo') else ''
    return (f'<li><a href="{_e(grau_path(node["ref"]))}">{_e(node.get("denominacion"))}</a>'
            f'<span class="g">Grado {_e(node.get("grado"))}</span>{old}</li>')


def _coded_list(items) -> str:
    """[{codigo, text}] → llista amb el codi en monoespaiada."""
    lis = ''.join(f'<li><span class="code">{_e(it.get("codigo"))}</span>{_e(it.get("text"))}</li>'
                  for it in items)
    return f'<ul class="list">{lis}</ul>'


# ---------------------------------------------------------------------------
# Pàgina de grau
# ---------------------------------------------------------------------------

def _description(rec: dict, ctx: dict) -> str:
    grado = rec.get('grado')
    parts = [f'{rec.get("denominacion")}: Grado {grado} de Formación Profesional '
             f'({GRADO_NOM.get(grado, "").lower()})']
    if rec.get('familia'):
        parts[0] += f' de la familia {rec["familia"]}'
    parts[0] += '.'
    total = (ctx.get('centres') or {}).get('total') or 0
    if total:
        parts.append(f'Se imparte en {total} centros de España.')
    parts.append('Contenidos, salidas profesionales e itinerario formativo.')
    return ' '.join(parts)


def _contingut_html(rec: dict, contingut: dict) -> str:
    grado = rec.get('grado')
    out = []
    if contingut.get('ra'):
        titol = 'Qué aprenderás' if grado == 'A' else 'Resultados de aprendizaje'
        out.append(f'<h2>{titol}</h2>{_coded_list(contingut["ra"])}')
    if contingut.get('ecp'):
        intro = ('<p>Estándares de competencia del Grado B del que forma parte:</p>'
                 if grado == 'A' else '')
        out.append(f'<h2>Competencias que acredita</h2>{intro}{_coded_list(contingut["ecp"])}')
    if contingut.get('uc'):
        lis = ''.join(f'<li><span class="code">{_e(u.get("codigo"))}</span>{_e(u.get("nombre") or "")}</li>'
                      for u in contingut['uc'])
        out.append(f'<h2>Unidades de competencia</h2><ul class="list">{lis}</ul>')
    if contingut.get('modulos'):
        lis = ''.join(f'<li>{_e(m)}</li>' for m in contingut['modulos'])
        out.append(f'<h2>Módulos profesionales</h2><ul class="list">{lis}</ul>')
    if contingut.get('acceso') or contingut.get('acceso_otros'):
        lis = ''.join(_node_li(n) for n in contingut.get('acceso') or [])
        lis += ''.join(f'<li>{_e(t)}</li>' for t in contingut.get('acceso_otros') or [])
        out.append('<h2>Requisitos de acceso</h2><p>Puedes acceder con alguno de estos títulos:</p>'
                   f'<ul class="list">{lis}</ul>')
    return ''.join(f'\n    <section>{s}</section>' for s in out)


def _centres_html(rec: dict, centres: dict) -> str:
    total = centres.get('total') or 0
    ref_q = _q(rec['ref'])
    h = f'<section data-centres-total="{int(total)}"><h2>Dónde se imparte</h2>'
    if not total:
        return h + '<p>Todavía no tenemos centros registrados para este grado.</p></section>'
    word = 'centro' if total == 1 else 'centros'
    h += f'<p><strong>{int(total)}</strong> {word} en toda España.</p>'
    if rec.get('grado') in ('A', 'B'):
        h += ('<p class="note">Los Grados A y B se imparten en los centros acreditados para el '
              'certificado profesional (Grado C) del que forman parte.</p>')
    rows = ''.join(f'<tr><td>{_e(nom_ccaa(c))}</td><td class="n">{int(n)}</td></tr>'
                   for c, n in centres.get('per_ccaa') or [])
    if rows:
        h += ('<table class="ccaa"><thead><tr><th scope="col">Comunidad autónoma</th>'
              f'<th scope="col">Centros</th></tr></thead><tbody>{rows}</tbody></table>')
    h += (f'<div class="btns"><a class="btn" href="/index.html?ref={_e(ref_q)}">Ver los centros</a></div>'
          '<p class="note">La lista con el nombre y los datos de cada centro está disponible '
          'con una cuenta gratuita.</p>')
    return h + '</section>'


def _itinerari_html(rec: dict, ctx: dict) -> str:
    grado = rec.get('grado')
    previs, seguents = ctx.get('previs') or [], ctx.get('seguents') or []
    if not previs and not seguents:
        return ''
    h = '<section><h2>Itinerario formativo</h2>'
    for titol, nodes in ((PREVIS_TITOL.get(grado, 'Grados anteriores'), previs),
                         (SEGUENTS_TITOL.get(grado, 'Grados siguientes'), seguents)):
        if nodes:
            h += f'<h3>{_e(titol)}</h3><ul class="list">{"".join(_node_li(n) for n in nodes)}</ul>'
    href = f'/itinerari.html?grado={_q(grado)}&ref={_q(rec["ref"])}'
    h += f'<div class="btns"><a class="btn" href="{_e(href)}">Ver itinerario completo</a></div>'
    return h + '</section>'


def render_grau(rec: dict, ctx: dict, site_url: str) -> str:
    """
    HTML de la pàgina d'un grau.

    ctx: {'contingut': {ra|ecp|uc|modulos|acceso|acceso_otros}, 'ocupaciones': [str],
          'centres': {'total', 'per_ccaa': [(ccaa, n)]}, 'previs': [node], 'seguents': [node],
          'familia_prefix': str | None, 'lastmod': 'AAAA-MM-DD'}
    node: {'ref', 'grado', 'denominacion', 'plan_antiguo'} (itinerary_graph.serialize_node).
    """
    grado = rec.get('grado')
    den = rec.get('denominacion') or ''
    canonical = f'{site_url}{grau_path(rec["ref"])}'
    title = f'{den} — Grado {grado} de FP | GrausFP'
    description = _description(rec, ctx)
    prefix = ctx.get('familia_prefix')
    familia = rec.get('familia')

    crumbs = [('GrausFP', '/index.html'), ('Familias profesionales', '/families')]
    if familia:
        crumbs.append((familia, f'/familia/{_q(prefix)}' if prefix else None))

    tags = [f'<span class="tag">Grado {_e(grado)}</span>']
    nivel = nivel_label(rec)
    if nivel:
        tags.append(f'<span class="tag">{_e(nivel)}</span>')
    if familia:
        tags.append(f'<a class="tag" href="/familia/{_e(_q(prefix))}">{_e(familia)}</a>' if prefix
                    else f'<span class="tag">{_e(familia)}</span>')
    if rec.get('codigo'):
        tags.append(f'<span class="tag tag-code">{_e(rec["codigo"])}</span>')
    if rec.get('plan_antiguo'):
        tags.append('<span class="badge-old">Plan antiguo</span>')

    body = _crumbs(crumbs)
    body += (f'  <div class="hero">\n    <p class="eyebrow">Grado {_e(grado)} · {_e(GRADO_NOM.get(grado, ""))}</p>\n'
             f'    <h1>{_e(den)}</h1>\n    <div class="tags">{"".join(tags)}</div>\n  </div>\n\n')
    body += '  <main class="content" lang="es">\n'
    body += f'    <p class="lead">{_e(GRADO_TEXT.get(grado, ""))}</p>\n'
    if rec.get('plan_antiguo'):
        body += f'    <p>{_e(PLAN_ANTIGUO_TEXT_C if grado == "C" else PLAN_ANTIGUO_TEXT)}</p>\n'
    body += _contingut_html(rec, ctx.get('contingut') or {})
    if rec.get('observaciones'):
        body += f'\n    <section><h2>Observaciones</h2><p>{_e(rec["observaciones"])}</p></section>'
    if ctx.get('ocupaciones'):
        lis = ''.join(f'<li>{_e(o)}</li>' for o in ctx['ocupaciones'])
        body += ('\n    <section><h2>Salidas profesionales</h2>'
                 f'<p>Ocupaciones y puestos de trabajo relacionados:</p><ul class="ocup">{lis}</ul></section>')
    body += '\n    ' + _centres_html(rec, ctx.get('centres') or {})
    itin = _itinerari_html(rec, ctx)
    if itin:
        body += '\n    ' + itin
    body += ('\n    <section><h2>Ficha oficial</h2><p><a href="/register.html">Ficha oficial disponible '
             'con una cuenta gratuita</a>. Si ya tienes cuenta, <a href="/login.html">inicia sesión</a> '
             'y ábrela desde el buscador.</p></section>')
    fecha = _fmt_date(ctx.get('lastmod'))
    body += ('\n    <p class="src">Datos oficiales del Ministerio de Educación, Formación Profesional y '
             'Deportes (todofp.es)' + (f'. Catálogo actualizado el {fecha}.' if fecha else '.') + '</p>')
    body += '\n  </main>'

    ld = {'@context': 'https://schema.org', '@type': 'Course', 'name': den,
          'description': description, 'url': canonical, 'inLanguage': 'es',
          'educationalCredentialAwarded': f'Grado {grado}: {GRADO_NOM.get(grado, "")}',
          'provider': PROVIDER}
    if rec.get('codigo'):
        ld['courseCode'] = rec['codigo']
    head_extra = f'<script type="application/ld+json">{_json_ld(ld)}</script>'
    return _shell(title=title, description=description, canonical=canonical, body=body,
                  site_url=site_url, head_extra=head_extra)


# ---------------------------------------------------------------------------
# Famílies
# ---------------------------------------------------------------------------

def render_familia(familia: str, prefix: str, records: list, site_url: str) -> str:
    """Graus d'una família agrupats per grau (A→E). records: registres d'ofertes.json."""
    canonical = f'{site_url}/familia/{_q(prefix)}'
    per_grado: dict = {g: [] for g in GRADOS}
    for r in records:
        if r.get('grado') in per_grado:
            per_grado[r['grado']].append(r)
    total = len(records)
    title = f'{familia}: grados de Formación Profesional | GrausFP'
    description = (f'Los {total} grados de Formación Profesional de la familia {familia}, '
                   'del Grado A al Grado E, con datos oficiales.')
    body = _crumbs([('GrausFP', '/index.html'), ('Familias profesionales', '/families'), (familia, None)])
    body += (f'  <div class="hero">\n    <p class="eyebrow">Familia profesional</p>\n'
             f'    <h1>{_e(familia)}</h1>\n    <p class="hero-sub">{total} grados del A al E</p>\n  </div>\n\n')
    body += '  <main class="content" lang="es">'
    for g in GRADOS:
        recs = sorted(per_grado[g], key=lambda r: (r.get('nivel') or 0, r.get('denominacion') or ''))
        if not recs:
            continue
        lis = []
        for r in recs:
            extra = ''
            if r.get('codigo'):
                extra += f'<span class="code">{_e(r["codigo"])}</span>'
            nivel = nivel_label(r)
            tail = f'<span class="g">{_e(nivel)}</span>' if nivel else ''
            if r.get('plan_antiguo'):
                tail += ' <span class="badge-old">Plan antiguo</span>'
            lis.append(f'<li>{extra}<a href="{_e(grau_path(r["ref"]))}">{_e(r.get("denominacion"))}</a>{tail}</li>')
        body += (f'\n    <section><h2>Grado {g} · {_e(GRADO_NOM_PLURAL[g])} ({len(recs)})</h2>'
                 f'<ul class="list">{"".join(lis)}</ul></section>')
    body += '\n  </main>'
    return _shell(title=title, description=description, canonical=canonical, body=body,
                  site_url=site_url)


def render_families(families: list, site_url: str) -> str:
    """families: [(prefix, familia, n_graus)] ja ordenades."""
    canonical = f'{site_url}/families'
    title = 'Familias profesionales de la Formación Profesional | GrausFP'
    description = ('Todas las familias profesionales de la Formación Profesional en España, '
                   'con sus grados del A al E y datos oficiales.')
    lis = ''.join(f'<li><a href="/familia/{_e(_q(p))}">{_e(f)}</a><span class="n">{int(n)}</span></li>'
                  for p, f, n in families)
    body = _crumbs([('GrausFP', '/index.html'), ('Familias profesionales', None)])
    body += ('  <div class="hero">\n    <p class="eyebrow">Formación Profesional</p>\n'
             '    <h1>Familias profesionales</h1>\n  </div>\n\n')
    body += ('  <main class="content" lang="es">\n    <p class="lead">La Formación Profesional se '
             'organiza en familias profesionales. Cada familia reúne los grados de un mismo sector, '
             'del Grado A (acreditación parcial de competencia) al Grado E (curso de especialización).</p>\n'
             f'    <ul class="fam-list">{lis}</ul>\n  </main>')
    return _shell(title=title, description=description, canonical=canonical, body=body,
                  site_url=site_url)


# ---------------------------------------------------------------------------
# Errors, sitemap i robots
# ---------------------------------------------------------------------------

def render_error(site_url: str, *, not_found: bool = True) -> str:
    """404 (grau o família inexistent) o 503 (catàleg no disponible), sense indexar."""
    if not_found:
        title, h1 = 'Página no encontrada | GrausFP', 'No hemos encontrado esta página'
        text = ('Puede que el grado haya cambiado de nombre o ya no forme parte del catálogo oficial. '
                'Puedes buscarlo en el buscador o en la lista de familias profesionales.')
    else:
        title, h1 = 'Datos no disponibles | GrausFP', 'Los datos no están disponibles ahora mismo'
        text = 'Estamos actualizando el catálogo. Vuelve a intentarlo en unos minutos.'
    body = (f'  <div class="hero">\n    <h1>{_e(h1)}</h1>\n  </div>\n\n'
            f'  <main class="content" lang="es">\n    <p>{_e(text)}</p>\n'
            '    <div class="btns"><a class="btn" href="/index.html">Ir al buscador</a>'
            '<a class="btn" href="/families">Familias profesionales</a></div>\n  </main>')
    return _shell(title=title, description=text, canonical=None, body=body,
                  site_url=site_url, noindex=True)


def render_sitemap(entries) -> str:
    """entries: [(loc, lastmod 'AAAA-MM-DD')] → XML del protocol sitemaps.org."""
    urls = ''.join(f'<url><loc>{_e(loc)}</loc><lastmod>{_e(lastmod)}</lastmod></url>\n'
                   for loc, lastmod in entries)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'{urls}</urlset>\n')


def render_robots(site_url: str) -> str:
    return ('User-agent: *\n'
            'Disallow: /api/\n'
            'Disallow: /admin.html\n'
            'Disallow: /perfil.html\n'
            '\n'
            f'Sitemap: {site_url}/sitemap.xml\n')
