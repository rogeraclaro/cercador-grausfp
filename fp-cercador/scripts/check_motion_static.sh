#!/usr/bin/env bash
# Comprovacions estructurals de la fase 07 (microanimacions GSAP): fitxer vendoritzat, ordre de càrrega,
# pàgines permeses, sense CDN/plugins/estat inicial ocult, excepció a CLAUDE.md.
# Ús: bash fp-cercador/scripts/check_motion_static.sh   (des de qualsevol directori)
# Sortida: "OK nom" / "FAIL nom: detall" i "static: N ok, M failed". Codi 0 si tot OK, 1 si algun falla, 2 si falta una eina.
set -u

# Pàgines que carreguen GSAP (07-02 i 07-03 hi afegeixen la seva)
LOADED_PAGES="index observatori"

GSAP_SHA="c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280"
ALLOWED_PAGES="index.html observatori.html itinerari.html"

for tool in rg shasum; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERROR $tool missing"; exit 2; }
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FE="$ROOT/fp-cercador/frontend"
VENDOR="$FE/vendor/gsap-3.14.2.min.js"
MOTION="$FE/motion.js"

OKS=0
FAILS=0
ok()   { echo "OK $1"; OKS=$((OKS + 1)); }
fail() { echo "FAIL $1: $2"; FAILS=$((FAILS + 1)); }

# vendor-hash
if [ -f "$VENDOR" ] && [ "$(shasum -a 256 "$VENDOR" | cut -d' ' -f1)" = "$GSAP_SHA" ]; then
  ok vendor-hash
else
  fail vendor-hash "sha256 diferent o fitxer absent ($VENDOR)"
fi

# vendor-header
if [ -f "$VENDOR" ] && head -8 "$VENDOR" | rg -q '@license Copyright 2025, GreenSock' \
  && head -8 "$VENDOR" | rg -q 'https://gsap.com/standard-license'; then
  ok vendor-header
else
  fail vendor-header "falta la capçalera de llicència a les 8 primeres línies"
fi

# single-vendor-file
COUNT=$(find "$FE" -type f -iname '*gsap*' | wc -l | tr -d ' ')
if [ "$COUNT" = "1" ]; then ok single-vendor-file; else fail single-vendor-file "$COUNT fitxers amb gsap al nom"; fi

# allowed-pages-only (D-03)
BAD=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  case " $ALLOWED_PAGES " in *" $(basename "$f") "*) ;; *) BAD="$BAD $(basename "$f")" ;; esac
done < <(rg -l 'vendor/gsap-' "$FE" --glob '*.html' 2>/dev/null)
if [ -z "$BAD" ]; then ok allowed-pages-only; else fail allowed-pages-only "pàgines no permeses:$BAD"; fi

# load-order:<page>
for page in $LOADED_PAGES; do
  f="$FE/$page.html"
  g=$(rg -n 'vendor/gsap-3\.14\.2\.min\.js' "$f" --glob '*.html' 2>/dev/null | rg -v '<!--|sha256' | head -1 | cut -d: -f1)
  m=$(rg -n 'src="motion\.js\?v=' "$f" 2>/dev/null | head -1 | cut -d: -f1)
  a=$(rg -n 'src="vendor/alpinejs-' "$f" 2>/dev/null | head -1 | cut -d: -f1)
  if [ -z "$g" ] || [ -z "$m" ]; then
    fail "load-order:$page" "falta l'etiqueta de gsap o de motion.js"
  elif [ "$g" -ge "$m" ]; then
    fail "load-order:$page" "gsap (línia $g) no precedeix motion.js (línia $m)"
  elif [ -n "$a" ] && [ "$m" -ge "$a" ]; then
    fail "load-order:$page" "motion.js (línia $m) no precedeix Alpine (línia $a)"
  elif [ -z "$a" ]; then
    # Pàgina sense Alpine: etiquetes planes (sense defer) abans de l'script inline que crida load()
    api=$(rg -n 'const API_BASE' "$f" 2>/dev/null | head -1 | cut -d: -f1)
    if awk -v a="$g" -v b="$m" 'NR==a || NR==b' "$f" | rg -q defer; then
      fail "load-order:$page" "gsap o motion.js porten defer en una pàgina sense Alpine"
    elif [ -z "$api" ] || [ "$m" -ge "$api" ]; then
      fail "load-order:$page" "motion.js (línia $m) no precedeix l'script inline (const API_BASE, línia ${api:-?})"
    else
      ok "load-order:$page"
    fi
  else
    ok "load-order:$page"
  fi
done

# no-remote-gsap
if rg -q '<script[^>]*src="https?://[^"]*gsap' "$FE" --glob '*.html' 2>/dev/null; then
  fail no-remote-gsap "hi ha un <script> remot que carrega gsap"
else
  ok no-remote-gsap
fi

# no-plugins (D-02: només el core)
# (es cerca des de $FE perquè el glob !vendor/** sigui relatiu a frontend/, també si la ruta conté espais)
if (cd "$FE" && rg -q 'ScrollTrigger|DrawSVG|SplitText|registerPlugin' . --glob '!vendor/**' 2>/dev/null); then
  fail no-plugins "referència a un plugin de GSAP fora de vendor/"
else
  ok no-plugins
fi

# no-hidden-start-state (D-05)
HIDDEN=$(rg -l 'opacity:\s*0\s*[;}"]' "$FE/index.html" "$FE/observatori.html" "$FE/itinerari.html" "$MOTION" 2>/dev/null | tr '\n' ' ')
if [ -z "$HIDDEN" ]; then ok no-hidden-start-state; else fail no-hidden-start-state "opacity:0 a: $HIDDEN"; fi

# motion-guard
if rg -q 'gsap\.matchMedia\(\)' "$MOTION" && rg -q 'prefers-reduced-motion: no-preference' "$MOTION" \
  && ! rg -q 'gsap\.context\(\s*\)' "$MOTION"; then
  ok motion-guard
else
  fail motion-guard "motion.js sense matchMedia/no-preference, o amb gsap.context() buit"
fi

# claude-md-exception (D-01)
if python3 - "$ROOT/CLAUDE.md" <<'EOF'
import sys
line = next((l for l in open(sys.argv[1], encoding="utf-8") if l.startswith("- **Tech Stack**")), "")
end = line.find("No afegir-ne cap altre.")
sys.exit(0 if 0 <= line.find("GSAP") < end else 1)
EOF
then ok claude-md-exception; else fail claude-md-exception "GSAP no apareix abans de «No afegir-ne cap altre.» a Tech Stack"; fi

# i18n-tick
if rg -q "'modal\.alert\.ok': '✓" "$FE/i18n.js"; then
  fail i18n-tick "un valor modal.alert.ok comença amb ✓"
elif ! rg -q 'class="ok-tick" aria-hidden="true"' "$FE/index.html"; then
  fail i18n-tick "index.html no conté el span .ok-tick amb aria-hidden"
else
  ok i18n-tick
fi

# d15-guards (regressió per a 07-03)
if rg -q '@media \(prefers-reduced-motion: no-preference\)' "$FE/itinerari.html" \
  && rg -q 'function reducedMotion\(\)' "$FE/itinerari.html"; then
  ok d15-guards
else
  fail d15-guards "itinerari.html ha perdut la guarda de reduced motion"
fi

# runtime-deps
if rg -qi 'playwright' "$ROOT/fp-cercador/backend/requirements.txt" 2>/dev/null; then
  fail runtime-deps "playwright a backend/requirements.txt"
else
  ok runtime-deps
fi

echo "static: $OKS ok, $FAILS failed"
[ "$FAILS" -eq 0 ]
