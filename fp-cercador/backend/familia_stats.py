"""
familia_stats.py — xifres d'una família professional per a /familia/<prefix> (Pla 088):
graus per lletra, centres per comunitat, novetats, sortides professionals més freqüents i
cursos FPO que comencen aviat. Funcions pures: sense Flask ni fitxers.
"""
from collections import Counter
from datetime import date, timedelta

GRADOS = ('A', 'B', 'C', 'D', 'E')
MAX_NOVETATS = 8
MAX_OCUPACIONS = 12
MAX_FPO = 6
FPO_DIES = 60


def _ocup_key(rec: dict):
    """La mateixa clau que app._grau_context: els C per codi; D i E per fitxa o, si no, per id."""
    if rec.get('grado') == 'C':
        return ('C', rec.get('codigo'))
    return ('url', rec['ficha_url']) if rec.get('ficha_url') else ('id', rec.get('id'))


def _is_occupation(name) -> bool:
    """ocupaciones.json porta, barrejades amb els oficis, frases senceres de les fitxes
    («Tu actividad está regulada por…») i trossos mal tallats («) geriatría, etc»)."""
    return (isinstance(name, str) and name[:1].isalpha() and len(name) <= 60
            and len(name.split()) <= 8)


def _novetats(familia: str, history: list) -> list:
    """Altes i baixes de la família, de la més recent a la més antiga."""
    out = []
    for entry in history or []:
        changes = entry.get('changes') or {}
        data = (entry.get('ts') or '')[:10]
        for tipus, meta_key, names_key in (('alta', 'new_by_grado_meta', 'new_by_grado'),
                                           ('baixa', 'removed_by_grado_meta', 'removed_by_grado')):
            names = changes.get(names_key)
            for grado in GRADOS:
                # Una entrada amb metadades però sense la llista de noms és una càrrega inicial
                # (tot el catàleg d'un cop), no una novetat.
                listed = set((names or {}).get(grado) or []) if names is not None else None
                for item in (changes.get(meta_key) or {}).get(grado) or []:
                    if item.get('familia') == familia and (listed is None or item.get('denominacio') in listed):
                        out.append({'data': data, 'tipus': tipus, 'grado': grado,
                                    'denominacio': item.get('denominacio')})
    out.sort(key=lambda n: n['data'], reverse=True)   # estable: dins d'un dia, altes abans que baixes i A→E
    return out[:MAX_NOVETATS]


def build_familia_stats(familia: str, records: list, ocupacions: dict | None = None,
                        oferta_centres: dict | None = None, centres_index: dict | None = None,
                        history: list | None = None) -> dict:
    """
    `records`: els graus de la família. `ocupacions`: {clau: [noms]} (seo['ocupacions']).
    `oferta_centres`: {ref: [id de centre]}. `centres_index`: {id: {ccaa, …}}.
    `history`: refresh_history.json (la més recent primer).
    """
    per_grado = Counter(r.get('grado') for r in records if r.get('grado') in GRADOS)

    # Centres diferents: un centre que imparteix tres graus de la família compta un cop.
    centre_ids = set()
    for r in records:
        centre_ids.update((oferta_centres or {}).get(r.get('ref')) or [])
    per_ccaa = Counter()
    for cid in centre_ids:
        ccaa = ((centres_index or {}).get(cid) or {}).get('ccaa')
        if ccaa:
            per_ccaa[ccaa] += 1

    ocup = Counter()
    for r in records:
        ocup.update({o for o in (ocupacions or {}).get(_ocup_key(r)) or [] if _is_occupation(o)})

    return {
        'total': len(records),
        'per_grado': {g: per_grado.get(g, 0) for g in GRADOS},
        'centres': {'total': len(centre_ids), 'n_ccaa': len(per_ccaa),
                    'per_ccaa': sorted(per_ccaa.items(), key=lambda kv: (-kv[1], kv[0]))},
        'novetats': _novetats(familia, history or []),
        # Empats: per ordre alfabètic, perquè la llista no canviï d'un dia per l'altre.
        'ocupacions': sorted(ocup.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:MAX_OCUPACIONS],
    }


def fpo_soon(prefix: str, cursos: list, avui: date, dies: int = FPO_DIES) -> dict:
    """
    Cursos FPO de la família que comencen d'avui a `dies` dies. `cursos`: files de
    fpo_agenda.row (la família de l'FPO és el mateix prefix de tres lletres).
    Torna {'cursos': [fins a 6], 'total': n}.
    """
    first, last = avui.isoformat(), (avui + timedelta(days=dies)).isoformat()
    hits = [c for c in cursos or []
            if (c.get('familia') or {}).get('codi') == prefix and c.get('dataInici')
            and first <= c['dataInici'] <= last]
    hits.sort(key=lambda c: (c['dataInici'], c.get('idCurs') or ''))
    return {'cursos': hits[:MAX_FPO], 'total': len(hits)}
