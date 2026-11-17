import json, os, re, sys
S = sys.argv[1]
CP = re.compile(r'Código:\s*([A-Z]{4}\d{4}(?:_\d)?)\b')
out = {}
for fn in sorted(os.listdir(f'{S}/txt')):
    code = fn[:-4]; t = open(f'{S}/txt/{fn}', encoding='utf-8', errors='replace').read()
    base = code.split('_')[0]
    cps = [(m.start(), m.group(1)) for m in CP.finditer(t)]
    own = [p for p, c in cps if c.split('_')[0] == base]
    info = {'chars': len(t), 'cp_codes_in_pdf': sorted({c for _, c in cps}), 'found_own': bool(own)}
    start = own[0] if own else 0
    nxt = [p for p, c in cps if p > start and c.split('_')[0] != base]
    end = nxt[0] if nxt else len(t)
    # retalla també el capçal "ANEXO N" de l'annex següent
    seg = t[start:end]
    info['uc_all_pdf'] = list(dict.fromkeys(re.findall(r'UC\d{4}_\d', t)))
    info['uc_seg'] = list(dict.fromkeys(re.findall(r'UC\d{4}_\d', seg)))
    info['uc_head'] = list(dict.fromkeys(re.findall(r'Código:\s*(UC\d{4}_\d)', seg)))
    mfs = []; cur = None
    for m in re.finditer(r'Código:\s*(MF\d{4}_\d|UF\d{4}|MP\d{4})|Duración:\s*(\d+)\s*horas', seg):
        if m.group(1):
            c = m.group(1)
            if c.startswith('UF'):
                if mfs: cur = {'code': c, 'h': None}; mfs[-1]['ufs'].append(cur)
            else:
                cur = {'code': c, 'h': None, 'ufs': []}; mfs.append(cur)
        elif cur is not None and cur['h'] is None:
            cur['h'] = int(m.group(2))
    info['mfs'] = mfs
    out[code] = info
json.dump(out, open(f'{S}/cp_parsed.json', 'w'), ensure_ascii=False)
n = len(out)
print('parsed', n, 'own code found', sum(v['found_own'] for v in out.values()),
      'multi-CP PDFs', sum(len(v['cp_codes_in_pdf']) > 1 for v in out.values()),
      'empty text', sum(v['chars'] < 2000 for v in out.values()),
      'no MF heads', sum(not v['mfs'] for v in out.values()),
      'no UC heads', sum(not v['uc_head'] for v in out.values()))
print('no own code:', [c for c, v in out.items() if not v['found_own']][:30])
print('no MF:', [c for c, v in out.items() if not v['mfs']][:30])
