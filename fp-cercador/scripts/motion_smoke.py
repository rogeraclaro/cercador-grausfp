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
window.__startSampler = function (key, selector, ms, limit) {
  window.__samples[key] = [];
  var t0 = performance.now();
  (function tick() {
    var els = Array.prototype.slice.call(document.querySelectorAll(selector), 0, limit);
    window.__samples[key].push({ t: performance.now(),
      styles: els.map(function (e) { return e.getAttribute('style') || ''; }) });
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
