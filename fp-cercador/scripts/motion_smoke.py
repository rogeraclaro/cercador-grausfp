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
