"""Per cada cicle D i curs E: fitxa todofp -> enllaços BOE -> XML -> Anexo V A/B."""
import html, json, os, re, sys, time, urllib.request
S, data = sys.argv[1], sys.argv[2]
recs = json.load(open(data)); recs = recs['records'] if isinstance(recs, dict) else recs
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
def get(url, path, extra=None):
    if os.path.exists(path): return open(path, encoding='utf-8', errors='replace').read()
    import subprocess
    cmd = ['curl', '-sfL', '--max-time', '90', '-o', path]
    for k, v in {**UA, **(extra or {})}.items(): cmd += ['-H', f'{k}: {v}']
    subprocess.run(cmd + [url], check=True); time.sleep(1)
    return open(path, encoding='utf-8', errors='replace').read()
UC = re.compile(r'UC\d{4}_\d')
MOD = re.compile(r'(?<![\d_/.])(\d{4})\s*[.:]\s+([^\n]+)')
def cell_text(c):
    return html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'</p>', '\n', c))).strip()
def parse(xml):
    out = {'A': [], 'B': []}
    for table in re.findall(r'<table.*?</table>', xml, re.S):
        low = table.lower()
        if 'unidades de competencia' not in low or 'correspondencia' not in low: continue
        for row in re.findall(r'<tr.*?</tr>', table, re.S):
            cells = [cell_text(c) for c in re.findall(r'<td.*?</td>', row, re.S)]
            if len(cells) != 2: continue
            a_uc, b_uc = UC.findall(cells[0]), UC.findall(cells[1])
            if a_uc and not b_uc: out['A'].append({'uc': a_uc, 'mods': MOD.findall(cells[1]), 'raw': cells[1]})
            elif b_uc and not a_uc: out['B'].append({'mods': MOD.findall(cells[0]), 'uc': b_uc, 'raw': cells[0]})
    return out
res = {}
log = open(f'{S}/rd.log', 'a')
for r in recs:
    if r.get('grado') not in ('D', 'E') or not r.get('ficha_url'): continue
    ref = r['ref']; safe = re.sub(r'[^a-z0-9]+', '_', ref.lower())
    try:
        page = get(r['ficha_url'], f'{S}/fitxa/{safe}.html', {'Referer': 'https://www.todofp.es/'})
        links = list(dict.fromkeys(re.findall(r'href="(https?://www\.boe\.es/[^"]+)"', page)))
        entry = {'grado': r['grado'], 'denominacion': r['denominacion'], 'nivel': r.get('nivel'), 'links': links, 'docs': []}
        for link in links:
            m = re.search(r'id=(BOE-A-\d{4}-\d+)', link) or re.search(r'(BOE-A-\d{4}-\d+)', link)
            if not m and '/eli/' in link:
                eli = get(link, f'{S}/boe/eli_' + re.sub(r'[^a-z0-9]+', '_', link.lower())[-60:] + '.html')
                m = re.search(r'(BOE-A-\d{4}-\d+)', eli)
            if not m: entry['docs'].append({'link': link, 'id': None}); continue
            bid = m.group(1)
            xml = get(f'https://www.boe.es/diario_boe/xml.php?id={bid}', f'{S}/boe/{bid}.xml')
            t = re.search(r'<titulo>(.*?)</titulo>', xml, re.S)
            p = parse(xml)
            entry['docs'].append({'id': bid, 'titulo': (t.group(1).strip() if t else '')[:200], 'A': p['A'], 'B': p['B']})
        res[ref] = entry
        log.write(f"{ref} links={len(links)} A={sum(len(d.get('A',[])) for d in entry['docs'])} B={sum(len(d.get('B',[])) for d in entry['docs'])}\n")
    except Exception as e:
        log.write(f'{ref} ERR {e}\n'); res[ref] = {'error': str(e), 'grado': r['grado'], 'denominacion': r['denominacion']}
    log.flush()
    json.dump(res, open(f'{S}/rd_corr.json', 'w'), ensure_ascii=False)
log.write('DONE\n')
