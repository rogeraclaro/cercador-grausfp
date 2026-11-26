#!/usr/bin/env python3
"""
sepe_descarrega_programes.py — Descàrrega dels programes formatius i les ocupacions
de totes les especialitats del catàleg del SEPE (Pla 100).

S'executa A L'ORDINADOR DEL PROPIETARI, mai al VPS ni durant el refresc del diumenge:
si el SEPE bloqueja una IP, que no sigui la de producció. El resultat es copia al
servidor amb scp (el backend el rellegeix per mtime: no cal reiniciar).

ORDRES (des de fp-cercador/, la carpeta d'aquest repositori que té backend/ i scripts/)

  Descàrrega completa (~7.550 especialitats; ~23 h segons la prova de 50 del 2026-11-26):
    caffeinate -i python3 scripts/sepe_descarrega_programes.py --des-de 2026-11-27

    `caffeinate -i` (macOS) evita que l'ordinador s'adormi mentre dura. --des-de és el
    dia que comença la passada: es tornen a baixar totes les especialitats baixades
    abans d'aquell dia. Posa-hi la data del dia que la llancis.

  Reprendre-la si s'atura (aturada automàtica, Ctrl+C, apagada…): la MATEIXA ordre, amb
    la MATEIXA data --des-de. Salta les que ja s'han baixat aquell dia o després.

  Ús habitual (només especialitats noves o que han canviat de versió):
    caffeinate -i python3 scripts/sepe_descarrega_programes.py --nomes-canvis

  Copiar el resultat al VPS (sense reinici):
    scp backend/data/sepe_programes.json contabo:/home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/
    ssh contabo chown masellas-grausfp: /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/sepe_programes.json

  Proves: --codis SSCE22,IFCD0025 o --limit 50, i --sortida/--informe a fitxers de prova.
  Només refer l'informe a partir d'un fitxer ja baixat: --nomes-informe.

Per especialitat: una sessió nova (GET flows/main), POST del PDF del programa i POST del
modal d'ocupacions; pausa aleatòria de 5–10 s (--pausa) entre especialitats.
Desa cada 25 especialitats (escriptura atòmica). S'atura sol, sense reintentar, amb un
HTTP 403 o 429 o amb 5 errors seguits; el que ja s'ha baixat queda desat.

Sortida (backend/data/sepe_programes.json):
  {codi: {versio, baixat, programa: {...} | null, ocupacions: [{codi, nom}], sense_pdf}}
programa: vegeu backend/sepe_programa.parse_programa. Es desa el contingut extret, no els PDF.
Codis de sortida: 0 bé, 2 aturada per errors seguits, 3 aturada per 403/429, 130 Ctrl+C.
"""
import argparse
import io
import json
import logging
import os
import random
import sys
import tempfile
import time
from datetime import date, datetime, timezone

import pdfplumber
import requests

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'backend'))
import sepe_programa  # noqa: E402
from scrapers import sepe_scraper  # noqa: E402

logger = logging.getLogger('sepe_programes')

ESPECS_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'sepe_especs.json')
OUT_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'sepe_programes.json')
INFORME_DIR = os.path.join(_REPO_ROOT, 'plans', 'outputs')

DESA_CADA = 25
MAX_ERRORS_SEGUITS = 5
ATURA_HTTP = (403, 429)
PITJORS = 30
ORDRE_COMPLETA = 'caffeinate -i python3 scripts/sepe_descarrega_programes.py --des-de {des_de}'

EXIT_OK, EXIT_ERRORS, EXIT_BLOQUEIG, EXIT_CTRL_C = 0, 2, 3, 130


# ---------------------------------------------------------------------------
# Fitxers
# ---------------------------------------------------------------------------

def carrega(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f'{path} no és un objecte JSON: no es toca')
    return data


def desa(path: str, data: dict) -> None:
    """Escriptura atòmica: un tall a mig desar mai deixa el fitxer a mitges."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def pdf_to_text(content: bytes) -> str:
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return '\n'.join((page.extract_text() or '') for page in pdf.pages)


# ---------------------------------------------------------------------------
# Selecció
# ---------------------------------------------------------------------------

def grup(espec: dict) -> str:
    """Plantilla esperada segons el catàleg: modern (≥2021), po, antic (<2015) o altres."""
    if espec.get('sufix') == 'PO':
        return 'po'
    any_inici = int((espec.get('vigenciaInici') or '0')[:4] or 0)
    if any_inici >= 2021:
        return 'modern'
    if any_inici and any_inici < 2015:
        return 'antic'
    return 'altres'


def pendents(especs: list, existents: dict, nomes_canvis: bool, des_de: str) -> list:
    """Especialitats a baixar. Sempre les noves i les que han canviat de versió; en mode
    complet, també les baixades abans de `des_de` (AAAA-MM-DD)."""
    out = []
    for e in especs:
        if not e.get('idSepe'):
            continue
        prev = existents.get(e['codi'])
        if not isinstance(prev, dict) or prev.get('versio') != e.get('versio'):
            out.append(e)
        elif not nomes_canvis and (prev.get('baixat') or '')[:10] < des_de:
            out.append(e)
    return out


# ---------------------------------------------------------------------------
# Descàrrega
# ---------------------------------------------------------------------------

def processa(espec: dict, fetch, textos=None) -> dict:
    """Entrada del fitxer de sortida per a una especialitat. Errors de xarxa i
    SepeDataError es propaguen (no es desa res d'aquesta especialitat).
    Amb `textos` (carpeta), hi desa el text del PDF per revisar-lo a mà."""
    pdf, ocupacions = fetch(espec['idSepe'])
    programa = None
    if pdf is not None:
        try:
            text = pdf_to_text(pdf)
            if textos:
                os.makedirs(textos, exist_ok=True)
                with open(os.path.join(textos, f"{espec['codi']}.txt"), 'w', encoding='utf-8') as f:
                    f.write(text)
            programa = sepe_programa.parse_programa(text, espec.get('hores'))
        except Exception as exc:  # un PDF trencat no ha d'aturar la descàrrega
            logger.warning('%s: no s\'ha pogut llegir el PDF: %s', espec['codi'], exc)
    return {
        'versio': espec.get('versio'),
        'baixat': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'programa': programa,
        'ocupacions': ocupacions,
        'sense_pdf': pdf is None,
    }


def descarrega(cua: list, data: dict, sortida: str, pausa: tuple, fetch, sleep=time.sleep, textos=None) -> tuple:
    """Baixa la cua. Retorna (codi de sortida, nombre d'especialitats baixades)."""
    errors_seguits = 0
    fetes = 0
    try:
        for n, espec in enumerate(cua, 1):
            if n > 1:
                sleep(random.uniform(*pausa))
            try:
                data[espec['codi']] = processa(espec, fetch, textos)
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in ATURA_HTTP:
                    logger.error('%s: HTTP %s del SEPE. Aturada: no es reintenta.', espec['codi'], status)
                    return EXIT_BLOQUEIG, fetes
                errors_seguits += 1
                logger.warning('%s: error HTTP %s (%d seguits)', espec['codi'], status, errors_seguits)
            except (requests.RequestException, sepe_scraper.SepeDataError) as exc:
                errors_seguits += 1
                logger.warning('%s: %s (%d seguits)', espec['codi'], exc, errors_seguits)
            else:
                errors_seguits = 0
                fetes += 1
                entry = data[espec['codi']]
                logger.info('[%d/%d] %s: %s, %d ocupacions', n, len(cua), espec['codi'],
                            'sense PDF' if entry['sense_pdf'] else
                            (entry['programa'] or {}).get('format') or 'PDF no llegit',
                            len(entry['ocupacions']))
                if fetes % DESA_CADA == 0:
                    desa(sortida, data)
            if errors_seguits >= MAX_ERRORS_SEGUITS:
                logger.error('%d errors seguits. Aturada: torna-ho a provar més tard.', errors_seguits)
                return EXIT_ERRORS, fetes
        return EXIT_OK, fetes
    except KeyboardInterrupt:
        logger.error('Aturada manual (Ctrl+C).')
        return EXIT_CTRL_C, fetes
    finally:
        desa(sortida, data)


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------

def _estat(espec: dict, entry):
    """(gravetat, motiu) per ordenar els pitjors casos; gravetat 0 = bé."""
    if entry is None:
        return 9, 'pendent (no baixada)'
    prog = entry.get('programa')
    if entry.get('sense_pdf'):
        return 6, 'el SEPE no hi té PDF'
    if prog is None:
        return 8, 'PDF no llegit (cap plantilla reconeguda)'
    if prog.get('moduls_error') == 'format':
        return 7, 'taula de mòduls il·legible'
    if prog.get('moduls_error') == 'suma':
        return 5, 'la suma d\'hores dels mòduls no quadra amb el catàleg'
    if not prog.get('objectiu'):
        return 4, 'sense objectiu'
    if prog.get('format') == 'modern' and not prog.get('moduls'):
        return 3, 'plantilla moderna sense mòduls'
    if not entry.get('ocupacions'):
        return 1, 'sense ocupacions'
    return 0, ''


def informe(especs: list, data: dict, titol: str, parametres: list) -> str:
    grups = ('modern', 'po', 'antic', 'altres')
    fila = {g: dict.fromkeys(('total', 'baixades', 'be', 'suma', 'format', 'sense_pdf',
                              'no_llegit', 'sense_ocu', 'moduls_ok'), 0) for g in grups}
    formats = {g: {} for g in grups}
    casos = []
    for e in especs:
        g = grup(e)
        entry = data.get(e['codi'])
        if entry is not None and entry.get('versio') != e.get('versio'):
            entry = None                     # versió antiga: compta com a pendent
        f = fila[g]
        f['total'] += 1
        grav, motiu = _estat(e, entry)
        if grav:
            casos.append((grav, e['codi'], g, motiu))
        if entry is None:
            continue
        f['baixades'] += 1
        prog = entry.get('programa')
        fmt = (prog or {}).get('format') or ('sense PDF' if entry.get('sense_pdf') else 'no llegit')
        formats[g][fmt] = formats[g].get(fmt, 0) + 1
        f['sense_pdf'] += bool(entry.get('sense_pdf'))
        f['no_llegit'] += prog is None and not entry.get('sense_pdf')
        f['sense_ocu'] += not entry.get('ocupacions')
        if prog:
            f['suma'] += prog.get('moduls_error') == 'suma'
            f['format'] += prog.get('moduls_error') == 'format'
            f['moduls_ok'] += bool(prog.get('moduls_ok'))
            f['be'] += grav in (0, 1)

    out = [f'# {titol}', '']
    out += [f'- {p}' for p in parametres] + ['']
    out += ['## Per plantilla esperada', '',
            'Plantilla segons el catàleg: modern = vigència des del 2021; po = sufix PO; '
            'antic = vigència abans del 2015; altres = 2015–2020 sense PO.', '',
            '| Plantilla | Especialitats | Baixades | Llegides bé | Mòduls validats | '
            'Mòduls no quadren | Mòduls il·legibles | Sense PDF | PDF no llegit | Sense ocupacions |',
            '|---|---|---|---|---|---|---|---|---|---|']
    for g in grups:
        f = fila[g]
        if f['total']:
            out.append(f"| {g} | {f['total']} | {f['baixades']} | {f['be']} | {f['moduls_ok']} | "
                       f"{f['suma']} | {f['format']} | {f['sense_pdf']} | {f['no_llegit']} | {f['sense_ocu']} |")
    m = fila['modern']
    if m['baixades']:
        pct = 100 * m['moduls_ok'] / m['baixades']
        out += ['', f"Plantilla moderna amb mòduls validats: {m['moduls_ok']}/{m['baixades']} "
                    f"({pct:.1f} %; objectiu orientatiu ≥ 90 %)."]
    out += ['', "«Llegides bé»: programa llegit, amb objectiu i, a la plantilla moderna, mòduls validats "
                "(pot no tenir ocupacions).", '',
            '## Plantilla detectada al PDF', '']
    for g in grups:
        if formats[g]:
            out.append(f'- {g}: ' + ', '.join(f'{k} {v}' for k, v in sorted(formats[g].items())))
    casos.sort(key=lambda c: (-c[0], c[1]))
    out += ['', f'## Pitjors casos (fins a {PITJORS}) per revisar a mà', '']
    if casos:
        out += ['| Codi | Plantilla | Motiu |', '|---|---|---|']
        out += [f'| {c} | {g} | {mot} |' for _, c, g, mot in casos[:PITJORS]]
    else:
        out.append('Cap.')
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

def _mostra_cami(path: str) -> str:
    rel = os.path.relpath(os.path.abspath(path), _REPO_ROOT)
    return os.path.abspath(path) if rel.startswith('..') else rel


def _args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--especs', default=ESPECS_PATH, help='catàleg (sepe_especs.json)')
    p.add_argument('--sortida', default=OUT_PATH, help='fitxer de sortida (per defecte backend/data/sepe_programes.json)')
    p.add_argument('--informe', default=None, help='informe Markdown (per defecte plans/outputs/sepe-programes-<data>.md)')
    p.add_argument('--nomes-canvis', action='store_true', help='només especialitats noves o amb versió nova')
    p.add_argument('--des-de', default=date.today().isoformat(),
                   help='mode complet: torna a baixar les baixades abans d\'aquest dia (AAAA-MM-DD; per defecte avui)')
    p.add_argument('--codis', default='', help='només aquests codis, separats per comes')
    p.add_argument('--limit', type=int, default=0, help='només les N primeres especialitats pendents')
    p.add_argument('--pausa', type=float, nargs=2, default=(5.0, 10.0), metavar=('MIN', 'MAX'),
                   help='pausa aleatòria entre especialitats, en segons (per defecte 5 10)')
    p.add_argument('--textos', default=None, help='carpeta on desar el text de cada PDF (per revisar casos)')
    p.add_argument('--nomes-informe', action='store_true', help='no baixa res: refà l\'informe de --sortida')
    args = p.parse_args(argv)
    try:
        date.fromisoformat(args.des_de)
    except ValueError:
        p.error('--des-de ha de ser AAAA-MM-DD')
    if args.pausa[0] < 0 or args.pausa[1] < args.pausa[0]:
        p.error('--pausa MIN MAX amb 0 ≤ MIN ≤ MAX')
    return args


def main(argv=None, fetch=None, sleep=time.sleep) -> int:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')
    args = _args(argv)
    fetch = fetch or sepe_scraper.fetch_programa_i_ocupacions
    with open(args.especs, encoding='utf-8') as f:
        especs = [e for e in json.load(f) if isinstance(e, dict) and e.get('codi')]
    n_cataleg = sum(1 for e in especs if e.get('idSepe'))
    codis = [c.strip() for c in args.codis.split(',') if c.strip()]
    if codis:
        per_codi = {e['codi']: e for e in especs}
        desconeguts = [c for c in codis if c not in per_codi]
        if desconeguts:
            logger.warning('Codis que no són al catàleg: %s', ', '.join(desconeguts))
        especs = [per_codi[c] for c in codis if c in per_codi]
    data = carrega(args.sortida)

    exit_code, fetes, segons = EXIT_OK, 0, 0.0
    cua = []
    if not args.nomes_informe:
        cua = pendents(especs, data, args.nomes_canvis, args.des_de)
        if args.limit:
            cua = cua[:args.limit]
        if not args.nomes_canvis and not codis and not args.limit:
            logger.info('Per reprendre-la si s\'atura: %s', ORDRE_COMPLETA.format(des_de=args.des_de))
        logger.info('%d especialitats a baixar (de %d); sortida: %s', len(cua), len(especs), args.sortida)
        t0 = time.monotonic()
        exit_code, fetes = descarrega(cua, data, args.sortida, tuple(args.pausa), fetch, sleep, args.textos)
        segons = time.monotonic() - t0

    abast = cua if args.limit and not args.nomes_informe else especs
    avui = date.today().isoformat()
    parametres = [
        f'Data: {avui}',
        f'Sortida: `{_mostra_cami(args.sortida)}`',
        f"Mode: {'només informe' if args.nomes_informe else 'només canvis' if args.nomes_canvis else f'complet des de {args.des_de}'}"
        + (f' · {len(codis)} codis triats' if codis else '') + (f' · límit {args.limit}' if args.limit else ''),
        f'Especialitats a l\'abast de l\'informe: {len(abast)}',
    ]
    if not args.nomes_informe:
        mitjana = segons / fetes if fetes else 0
        parametres += [
            f'Baixades en aquesta execució: {fetes} de {len(cua)} · pausa {args.pausa[0]:g}–{args.pausa[1]:g} s',
            f'Temps total: {segons / 60:.1f} min · mitjana {mitjana:.1f} s per especialitat (amb la pausa)',
        ]
        if mitjana:
            parametres.append(f'Estimació per a tot el catàleg ({n_cataleg} especialitats): '
                              f'{n_cataleg * mitjana / 3600:.1f} h')
        if exit_code != EXIT_OK:
            parametres.append(f'**Aturada abans d\'acabar (codi {exit_code}).** Per reprendre-la: '
                              f'la mateixa ordre (amb la mateixa --des-de).')
    path = args.informe or os.path.join(INFORME_DIR, f'sepe-programes-{avui}.md')
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(informe(abast, data, 'Programes formatius i ocupacions del SEPE', parametres))
    logger.info('Informe: %s', path)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
