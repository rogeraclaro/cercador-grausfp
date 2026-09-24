#!/usr/bin/env python3
"""Mobile layout verification harness for fp-cercador/frontend/index.html.

Headless-Chrome (Playwright sync API, channel=chrome) layout harness with
mocked /api/* endpoints. Installs nothing: it drives the system Google Chrome
and uses the playwright/PIL packages that are already present.

Usage:
    python3 mobile_check.py [--only group1,group2,...]

Groups: desktop, cards, fpo, topbar, toggle, touch, overflow
Prints MOBILE_CHECK_OK and exits 0 when every requested group passes.
"""
import argparse
import io
import json
import mimetypes
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Error as PlaywrightError
from PIL import Image, ImageChops

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = (REPO_ROOT / "fp-cercador" / "frontend").resolve()
DATA_FILE = REPO_ROOT / "fp-cercador" / "backend" / "data" / "ofertes.json"
BASE_REF = "9b3edf2"
INDEX_REL_PATH = "fp-cercador/frontend/index.html"
MOBILE_HOST = "grausfp.test"

FAILURES = []


def fail(msg):
    FAILURES.append(msg)


# ---------------------------------------------------------------------------
# Fixtures / cached bytes
# ---------------------------------------------------------------------------

_INDEX_CACHE = {}
_OFERTES_BYTES = None
_CENTRES_COUNT_BYTES = None


def get_index_bytes(ref):
    if ref == "work":
        return (FRONTEND_DIR / "index.html").read_bytes()
    if ref not in _INDEX_CACHE:
        result = subprocess.run(
            ["git", "show", f"{ref}:{INDEX_REL_PATH}"],
            cwd=REPO_ROOT, capture_output=True, check=True,
        )
        _INDEX_CACHE[ref] = result.stdout
    return _INDEX_CACHE[ref]


def ofertes_bytes():
    global _OFERTES_BYTES
    if _OFERTES_BYTES is None:
        _OFERTES_BYTES = DATA_FILE.read_bytes()
    return _OFERTES_BYTES


def centres_count_bytes():
    global _CENTRES_COUNT_BYTES
    if _CENTRES_COUNT_BYTES is None:
        data = json.loads(ofertes_bytes())
        mapping = {str(r["id"]): 3 for r in data}
        _CENTRES_COUNT_BYTES = json.dumps(mapping).encode("utf-8")
    return _CENTRES_COUNT_BYTES


def fpo_fixtures():
    return [
        {
            "codi": "FPO001",
            "titol": {"ca": "Especialitat normal", "es": "Especialidad normal"},
            "familia": {"codi": "FAM1", "desc": {"ca": "Família 1", "es": "Familia 1"}},
            "area": {"codi": "ARE1", "desc": {"ca": "Àrea 1", "es": "Área 1"}},
            "nivell": 2,
            "hores": 320,
            "nCursos": 3,
            "esCertProf": True,
            "comarques": [], "municipis": [], "estats": [], "modalitats": [],
        },
        {
            "codi": "FPO002",
            "titol": {"ca": "Especialitat sense dades", "es": "Especialidad sin datos"},
            "familia": None,
            "area": None,
            "nivell": None,
            "hores": 0,
            "nCursos": 1,
            "esCertProf": False,
            "comarques": [], "municipis": [], "estats": [], "modalitats": [],
        },
        {
            "codi": "FPO003",
            "titol": {
                "ca": "Especialitat amb un títol molt llarg per comprovar que la targeta no desborda en cap idioma",
                "es": "Especialidad con un título muy largo para comprobar que la tarjeta no desborda en ningún idioma",
            },
            "familia": {"codi": "FAM2", "desc": {"ca": "Família 2", "es": "Familia 2"}},
            "area": {"codi": "ARE2", "desc": {"ca": "Àrea 2", "es": "Área 2"}},
            "nivell": 3,
            "hores": 450,
            "nCursos": 5,
            "esCertProf": False,
            "comarques": [], "municipis": [], "estats": [], "modalitats": [],
        },
    ]


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _handle_api(route, path, auth):
    if path == "/api/ofertes":
        route.fulfill(status=200, content_type="application/json", body=ofertes_bytes())
        return
    if path == "/api/auth/me":
        if auth == "user":
            body = json.dumps({"email": "test@local.dev", "is_admin": False}).encode("utf-8")
            route.fulfill(status=200, content_type="application/json", body=body)
        else:
            route.fulfill(status=401, content_type="application/json", body=b'{"error":"unauthorized"}')
        return
    if path == "/api/centres/count":
        route.fulfill(status=200, content_type="application/json", body=centres_count_bytes())
        return
    if path == "/api/centres/nous":
        route.fulfill(status=200, content_type="application/json", body=b"{}")
        return
    if path == "/api/fpo/especialitats":
        payload = json.dumps({"especialitats": fpo_fixtures(), "warning": None}).encode("utf-8")
        route.fulfill(status=200, content_type="application/json", body=payload)
        return
    route.fulfill(status=200, content_type="application/json", body=b"[]")


def route_handler_factory(auth, ref, fonts):
    def handler(route):
        request = route.request
        parsed = urlparse(request.url)
        host = parsed.hostname
        path = parsed.path

        if host in ("fonts.googleapis.com", "fonts.gstatic.com"):
            if fonts:
                route.continue_()
            else:
                route.abort()
            return

        if host != MOBILE_HOST:
            route.abort()
            return

        if path.startswith("/api/"):
            _handle_api(route, path, auth)
            return

        if path in ("/", "/index.html"):
            body = get_index_bytes(ref)
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)
            return

        rel = path.lstrip("/")
        try:
            target = (FRONTEND_DIR / rel).resolve()
            target.relative_to(FRONTEND_DIR)
        except (ValueError, RuntimeError):
            route.fulfill(status=404, body=b"not found")
            return
        if not target.is_file():
            route.fulfill(status=404, body=b"not found")
            return
        ctype, _ = mimetypes.guess_type(str(target))
        route.fulfill(status=200, content_type=ctype or "application/octet-stream", body=target.read_bytes())

    return handler


# ---------------------------------------------------------------------------
# Page loader
# ---------------------------------------------------------------------------

def open_page(browser, width, lang, auth, touch=False, mode=None, ref="work", fonts=True, height=900):
    context = browser.new_context(viewport={"width": width, "height": height}, has_touch=touch)
    context.add_init_script(
        "try { localStorage.setItem('lang', %s); } catch (e) {}" % json.dumps(lang)
    )
    context.route("**/*", route_handler_factory(auth, ref, fonts))
    page = context.new_page()

    errors = []
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

    def on_console(msg):
        if "Alpine" in msg.text:
            errors.append(f"console: {msg.text}")

    page.on("console", on_console)

    url = f"http://{MOBILE_HOST}/index.html"
    if mode:
        url += f"?mode={mode}"
    page.goto(url, wait_until="domcontentloaded")

    page.wait_for_function(
        "() => { const el = document.querySelector('[x-data]'); "
        "if (!el || !window.Alpine) return false; "
        "const d = Alpine.$data(el); "
        "return !!d && d.state === 'ready' && !!document.querySelector('#auth-widget .auth-btn'); }",
        timeout=15000,
    )

    if mode == "fpo":
        page.wait_for_function(
            "() => { const el = document.querySelector('[x-data]'); const d = Alpine.$data(el); "
            "return !!d && d.fpoLoaded && Array.isArray(d.filteredFpoEspecs) && d.filteredFpoEspecs.length > 0; }",
            timeout=15000,
        )

    try:
        page.evaluate(
            "() => Promise.race(["
            "  (document.fonts ? document.fonts.ready : Promise.resolve()),"
            "  new Promise(resolve => setTimeout(resolve, 5000))"
            "])"
        )
    except PlaywrightError:
        pass

    return context, page, errors


def check_errors(errors, label):
    if errors:
        fail(f"[{label}] page/Alpine errors: {errors}")


def resolve_color(page, var_name):
    return page.evaluate(
        "(name) => { const el = document.createElement('span'); "
        "el.style.color = 'var(' + name + ')'; document.body.appendChild(el); "
        "const c = getComputedStyle(el).color; el.remove(); return c; }",
        var_name,
    )


# ---------------------------------------------------------------------------
# Group: cards
# ---------------------------------------------------------------------------

CARD_SCENARIOS = [(390, "ca"), (390, "es"), (320, "ca"), (768, "ca")]


def check_cards(browser):
    for width, lang in CARD_SCENARIOS:
        label = f"cards@{width}/{lang}"
        context, page, errors = open_page(browser, width, lang, auth="user")
        try:
            check_errors(errors, label)
            expected_niv_label = "Nivell" if lang == "ca" else "Nivel"
            dark_color = resolve_color(page, "--dark")
            warm2_color = resolve_color(page, "--warm2")

            result = page.evaluate(
                """
                () => {
                  const out = {};
                  const table = document.querySelector('#results-table');
                  const wrap = table.closest('.table-wrap');
                  out.wrapOverflow = wrap.scrollWidth - wrap.clientWidth;

                  const thead = table.querySelector('thead');
                  const theadCs = getComputedStyle(thead);
                  out.theadPosition = theadCs.position;
                  out.theadHeight = thead.getBoundingClientRect().height;

                  const tr = table.querySelector('tbody tr[data-row-id]');
                  const trCs = getComputedStyle(tr);
                  out.trDisplay = trCs.display;
                  out.trPaddingTop = parseFloat(trCs.paddingTop);
                  out.trPaddingLeft = parseFloat(trCs.paddingLeft);
                  out.trBorderBottomWidth = parseFloat(trCs.borderBottomWidth);

                  const nom = tr.querySelector('td.col-nom');
                  out.nomWidth = nom.getBoundingClientRect().width;
                  out.trClientWidth = tr.clientWidth;

                  const grau = tr.querySelector('td.col-grau');
                  const grauCs = getComputedStyle(grau);
                  out.grauBorderTopWidth = parseFloat(grauCs.borderTopWidth);
                  out.grauBorderTopStyle = grauCs.borderTopStyle;
                  out.grauBorderTopColor = grauCs.borderTopColor;
                  const grauRect = grau.getBoundingClientRect();
                  out.grauLeft = grauRect.left;
                  out.grauTop = grauRect.top;
                  const nomRect = nom.getBoundingClientRect();
                  out.nomBottom = nomRect.bottom;

                  const metaTds = [...tr.querySelectorAll('td')].filter(td => !td.classList.contains('col-nom'));
                  out.metaLefts = metaTds
                    .filter(td => getComputedStyle(td).display !== 'none')
                    .map(td => td.getBoundingClientRect().left);

                  const niv = tr.querySelector('td.col-niv');
                  out.nivDataLabel = niv.getAttribute('data-label');
                  out.nivBeforeContent = getComputedStyle(niv, '::before').content;

                  const codi = tr.querySelector('td.col-codi');
                  out.codiFontFamily = getComputedStyle(codi).fontFamily;

                  return out;
                }
                """
            )

            if result["wrapOverflow"] > 1:
                fail(f"[{label}] table-wrap overflows horizontally by {result['wrapOverflow']}px")
            if result["theadPosition"] != "absolute":
                fail(f"[{label}] thead position is {result['theadPosition']}, expected absolute")
            if result["theadHeight"] > 1:
                fail(f"[{label}] thead height is {result['theadHeight']}, expected <=1")
            if result["trDisplay"] != "flex":
                fail(f"[{label}] tr display is {result['trDisplay']}, expected flex")
            if abs(result["trPaddingTop"] - 14) > 1:
                fail(f"[{label}] tr padding-top is {result['trPaddingTop']}, expected ~14px")
            if abs(result["trPaddingLeft"] - 16) > 1:
                fail(f"[{label}] tr padding-left is {result['trPaddingLeft']}, expected ~16px")
            if abs(result["trBorderBottomWidth"] - 1) > 1:
                fail(f"[{label}] tr border-bottom-width is {result['trBorderBottomWidth']}, expected ~1px")
            if result["nomWidth"] < result["trClientWidth"] - 32 - 1:
                fail(f"[{label}] col-nom width {result['nomWidth']} < row width - 32")
            if result["grauBorderTopWidth"] < 0.5 or result["grauBorderTopStyle"] != "solid":
                fail(f"[{label}] col-grau border-top is not 1px solid "
                     f"({result['grauBorderTopWidth']}px {result['grauBorderTopStyle']})")
            if result["grauBorderTopColor"] != dark_color:
                fail(f"[{label}] col-grau border-top-color {result['grauBorderTopColor']} != --dark {dark_color}")
            if result["metaLefts"] and result["grauLeft"] > min(result["metaLefts"]) + 0.5:
                fail(f"[{label}] col-grau is not the leftmost visible meta cell")
            if result["grauTop"] < result["nomBottom"] - 1:
                fail(f"[{label}] col-grau top is above col-nom bottom")
            if result["nivDataLabel"] != expected_niv_label:
                fail(f"[{label}] col-niv data-label is {result['nivDataLabel']!r}, expected {expected_niv_label!r}")
            if expected_niv_label not in result["nivBeforeContent"]:
                fail(f"[{label}] col-niv ::before content {result['nivBeforeContent']!r} missing {expected_niv_label!r}")
            if "Geist Mono" not in result["codiFontFamily"]:
                fail(f"[{label}] col-codi font-family {result['codiFontFamily']!r} missing Geist Mono")

            focus_result = page.evaluate(
                """
                () => {
                  const tr = document.querySelector('#results-table tbody tr.row-link');
                  if (!tr) return null;
                  tr.focus();
                  const cs = getComputedStyle(tr);
                  return {
                    matches: tr.matches(':focus-visible'),
                    outlineStyle: cs.outlineStyle,
                    outlineWidth: cs.outlineWidth,
                    backgroundColor: cs.backgroundColor,
                  };
                }
                """
            )
            if focus_result is None:
                fail(f"[{label}] no tr.row-link found to focus")
            else:
                if not focus_result["matches"]:
                    fail(f"[{label}] focused row does not match :focus-visible")
                if focus_result["outlineStyle"] != "solid":
                    fail(f"[{label}] focus outline-style is {focus_result['outlineStyle']}, expected solid")
                if focus_result["outlineWidth"] != "2px":
                    fail(f"[{label}] focus outline-width is {focus_result['outlineWidth']}, expected 2px")
                if focus_result["backgroundColor"] != warm2_color:
                    fail(f"[{label}] focus background {focus_result['backgroundColor']} != --warm2 {warm2_color}")

            page.evaluate(
                "() => { const el = document.querySelector('[x-data]'); const d = Alpine.$data(el); "
                "d.filterGrado = 'E'; d.currentPage = 1; }"
            )
            page.wait_for_function(
                "() => { const el = document.querySelector('[x-data]'); const d = Alpine.$data(el); "
                "return d.pagedRecords.length > 0 && d.pagedRecords.every(r => r.grado === 'E'); }",
                timeout=5000,
            )
            empty_result = page.evaluate(
                """
                () => {
                  const cells = [...document.querySelectorAll('#results-table tbody tr[data-row-id] td')]
                    .filter(td => td.textContent.trim() === '—');
                  return {
                    count: cells.length,
                    allHidden: cells.every(td => getComputedStyle(td).display === 'none'),
                  };
                }
                """
            )
            if empty_result["count"] == 0:
                fail(f"[{label}] no '—' cells found for grade E rows")
            elif not empty_result["allHidden"]:
                fail(f"[{label}] some '—' cells are not hidden (display != none)")
        finally:
            context.close()


# ---------------------------------------------------------------------------
# Group: fpo
# ---------------------------------------------------------------------------

def check_fpo(browser):
    label = "fpo@390/ca"
    context, page, errors = open_page(browser, 390, "ca", auth="user", mode="fpo")
    try:
        check_errors(errors, label)
        result = page.evaluate(
            """
            () => {
              const table = document.querySelector('table.results-table--fpo');
              if (!table) return { exists: false };
              const wrap = table.closest('.table-wrap');
              const thead = table.querySelector('thead');
              const tr = table.querySelector('tbody tr.row-link');
              const trCs = tr ? getComputedStyle(tr) : null;
              const theadCs = getComputedStyle(thead);

              const rows = [...table.querySelectorAll('tbody tr.row-link')];
              const findRowByCodi = (codi) => rows.find(
                r => (r.querySelector('td.col-codi') || {}).textContent === codi
              );

              const rowNormal = findRowByCodi('FPO001');
              const rowEmpty = findRowByCodi('FPO002');

              const out = {
                exists: true,
                wrapOverflow: wrap.scrollWidth - wrap.clientWidth,
                theadPosition: theadCs.position,
                theadHeight: thead.getBoundingClientRect().height,
                trDisplay: trCs ? trCs.display : null,
              };

              if (rowNormal) {
                const hores = rowNormal.querySelector('td.col-hores');
                const ncursos = rowNormal.querySelector('td.col-ncursos');
                const niv = rowNormal.querySelector('td.col-niv');
                const codi = rowNormal.querySelector('td.col-codi');
                out.horesLabel = hores ? hores.getAttribute('data-label') : null;
                out.ncursosLabel = ncursos ? ncursos.getAttribute('data-label') : null;
                out.nivLabel = niv ? niv.getAttribute('data-label') : null;
                out.codiBeforeContent = codi ? getComputedStyle(codi, '::before').content : null;
              }
              if (rowEmpty) {
                const hores = rowEmpty.querySelector('td.col-hores');
                const niv = rowEmpty.querySelector('td.col-niv');
                out.emptyHoresDisplay = hores ? getComputedStyle(hores).display : null;
                out.emptyNivDisplay = niv ? getComputedStyle(niv).display : null;
              }
              return out;
            }
            """
        )
        if not result["exists"]:
            fail(f"[{label}] table.results-table--fpo not found")
            return
        if result["wrapOverflow"] > 1:
            fail(f"[{label}] FPO table-wrap overflows by {result['wrapOverflow']}px")
        if result["theadPosition"] != "absolute":
            fail(f"[{label}] FPO thead position is {result['theadPosition']}, expected absolute")
        if result["theadHeight"] > 1:
            fail(f"[{label}] FPO thead height is {result['theadHeight']}, expected <=1")
        if result["trDisplay"] != "flex":
            fail(f"[{label}] FPO row display is {result['trDisplay']}, expected flex")
        if result.get("horesLabel") != "Hores":
            fail(f"[{label}] col-hores data-label is {result.get('horesLabel')!r}, expected 'Hores'")
        if result.get("ncursosLabel") != "Cursos actius":
            fail(f"[{label}] col-ncursos data-label is {result.get('ncursosLabel')!r}, expected 'Cursos actius'")
        if result.get("nivLabel") != "Nivell":
            fail(f"[{label}] col-niv data-label is {result.get('nivLabel')!r}, expected 'Nivell'")
        if result.get("codiBeforeContent") not in ("none", "normal"):
            fail(f"[{label}] col-codi ::before content is {result.get('codiBeforeContent')!r}, expected none")
        if result.get("emptyHoresDisplay") != "none":
            fail(f"[{label}] fixture2 col-hores display is {result.get('emptyHoresDisplay')}, expected none")
        if result.get("emptyNivDisplay") != "none":
            fail(f"[{label}] fixture2 col-niv display is {result.get('emptyNivDisplay')}, expected none")
    finally:
        context.close()


# ---------------------------------------------------------------------------
# Group: topbar
# ---------------------------------------------------------------------------

def check_topbar(browser):
    for width in (320, 390, 768):
        for lang in ("ca", "es"):
            for auth in ("guest", "user"):
                label = f"topbar@{width}/{lang}/{auth}"
                context, page, errors = open_page(browser, width, lang, auth=auth)
                try:
                    check_errors(errors, label)
                    result = page.evaluate(
                        """
                        () => {
                          const inner = document.querySelector('.topbar-inner');
                          const innerRect = inner.getBoundingClientRect();
                          const authBtns = [...document.querySelectorAll('.auth-btn')];
                          const langBtns = [...document.querySelectorAll('.lang-btn')];
                          const greeting = document.querySelector('.auth-greeting');
                          const langSel = document.querySelector('.lang-selector');
                          return {
                            overflow: inner.scrollWidth - inner.clientWidth,
                            innerLeft: innerRect.left,
                            innerRight: innerRect.right,
                            authBtns: authBtns.map(b => {
                              const r = b.getBoundingClientRect();
                              return { left: r.left, right: r.right, height: r.height,
                                       scrollWidth: b.scrollWidth, clientWidth: b.clientWidth };
                            }),
                            langBtns: langBtns.map(b => {
                              const r = b.getBoundingClientRect();
                              return { left: r.left, right: r.right };
                            }),
                            greetingDisplay: greeting ? getComputedStyle(greeting).display : null,
                            langSelRight: langSel.getBoundingClientRect().right,
                          };
                        }
                        """
                    )
                    tol = 0.5
                    if result["overflow"] > 1:
                        fail(f"[{label}] .topbar-inner overflows by {result['overflow']}px")
                    for b in result["authBtns"]:
                        if b["left"] < result["innerLeft"] - tol or b["right"] > result["innerRight"] + tol:
                            fail(f"[{label}] .auth-btn out of .topbar-inner bounds")
                        if b["height"] >= 36:
                            fail(f"[{label}] .auth-btn height {b['height']} >= 36")
                        if b["scrollWidth"] > b["clientWidth"] + 1:
                            fail(f"[{label}] .auth-btn text wraps/spills (scrollWidth>{b['clientWidth']})")
                    for b in result["langBtns"]:
                        if b["left"] < result["innerLeft"] - tol or b["right"] > result["innerRight"] + tol:
                            fail(f"[{label}] .lang-btn out of .topbar-inner bounds")
                    if auth == "user" and result["greetingDisplay"] != "none":
                        fail(f"[{label}] .auth-greeting display is {result['greetingDisplay']}, expected none")
                    if abs(result["langSelRight"] - result["innerRight"]) > 1:
                        fail(f"[{label}] .lang-selector right edge {result['langSelRight']} "
                             f"!= .topbar-inner right {result['innerRight']}")
                finally:
                    context.close()


# ---------------------------------------------------------------------------
# Group: toggle
# ---------------------------------------------------------------------------

def check_toggle(browser):
    for width in (320, 390):
        for lang in ("ca", "es"):
            label = f"toggle@{width}/{lang}"
            context, page, errors = open_page(browser, width, lang, auth="user")
            try:
                check_errors(errors, label)
                result = page.evaluate(
                    """
                    () => {
                      const toggle = document.querySelector('.mode-toggle');
                      const cs = getComputedStyle(toggle);
                      const buttons = [...toggle.querySelectorAll('button')];
                      return {
                        flexDirection: cs.flexDirection,
                        toggleWidth: toggle.clientWidth,
                        buttons: buttons.map(b => {
                          const r = b.getBoundingClientRect();
                          const bcs = getComputedStyle(b);
                          return { width: r.width, height: r.height, minHeight: bcs.minHeight,
                                   scrollWidth: b.scrollWidth, clientWidth: b.clientWidth };
                        }),
                      };
                    }
                    """
                )
                if result["flexDirection"] != "column":
                    fail(f"[{label}] .mode-toggle flex-direction is {result['flexDirection']}, expected column")
                for i, b in enumerate(result["buttons"]):
                    if b["width"] < result["toggleWidth"] - 1:
                        fail(f"[{label}] button[{i}] width {b['width']} < toggle width - 1")
                    if b["height"] > 46:
                        fail(f"[{label}] button[{i}] height {b['height']} > 46 (wraps to 2 lines?)")
                    if b["minHeight"] != "44px":
                        fail(f"[{label}] button[{i}] min-height is {b['minHeight']}, expected 44px")
                    if b["scrollWidth"] > b["clientWidth"] + 1:
                        fail(f"[{label}] button[{i}] label overflows (scrollWidth>{b['clientWidth']})")
            finally:
                context.close()


# ---------------------------------------------------------------------------
# Group: touch
# ---------------------------------------------------------------------------

def check_touch(browser):
    label = "touch@390/ca/user"
    context, page, errors = open_page(browser, 390, "ca", auth="user", touch=True)
    try:
        check_errors(errors, label)
        page.evaluate(
            "() => { const el = document.querySelector('[x-data]'); const d = Alpine.$data(el); "
            "d.filterGrado = 'B'; d.currentPage = 1; }"
        )
        page.wait_for_function(
            "() => { const el = document.querySelector('[x-data]'); const d = Alpine.$data(el); "
            "return d.pagedRecords.length > 0 && d.pagedRecords.every(r => r.grado === 'B'); }",
            timeout=5000,
        )

        fav_result = page.evaluate(
            """
            () => {
              const btn = document.querySelector('#results-table .btn-fav');
              if (!btn) return null;
              const afterCs = getComputedStyle(btn, '::after');
              const rect = btn.getBoundingClientRect();
              const svg = btn.querySelector('svg');
              const svgRect = svg.getBoundingClientRect();
              return {
                afterWidth: afterCs.width, afterHeight: afterCs.height,
                btnHeight: rect.height,
                svgWidth: svgRect.width, svgHeight: svgRect.height,
              };
            }
            """
        )
        if fav_result is None:
            fail(f"[{label}] no .btn-fav found")
        else:
            if fav_result["afterWidth"] != "44px" or fav_result["afterHeight"] != "44px":
                fail(f"[{label}] .btn-fav ::after size is "
                     f"{fav_result['afterWidth']}x{fav_result['afterHeight']}, expected 44x44")
            if fav_result["btnHeight"] > 24:
                fail(f"[{label}] .btn-fav rect height {fav_result['btnHeight']} > 24 (visual size jump)")
            if abs(fav_result["svgWidth"] - 16) > 1 or abs(fav_result["svgHeight"] - 16) > 1:
                fail(f"[{label}] .btn-fav svg size changed to "
                     f"{fav_result['svgWidth']}x{fav_result['svgHeight']}")

        badge_result = page.evaluate(
            """
            () => {
              const out = [];
              const centres = document.querySelector('.badge-centres');
              if (centres) {
                const cs = getComputedStyle(centres, '::after');
                const rect = centres.getBoundingClientRect();
                out.push({ name: 'badge-centres', afterHeight: cs.height, rectHeight: rect.height });
              }
              const itin = document.querySelector('.badge-itinerari-b[role="button"]');
              if (itin) {
                const cs = getComputedStyle(itin, '::after');
                const rect = itin.getBoundingClientRect();
                out.push({ name: 'badge-itinerari-b', afterHeight: cs.height, rectHeight: rect.height });
              }
              return out;
            }
            """
        )
        if not badge_result:
            fail(f"[{label}] no touch badges (.badge-centres / .badge-itinerari-b[role=button]) found to verify")
        for b in badge_result:
            if b["afterHeight"] != "44px":
                fail(f"[{label}] {b['name']} ::after height is {b['afterHeight']}, expected 44px")
            if b["rectHeight"] > 24:
                fail(f"[{label}] {b['name']} rect height {b['rectHeight']} > 24 (visual size jump)")

        min_targets = page.evaluate(
            """
            () => {
              const selectors = ['.lang-btn', '.auth-btn', 'select', '.save-alert-btn', '.clear-btn',
                                  '.mode-toggle button', 'footer a', '.checkbox-label'];
              const out = [];
              for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                  if (getComputedStyle(el).display === 'none') continue;
                  const rect = el.getBoundingClientRect();
                  if (rect.width === 0 && rect.height === 0) continue;
                  out.push({ sel, height: rect.height });
                }
              }
              return out;
            }
            """
        )
        if not min_targets:
            fail(f"[{label}] no touch targets found for min-height check")
        for t in min_targets:
            if t["height"] < 43.5:
                fail(f"[{label}] {t['sel']} height {t['height']} < 43.5px")
    finally:
        context.close()


# ---------------------------------------------------------------------------
# Group: overflow
# ---------------------------------------------------------------------------

def rule_present_in_worktree():
    content = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return bool(re.search(r"\[x-data\]\s*\{", content))


def check_overflow(browser):
    scenarios = [(w, l, a, None) for w in (320, 390, 768) for l in ("ca", "es") for a in ("guest", "user")]
    scenarios += [(320, "ca", "user", "fpo"), (390, "ca", "user", "fpo")]

    all_offenders = {}
    overflow_found = False
    for (width, lang, auth, mode) in scenarios:
        label = f"overflow@{width}/{lang}/{auth}" + (f"/{mode}" if mode else "")
        context, page, errors = open_page(browser, width, lang, auth=auth, mode=mode)
        try:
            check_errors(errors, label)
            page.evaluate(
                """
                () => {
                  const style = document.createElement('style');
                  style.id = '__overflow_gate__';
                  style.textContent = 'html, body, [x-data] '
                    + '{ overflow-x: visible !important; max-width: none !important; }';
                  document.head.appendChild(style);
                }
                """
            )
            result = page.evaluate(
                """
                () => {
                  const docWidth = document.documentElement.scrollWidth;
                  const winWidth = window.innerWidth;
                  const offenders = [];
                  if (docWidth > winWidth + 0.5) {
                    const all = document.querySelectorAll('body *');
                    for (const el of all) {
                      if (el.closest('.grau-tabs') || el.closest('thead') ||
                          el.classList.contains('sr-only') || el.closest('.sr-only')) continue;
                      const cs = getComputedStyle(el);
                      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
                      const rect = el.getBoundingClientRect();
                      if (rect.right > winWidth + 0.5) {
                        offenders.push({ tag: el.tagName, cls: el.className, right: rect.right });
                        if (offenders.length >= 10) break;
                      }
                    }
                  }
                  return { docWidth, winWidth, offenders };
                }
                """
            )
            if result["docWidth"] > result["winWidth"] + 0.5:
                overflow_found = True
                all_offenders[label] = result["offenders"]
        finally:
            context.close()

    rule_present = rule_present_in_worktree()

    if not overflow_found and rule_present:
        fail("overflow gate passes — remove the html/body/[x-data] rule")
    elif not overflow_found and not rule_present:
        print("OVERFLOW_GATE=PASS")
    elif overflow_found and not rule_present:
        fail(f"overflow gate fails with the rule absent: offenders={all_offenders}")
    else:
        print(f"OVERFLOW_GATE=FAIL offenders={all_offenders}")


# ---------------------------------------------------------------------------
# Group: desktop parity
# ---------------------------------------------------------------------------

def render_desktop(browser, width, mode, ref):
    # Chromium's full_page=True screenshot mode is flaky for this page: it
    # intermittently stitches a frame where the grau-tabs/filter-bar rows
    # haven't repainted after the animations-disabling style tag triggers a
    # layout pass, even though the DOM/computed styles are already correct
    # (verified independently). Explicitly resizing the viewport to the
    # settled content height, then taking a plain (non full-page) screenshot,
    # is pixel-deterministic across repeated renders — see task notes.
    context, page, errors = open_page(
        browser, width, "ca", auth="user", mode=mode, ref=ref, fonts=False, height=1000
    )
    try:
        if errors:
            fail(f"[desktop render ref={ref} w={width} mode={mode}] page/Alpine errors: {errors}")
        page.add_style_tag(
            content="*, *::before, *::after { transition: none !important; "
                    "animation: none !important; caret-color: transparent !important; }"
        )
        # Wait for layout height to stop changing (Alpine can still be settling
        # reactive x-for/x-show effects a frame or two after 'ready') before
        # locking the viewport to the content height.
        page.evaluate(
            """
            () => new Promise(resolve => {
              let last = -1, stableFrames = 0;
              function tick() {
                const h = document.documentElement.scrollHeight;
                if (h === last) {
                  stableFrames++;
                } else {
                  stableFrames = 0;
                  last = h;
                }
                if (stableFrames >= 6) { resolve(); return; }
                requestAnimationFrame(tick);
              }
              requestAnimationFrame(tick);
            })
            """
        )
        content_height = page.evaluate("() => document.documentElement.scrollHeight")
        page.set_viewport_size({"width": width, "height": content_height})
        page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        return page.screenshot(full_page=False)
    finally:
        context.close()


def check_desktop(browser):
    scenarios = [(1280, None, "name"), (800, None, "name"), (1280, "fpo", "fpo")]
    for width, mode, tag in scenarios:
        label = f"desktop@{width}/{tag}"
        base_png = render_desktop(browser, width, mode, ref=BASE_REF)
        work_png = render_desktop(browser, width, mode, ref="work")

        base_img = Image.open(io.BytesIO(base_png)).convert("RGB")
        work_img = Image.open(io.BytesIO(work_png)).convert("RGB")

        if base_img.size != work_img.size:
            fail(f"[{label}] screenshot size mismatch base={base_img.size} work={work_img.size}")
            diff_dir = tempfile.mkdtemp(prefix="mobile_check_diff_")
            base_img.save(Path(diff_dir) / "base.png")
            work_img.save(Path(diff_dir) / "work.png")
            print(f"[{label}] saved mismatched screenshots to {diff_dir}")
            continue

        diff = ImageChops.difference(base_img, work_img)
        bbox = diff.getbbox()
        if bbox is not None:
            fail(f"[{label}] desktop screenshot differs from base at bbox={bbox}")
            diff_dir = tempfile.mkdtemp(prefix="mobile_check_diff_")
            base_img.save(Path(diff_dir) / "base.png")
            work_img.save(Path(diff_dir) / "work.png")
            print(f"[{label}] saved diffing screenshots to {diff_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

GROUPS = {
    "desktop": check_desktop,
    "cards": check_cards,
    "fpo": check_fpo,
    "topbar": check_topbar,
    "toggle": check_toggle,
    "touch": check_touch,
    "overflow": check_overflow,
}

# overflow runs last: its injected style mutates layout for the rest of the page life.
DEFAULT_ORDER = ["cards", "fpo", "topbar", "toggle", "touch", "desktop", "overflow"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default=None, help="comma-separated list of group names")
    args = parser.parse_args()

    if args.only:
        requested = [g.strip() for g in args.only.split(",") if g.strip()]
        for g in requested:
            if g not in GROUPS:
                print(f"Unknown group: {g}", file=sys.stderr)
                sys.exit(2)
        order = [g for g in DEFAULT_ORDER if g in requested]
    else:
        order = DEFAULT_ORDER

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        try:
            for group in order:
                GROUPS[group](browser)
        finally:
            browser.close()

    if FAILURES:
        print("MOBILE CHECK FAILURES:")
        for f in FAILURES:
            print(f" - {f}")
        sys.exit(1)

    print("MOBILE_CHECK_OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
