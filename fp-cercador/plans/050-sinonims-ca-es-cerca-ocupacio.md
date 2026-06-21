# Pla 050 — Cerca d'ocupació en català: sinònims CA↔ES

> Generat: 2026-06-21 · Commit base: `2b4fa22`
> Categoria: UX / accessibilitat lingüística · Esforç: S–M · Priority: P2

## Problema

La cerca de graus per ocupació (F6) utilitza `ocupaciones.json`, que conté totes
les ocupacions en **castellà** (font: PDFs i fitxes oficials del ministeri). La
funció de cerca a `backend/app.py:797-836` fa match per paraula completa sobre
el text normalitzat (minúscules, sense accents).

Un usuari que escriu en **català** obté 0 resultats perquè:

1. **Sufixos sistemàtics divergents** (no resolts per l'eliminació d'accents):
   - `-ació` (CA) normalitza a `-acio`, que ≠ `-acion` (ES): «comunicació» ≠ «comunicacion»
   - `-itat` (CA) → `-itat` ≠ `-idad`: «electricitat» ≠ «electricidad»
   - `-ment` (CA) → `-ment` ≠ `-miento/-amiento`: «manteniment» ≠ «mantenimiento»
   - `-atge` (CA) → `-atge` ≠ `-aje`: «muntatge» ≠ «montaje»

2. **Arrels diferents** (no hi ha relació morfològica):
   - cuina ≠ cocina, esport ≠ deporte, fusteria ≠ carpinteria, etc.

El spike `.planning/spikes/003-reverse-search-feel` anota explícitament aquesta
limitació com a «millora de 2a iteració».

## Solució

Afegir a `backend/app.py`, just al bloc de la cerca d'ocupacions (a partir de
la línia 771), dos mecanismes lleugers:

1. **Diccionari estàtic `_CA_ES_TERMS`** (~40 parells) per a arrels completament
   divergents (cuina→cocina, fusteria→carpinteria, etc.).
2. **Regles de sufix `_CA_ES_SUFFIXES`** (4 parells) per als casos sistemàtics
   (`-acio`→`-acion`, `-itat`→`-idad`, `-ment`→`-miento`, `-atge`→`-aje`).

Cada token de cerca s'expan a una llista de variants (original + equivalent ES si
n'hi ha). La condició de match passa de «tot AND» a «per a cada token, almenys
una variant coincideix» — semànticament equivalent però accepta CA i ES.

## Fitxers en àmbit

| Fitxer | Canvi |
|--------|-------|
| `backend/app.py` | Afegir ~60 línies al bloc d'ocupacions |

**Fora d'àmbit:** `ocupaciones.json`, `frontend/`, `scheduler_service.py`, cap
altre fitxer backend.

## Implementació pas a pas

### Pas 1 — Afegir el diccionari i les regles de sufix

A `backend/app.py`, insereix **just abans de `_ocupaciones_cache`** (línia 774),
dins del bloc que ja té `import re as _re_ocup` i `import unicodedata as _ud_ocup`:

```python
# Diccionari CA→ES per a arrels divergents (termes comuns del domini FP).
# Claus i valors ja estan en forma normalitzada (minúscules, sense accents).
_CA_ES_TERMS: dict[str, str] = {
    # Alimentació i hoteleria
    'cuina': 'cocina', 'cuiner': 'cocinero', 'cuinera': 'cocinera',
    'pastisseria': 'pasteleria', 'hostaleria': 'hosteleria',
    'turisme': 'turismo',
    # Artesania i fusta
    'fusteria': 'carpinteria', 'fuster': 'carpintero',
    'cuir': 'cuero', 'vidre': 'vidrio',
    # Bellesa i imatge personal
    'perruqueria': 'peluqueria', 'bellesa': 'belleza',
    # Construcció i instal·lacions
    'paleta': 'albanil',
    # Comerç i màrqueting
    'comerc': 'comercio',  # comerç normalitzat: comerc (ç→c)
    'vendes': 'ventas', 'venda': 'venta',
    'publicitat': 'publicidad',
    # Educació i serveis socials
    'infermeria': 'enfermeria', 'infermer': 'enfermero', 'infermera': 'enfermera',
    # Esport i activitats físiques
    'esport': 'deporte', 'esports': 'deportes',
    # Finances i assegurances
    'assegurances': 'seguros', 'asseguranca': 'seguro',  # ç→c
    'inmobiliaria': 'inmobiliaria',  # immobiliària→inmobiliaria (doble m→m)
    # Imatge i so
    'imatge': 'imagen',
    # Seguretat i emergències
    'bombers': 'bomberos',
    # Arts i espectacle
    'dansa': 'danza', 'teatre': 'teatro', 'cinema': 'cine',
    'arts': 'artes', 'art': 'arte',
    'grafic': 'grafico',  # gràfic→grafic
    # Transport
    'transport': 'transporte',
    # Muntatge i instal·lació
    'muntatge': 'montaje', 'muntador': 'montador',
}

# Regles de sufix CA→ES (sobre text ja normalitzat, en ordre d'aplicació).
# Exemple: 'comunicacio' → 'comunicacion', 'electricitat' → 'electricidad'.
_CA_ES_SUFFIXES: list[tuple[str, str]] = [
    ('acio', 'acion'),   # -ació → -ación   (comunicació, educació, animació…)
    ('itat', 'idad'),    # -itat → -idad     (electricitat, seguretat, activitat…)
    ('ment', 'miento'),  # -ment → -miento   (manteniment, funcionament…)
    ('atge', 'aje'),     # -atge → -aje      (muntatge, emmagatzematge…)
]


def _expand_token(t: str) -> list[str]:
    """Retorna [t] + variants ES si t sembla un terme en català.

    Ordre: primer el diccionari d'arrels (prioritat), després les regles de sufix.
    Si es troba coincidència al diccionari, NO s'apliquen les regles de sufix
    (evita dobles transformacions).
    """
    if t in _CA_ES_TERMS:
        es = _CA_ES_TERMS[t]
        return [t, es] if es != t else [t]
    for ca_sfx, es_sfx in _CA_ES_SUFFIXES:
        if t.endswith(ca_sfx) and len(t) > len(ca_sfx) + 2:
            es_form = t[:-len(ca_sfx)] + es_sfx
            return [t, es_form]
    return [t]
```

**Nota sobre `ç`**: `_norm_ocup()` ja elimina els diacrítics via NFD, de manera
que «comerç» → «comerc» i «assegurança» → «asseguranca» **abans** que arribin al
diccionari. Les claus del diccionari han d'estar en forma normalitzada (sense `ç`,
sense accents). Comprova que totes les claus del diccionari siguin ASCII purs.

### Pas 2 — Modificar `api_ocupaciones()` per usar `_expand_token`

A la funció `api_ocupaciones()` (`app.py:804`), substitueix el bloc que construeix
`patterns`:

**Codi actual** (app.py:821):
```python
    patterns = [_re_ocup.compile(r'\b' + _re_ocup.escape(t) + r'\b') for t in tokens]

    grouped: dict = {}
    for e in entries:
        hay = e.get('norm', '')
        if all(p.search(hay) for p in patterns):
```

**Codi nou**:
```python
    # Cada token s'expandeix a [original, equivalent_ES] (si és terme en català).
    token_groups = [_expand_token(t) for t in tokens]
    # Compile patterns per grup: per a cada grup, almenys una variant ha de coincidir.
    compiled_groups = [
        [_re_ocup.compile(r'\b' + _re_ocup.escape(v) + r'\b') for v in grp]
        for grp in token_groups
    ]

    grouped: dict = {}
    for e in entries:
        hay = e.get('norm', '')
        if all(any(p.search(hay) for p in grp) for grp in compiled_groups):
```

La resta de la funció (construcció del dict `grouped`, l'ordenació i el `return`)
no canvia.

### Pas 3 — Verificació manual ràpida (sense xarxa)

Des de la carpeta `backend/` (amb el venv actiu i `ocupaciones.json` present al VPS
o en local):

```bash
python3 -c "
from app import _norm_ocup, _expand_token
tests = [
    ('comunicacio', ['comunicacio', 'comunicacion']),
    ('electricitat', ['electricitat', 'electricidad']),
    ('manteniment', ['manteniment', 'mantenimiento']),
    ('muntatge', ['muntatge', 'montaje']),
    ('cuina', ['cuina', 'cocina']),
    ('infermeria', ['infermeria', 'enfermeria']),
    ('soldador', ['soldador']),   # castellà pur, sense expansió
    ('comerc', ['comerc', 'comercio']),
]
for t, expected in tests:
    result = _expand_token(t)
    ok = '✓' if result == expected else f'✗ got {result}'
    print(f'{t}: {ok}')
"
```

Expected: tots ✓.

### Pas 4 — Tests unitaris

Afegeix als tests existents (o crea `backend/tests/test_ocupaciones_synonyms.py`):

```python
import pytest
# Importa directament per no arrencar Flask
import importlib, sys, types

# Stub mínim per importar la part de sinonims sense tota l'app
# (alternativa: si els tests ja importaven app, usa el client de test habitual)

def test_expand_token_suffix_acio():
    from app import _expand_token
    assert _expand_token('comunicacio') == ['comunicacio', 'comunicacion']

def test_expand_token_suffix_itat():
    from app import _expand_token
    assert _expand_token('electricitat') == ['electricitat', 'electricidad']

def test_expand_token_suffix_ment():
    from app import _expand_token
    assert _expand_token('manteniment') == ['manteniment', 'mantenimiento']

def test_expand_token_suffix_atge():
    from app import _expand_token
    assert _expand_token('muntatge') == ['muntatge', 'montaje']

def test_expand_token_dict_cuina():
    from app import _expand_token
    assert _expand_token('cuina') == ['cuina', 'cocina']

def test_expand_token_no_expansion():
    from app import _expand_token
    assert _expand_token('soldador') == ['soldador']

def test_expand_token_already_es():
    from app import _expand_token
    # 'comunicacion' ja és castellà — cap suffix CA coincideix
    assert _expand_token('comunicacion') == ['comunicacion']
```

Execució:
```bash
cd backend && python -m pytest tests/ -v
```
Expected: tots verds, incloent els nous.

### Pas 5 — Test d'integració manual (opcional però recomanat)

Si hi ha `ocupaciones.json` disponible (localment o al VPS), verifica:

```bash
# Castellà (comportament previ — no ha de trencar-se)
curl "http://localhost:5001/api/ocupaciones?q=soldador"
# → n > 0

# Català (el que aquest pla arregla)
curl "http://localhost:5001/api/ocupaciones?q=infermeria"
# → n > 0 (s'ha d'expandir a 'enfermeria')

curl "http://localhost:5001/api/ocupaciones?q=electricitat"
# → n > 0 (s'ha d'expandir a 'electricidad')

curl "http://localhost:5001/api/ocupaciones?q=comunicacio"
# → n > 0 (s'ha d'expandir a 'comunicacion')

# Mix (castellà i català en una mateixa query)
curl "http://localhost:5001/api/ocupaciones?q=tecnic+electricitat"
# → n > 0
```

## Criteris de done

```bash
# 1. Nous símbols presents
grep "_CA_ES_TERMS\|_CA_ES_SUFFIXES\|_expand_token\|token_groups" backend/app.py

# 2. El patró de match antic (patterns = [...]) substituït
# Ha de retornar 0 línies (la variable 'patterns' del match anterior ja no existeix
# en el context d'api_ocupaciones):
grep "patterns = \[_re_ocup.compile" backend/app.py

# 3. Tests passen
cd backend && python -m pytest tests/ -v

# 4. Verificació manual de _expand_token (pas 3 d'aquest pla)
```

## STOP conditions

- **Si trobes que `_norm_ocup()` ja modifica la ç o la l·l** d'una manera
  inesperada, para i reporta. Potser les claus del diccionari cal ajustar-les.
- **Si la regla de sufix `-ment → -miento` produeix falsos positius** (paraules
  castellanes que acabin en `-ment` i no siguin catalanes), revisa la longitud
  mínima (`len(t) > len(ca_sfx) + 2`) o afegeix una whitelist negativa.
- **No afegeixis dependències noves** (cap `langdetect`, cap `translate`). Tota
  la lògica ha de ser diccionari + regex estàtics.

## Notes de manteniment

- Si s'afegeixen famílies professionals noves al catàleg FP, comprovar si els
  seus noms en català necessiten entrades al diccionari.
- La llista `_CA_ES_TERMS` és intencionadament petita (~40 entrades). Si apareixen
  falsos positius (paraules no-FP que coincideixen per accident), afegir-les a
  una whitelist negativa dins `_expand_token`.
- Les regles de sufix s'apliquen en ordre; la primera coincidència guanya. Si
  en el futur es detecta que una regla és massa àmplia, es pot restringir afegint
  una longitud mínima o un prefix obligatori.
