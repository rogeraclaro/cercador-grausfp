"""
oferta_ref.py — Clau estable `ref` de cada registre d'ofertes.json (Pla 076).

Els `id` es reassignen a cada refresc del catàleg; el `ref` no depèn de l'ordre
i és el que es guarda (favorits, avisos) i es comparteix (enllaços):

  A/B/C  codigo. Si el codi es repeteix (21 A i 21 B de pla antic surten a
         diverses famílies), codigo~<prefix PREFIX_MAP de la família>.
  D/E    <carpeta família>~<slug>: els dos últims segments de ficha_url sense
         .html. El slug sol no és únic (un cicle D pot sortir a dues famílies),
         i la família va a tots perquè el ref no canviï si un cicle n'hi apareix.

Només caràcters "unreserved" d'URL: es pot posar a ?ref= sense codificar.
"""
import re
from collections import Counter
from urllib.parse import urlsplit

from scrapers.families import PREFIX_MAP

REF_RE = re.compile(r'^[A-Za-z0-9_.~-]{1,160}$')

# Família → primer prefix de PREFIX_MAP ("Certificados de Profesionalidad" té UF i MF).
_PREFIX_BY_FAMILIA: dict = {}
for _prefix, _familia in PREFIX_MAP.items():
    _PREFIX_BY_FAMILIA.setdefault(_familia, _prefix)


def family_prefix(familia) -> str | None:
    """Prefix canònic d'una família (el de PREFIX_MAP), o None si no en té."""
    return _PREFIX_BY_FAMILIA.get(familia)


def duplicated_codes(records) -> set:
    """Codis A/B/C que surten a més d'un registre."""
    counts = Counter(r.get('codigo') for r in records
                     if r.get('grado') in ('A', 'B', 'C') and r.get('codigo'))
    return {codigo for codigo, n in counts.items() if n > 1}


def stable_ref(record: dict, dup_codes: set) -> str:
    """Ref del registre. ValueError si no se'n pot derivar un de vàlid (no s'inventa res)."""
    grado = record.get('grado')
    if grado in ('A', 'B', 'C'):
        codigo = record.get('codigo')
        if not codigo:
            raise ValueError(f"registre {grado} sense codigo: {record.get('id')}")
        ref = codigo
        if codigo in dup_codes:
            prefix = _PREFIX_BY_FAMILIA.get(record.get('familia'))
            if not prefix:
                raise ValueError(f"codi repetit {codigo} amb família sense prefix: "
                                 f"{record.get('familia')!r}")
            ref = f'{codigo}~{prefix}'
    elif grado in ('D', 'E'):
        path = urlsplit(record.get('ficha_url') or '').path
        segments = [s for s in path.removesuffix('.html').split('/') if s]
        if len(segments) < 2:
            raise ValueError(f"registre {grado} sense ficha_url vàlida: {record.get('ficha_url')!r}")
        ref = f'{segments[-2]}~{segments[-1]}'
    else:
        raise ValueError(f'grado desconegut: {grado!r}')
    if not REF_RE.match(ref):
        raise ValueError(f'ref invàlid: {ref!r}')
    return ref


def _check_unique(records) -> None:
    repetits = sorted(ref for ref, n in Counter(r['ref'] for r in records).items() if n > 1)
    if repetits:
        raise ValueError(f'refs repetits ({len(repetits)}): {", ".join(repetits[:10])}')


def assign_refs(records: list) -> list:
    """Afegeix `ref` a tots els registres (in place). Falla si n'hi ha de repetits."""
    dup = duplicated_codes(records)
    for r in records:
        r['ref'] = stable_ref(r, dup)
    _check_unique(records)
    return records


def ensure_refs(records: list) -> list:
    """
    Com assign_refs, però respecta els `ref` que ja hi siguin: només calcula els
    que falten (ofertes.json d'abans del Pla 076, fixtures de tests).
    """
    if all(r.get('ref') for r in records):
        return records
    dup = duplicated_codes(records)
    for r in records:
        if not r.get('ref'):
            r['ref'] = stable_ref(r, dup)
    _check_unique(records)
    return records
