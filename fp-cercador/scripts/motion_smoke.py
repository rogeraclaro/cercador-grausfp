#!/usr/bin/env python3
"""Proves de fum de les microanimacions GSAP (fase 07) amb Playwright + Chrome del sistema.

Eina de desenvolupament: no és una dependència del backend ni la recull pytest.
Serveix fp-cercador/frontend en un port efímer i simula l'API amb page.route, de manera
que no cal backend ni dades locals.

Ús:  python3 -u fp-cercador/scripts/motion_smoke.py [-k SUBSTR ...]
Sortida: "PASS nom" / "FAIL nom: motiu" i "<N> passed, <M> failed".
Codi de sortida: 0 tot OK, 1 algun FAIL, 2 cap prova coincideix amb el filtre o Chrome no arrenca.
"""
import argparse
import functools
import http.server
import json
import re
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
API_ORIGIN = "http://localhost:5001"
ROWS_SEL = "#results-table tr[data-row-id]"
CASCADE_BUDGET_MS = 650  # 600 ms de pressupost (D-07) + un frame

# --- Sampler: es injecta a cada document; mostreja l'atribut style amb requestAnimationFrame ---
SAMPLER_JS = """
window.__samples = {};
window.__startSampler = function (key, selector, ms, limit, mode) {
  window.__samples[key] = [];
  var t0 = performance.now();
  (function tick() {
    var els = Array.prototype.slice.call(document.querySelectorAll(selector), 0, limit);
    var sample = { t: performance.now(),
      styles: els.map(function (e) { return e.getAttribute('style') || ''; }) };
    if (mode === 'text') {
      // own: primer node de text de l'element; ghost: text del fill aria-hidden (còpia que compta) o null
      sample.texts = els.map(function (e) {
        var first = e.firstChild, ghost = e.querySelector('[aria-hidden="true"]');
        return { own: first && first.nodeType === 3 ? first.textContent.trim() : null,
                 ghost: ghost ? ghost.textContent : null, style: e.getAttribute('style') || '' };
      });
    }
    window.__samples[key].push(sample);
    if (performance.now() - t0 < ms) requestAnimationFrame(tick);
  })();
};
"""

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


# --- Servidor estàtic ---
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def start_static_server():
    handler = functools.partial(QuietHandler, directory=str(FRONTEND))
    srv = http.server.ThreadingHTTPServer(("localhost", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://localhost:%d" % srv.server_address[1]


# --- Dades sintètiques (no es llegeix backend/data/ofertes.json: és ignorat per git) ---
def catalog_fixture():
    families = ["Hostelería y Turismo", "Electricidad y Electrónica", "Informática y Comunicaciones"]
    other_words = ["Soldadura", "Redes", "Mantenimiento", "Domótica", "Programación", "Sistemas", "Instalaciones"]
    records = []
    for i in range(1, 121):
        word = "Cocina" if i <= 70 else other_words[i % len(other_words)]
        codigo = "COD%03d" % i
        records.append({
            "id": i, "ref": codigo, "codigo": codigo,
            "denominacion": "%s técnico %d" % (word, i),
            "familia": families[i % 3], "nivel": 1 + (i % 3),
            "plan_antiguo": False, "observaciones": "", "grado": "ABCDE"[i % 5],
        })
    return records


# --- Pàgines de prova ---
def new_page(browser, base, reduced=False, block_gsap=False, api=None, sample=None):
    ctx = browser.new_context(
        locale="ca-ES", viewport={"width": 1280, "height": 900},
        reduced_motion="reduce" if reduced else "no-preference")
    ctx.add_init_script(SAMPLER_JS)
    if sample:
        ctx.add_init_script("window.__startSampler.apply(null, %s);" % json.dumps(list(sample)))
    routes = {"/api/ofertes": catalog_fixture()}
    routes.update(api or {})

    def handler(route):
        req = route.request
        url = urlparse(req.url)
        origin = "%s://%s" % (url.scheme, url.netloc)
        if origin == base:
            if block_gsap and "/vendor/gsap-" in url.path:
                return route.abort()
            return route.continue_()
        if origin == API_ORIGIN:
            cors = {"access-control-allow-origin": req.headers.get("origin", "*"),
                    "access-control-allow-credentials": "true",
                    "access-control-allow-headers": "*"}
            if req.method == "OPTIONS":
                return route.fulfill(status=204, headers=cors)
            if url.path in routes:
                return route.fulfill(status=200, headers=dict(cors, **{"content-type": "application/json"}),
                                     body=json.dumps(routes[url.path]))
            return route.fulfill(status=404, headers=dict(cors, **{"content-type": "application/json"}), body="{}")
        return route.abort()

    ctx.route("**/*", handler)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    return page, errors


def start_sampler(page, key, selector, ms, limit):
    page.evaluate("window.__startSampler(%s, %s, %d, %d); 0" % (
        json.dumps(key), json.dumps(selector), ms, limit))


def read_samples(page, key):
    return page.evaluate("JSON.parse(JSON.stringify(window.__samples[%s] || []))" % json.dumps(key))


def open_index(page, base, rows=10):
    page.goto(base + "/index.html")
    page.wait_for_function("document.querySelectorAll('%s').length >= %d" % (ROWS_SEL, rows), timeout=10000)


def animated(sample):
    """Un mostreig és «animat» si alguna fila té opacity o transform en línia."""
    return any(re.search(r"opacity|transform", s) for s in sample["styles"])


def opacity_of(style):
    m = re.search(r"opacity:\s*([\d.]+)", style)
    return float(m.group(1)) if m else None


def assert_clean_rows(page, n=12):
    state = page.evaluate("""Array.from(document.querySelectorAll('%s')).slice(0, %d).map(function (e) {
      return { style: e.getAttribute('style') || '', op: getComputedStyle(e).opacity }; })""" % (ROWS_SEL, n))
    assert len(state) == n, "només %d files renderitzades" % len(state)
    dirty = [s for s in state if s["style"].strip() or s["op"] != "1"]
    assert not dirty, "files amb estil residual: %r" % dirty[:2]


# --- Proves ---
@check("index:rows-cascade")
def rows_cascade(browser, base):
    page, errors = new_page(browser, base)
    open_index(page, base)
    start_sampler(page, "rows", ROWS_SEL, 1500, 12)
    page.fill("#search", "cocina")
    page.wait_for_timeout(1700)
    samples = read_samples(page, "rows")
    anim = [s for s in samples if animated(s)]
    assert anim, "la cascada no s'ha executat (cap fila amb estil en línia)"
    assert any(opacity_of(s["styles"][0]) is not None and opacity_of(s["styles"][0]) < 1 and "transform" in s["styles"][0]
               for s in samples), "la fila 0 no mostra opacity < 1 amb transform"
    first = anim[0]
    assert all("opacity" not in st for st in first["styles"][10:12]), "més de 10 files animades"
    low = [opacity_of(st) for s in anim for st in s["styles"] if opacity_of(st) is not None]
    assert min(low) >= 0.4 - 1e-6, "una fila baixa de 0.4 d'opacitat (%s)" % min(low)
    span = anim[-1]["t"] - first["t"]
    assert span <= CASCADE_BUDGET_MS, "la cascada dura %.0f ms (> %d)" % (span, CASCADE_BUDGET_MS)
    assert_clean_rows(page)
    assert not errors, "errors de pàgina: %r" % errors


VM_JS = "Alpine.$data(document.querySelector('[x-data=\"cercador\"]'))"
BOX_SEL = '[x-ref="alertBox"]'


def open_alert_modal(page, error=""):
    """Obre el modal d'alerta via l'estat d'Alpine; retorna performance.now() del moment d'obrir."""
    return page.evaluate("""(function () {
      var vm = %s; vm.alertSaveError = %s;
      var t = performance.now(); vm.alertModalVisible = true; return t; })()""" % (VM_JS, json.dumps(error)))


def transform_samples(samples, t_set=None, within=None):
    out = [s for s in samples if any("transform" in st for st in s["styles"])]
    if within is not None:
        out = [s for s in out if s["t"] - t_set <= within]
    return out


def start_modal_samplers(page, ms):
    start_sampler(page, "box", BOX_SEL, ms, 1)
    start_sampler(page, "tick", ".ok-tick", ms, 1)


@check("index:modal-pop")
def modal_pop(browser, base):
    page, errors = new_page(browser, base)
    open_index(page, base)
    start_modal_samplers(page, 900)
    t_set = open_alert_modal(page)
    page.wait_for_timeout(150)
    box_early = transform_samples(read_samples(page, "box"), t_set, 150)
    tick_early = transform_samples(read_samples(page, "tick"), t_set, 150)
    assert box_early, "el box no té transform en línia en els primers 150 ms"
    assert tick_early, "el .ok-tick no té transform en línia en els primers 150 ms"
    focused = page.evaluate("document.activeElement && document.activeElement.className || ''")
    assert "centres-modal-close" in focused, "el focus no és al botó de tancar: %r" % focused
    page.wait_for_timeout(750)
    samples = read_samples(page, "box") + read_samples(page, "tick")
    anim = sorted(transform_samples(samples), key=lambda s: s["t"])
    span = anim[-1]["t"] - anim[0]["t"]
    assert span <= CASCADE_BUDGET_MS, "l'animació dura %.0f ms (> %d)" % (span, CASCADE_BUDGET_MS)
    final = page.evaluate("""(function () {
      var box = document.querySelector('%s'), tick = document.querySelector('.ok-tick');
      var label = document.querySelector('[data-i18n="modal.alert.ok"]');
      return { boxStyle: box.getAttribute('style') || '', boxTf: getComputedStyle(box).transform,
        tickDisplay: getComputedStyle(tick).display, tickAria: tick.getAttribute('aria-hidden'),
        tickText: tick.textContent, label: label.textContent.trim() }; })()""" % BOX_SEL)
    assert "transform" not in final["boxStyle"] and final["boxTf"] == "none", "el box conserva transform: %r" % final
    assert final["tickDisplay"] == "inline-block", "el .ok-tick no és inline-block: %r" % final["tickDisplay"]
    assert final["tickAria"] == "true", "el .ok-tick no té aria-hidden"
    assert final["tickText"] == "✓", "text del .ok-tick: %r" % final["tickText"]
    assert final["label"] == "Alerta desada correctament", "text de l'etiqueta: %r" % final["label"]
    assert not errors, "errors de pàgina: %r" % errors


@check("index:modal-error-untouched")
def modal_error_untouched(browser, base):
    page, errors = new_page(browser, base)
    open_index(page, base)
    start_modal_samplers(page, 400)
    open_alert_modal(page, "Error de prova")
    page.wait_for_timeout(500)
    assert not transform_samples(read_samples(page, "box")), "el box de l'error té transform en línia"
    assert page.evaluate("document.querySelectorAll('.ok-tick').length") == 0, "hi ha un .ok-tick a la variant d'error"
    assert not errors, "errors de pàgina: %r" % errors


@check("index:no-cascade-on-load")
def no_cascade_on_load(browser, base):
    page, errors = new_page(browser, base, sample=("rows", ROWS_SEL, 3000, 12))
    open_index(page, base)
    page.wait_for_timeout(3000)
    samples = read_samples(page, "rows")
    assert any(len(s["styles"]) > 0 for s in samples), "no s'han renderitzat files durant el mostreig"
    assert not any(re.search(r"opacity", st) for s in samples for st in s["styles"]), \
        "la càrrega inicial ha animat files"
    assert not errors, "errors de pàgina: %r" % errors


@check("index:no-cascade-on-pagination")
def no_cascade_on_pagination(browser, base):
    page, errors = new_page(browser, base)
    open_index(page, base)
    page.fill("#search", "cocina")
    page.wait_for_timeout(1000)
    first_before = page.evaluate("document.querySelector('%s').dataset.rowId" % ROWS_SEL)
    start_sampler(page, "rows", ROWS_SEL, 800, 12)
    btn = page.locator("nav.pagination").first.locator(".pagination-item button", has_text="2")
    if btn.count() == 1:
        btn.click()
    else:  # el control no és seleccionable de manera única: fa el mateix que el clic
        page.evaluate("%s.goToPage(2); 0" % VM_JS)
    page.wait_for_timeout(1000)
    first_after = page.evaluate("document.querySelector('%s').dataset.rowId" % ROWS_SEL)
    assert first_before != first_after, "la pàgina no ha canviat"
    samples = read_samples(page, "rows")
    assert not any(re.search(r"opacity", st) for s in samples for st in s["styles"]), "paginar ha animat files"
    assert not errors, "errors de pàgina: %r" % errors


@check("index:restart-clean")
def restart_clean(browser, base):
    page, errors = new_page(browser, base)
    open_index(page, base)
    start_sampler(page, "rows", ROWS_SEL, 1700, 12)
    page.select_option("#filter-familia", "Hostelería y Turismo")
    page.wait_for_timeout(40)
    t_second = page.evaluate("(function () { var t = performance.now(); return t; })()")
    page.select_option("#filter-familia", "Electricidad y Electrónica")
    page.wait_for_timeout(1400)
    samples = [s for s in read_samples(page, "rows") if s["t"] >= t_second]
    anim = [s for s in samples if animated(s)]
    assert anim, "cap cascada després del segon canvi"
    span = anim[-1]["t"] - t_second
    assert span <= CASCADE_BUDGET_MS, "la cascada reiniciada acaba %.0f ms després (> %d)" % (span, CASCADE_BUDGET_MS)
    assert_clean_rows(page)
    assert not errors, "errors de pàgina: %r" % errors


@check("index:reduced-motion")
def reduced_motion(browser, base):
    page, errors = new_page(browser, base, reduced=True)
    open_index(page, base)
    start_sampler(page, "rows", ROWS_SEL, 800, 12)
    page.fill("#search", "cocina")
    page.wait_for_timeout(1000)
    samples = read_samples(page, "rows")
    assert not any(re.search(r"opacity|transform", st) for s in samples for st in s["styles"]), \
        "amb reduced motion hi ha estils d'animació en línia a les files"
    start_modal_samplers(page, 400)
    open_alert_modal(page)
    page.wait_for_timeout(500)
    assert not transform_samples(read_samples(page, "box")), "el box del modal s'ha animat amb reduced motion"
    assert page.evaluate("window.GFPMotion.play('probe', function () {})") is False, "GFPMotion.play no retorna false"
    assert not errors, "errors de pàgina: %r" % errors


@check("index:gsap-blocked")
def gsap_blocked(browser, base):
    page, errors = new_page(browser, base, block_gsap=True)
    open_index(page, base)
    assert page.evaluate("typeof gsap") == "undefined", "gsap s'ha carregat tot i el bloqueig"
    assert page.evaluate("window.GFPMotion.play('probe', function () {})") is False, "GFPMotion.play no retorna false"
    page.fill("#search", "cocina")
    page.wait_for_timeout(800)
    state = page.evaluate("""(function () {
      var rows = Array.from(document.querySelectorAll('%s'));
      return { n: rows.length, first: rows[0].textContent, op: getComputedStyle(rows[0]).opacity,
        styled: rows.filter(function (r) { return (r.getAttribute('style') || '').trim(); }).length }; })()""" % ROWS_SEL)
    assert state["n"] > 0 and "Cocina" in state["first"], "la cerca no filtra les files: %r" % state["first"][:60]
    assert state["op"] == "1" and state["styled"] == 0, "files amb estil en línia: %r" % state
    start_modal_samplers(page, 300)
    open_alert_modal(page)
    page.wait_for_timeout(150)
    focused = page.evaluate("document.activeElement && document.activeElement.className || ''")
    assert "centres-modal-close" in focused, "el focus no és al botó de tancar: %r" % focused
    assert not errors, "errors de pàgina: %r" % errors


# --- Observatori (07-02) ---
OBS_FIXTURE = {
    "current": {"ts": "2026-10-25T03:00:00Z", "total": 12894, "A": 8537, "B": 2786, "C": 820, "D": 600, "E": 151},
    "series": [],  # sèrie buida: renderLineChart queda a la branca «poques dades»
    "recent_changes": [],
}
OBS_API = {"/api/observatory": OBS_FIXTURE}
BARS_SEL = "#chart-grados .bar-fill"


def open_observatori(page, base):
    page.goto(base + "/observatori.html")
    page.wait_for_selector("#chart-grados .bar-row", timeout=10000)


def expected_widths():
    total = OBS_FIXTURE["current"]["total"]
    return ["%.1f%%" % (OBS_FIXTURE["current"][g] / total * 100) for g in "ABCDE"]


def assert_final_bars(page):
    state = page.evaluate("""Array.from(document.querySelectorAll('%s')).map(function (e) {
      return { style: e.getAttribute('style') || '', width: e.style.width, tf: getComputedStyle(e).transform }; })""" % BARS_SEL)
    assert len(state) == 5, "barres renderitzades: %d" % len(state)
    assert all("transform" not in s["style"] and s["tf"] == "none" for s in state), "barres amb transform residual: %r" % state
    assert [s["width"] for s in state] == expected_widths(), "amplades finals: %r" % [s["width"] for s in state]


@check("observatori:bars-grow")
def obs_bars_grow(browser, base):
    page, errors = new_page(browser, base, api=OBS_API, sample=("fills", BARS_SEL, 1500, 5))
    open_observatori(page, base)
    page.wait_for_timeout(1500)
    samples = read_samples(page, "fills")
    anim = [s for s in samples if any("transform" in st for st in s["styles"])]
    assert anim, "les barres no s'han animat (cap transform en línia)"
    span = anim[-1]["t"] - anim[0]["t"]
    assert span <= CASCADE_BUDGET_MS, "l'animació de les barres dura %.0f ms (> %d)" % (span, CASCADE_BUDGET_MS)
    assert_final_bars(page)
    total = page.evaluate("document.getElementById('stat-total').textContent")
    assert total == page.evaluate("(12894).toLocaleString('ca-ES')"), "#stat-total: %r" % total
    assert not errors, "errors de pàgina: %r" % errors


VALUES_SEL = "#chart-grados .bar-value"
FINAL_TEXTS_JS = """(function () {
  var c = %s, total = c.total;
  return ['A', 'B', 'C', 'D', 'E'].map(function (g) {
    return c[g].toLocaleString('ca-ES') + ' (' + ((c[g] / total) * 100).toFixed(1) + '%%)'; });
})()""" % json.dumps(OBS_FIXTURE["current"])


def assert_final_values(page, samples):
    """Cap mostreig pot mostrar un text propi diferent del final; retorna els textos finals."""
    finals = page.evaluate(FINAL_TEXTS_JS)
    seen = [s for s in samples if s.get("texts")]
    assert seen, "el sampler no ha vist cap .bar-value"
    for s in seen:
        assert [t["own"] for t in s["texts"]] == finals, "text propi no final: %r" % [t["own"] for t in s["texts"]]
    return finals


def assert_idle_values(page):
    state = page.evaluate("""Array.from(document.querySelectorAll('%s')).map(function (e) {
      return { style: e.getAttribute('style') || '', n: e.dataset.n, ghosts: e.querySelectorAll('[aria-hidden]').length }; })""" % VALUES_SEL)
    want = [str(OBS_FIXTURE["current"][g]) for g in "ABCDE"]
    assert [s["n"] for s in state] == want, "data-n: %r" % [s["n"] for s in state]
    assert all(not s["style"].strip() and s["ghosts"] == 0 for s in state), "estat residual a .bar-value: %r" % state
    assert page.evaluate("document.querySelectorAll('#chart-grados [aria-hidden=\"true\"]').length") == 0, \
        "queden elements aria-hidden al gràfic"


@check("observatori:final-text")
def obs_final_text(browser, base):
    page, errors = new_page(browser, base, api=OBS_API, sample=("vals", VALUES_SEL, 1500, 5, "text"))
    page.goto(base + "/observatori.html")
    page.wait_for_selector("#chart-grados .bar-row", timeout=10000)
    tree = page.locator("#chart-grados").aria_snapshot()  # just after the first .bar-row appears
    finals = page.evaluate(FINAL_TEXTS_JS)
    missing = [f for f in finals if f not in tree]
    assert not missing, "l'arbre d'accessibilitat no conté els valors finals %r: %s" % (missing, tree)
    page.wait_for_timeout(1500)
    samples = read_samples(page, "vals")
    assert_final_values(page, samples)
    counted = [s for s in samples for t in s.get("texts", []) if t["ghost"] is not None and t["ghost"] not in finals]
    assert counted, "cap mostreig amb una còpia que compta (aria-hidden) diferent del valor final"
    assert_idle_values(page)
    assert not errors, "errors de pàgina: %r" % errors


def assert_no_motion(page, samples):
    assert not [s for s in samples if any(re.search(r"transform", st) for st in s["styles"])], "barres amb transform"
    assert not [s for s in samples for t in s.get("texts", []) if t["ghost"] is not None or t["style"].strip()], \
        "còpia que compta o estil a .bar-value"


def run_static_obs(browser, base, **flags):
    page, errors = new_page(browser, base, api=OBS_API, **flags)
    page.add_init_script("window.__startSampler('fills', %s, 1500, 5); window.__startSampler('vals', %s, 1500, 5, 'text');"
                         % (json.dumps(BARS_SEL), json.dumps(VALUES_SEL)))
    open_observatori(page, base)
    page.wait_for_timeout(1200)
    fills, vals = read_samples(page, "fills"), read_samples(page, "vals")
    assert_no_motion(page, fills)
    assert_no_motion(page, vals)
    assert_final_values(page, vals)
    assert_final_bars(page)
    assert_idle_values(page)
    return page, errors


@check("observatori:reduced-motion")
def obs_reduced_motion(browser, base):
    page, errors = run_static_obs(browser, base, reduced=True)
    assert page.evaluate("window.GFPMotion.play('probe', function () {})") is False, "GFPMotion.play no retorna false"
    assert not errors, "errors de pàgina: %r" % errors


@check("observatori:gsap-blocked")
def obs_gsap_blocked(browser, base):
    page, errors = run_static_obs(browser, base, block_gsap=True)
    assert page.evaluate("typeof gsap") == "undefined", "gsap s'ha carregat tot i el bloqueig"
    assert page.evaluate("window.GFPMotion.play('probe', function () {})") is False, "GFPMotion.play no retorna false"
    assert not errors, "errors de pàgina: %r" % errors


# --- Itinerari (07-03) ---
def _itin_node(grado, n, familia="Informática y Comunicaciones", **extra):
    ref = "%s%d" % (grado, n)
    node = {"key": "%s:%s" % (grado, ref), "ref": ref, "grado": grado, "codigo": ref, "id": None,
            "denominacion": "Títol de prova %s" % ref, "familia": familia, "nivel": 1,
            "plan_antiguo": False, "ficha": None}
    node.update(extra)
    return node


# Mateixa forma que /api/itinerari/complet: from = grau inferior; kind ab|bc|cd|de; cd porta shared/total (LOMLOE).
ITIN_FIXTURE = {
    "focus": "C:C1",
    "nodes": [_itin_node("A", 1), _itin_node("B", 1), _itin_node("C", 1),
              _itin_node("D", 1), _itin_node("D", 2), _itin_node("D", 3, plan_antiguo=True),
              _itin_node("E", 1)],
    "edges": [
        {"from": "A:A1", "to": "B:B1", "kind": "ab"},
        {"from": "B:B1", "to": "C:C1", "kind": "bc"},
        {"from": "C:C1", "to": "D:D1", "kind": "cd", "shared": 3, "total": 3},   # t-full
        {"from": "C:C1", "to": "D:D2", "kind": "cd", "shared": 1, "total": 3},   # t-part
        {"from": "C:C1", "to": "D:D3", "kind": "cd"},                            # t-old
        {"from": "D:D1", "to": "E:E1", "kind": "de"},
    ],
    "warnings": [],
}
ITIN_API = {"/api/itinerari/complet": ITIN_FIXTURE}
ITIN_URL = "/itinerari.html?grado=C&ref=C1"
PATHS_SEL = ".tl-lines path"
ITIN_SAMPLE_MS = 3000
ITIN_SPAN_BUDGET_MS = 617  # topall de 600 ms (D-07) + un frame a 60 Hz
ITIN_VM_JS = "Alpine.$data(document.querySelector('[x-data=\"itinerari\"]'))"


def open_itinerari(page, base):
    page.goto(base + ITIN_URL)
    page.wait_for_selector(PATHS_SEL, state="attached", timeout=10000)


def wait_sampler_done(page, key, ms):
    page.wait_for_function(
        "(function () { var s = window.__samples[%s]; return !!s && s.length > 1 && s[s.length - 1].t - s[0].t >= %d; })()"
        % (json.dumps(key), ms - 30), timeout=ms + 8000)


def path_animated(sample):
    return any("stroke-dashoffset" in st for st in sample["styles"])


def assert_itin_idle(page):
    """Estat final del SVG: sis trams, cap pathLength/màscara/defs i cap estil de traç en línia."""
    state = page.evaluate("""(function () {
      var ps = Array.from(document.querySelectorAll('.tl-lines path'));
      return { n: ps.length,
        pathLength: ps.filter(function (p) { return p.hasAttribute('pathLength'); }).length,
        dash: ps.filter(function (p) { return /stroke-dash/.test(p.getAttribute('style') || ''); }).length }; })()""")
    assert state["n"] == 6, "trams dibuixats: %d" % state["n"]
    assert state["pathLength"] == 0, "queden %d paths amb pathLength" % state["pathLength"]
    assert state["dash"] == 0, "queden %d paths amb stroke-dash* en línia" % state["dash"]


def assert_sequence_span(page, errors):
    samples = read_samples(page, "paths")
    anim = [s for s in samples if path_animated(s)]
    assert anim, "el dibuix no s'ha executat (cap path amb stroke-dashoffset)"
    span = anim[-1]["t"] - anim[0]["t"]
    assert span <= ITIN_SPAN_BUDGET_MS, "la seqüència dura %.0f ms (> %d)" % (span, ITIN_SPAN_BUDGET_MS)
    assert_itin_idle(page)
    assert not errors, "errors de pàgina: %r" % errors


@check("itinerari:solid-draw")
def itin_solid_draw(browser, base):
    page, errors = new_page(browser, base, api=ITIN_API, sample=("paths", PATHS_SEL, ITIN_SAMPLE_MS, 12))
    open_itinerari(page, base)
    wait_sampler_done(page, "paths", ITIN_SAMPLE_MS)
    assert_sequence_span(page, errors)


@check("itinerari:restart-keeps-t0")
def itin_restart_keeps_t0(browser, base):
    page, errors = new_page(browser, base, api=ITIN_API, sample=("paths", PATHS_SEL, ITIN_SAMPLE_MS, 12))
    open_itinerari(page, base)
    page.wait_for_function("document.querySelector('.tl-lines path[style*=\"stroke-dashoffset\"]') !== null", timeout=10000)
    page.wait_for_timeout(100)
    page.set_viewport_size({"width": 1200, "height": 900})  # > 759 px: segueix en línia de temps i força un redibuix
    wait_sampler_done(page, "paths", ITIN_SAMPLE_MS)
    assert_sequence_span(page, errors)


# Mostreja per frame les màscares i l'estat dels trams discontinus (t-part / t-old) des de l'inici del document.
DASH_SAMPLER_JS = """
window.__dash = [];
(function () {
  var t0 = performance.now();
  (function tick() {
    var svg = document.querySelector('.tl-lines');
    var masks = svg ? Array.prototype.slice.call(svg.querySelectorAll('mask')) : [];
    var dashed = svg ? Array.prototype.slice.call(svg.querySelectorAll('path.t-part, path.t-old')) : [];
    window.__dash.push({
      masks: masks.length,
      units: masks.map(function (m) { return m.getAttribute('maskUnits'); }),
      bad: dashed.filter(function (p) {
        return p.hasAttribute('pathLength') || /stroke-dasharray/.test(p.getAttribute('style') || ''); }).length });
    if (performance.now() - t0 < %d) requestAnimationFrame(tick);
  })();
})();
""" % ITIN_SAMPLE_MS


@check("itinerari:dashed-preserved")
def itin_dashed_preserved(browser, base):
    page, errors = new_page(browser, base, api=ITIN_API)
    page.add_init_script(DASH_SAMPLER_JS)
    open_itinerari(page, base)
    page.wait_for_timeout(ITIN_SAMPLE_MS + 200)
    frames = page.evaluate("window.__dash")
    assert any(f["masks"] > 0 for f in frames), "cap màscara durant el dibuix dels trams discontinus"
    units = {u for f in frames for u in f["units"]}
    assert units == {"userSpaceOnUse"}, "maskUnits inesperats: %r" % units
    assert not any(f["bad"] for f in frames), "un tram discontinu ha tingut pathLength o stroke-dasharray en línia"
    final = page.evaluate("""(function () {
      function dash(sel) { return getComputedStyle(document.querySelector(sel)).strokeDasharray; }
      var q = function (sel) { return document.querySelectorAll(sel).length; };
      return { part: dash('.tl-lines path.t-part'), old: dash('.tl-lines path.t-old'),
        left: q('.tl-lines mask') + q('.tl-lines defs') + q('.tl-lines path[mask]') + q('.tl-lines path[pathLength]') }; })()""")
    assert final["part"] == "7px, 4px", "patró de t-part: %r" % final["part"]
    assert final["old"] == "1.5px, 4px", "patró de t-old: %r" % final["old"]
    assert final["left"] == 0, "queden %d màscares/defs/pathLength al SVG" % final["left"]
    assert_itin_idle(page)
    assert not errors, "errors de pàgina: %r" % errors


@check("itinerari:endpoints-aligned")
def itin_endpoints_aligned(browser, base):
    page, errors = new_page(browser, base, api=ITIN_API)
    open_itinerari(page, base)
    page.wait_for_timeout(2000)
    rows = page.evaluate("""(function () {
      var box = document.querySelector('.tl').getBoundingClientRect();
      function rect(key) { return document.querySelector('.node[data-key="' + key + '"]').getBoundingClientRect(); }
      return Array.from(document.querySelectorAll('.tl-lines path')).map(function (p) {
        var n = (p.getAttribute('d').match(/-?\\d+(?:\\.\\d+)?/g) || []).map(Number);   // M x1,y1 C c1x,c1y c2x,c2y x2,y2
        var a = rect(p.dataset.from), b = rect(p.dataset.to);
        return { pair: p.dataset.from + '>' + p.dataset.to, n: n.length,
          dx1: n[0] - (a.right - box.left), dy1: n[1] - (a.top - box.top + a.height / 2),
          dx2: n[6] - (b.left - box.left), dy2: n[7] - (b.top - box.top + b.height / 2) }; });
    })()""")
    assert len(rows) == 6, "trams dibuixats: %d" % len(rows)
    for r in rows:
        assert r["n"] == 8, "format de d inesperat a %s" % r["pair"]
        off = max(abs(r[k]) for k in ("dx1", "dy1", "dx2", "dy2"))
        assert off < 1, "el tram %s s'allunya %.2f px dels nodes" % (r["pair"], off)
    assert not errors, "errors de pàgina: %r" % errors


# Mostrejador de tota la línia de temps: trams, màscares, parades (.node) i el seu .node-main.
# window.__startItin(ms) reinicia window.__itin i mostreja amb requestAnimationFrame.
ITIN_SAMPLER_JS = """
window.__itin = [];
window.__startItin = function (ms) {
  window.__itin = [];
  var t0 = performance.now();
  (function tick() {
    var svg = document.querySelector('.tl-lines');
    var paths = svg ? Array.prototype.slice.call(svg.querySelectorAll('path')) : [];
    var nodes = Array.prototype.slice.call(document.querySelectorAll('.node[data-key]'));
    var focus = document.querySelector('.node.is-focus .node-main');
    var styleOf = function (e) { return e.getAttribute('style') || ''; };
    window.__itin.push({
      t: performance.now(),
      pathDash: paths.some(function (p) { return /stroke-dash/.test(styleOf(p)); }),
      pathLength: paths.some(function (p) { return p.hasAttribute('pathLength'); }),
      masks: svg ? svg.querySelectorAll('mask').length : 0,
      nodeStyles: nodes.map(styleOf),
      mainStyles: Array.prototype.slice.call(document.querySelectorAll('.node .node-main')).map(styleOf),
      focusStyle: focus ? styleOf(focus) : null });
    if (performance.now() - t0 < ms) requestAnimationFrame(tick);
  })();
};
"""


def itin_page(browser, base, sample_ms=ITIN_SAMPLE_MS, **flags):
    """Pàgina d'itinerari amb el mostrejador de la línia de temps actiu des de l'inici del document."""
    page, errors = new_page(browser, base, api=ITIN_API, **flags)
    page.add_init_script(ITIN_SAMPLER_JS)
    if sample_ms:
        page.add_init_script("window.__startItin(%d);" % sample_ms)
    return page, errors


def itin_samples(page):
    return page.evaluate("JSON.parse(JSON.stringify(window.__itin))")


def itin_animated(s):
    """Mostreig amb qualsevol estil d'animació de la línia de temps."""
    return (s["pathDash"] or s["masks"] > 0 or any(s["nodeStyles"]) or any(s["mainStyles"]))


def wait_itin_done(page, ms):
    page.wait_for_function("(function () { var s = window.__itin; return s.length > 1 && s[s.length - 1].t - s[0].t >= %d; })()"
                           % (ms - 30), timeout=ms + 8000)


@check("itinerari:stops-light")
def itin_stops_light(browser, base):
    page, errors = itin_page(browser, base)
    open_itinerari(page, base)
    wait_itin_done(page, ITIN_SAMPLE_MS)
    samples = itin_samples(page)
    assert any("background-color" in st for s in samples for st in s["nodeStyles"]), "cap parada s'ha il·luminat"
    assert not any(re.search(r"transform|opacity", st) for s in samples for st in s["nodeStyles"]), \
        "un .node ha tingut transform o opacity en línia"
    left = page.evaluate("Array.from(document.querySelectorAll('.node')).filter(function (n) { return (n.getAttribute('style') || '').trim(); }).length")
    assert left == 0, "queden %d .node amb estil en línia" % left
    anim = [s for s in samples if itin_animated(s)]
    span = anim[-1]["t"] - anim[0]["t"]
    assert span <= ITIN_SPAN_BUDGET_MS, "la seqüència dura %.0f ms (> %d)" % (span, ITIN_SPAN_BUDGET_MS)
    assert not errors, "errors de pàgina: %r" % errors


@check("itinerari:first-stop")
def itin_first_stop(browser, base):
    page, errors = itin_page(browser, base)
    open_itinerari(page, base)
    wait_itin_done(page, ITIN_SAMPLE_MS)
    samples = itin_samples(page)
    rises = [s for s in samples if s["focusStyle"] and "transform" in s["focusStyle"]
             and 0.4 - 1e-6 <= (opacity_of(s["focusStyle"]) or 9) < 1]
    assert rises, "el .node-main del focus no mostra opacity 0.4..1 amb transform"
    floor = [opacity_of(s["focusStyle"]) for s in samples if opacity_of(s["focusStyle"] or "") is not None]
    assert min(floor) >= 0.4 - 1e-6, "el focus baixa de 0.4 d'opacitat (%s)" % min(floor)
    assert not (samples[-1]["focusStyle"] or "").strip(), "el .node-main del focus conserva estil: %r" % samples[-1]["focusStyle"]
    text = page.evaluate("document.querySelector('.node.is-focus').textContent.replace(/\\s+/g, ' ').trim()")
    plain, plain_errors = itin_page(browser, base, sample_ms=0, block_gsap=True)
    open_itinerari(plain, base)
    plain.wait_for_timeout(500)
    plain_text = plain.evaluate("document.querySelector('.node.is-focus').textContent.replace(/\\s+/g, ' ').trim()")
    assert text == plain_text, "el focus té text nou: %r != %r" % (text, plain_text)
    assert not errors and not plain_errors, "errors de pàgina: %r" % (errors + plain_errors)


@check("itinerari:no-reanimate")
def itin_no_reanimate(browser, base):
    page, errors = itin_page(browser, base, sample_ms=0)
    open_itinerari(page, base)
    page.wait_for_timeout(2000)
    page.evaluate("window.__startItin(1800)")
    page.set_viewport_size({"width": 1100, "height": 900})  # > 759 px: redibuix, no arbre
    page.wait_for_timeout(600)
    page.evaluate("var vm = %s; vm.setView('tree'); 0" % ITIN_VM_JS)
    page.wait_for_timeout(300)
    page.evaluate("var vm = %s; vm.setView('timeline'); 0" % ITIN_VM_JS)
    page.wait_for_timeout(600)
    wait_itin_done(page, 1800)
    samples = itin_samples(page)
    assert samples, "el mostrejador no ha vist res"
    assert not [s for s in samples if itin_animated(s) or s["pathLength"]], "un redibuix tardà ha tornat a animar"
    assert page.evaluate("document.querySelectorAll('.tl-lines path').length") == 6, "no hi ha 6 trams després de tornar a la línia de temps"
    assert not errors, "errors de pàgina: %r" % errors


def assert_itin_static(page, samples):
    assert samples, "el mostrejador no ha vist res"
    assert not [s for s in samples if itin_animated(s) or s["pathLength"]], "hi ha estils d'animació a la línia de temps"
    assert not [s for s in samples if s["focusStyle"]], "el .node-main del focus s'ha animat"
    assert page.evaluate("document.querySelectorAll('.tl-lines path').length") == 6, "no hi ha 6 trams dibuixats"
    assert page.evaluate("window.GFPMotion.play('probe', function () {})") is False, "GFPMotion.play no retorna false"


@check("itinerari:reduced-motion")
def itin_reduced_motion(browser, base):
    page, errors = itin_page(browser, base, reduced=True)
    open_itinerari(page, base)
    wait_itin_done(page, ITIN_SAMPLE_MS)
    assert_itin_static(page, itin_samples(page))
    assert not errors, "errors de pàgina: %r" % errors


@check("itinerari:gsap-blocked")
def itin_gsap_blocked(browser, base):
    page, errors = itin_page(browser, base, block_gsap=True)
    open_itinerari(page, base)
    wait_itin_done(page, ITIN_SAMPLE_MS)
    assert page.evaluate("typeof gsap") == "undefined", "gsap s'ha carregat tot i el bloqueig"
    assert_itin_static(page, itin_samples(page))
    assert not errors, "errors de pàgina: %r" % errors


# --- Execució ---
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-k", action="append", default=[], metavar="SUBSTR",
                    help="només les proves el nom de les quals conté SUBSTR (repetible)")
    args = ap.parse_args()
    selected = [(n, f) for n, f in CHECKS if not args.k or any(k in n for k in args.k)]
    if not selected:
        print("ERROR: cap prova coincideix amb el filtre %r" % args.k)
        return 2
    srv, base = start_static_server()
    passed = failed = 0
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="chrome", headless=True)
        except Exception as e:  # noqa: BLE001
            print("ERROR chrome: %s" % e)
            srv.shutdown()
            return 2
        for name, fn in selected:
            try:
                fn(browser, base)
                print("PASS %s" % name)
                passed += 1
            except Exception as e:  # noqa: BLE001
                print("FAIL %s: %s" % (name, str(e).splitlines()[0] if str(e) else type(e).__name__))
                failed += 1
        browser.close()
    srv.shutdown()
    print("%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
