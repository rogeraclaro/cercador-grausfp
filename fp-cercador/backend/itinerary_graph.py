"""
itinerary_graph.py — Graf complet de l'itinerari A→B→C→D→E (Pla 071).

Funcions pures: no fa I/O. Rep els registres d'ofertes.json i els fitxers de
relacions ja carregats, i construeix un graf amb arestes dirigides "cap amunt"
(A→B, B→C, C→D, D→E) indexades en totes dues direccions.

Clau de node: "{grado}:{ref}" (clau estable del Pla 076, per a tots els graus).
Els fitxers de relacions van per codi (A/B/C) o per id vigent (D/E) i es
tradueixen a la clau del node aquí.

Fonts de cada aresta:
  ab  itinerary.build_ab_index / get_parents_b (LOMLOE pel codi; LOE via a_loe_pares)
  bc  bc_loe.json (C LOE → UC####_N ↔ B MF####_N) i bc_lomloe.json (C LOMLOE → B)
  cd  LOMLOE: cd_lomloe.build_c_lomloe_to_d (porta shared/total)
      LOE:    ciclos_fp.json, resolt contra els D per ficha_url i, si no, per
              denominació curta normalitzada + família. Els no resolts es
              guarden a 'unresolved' (no s'inventen ids).
  de  ce_acces.json (Pla 074): {str(id_e): {d_ids: [id_d], unmatched: [...]}}.
"""
from urllib.parse import urlsplit

import itinerary
from cd_lomloe import normalize_module_name
from oferta_ref import ensure_refs

# Mateixos prefixos que certificados_scraper._D_PREFIXES: ciclosFP dona el nom curt.
_D_PREFIXES = (
    'Título Profesional Básico en ',
    'Técnico Superior en ',
    'Técnico en ',
)


def node_key(rec: dict) -> str | None:
    grado = rec.get('grado')
    if grado in ('A', 'B', 'C', 'D', 'E') and rec.get('ref'):
        return f"{grado}:{rec['ref']}"
    return None


def _http_url(url) -> str | None:
    """L'URL tal qual si és http(s) amb host; altrament None (criteri de safeHttpUrl)."""
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    return url.strip() if parts.scheme in ('http', 'https') and parts.netloc else None


def _norm_url(url) -> str | None:
    """Host (sense www.) + camí sense barra final: ignora esquema i majúscules del host."""
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    host = (parts.hostname or '').removeprefix('www.')
    return f"{host}{parts.path.rstrip('/')}" if host else None


def _short_name(den: str) -> str:
    for prefix in _D_PREFIXES:
        if den.startswith(prefix):
            den = den[len(prefix):]
            break
    return normalize_module_name(den)


def serialize_node(rec: dict) -> dict:
    grado = rec.get('grado')
    abc = grado in ('A', 'B', 'C')
    codigo = rec.get('codigo') if abc else None
    return {
        'key': node_key(rec),
        'ref': rec.get('ref'),
        'grado': grado,
        'codigo': codigo,
        'id': None if abc else rec.get('id'),
        'denominacion': rec.get('denominacion'),
        'familia': rec.get('familia'),
        'nivel': rec.get('nivel'),
        'plan_antiguo': bool(rec.get('plan_antiguo')),
        'ficha': (f'/api/ficha-redirect?grado={grado}&codigo={codigo}' if abc
                  else _http_url(rec.get('ficha_url'))),
    }


def build_graph(records, *, a_loe_pares=None, bc_loe=None, bc_lomloe=None,
                c_lomloe_to_d=None, ciclos_fp=None, ce_acces=None) -> dict:
    """
    Retorna {'records': {key: rec}, 'up': {key: [aresta]}, 'down': {key: [aresta]},
             'unresolved': {key_c: [denominacio_d, ...]}}.
    Cada aresta és {'from', 'to', 'kind'} (+ 'shared'/'total' a les cd LOMLOE).
    """
    ensure_refs(records)
    by_key: dict = {}
    key_by_code: dict = {}  # (grado, codigo) → clau; un codi repetit es queda el primer
    key_by_id: dict = {}    # id vigent → clau (fitxers D/E per id)
    for r in records:
        k = node_key(r)
        if k:
            by_key[k] = r
            if r.get('codigo'):
                key_by_code.setdefault((r['grado'], r['codigo']), k)
            if r.get('id') is not None:
                key_by_id[r['id']] = k

    def code_key(grado, codigo):
        return key_by_code.get((grado, codigo))

    def id_key(id_):
        try:
            return key_by_id.get(int(id_))
        except (TypeError, ValueError):
            return None

    up: dict = {}
    down: dict = {}
    seen: set = set()

    def add(src, dst, kind, **extra):
        if src not in by_key or dst not in by_key or (src, dst) in seen:  # None inclòs
            return
        seen.add((src, dst))
        edge = {'from': src, 'to': dst, 'kind': kind, **extra}
        up.setdefault(src, []).append(edge)
        down.setdefault(dst, []).append(edge)

    # A → B
    ab_idx = itinerary.build_ab_index(records, a_loe_pares)
    for r in records:
        if r.get('grado') == 'A' and r.get('codigo'):
            for b in itinerary.get_parents_b(r, ab_idx):
                add(node_key(r), node_key(b), 'ab')

    # B → C
    b_by_uc = ab_idx['b_by_uc']
    for c_code, ucs in (bc_loe or {}).items():
        for uc in ucs:
            b = b_by_uc.get(uc)
            if b:
                add(node_key(b), code_key('C', c_code), 'bc')
    for c_code, b_codes in (bc_lomloe or {}).items():
        for b_code in b_codes:
            add(code_key('B', b_code), code_key('C', c_code), 'bc')

    # C → D LOMLOE (mòduls compartits)
    for c_code, entries in (c_lomloe_to_d or {}).items():
        for e in entries:
            add(code_key('C', c_code), id_key(e['id']), 'cd', shared=e['shared'], total=e['total'])

    # C → D LOE (ciclos_fp.json, sense id de D)
    d_by_url: dict = {}
    d_by_name: dict = {}
    for r in records:
        if r.get('grado') != 'D' or r.get('id') is None:
            continue
        u = _norm_url(r.get('ficha_url'))
        if u:
            d_by_url.setdefault(u, node_key(r))
        fam = normalize_module_name(r.get('familia') or '')
        d_by_name.setdefault((_short_name(r.get('denominacion') or ''), fam), node_key(r))

    unresolved: dict = {}
    for c_code, ciclos in (ciclos_fp or {}).items():
        c_key = code_key('C', c_code)
        if c_key not in by_key:
            continue
        for ciclo in ciclos:
            den = ciclo.get('denominacion') or ''
            d_key = (d_by_url.get(_norm_url(ciclo.get('ficha_url')))
                     or d_by_name.get((_short_name(den),
                                       normalize_module_name(ciclo.get('familia') or ''))))
            if d_key:
                add(c_key, d_key, 'cd')
            else:
                unresolved.setdefault(c_key, []).append(den)

    # D → E: requisits d'accés dels cursos E (Pla 074).
    for e_id, entry in (ce_acces or {}).items():
        for d_id in (entry or {}).get('d_ids', []):
            add(id_key(d_id), id_key(e_id), 'de')

    return {'records': by_key, 'up': up, 'down': down, 'unresolved': unresolved}


def subgraph(graph: dict, focus: str, depth: int | None = None) -> dict:
    """
    Cadena del focus: tots els ascendents (arestes cap amunt) i tots els
    descendents (cap avall), sense germans d'altres branques. Amb depth=1,
    només els veïns directes. 'warnings' = cicles D no resolts dels C dels
    quals se segueixen les arestes cap amunt.
    """
    edges: list = []
    nodes: set = {focus}
    warnings: list = []

    for direction, end in (('up', 'to'), ('down', 'from')):
        frontier = [focus]
        visited = {focus}
        while frontier:
            current = frontier.pop()
            if direction == 'up':
                warnings += [f'{current}: cicle D no resolt a ciclos_fp.json: {den}'
                             for den in graph['unresolved'].get(current, [])]
            for e in graph[direction].get(current, []):
                edges.append(e)
                nxt = e[end]
                nodes.add(nxt)
                if nxt not in visited and depth is None:
                    visited.add(nxt)
                    frontier.append(nxt)

    records = graph['records']
    return {
        'focus': focus,
        'nodes': [serialize_node(records[k]) for k in sorted(nodes)],
        'edges': edges,
        'warnings': warnings,
    }
