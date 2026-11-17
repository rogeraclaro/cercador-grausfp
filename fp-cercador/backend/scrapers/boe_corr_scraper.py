"""
boe_corr_scraper.py — Plan 091: official correspondence between units of competence (UC)
and professional modules of each FP title, read from the BOE open XML
(https://www.boe.es/diario_boe/xml.php?id=BOE-A-…).

Two tables per title:
  A  «Unidades de competencia acreditadas» → «Módulos profesionales convalidables»
  B  «Módulos profesionales superados»     → «Unidades de competencia acreditables»

The annex heading sits outside the table, so tables are recognised by their column headers.
A decree can carry tables for another decree (RD 498–500/2024 and the 2023 «actualización»
decrees replace the annexes of many titles): each table is tagged with the royal decree its
surrounding text targets, and resolve_title() picks the newest one for a given title.

Everything here is pure (no network) except fetch(); scripts/build_d_uc_corr.py drives it.
"""
import html
import os
import re
import time
import unicodedata

import requests

BOE_XML_URL = 'https://www.boe.es/diario_boe/xml.php?id={}'
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
REQUEST_DELAY = 1.0  # seconds between requests, todofp and BOE alike

_BOE_ID_RE = re.compile(r'BOE-A-\d{4}-\d+')
_BOE_LINK_RE = re.compile(r'href="(https?://www\.boe\.es/[^"]+)"')
_TOKEN_RE = re.compile(r'<table\b.*?</table>|<p\b[^>]*>.*?</p>', re.S)
_ROW_RE = re.compile(r'<tr\b.*?</tr>', re.S)
_CELL_RE = re.compile(r'<t[dh]\b([^>]*)>(.*?)</t[dh]>', re.S)
_SPAN_RE = re.compile(r'(row|col)span="(\d+)"')
# BOE typos seen: «UCO255_1» (letter O for zero), «UC 0255_1», «UC437_1» (three digits) and
# «UC01263_2» (five digits, extra leading zero). Titles from 2026 on write «ECP1690_2»
# (estándar de competencia profesional); the prefix is kept as printed.
_UC_RE = re.compile(r'\b(UC|ECP)\s?([O0-9]\d{2,4})\s?_\s?(\d)')
# Module code: «0235. Name», «0624.Name», «0902 .Name», «O856. Name», «1528: Name».
_MOD_RE = re.compile(r'(?<![\w/.,])([O0-9]\d{3})\s*[.:]?\s*(?=[A-ZÁÉÍÓÚÑ¿])')
_RD_NUM_RE = re.compile(r'Real Decreto (\d+/\d{4})')
_ARTICLE_RE = re.compile(r'^(Artículo|Disposición) ', re.I)
_ARTICLE_TARGET_RE = re.compile(r'(?:Actualización|Modificación)(?: del)? Real Decreto (\d+/\d{4})')
# Numbered amendment: «Uno. En el Real Decreto 1685/2007, …», «Quince. Se modifica el Real
# Decreto …», «Dos. El artículo 6 queda redactado…» (group 1 is None without a decree).
_INSTRUCTION_RE = re.compile(
    r'^(?:Uno|Dos|Tres|Cuatro|Cinco|Seis|Siete|Ocho|Nueve|Diez|Once|Doce|Trece|Catorce|Quince'
    r'|Dieci\w+|Veint\w+|Treinta|Cuarenta|Cincuenta|Sesenta|Setenta|Ochenta|Noventa)'
    r'(?: y \w+)?\.\s+(?:[^.]{0,40}?Real Decreto (\d+/\d{4}))?')
_ANNEX_OF_TITLE_RE = re.compile(r'anexo ([IVXL]+)\b(?!\s?\.?[AB]\b)')
_ANNEX_NUM_RE = re.compile(r'^ANEXO ([IVXL]+)$')
_ANNEX_TITLE_RE = re.compile(r'^Título Profesional Básico en ', re.I)
_NOTE_RE = re.compile(r'convalid|acredit', re.I)
_HEADING_RE = re.compile(r'^(«?ANEXO\b|«?\d+(?: bis)?\. |Correspondencia )', re.I)
_OWN_TITLE_RE = re.compile(
    r'^Real Decreto [^,]+,[^,]*, por el que se establece el título\b', re.I)
_SHARED_TITLE_RE = re.compile(r'se (?:aprueban|establecen) \w+ títulos', re.I)
_ESTABLISHES_RE = re.compile(
    r'Real Decreto (\d+/\d{4}), de [^,]+, por el que se establece el título de ([^,.]+?) y se fijan')
_REFERENCE_RE = re.compile(r'<anterior referencia="(BOE-A-\d{4}-\d+)"[^>]*>(.*?)</anterior>', re.S)
_MAX_NOTES_AFTER_TABLE = 3


def normalize_title(name: str) -> str:
    """Accent- and case-insensitive key for a title name."""
    s = unicodedata.normalize('NFD', name or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def _text(fragment: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment))).strip()


def boe_links(page_html: str) -> list[str]:
    """BOE links of a todofp title page, in order, without duplicates."""
    return list(dict.fromkeys(_BOE_LINK_RE.findall(page_html)))


def boe_id(text: str) -> str | None:
    """BOE identifier inside a link, or inside the page an ELI address resolves to."""
    m = _BOE_ID_RE.search(text or '')
    return m.group(0) if m else None


def _meta(xml: str, tag: str) -> str:
    m = re.search(rf'<{tag}\b[^>]*>(.*?)</{tag}>', xml[:20000], re.S)
    return _text(m.group(1)) if m else ''


def _grid(table: str) -> list[list[tuple[str, bool]]]:
    """
    Table as rows of (cell text, carried) slots. Cells with rowspan/colspan are repeated in
    every slot they cover; 'carried' is True for the slots filled from a rowspan above.
    """
    rows: list[list[tuple[str, bool]]] = []
    carry: dict[int, tuple[str, int]] = {}  # column → (text, rows still to fill)
    for tr in _ROW_RE.findall(table):
        row: list[tuple[str, bool]] = []
        cells = _CELL_RE.findall(tr)
        col = 0
        while cells or col in carry:
            if col in carry:
                text, left = carry[col]
                row.append((text, True))
                if left > 1:
                    carry[col] = (text, left - 1)
                else:
                    del carry[col]
                col += 1
                continue
            attrs, inner = cells.pop(0)
            spans = dict(_SPAN_RE.findall(attrs))
            text = _text(inner)
            for _ in range(int(spans.get('col', 1))):
                row.append((text, False))
                if int(spans.get('row', 1)) > 1:
                    carry[col] = (text, int(spans['row']) - 1)
                col += 1
        rows.append(row)
    return rows


def parse_ucs(cell: str) -> list[str]:
    ucs = []
    for prefix, num, level in _UC_RE.findall(cell):
        num = num.replace('O', '0').zfill(4)
        if len(num) == 5:
            if not num.startswith('0'):
                continue
            num = num[1:]
        ucs.append(f'{prefix}{num}_{level}')
    return list(dict.fromkeys(ucs))


def parse_modules(cell: str) -> list[dict]:
    """[{num, name}] for every coded module in a cell."""
    marks = list(_MOD_RE.finditer(cell))
    modules = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(cell)
        name = re.sub(r'\(\*+\)|\*', '', cell[m.end():end]).strip(' .;,"“”«»')
        modules.append({'num': m.group(1).replace('O', '0'), 'name': name})
    return modules


def _drop_repeated_columns(grid: list[list[tuple[str, bool]]]) -> list[list[tuple[str, bool]]]:
    """Remove the extra columns that only repeat the one to their left (colspan) or are empty."""
    width = max((len(row) for row in grid), default=0)
    for col in range(width - 1, 0, -1):
        full = [row for row in grid if len(row) == width]
        if width > 2 and all(row[col][0] in ('', row[col - 1][0]) for row in full):
            grid = [row[:col] + row[col + 1:] if len(row) == width else row for row in grid]
            width -= 1
    return grid


def _is_corr_header(row: list[tuple[str, bool]]) -> bool:
    # Titles from 2025 on say «estándares de competencias profesionales» for the same UC codes.
    low = ' '.join(text for text, _ in row).lower()
    return ('unidades de competencia' in low or 'estándares de competencia' in low) \
        and ('convalidables' in low or 'acreditables' in low)


def parse_table(table: str) -> dict | None:
    """
    {'kind', 'rows': [{'uc', 'moduls'}], 'notes', 'unread'} or None when it is not a
    correspondence table.

    The header only identifies the table; the kind comes from the data, because the BOE
    sometimes prints the table A header over table B (RD 1691/2007): UC in the first column
    is A, modules in the first column is B.
    Rows joined by a rowspan cell, or left with an empty cell, continue the row above: the
    cell is a single group in the BOE. Rows that merely repeat a module or a UC stay
    separate (they are alternatives). 'unread' keeps the raw text of rows where no UC or no
    module code could be read.
    """
    grid = _drop_repeated_columns(_grid(table))
    header = next((i for i, row in enumerate(grid[:3]) if _is_corr_header(row)), None)
    if header is None or len(grid[header]) != 2:
        return None
    body = [slots for slots in grid[header + 1:] if len(slots) == 2 and any(text for text, _ in slots)]
    uc_first = sum(1 for slots in body if parse_ucs(slots[0][0]))
    uc_second = sum(1 for slots in body if parse_ucs(slots[1][0]))
    if uc_first == uc_second:
        uc_col = 0 if 'convalidables' in ' '.join(text for text, _ in grid[header]).lower() else 1
    else:
        uc_col = 0 if uc_first > uc_second else 1
    rows: list[dict] = []
    notes: list[str] = []
    unread: list[str] = []
    for slots in body:
        cells = [text for text, _ in slots]
        if cells[0] == cells[1]:  # full-width row: a note inside the table
            if _NOTE_RE.search(cells[0]) and cells[0] not in notes:
                notes.append(cells[0])
            continue
        ucs, modules = parse_ucs(cells[uc_col]), parse_modules(cells[1 - uc_col])
        continues = any(carried for _, carried in slots) or not all(cells)
        if rows and continues and (ucs or modules):
            row = rows[-1]
            row['uc'] += [u for u in ucs if u not in row['uc']]
            row['moduls'] += [m for m in modules if m['num'] not in {x['num'] for x in row['moduls']}]
        elif ucs and modules:
            rows.append({'uc': ucs, 'moduls': modules})
        else:
            unread.append(' | '.join(cells))
    return {'kind': 'A' if uc_col == 0 else 'B', 'rows': rows, 'notes': notes, 'unread': unread}


def parse_doc(xml: str) -> dict:
    """
    {'id', 'numero', 'titulo', 'fecha', 'rango', 'blocks', 'cites', 'has_uc', 'has_images'}.

    'cites' maps the title names this decree mentions as established by another royal decree
    to that decree's BOE id (taken from the <anterior> references), for the titles whose
    todofp page links the amending decree but not the establishing one.

    Each block is a parse_table() result plus where it applies:
      'target_rd'     royal decree the surrounding text modifies («1685/2007»), None for the
                      decree's own tables
      'target_anexo'  annex of the target decree, when the target holds several titles
      'anexo', 'anexo_titol'  annex of this decree the table sits in (shared basic decrees)
    """
    doc = {'id': _meta(xml, 'identificador'), 'numero': _meta(xml, 'numero_oficial'),
           'titulo': _meta(xml, 'titulo'), 'fecha': _meta(xml, 'fecha_disposicion'),
           'rango': _meta(xml, 'rango'), 'blocks': [], 'cites': {}}
    body = xml[xml.find('<texto'):]
    doc['has_uc'], doc['has_images'] = bool(_UC_RE.search(body)), '<img' in body
    ids = {m.group(1): ref for ref, text in _REFERENCE_RE.findall(xml) for m in [_RD_NUM_RE.search(text)] if m}
    for numero, name in _ESTABLISHES_RE.findall(_text(body)):
        if numero in ids:
            doc['cites'][normalize_title(name)] = ids[numero]
    article_rd = target_rd = target_anexo = anexo = anexo_titol = pending_anexo = None
    last_block: dict | None = None
    notes_left = 0
    for token in _TOKEN_RE.findall(body):
        if token.startswith('<table'):
            parsed = parse_table(token)
            last_block, notes_left = None, 0
            if parsed:
                parsed.update(target_rd=target_rd, target_anexo=target_anexo,
                              anexo=None if target_rd else anexo,
                              anexo_titol=None if target_rd else anexo_titol)
                doc['blocks'].append(parsed)
                last_block, notes_left = parsed, _MAX_NOTES_AFTER_TABLE
            continue
        text = _text(token)
        if not text:
            continue
        if _ARTICLE_RE.match(text):
            m = _ARTICLE_TARGET_RE.search(text)
            article_rd = target_rd = m.group(1) if m else None
            target_anexo = last_block = None
            continue
        m = _INSTRUCTION_RE.match(text)
        if m:
            # An amendment that names no decree falls back to the one its article names.
            target_rd = m.group(1) or article_rd
            annexes = _ANNEX_OF_TITLE_RE.findall(text) if 'apartado' in text else []
            target_anexo = annexes[-1] if annexes else None
            last_block = None
            continue
        m = _ANNEX_NUM_RE.match(text)
        if m:
            pending_anexo, last_block = m.group(1), None
            continue
        if pending_anexo and _ANNEX_TITLE_RE.match(text):
            anexo, anexo_titol, pending_anexo = pending_anexo, text, None
            continue
        pending_anexo = None
        if last_block is not None and notes_left > 0:
            if _HEADING_RE.match(text):
                last_block = None
            else:
                notes_left -= 1
                if _NOTE_RE.search(text) and len(text) > 40:
                    last_block['notes'].append(text.strip('«»'))
    return doc


def is_own_decree(doc: dict) -> bool:
    """Royal decree that establishes exactly one title."""
    return bool(_OWN_TITLE_RE.match(doc['titulo'])) and 'especialización' not in doc['titulo'].lower()


def is_shared_decree(doc: dict) -> bool:
    """Royal decree that establishes several basic titles, one per annex."""
    return doc['rango'] == 'Real Decreto' and bool(_SHARED_TITLE_RE.search(doc['titulo'])) \
        and 'modifican' not in doc['titulo'].lower()


def find_base(denominacion: str, linked: list[dict]) -> tuple[dict | None, str | None, str]:
    """
    (decree that establishes the title, annex within it or None, reason when not found).

    The annex is only set for shared decrees; a title that cannot be pinned to exactly one
    decree (and one annex) is left without a base rather than guessed.
    """
    key = normalize_title(denominacion)
    own = [d for d in linked if is_own_decree(d)]
    if len(own) > 1:
        named = [d for d in own if key and key in normalize_title(d['titulo'])]
        own = named if len(named) == 1 else own
    if len(own) == 1:
        return own[0], None, ''
    if len(own) > 1:
        return None, None, 'several establishing decrees linked: ' + ', '.join(d['id'] for d in own)
    matches = []
    for doc in linked:
        if not is_shared_decree(doc):
            continue
        annexes = {b['anexo'] for b in doc['blocks'] if normalize_title(b.get('anexo_titol') or '') == key}
        matches += [(doc, a) for a in annexes if a]
    if len(matches) == 1:
        return matches[0][0], matches[0][1], ''
    if matches:
        return None, None, 'title found in several shared annexes'
    if any(is_shared_decree(d) for d in linked):
        return None, None, 'title not found among the annexes of its shared decree'
    return None, None, 'no establishing decree among the BOE links'


def cited_decree(denominacion: str, linked: list[dict]) -> str | None:
    """BOE id of the establishing decree, as cited by a linked decree, when it is not linked."""
    key = normalize_title(denominacion)
    ids = {doc['cites'][key] for doc in linked if key in doc['cites']}
    return ids.pop() if len(ids) == 1 else None


def resolve_title(denominacion: str, linked: list[dict], all_docs: list[dict]) -> dict:
    """
    Tables in force for one title:
    {'decret', 'vigent', 'convalida', 'acredita', 'notes', 'unread'} or {'motiu': reason}.
    Optional keys: 'vigent_acredita' when table B comes from a different decree than table A,
    and 'convalida_anterior' with the title's original table A when a later decree replaced
    it (certificates issued before the change still list the UC codes of the old table).

    For each table kind the newest decree wins among the base decree and every decree in
    all_docs whose text targets it (same royal decree number and, for shared decrees, annex).
    """
    base, anexo, reason = find_base(denominacion, linked)
    if not base:
        return {'motiu': reason}
    chosen: dict[str, tuple[str, dict, list[dict]]] = {}
    for doc in all_docs:
        for kind in ('A', 'B'):
            if doc['id'] == base['id']:
                blocks = [b for b in doc['blocks'] if b['kind'] == kind and not b['target_rd']
                          and (anexo is None or b['anexo'] == anexo)]
            else:
                blocks = [b for b in doc['blocks'] if b['kind'] == kind
                          and b['target_rd'] == base['numero'] and b['target_anexo'] == anexo]
            if blocks and (kind not in chosen or doc['fecha'] > chosen[kind][0]):
                chosen[kind] = (doc['fecha'], doc, blocks)
    if not chosen:
        if not base['has_uc']:
            reason = 'the decree names no unit of competence'
        elif base['has_images']:
            reason = 'the annexes are published as images in the BOE XML'
        else:
            reason = 'no correspondence table in the decree'
        return {'decret': base['id'], 'motiu': reason}

    def rows(kind: str) -> list[dict]:
        return [r for b in chosen[kind][2] for r in b['rows']] if kind in chosen else []

    used = [b for kind in chosen for b in chosen[kind][2]]
    entry = {
        'decret': base['id'],
        'vigent': chosen['A' if 'A' in chosen else 'B'][1]['id'],
        'convalida': rows('A'),
        'acredita': [{'moduls': r['moduls'], 'uc': r['uc']} for r in rows('B')],
        'notes': list(dict.fromkeys(n for b in used for n in b['notes'])),
        'unread': [u for b in used for u in b['unread']],
    }
    if 'A' in chosen and 'B' in chosen and chosen['B'][1]['id'] != entry['vigent']:
        entry['vigent_acredita'] = chosen['B'][1]['id']
    if 'A' in chosen and chosen['A'][1]['id'] != base['id']:
        original = [r for b in base['blocks'] if b['kind'] == 'A' and not b['target_rd']
                    and (anexo is None or b['anexo'] == anexo) for r in b['rows']]
        if original:
            entry['convalida_anterior'] = original
    return entry


def fetch(url: str, path: str, referer: str | None = None) -> str:
    """Download url into path unless it is already there (cache); 1 request per second."""
    if os.path.exists(path):
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    headers = {'User-Agent': USER_AGENT}
    if referer:
        headers['Referer'] = referer
    resp = requests.get(url, headers=headers, timeout=90)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(resp.content)
    return resp.content.decode('utf-8', errors='replace')
