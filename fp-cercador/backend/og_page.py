"""
og_page.py — Metadades de previsualització (og:*) en castellà per a les pàgines públiques.

L'idioma de la interfície es tria al navegador, però WhatsApp, LinkedIn i companyia
llegeixen l'HTML tal com surt del servidor (sempre en català). Quan un enllaç compartit
porta ?lang=es, nginx reescriu la petició a /api/og-page/<pàgina> i aquí se li canvien
les metadades al castellà. La resta de la pàgina és idèntica: els textos visibles els
tradueix i18n.js com sempre.
"""
import html
import os
import re

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

OG_IMAGE_ES = "https://grausfp.masellas.info/og-image-es.png"
OG_IMAGE_ALT_ES = "GrausFP: toda la Formación Profesional, en un solo buscador"

# Pàgina → (og:title, descripció). La descripció va a og:description i a meta description.
PAGES_ES = {
    "index": ("GrausFP — Buscador de Formación Profesional",
              "Toda la oferta de Formación Profesional, del Grado A al Grado E, en un solo buscador con datos oficiales."),
    "itinerari": ("Itinerario formativo — GrausFP",
                  "De qué grados está formada una enseñanza de FP y a qué grados da acceso, con datos oficiales."),
    "per-que-grausfp": ("¿Por qué GrausFP?",
                        "Por qué hemos hecho un único buscador para toda la oferta de Formación Profesional."),
    "fonts": ("Fuentes de datos — GrausFP",
              "De dónde salen los datos de GrausFP y cada cuánto se actualizan."),
    "observatori": ("Observatorio de la oferta FP — GrausFP",
                    "Evolución semanal de las titulaciones de Formación Profesional en España (Grados A–E). Estadísticas actualizadas automáticamente desde el Ministerio de Educación."),
    "historial": ("Historial de actualizaciones — GrausFP",
                  "Los cambios de cada actualización del catálogo de Formación Profesional."),
}


def _set_meta(page_html, attr, key, value):
    """Canvia el content de <meta attr="key" content="…">, o l'afegeix si no hi és."""
    pattern = re.compile(r'(<meta\s+%s="%s"\s+content=")[^"]*(")' % (attr, re.escape(key)))
    escaped = html.escape(value, quote=True)
    if pattern.search(page_html):
        return pattern.sub(lambda m: m.group(1) + escaped + m.group(2), page_html, count=1)
    tag = '  <meta %s="%s" content="%s">\n' % (attr, key, escaped)
    return page_html.replace("</head>", tag + "</head>", 1)


def localize_es(page_html, page):
    title, description = PAGES_ES[page]
    out = page_html.replace('<html lang="ca">', '<html lang="es">', 1)
    out = _set_meta(out, "name", "description", description)
    out = _set_meta(out, "property", "og:title", title)
    out = _set_meta(out, "property", "og:description", description)
    out = _set_meta(out, "property", "og:image", OG_IMAGE_ES)
    out = _set_meta(out, "property", "og:image:alt", OG_IMAGE_ALT_ES)
    return out


def render_es(page):
    """HTML de la pàgina amb les metadades en castellà, o None si no és una pàgina pública."""
    if page not in PAGES_ES:
        return None
    with open(os.path.join(FRONTEND_DIR, page + ".html"), encoding="utf-8") as fh:
        return localize_es(fh.read(), page)
