import json, os, subprocess, sys, time, urllib.request
S, data = sys.argv[1], sys.argv[2]
recs = json.load(open(data)); recs = recs['records'] if isinstance(recs, dict) else recs
codes = sorted(r['codigo'] for r in recs if r.get('grado') == 'C' and r.get('plan_antiguo') and r.get('codigo'))
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
     'Referer': 'https://www.todofp.es/'}
log = open(f'{S}/fetch.log', 'a')
for i, c in enumerate(codes, 1):
    out = f'{S}/txt/{c}.txt'
    if os.path.exists(out): continue
    pdf = f'{S}/pdf/{c.lower()}.pdf'
    try:
        if not os.path.exists(pdf):
            subprocess.run(['curl', '-sf', '--max-time', '120', '-o', pdf, '-H', 'User-Agent: ' + H['User-Agent'], '-H', 'Referer: ' + H['Referer'],
                            f'https://www.todofp.es/dam/todofp/certificados-profesionales/anexos/{c.lower()}.pdf'], check=True)
            time.sleep(1)
        subprocess.run(['pdftotext', '-layout', pdf, out], check=True, timeout=120)
        if c.lower() not in ('elem0311','imai0110','imar0109','adgn0110','mapu0112','eoch0108','quib0108','fmem0311','elee0109'):
            os.remove(pdf)
        log.write(f'{i} {c} ok\n')
    except Exception as e:
        log.write(f'{i} {c} ERR {e}\n')
    log.flush()
log.write('DONE\n'); log.close()
