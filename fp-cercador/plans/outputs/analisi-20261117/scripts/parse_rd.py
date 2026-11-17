import html, json, re, sys, collections
S, D = sys.argv[1], sys.argv[2]
UC = re.compile(r'UC\d{4}_\d'); MOD = re.compile(r'(?<![\d_/.A-Z])[O0]?(\d{3,4})\s*[.:]?\s*([A-ZÁÉÍÓÚÑ][^\n]+)')
def cell_text(c):
    c = re.sub(r'<br\s*/?>|</p>', '\n', c)
    return html.unescape(re.sub(r'<[^>]+>', '', c)).strip()
def parse(xml):
    out = {'A': [], 'B': [], 'titles': len(re.findall(r'Título Profesional Básico en', xml[:200000]))}
    for table in re.findall(r'<table.*?</table>', xml, re.S):
        rows = [[cell_text(c) for c in re.findall(r'<t[dh]\b.*?</t[dh]>', row, re.S)] for row in re.findall(r'<tr.*?</tr>', table, re.S)]
        head = ' '.join(' '.join(r) for r in rows[:3]).lower()
        if 'convalidables' in head and 'unidades de competencia' in head: kind = 'A'
        elif 'acreditables' in head and 'superados' in head: kind = 'B'
        else: continue
        last = None
        for cells in rows:
            if len(cells) == 1 and last is not None:
                cells = [last, cells[0]] if kind == 'B' else [cells[0], last]   # rowspan
            if len(cells) != 2: continue
            ucs, mods = (cells[0], cells[1]) if kind == 'A' else (cells[1], cells[0])
            u, m = UC.findall(ucs), MOD.findall(mods)
            if not u: continue
            last = cells[0] if kind == 'B' else cells[1]
            out[kind].append({'uc': u, 'mods': m, 'raw': mods[:200]})
    return out
res = json.load(open(f'{S}/rd_corr.json'))
cache = {}
final = {}
use = collections.Counter(bid for e in res.values() for bid in {d.get('id') for d in e.get('docs', []) if d.get('id')})
def P(bid):
    if bid not in cache: cache[bid] = parse(open(f'{S}/boe/{bid}.xml', encoding='utf-8', errors='replace').read())
    return cache[bid]
for ref, e in res.items():
    if 'docs' not in e: continue
    A = []; B = []; ids = []; shared = []
    for d in e['docs']:
        bid = d.get('id')
        if not bid or bid in ids or bid in shared: continue
        p = P(bid)
        if use[bid] > 3:
            if p['A'] or p['B']: shared.append(bid)
            continue
        ids.append(bid)
        A += [dict(r, doc=bid) for r in p['A']]; B += [dict(r, doc=bid) for r in p['B']]
    final[ref] = {'grado': e['grado'], 'nivel': e.get('nivel'), 'denominacion': e['denominacion'], 'ids': ids, 'shared': shared, 'A': A, 'B': B, 'multi': False}
json.dump(final, open(f'{S}/rd_final.json', 'w'), ensure_ascii=False)
st = collections.Counter(); none = []
for ref, f in final.items():
    k = (f['grado'], f['nivel'])
    st[k, '0 total'] += 1
    if f['multi']: st[k, '3 decret compartit (multi-titol)'] += 1
    elif f['A']: st[k, '1 amb V A'] += 1
    if f['B'] and not f['multi']: st[k, '2 amb V B'] += 1
    if not f['A'] and not f['B']: st[k, '4 sense taula'] += 1; none.append((k, f['denominacion'][:55], f['ids']))
    st[k, '5 files A sense modul'] += sum(1 for r in f['A'] if not r['mods'])
for k in sorted(st, key=str): print(k, st[k])
print('decrets compartits amb taules:', {b: (use[b], len(P(b)['A']), len(P(b)['B'])) for b in use if use[b] > 3 and (P(b)['A'] or P(b)['B'])})
print('cicles sense taula propia pero amb decret compartit amb taules', sum(1 for f in final.values() if not f['A'] and f['shared']))
print('sense taula:'); [print('  ', x) for x in none[:40]]
bc = json.load(open(D + '/bc_loe.json')); cf = json.load(open(D + '/ciclos_fp.json'))
ok = {r: f for r, f in final.items() if f['A'] and not f['multi']}
ucs = {u for f in ok.values() for r in f['A'] for u in r['uc']}
our = {u for v in bc.values() for u in v}
print('UC amb correspondencia', len(ucs), '| UC dels CP LOE', len(our), 'cobertes', len(our & ucs))
print('CP LOE amb >=1 UC convalidable', sum(1 for v in bc.values() if set(v) & ucs), 'de', len(bc), '| tots els UC', sum(1 for v in bc.values() if v and set(v) <= ucs), '| ciclos_fp>0:', sum(1 for v in cf.values() if v))
both = sum(1 for c, v in bc.items() if set(v) & ucs and cf.get(c)); onlyboe = [c for c, v in bc.items() if set(v) & ucs and not cf.get(c)]; onlytodo = [c for c, v in bc.items() if cf.get(c) and not set(v) & ucs]
print('tots dos', both, 'nomes BOE', len(onlyboe), onlyboe[:8], 'nomes todofp', len(onlytodo), onlytodo[:12])
raw = [(f['denominacion'][:40], r['raw'][:110]) for f in final.values() for r in f['A'] if not r['mods']][:8]; print(raw)
