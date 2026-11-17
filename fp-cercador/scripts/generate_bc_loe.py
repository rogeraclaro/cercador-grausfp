#!/usr/bin/env python3
"""
generate_bc_loe.py — Genera backend/data/bc_loe.json a partir dels Annexos PDF
dels Certificats de Profesionalitat C LOE.

Execució única (~10 min amb rate limiting). Necessita xarxa i pdfplumber.
Escriu backend/data/bc_loe.json (gitignored) i plans/outputs/audit_bc_loe.md.

Pla 090: el PDF d'un annex és un tall del BOE i sovint arrossega un tros de
l'annex veí, així que només es llegeix el segment del certificat. Els codis
surten de les capçaleres «Código: MF####_N» (les «Código: UC####_N» falten en
uns 80 annexos i porten errades en d'altres), es desen com a UC####_N —tots
els consumidors casen UC i MF pel número— i es contrasten amb la llista de
mòduls del SEPE (scripts/data/sepe_cp_mf.json), que és la font quan l'annex
és escanejat o incomplet.

Ús: python3 scripts/generate_bc_loe.py [--dry-run N] [--cache DIR]
  --dry-run N  Processa només els primers N PDFs (per a proves ràpides)
  --cache DIR  Desa els PDFs baixats a DIR i els reaprofita
"""
import argparse
import io
import json
import logging
import os
import re
import sys
import time

import requests
import pdfplumber

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
DATA_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'ofertes.json')
OUT_PATH  = os.path.join(_REPO_ROOT, 'backend', 'data', 'bc_loe.json')
BASE_DAM  = 'https://www.todofp.es/dam/todofp/certificados-profesionales'

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://www.todofp.es/',
}
SEPE_PATH = os.path.join(_REPO_ROOT, 'scripts', 'data', 'sepe_cp_mf.json')
REPORT_PATH = os.path.join(_REPO_ROOT, 'plans', 'outputs', 'audit_bc_loe.md')

_CP_PAT = re.compile(r'Código:\s*([A-Z]{4}\d{4})')
_MF_HEAD_PAT = re.compile(r'Código:\s*(MF\d{4}_\d)')
# El SEPE publica com a molt 8 codis per certificat (MF + MP): amb 8, la llista pot estar tallada.
_SEPE_MAX_CODES = 8


def own_segment(text: str, codigo: str) -> str:
    """Tros del text que pertany a l'annex de `codigo`; '' si el codi no hi surt."""
    base = codigo.split('_')[0]
    marks = [(m.start(), m.group(1)) for m in _CP_PAT.finditer(text)]
    start = next((pos for pos, code in marks if code == base), None)
    if start is None:
        return ''
    end = next((pos for pos, code in marks if pos > start and code != base), len(text))
    return text[start:end]


def mf_headings(segment: str) -> list[str]:
    return list(dict.fromkeys(_MF_HEAD_PAT.findall(segment)))


def resolve_uc_codes(codigo: str, text: str, sepe: dict | None, b_by_num: dict,
                     nivel) -> tuple[list[str], str]:
    """UC del certificat i d'on surten: 'annex', 'sepe' o 'none'.

    sepe: {'mf': ['MF1978', ...], 'mp': [...]} o None. b_by_num: {'1978': 'MF1978_2'}
    (mòduls B LOE del catàleg), per posar nivell als codis que només dona el SEPE.
    """
    heads = mf_headings(own_segment(text, codigo))
    as_uc = lambda mf: 'UC' + mf[2:]
    if not sepe:
        return ([as_uc(h) for h in heads], 'annex') if heads else ([], 'none')

    sepe_nums = [code[2:6] for code in sepe['mf']]
    head_nums = {h[2:6] for h in heads}
    truncated = len(sepe['mf']) + len(sepe.get('mp', [])) >= _SEPE_MAX_CODES
    if heads and (head_nums == set(sepe_nums) or (truncated and set(sepe_nums) < head_nums)):
        return [as_uc(h) for h in heads], 'annex'

    level_of = {h[2:6]: h for h in heads}
    codes = []
    for num in sepe_nums:
        mf = level_of.get(num) or b_by_num.get(num) or f'MF{num}_{nivel}'
        codes.append(as_uc(mf))
    return codes, 'sepe'


def _fetch_pdf_text(codigo: str, cache_dir: str | None) -> str:
    """Text de l'annex; '' si no existeix (404). Dorm 1 s després de cada baixada."""
    cached = os.path.join(cache_dir, f'{codigo.lower()}.pdf') if cache_dir else None
    if cached and os.path.exists(cached):
        with open(cached, 'rb') as f:
            content = f.read()
    else:
        url = f"{BASE_DAM}/anexos/{codigo.lower()}.pdf"
        resp = requests.get(url, headers=_HEADERS, timeout=60)
        time.sleep(1)
        if resp.status_code == 404:
            return ''
        resp.raise_for_status()
        content = resp.content
        if cached:
            with open(cached, 'wb') as f:
                f.write(content)
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return '\n'.join(page.extract_text() or '' for page in pdf.pages)


def _write_report(result: dict, sources: dict, previous: dict, sepe: dict) -> None:
    lines = ['# Auditoria de bc_loe.json (pla 090)', '',
             f'Certificats: {len(result)}. Per font: '
             + ', '.join(f'{k} {sum(1 for s in sources.values() if s == k)}' for k in ('annex', 'sepe', 'none'))
             + '.', '']
    changed = [(c, sorted(set(previous.get(c, [])) - set(v)), sorted(set(v) - set(previous.get(c, []))))
               for c, v in sorted(result.items()) if set(previous.get(c, [])) != set(v)]
    lines += [f'## Canvis respecte al fitxer anterior ({len(changed)} certificats)', '',
              '| Certificat | UC que desapareixen | UC que apareixen |', '|---|---|---|']
    lines += [f"| {c} | {', '.join(out) or '—'} | {', '.join(new) or '—'} |" for c, out, new in changed]
    lines += ['', '## Certificats resolts amb la llista del SEPE', '',
              "L'annex és escanejat, incomplet o no quadra amb la llista. Amb 8 codis al SEPE la llista pot",
              'estar tallada.', '', '| Certificat | UC | Codis al SEPE |', '|---|---|---|']
    lines += [f"| {c} | {', '.join(result[c])} | {len(sepe[c]['mf']) + len(sepe[c].get('mp', []))} |"
              for c in sorted(result) if sources[c] == 'sepe']
    lines += ['', '## Certificats sense cap UC', '', ', '.join(c for c in sorted(result) if not result[c]) or '—', '']
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', type=int, metavar='N',
                        help='Processa només els primers N PDFs')
    parser.add_argument('--cache', metavar='DIR', help='Directori on desar i reaprofitar els PDFs')
    args = parser.parse_args()
    if args.cache:
        os.makedirs(args.cache, exist_ok=True)

    if not os.path.exists(DATA_PATH):
        logger.error("ofertes.json no trobat a: %s", DATA_PATH)
        sys.exit(1)

    with open(DATA_PATH, encoding='utf-8') as f:
        records = json.load(f)

    c_loe = [
        r for r in records
        if r.get('grado') == 'C' and r.get('plan_antiguo') and r.get('codigo')
    ]
    if args.dry_run:
        c_loe = c_loe[:args.dry_run]
        logger.info("DRY-RUN: processant %d PDFs (de %d totals)", args.dry_run, len(c_loe))
    else:
        logger.info("%d registres C LOE a processar (~6 min)", len(c_loe))

    with open(SEPE_PATH, encoding='utf-8') as f:
        sepe = json.load(f)
    b_by_num = {r['codigo'][2:6]: r['codigo'] for r in records
                if r.get('grado') == 'B' and r.get('plan_antiguo') and re.match(r'^MF\d{4}_\d$', r.get('codigo') or '')}
    previous: dict[str, list[str]] = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding='utf-8') as f:
            previous = json.load(f)

    result: dict[str, list[str]] = {}
    sources: dict[str, str] = {}
    errors: list[str] = []
    no_codes: list[str] = []

    for i, r in enumerate(c_loe, 1):
        codigo = r['codigo']
        try:
            text = _fetch_pdf_text(codigo, args.cache)
            codes, sources[codigo] = resolve_uc_codes(codigo, text, sepe.get(codigo), b_by_num, r.get('nivel'))
            result[codigo] = codes
            if codes:
                logger.info("[%d/%d] %s → %d UC codes (%s)", i, len(c_loe), codigo, len(codes), sources[codigo])
            else:
                no_codes.append(codigo)
                logger.warning("[%d/%d] 0 UC codes (404 o PDF sense texto): %s",
                               i, len(c_loe), codigo)
        except Exception as exc:
            logger.error("[%d/%d] ERROR: %s — %s", i, len(c_loe), codigo, exc)
            errors.append(codigo)
            result[codigo] = []
            sources[codigo] = 'none'

    # Estadística de cobertura
    with_codes = sum(1 for v in result.values() if v)
    total = len(result)
    pct = with_codes / total * 100 if total else 0
    logger.info("═══ Resultat ═══")
    logger.info("Total processats: %d", total)
    logger.info("PDFs amb UC codes: %d (%.0f%%)", with_codes, pct)
    logger.info("Sense UC codes:   %d", len(no_codes))
    logger.info("Errors HTTP:      %d", len(errors))
    if no_codes:
        logger.info("Sense UC codes: %s", no_codes[:10])
    if errors:
        logger.info("Errors: %s", errors[:10])

    if not args.dry_run and pct < 80:
        logger.error(
            "COBERTURA INSUFICIENT (%.0f%% < 80%%). bc_loe.json NO s'ha escrit. "
            "Investiga els PDFs problemàtics i reporta.", pct
        )
        sys.exit(1)

    if args.dry_run:
        # Un dry-run no pot trepitjar el fitxer real amb N entrades.
        logger.info("DRY-RUN: no s'escriu res. Mostra: %s", dict(list(result.items())[:5]))
        return

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))
    _write_report(result, sources, previous, sepe)
    logger.info("Informe escrit: %s", REPORT_PATH)

    size = os.path.getsize(OUT_PATH)
    logger.info("bc_loe.json escrit: %d entrades, %d bytes", len(result), size)


if __name__ == '__main__':
    main()
