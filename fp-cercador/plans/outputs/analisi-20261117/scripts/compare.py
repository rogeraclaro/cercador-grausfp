import json, sys, collections, openpyxl
S, D, X = sys.argv[1:4]
P = json.load(open(f'{S}/cp_parsed.json'))
bc = json.load(open(D + '/bc_loe.json')); ap = json.load(open(D + '/a_loe_pares.json'))
recs = json.load(open(D + '/ofertes.json')); recs = recs['records'] if isinstance(recs, dict) else recs
by = {r['codigo']: r for r in recs if r.get('codigo')}
wb = openpyxl.load_workbook(X, read_only=True)
sepe = {r[1]: r for r in wb['CERT_PROF_All'].iter_rows(min_row=2, values_only=True) if r and r[1]}
num = lambda codes: {c[2:6] for c in codes}
truth = {}; unreliable = []
for c, v in P.items():
    mf = num(m['code'] for m in v['mfs'] if m['code'].startswith('MF')); uc = num(v['uc_head'])
    if v['found_own'] and mf and mf == uc: truth[c] = mf
    else: unreliable.append((c, sorted(mf), sorted(uc)))
print('annexos amb MF==UC coherents (veritat fiable):', len(truth), '| dubtosos:', len(unreliable)); [print('   ', u) for u in unreliable[:14]]
# 1. bc_loe actual
ok = extra = miss = 0; L = []
for c, t in truth.items():
    o = num(bc.get(c, []))
    if o == t: ok += 1
    else:
        extra += bool(o - t); miss += bool(t - o); L.append({'cp': c, 'sobren': sorted(o - t), 'falten': sorted(t - o)})
print('\n[1] bc_loe.json vs annex: correctes', ok, '| amb UC de mes', extra, '| amb UC de menys', miss, '| UC sobrants totals', sum(len(l['sobren']) for l in L))
print('   exemples', L[:6])
json.dump(L, open(f'{S}/errors_bc_loe.json', 'w'))
# impacte B->C: enllaços falsos
print('   enllaços UC→CP falsos:', sum(len(l['sobren']) for l in L), 'de', sum(len(v) for v in bc.values()))
# 2. SEPE vs annex
a = b = 0; dif = []
for c, t in truth.items():
    if c not in sepe: continue
    s = {m.strip()[2:6] for m in str(sepe[c][5]).split(',') if m.strip().startswith('MF')}
    if s == t: a += 1
    else: b += 1; dif.append((c, 'annex-SEPE', sorted(t - s), 'SEPE-annex', sorted(s - t)))
print('\n[2] SEPE (el seu full) vs annex: iguals', a, 'diferents', b, dif[:8])
# 3. UF pares
uf_pdf = collections.defaultdict(set)
for c in truth:
    for m in P[c]['mfs']:
        for u in m.get('ufs', []): uf_pdf[u['code']].add(m['code'])
same = d3 = 0; ex = []; absent = 0
for u, mfs in uf_pdf.items():
    if u not in ap: absent += 1; continue
    if set(ap[u]) == mfs: same += 1
    else:
        d3 += 1
        if len(ex) < 6: ex.append((u, 'nosaltres', sorted(ap[u]), 'annex', sorted(mfs)))
print('\n[3] a_loe_pares vs annex: UF als annexos', len(uf_pdf), 'iguals', same, 'diferents', d3, 'absents nostres', absent, '| nostres no vistes als annexos', len(set(ap) - set(uf_pdf)))
print('   ', ex)
# 4. hores
hok = hbad = 0; hx = []; nohours = 0
for c in truth:
    hs = [m['h'] for m in P[c]['mfs']]
    if None in hs: nohours += 1; continue
    tot = sum(hs); ours = by.get(c, {}).get('duracion_horas'); sp = sepe.get(c, [None] * 13)[12]
    if ours == tot: hok += 1
    else:
        hbad += 1
        if len(hx) < 25: hx.append((c, 'annex', tot, 'nosaltres', ours, 'SEPE', sp))
print('\n[4] hores totals: coincideixen', hok, 'difereixen', hbad, 'sense hores parsejades', nohours); [print('   ', h) for h in hx]
print('   difereixen i SEPE==annex:', sum(1 for h in hx if str(h[6]) == str(h[2])), 'de', len(hx))
# 5. el seu MANT
his = collections.defaultdict(set)
for r in wb['MANT_CERT_PROF_MF'].iter_rows(min_row=2, values_only=True):
    if r and r[0] and str(r[1]).startswith('MF'): his[r[0]].add(str(r[1])[2:6])
g = w = 0
for c, s in his.items():
    if c in truth: g += s == truth[c]; w += s != truth[c]
print('\n[5] el seu MANT_CERT_PROF_MF vs annex: correctes', g, 'incorrectes', w, '| CP seus no verificables (codi inexistent o sense annex)', sum(1 for c in his if c not in truth))
hisuf = collections.defaultdict(set)
for r in wb['MANT_CERT_PROF_MF_UF'].iter_rows(min_row=2, max_row=3000, values_only=True):
    if r and r[0] and str(r[3]).startswith('UF'): hisuf[(r[0], str(r[1]))].add(r[3])
g = w = 0
for (c, mf), s in hisuf.items():
    if c in truth:
        t = next(({u['code'] for u in m['ufs']} for m in P[c]['mfs'] if m['code'] == mf), None)
        if t is None: continue
        g += s == t; w += s != t
print('   les seves UF per MF: correctes', g, 'incorrectes', w)
