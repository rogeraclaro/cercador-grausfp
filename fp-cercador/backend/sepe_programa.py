"""
sepe_programa.py — Lector del text dels programes formatius del SEPE (Pla 100).

Funcions pures: reben el text que pdfplumber treu del PDF del programa i en
retornen un dict. No fan xarxa ni llegeixen fitxers.

El SEPE fa servir tres plantilles (plans/100, «Diagnosi»):

  - modern (vigència des del 2021): apartats amb títol («Objetivo general»,
    «Relación de módulos de formación», «Duración de la formación»…);
  - «po» (2016–2018, programes per a persones ocupades): camps numerats
    («4. Objetivo General:», «6. Duración: … Distribución de horas»);
  - antic (abans del 2015): numerat i variable («5. Objetivo general:»).

El text és en castellà i es desa tal qual (no es tradueix). Qui el mostri l'ha de
tractar com a text pla.
"""
import re

_RE_PAGINA = re.compile(r'^Página\s+\d+(\s+de\s+\d+)?$', re.I)
_RE_NUM_SOL = re.compile(r'^\d{1,3}$')
_RE_WS = re.compile(r'\s+')

# Títols d'apartat de la plantilla moderna (línia sencera). Un apartat acaba on en
# comença un altre d'aquesta llista; després de «DESARROLLO MODULAR» no es llegeix res.
_SECCIONS = (
    'Objetivo general',
    'Relación de módulos de formación',
    'Modalidades de impartición',
    'Modalidad de impartición',
    'Duración de la formación',
    'Requisitos de acceso del alumnado',
    'Justificación de los requisitos del alumnado',
    'Prescripciones de formadores y tutores',
    'Justificación de las prescripciones de formadores y tutores',
    'Requisitos mínimos de espacios, instalaciones y equipamientos',
    'Otras especificaciones',
    'Vinculaciones con capacitaciones profesionales',
    'Ocupaciones y puestos de trabajo relacionados',
    'Requisitos necesarios para el ejercicio profesional',
    'Requisitos oficiales de las entidades o centros de formación',
    'Centro Móvil',
    'DESARROLLO MODULAR',
)

_RE_MODUL = re.compile(r'^Módulo\s+(\d+)\b\s*(.*)$', re.I)
_RE_HORES_FI = re.compile(r'(?:^|\s)(\d+(?:[.,]\d+)?)\s*horas?$', re.I)
_RE_TUTORIES = re.compile(r'Duración total de las tutorías presenciales:\s*(\d+(?:[.,]\d+)?)\s*horas', re.I)
_RE_PRESENCIAL_MIXTA = re.compile(r'Duración total de la formación presencial:\s*(\d+(?:[.,]\d+)?)\s*horas', re.I)
_RE_TOTAL_MODERN = re.compile(r'^(\d+(?:[.,]\d+)?)\s*horas$', re.I)

# Plantilla moderna, «Requisitos de acceso del alumnado»: taula de dues columnes. El
# rètol de l'esquerra («Acreditaciones / titulaciones», «Experiencia profesional»…) surt
# partit a l'inici de les primeres línies del text de la dreta.
_REQ_RETOLS = (
    (re.compile(r'^Acreditaciones\b\s*'), 'titulacio', re.compile(r'^/\s*titulaciones\b\s*')),
    (re.compile(r'^Experiencia\b\s*'), 'experiencia', re.compile(r'^profesional\b\s*')),
    (re.compile(r'^Otros\b\s*'), 'altres', None),
    (re.compile(r'^Modalidad(\s+de)?\b\s*'), 'modalitat', re.compile(r'^(de\s+)?(teleformación|mixta)\b\s*', re.I)),
)

# Plantilles numerades («4. Objetivo General:», «5. Objetivo general:»).
_RE_OBJ_NUM = re.compile(r'^\d+\.\s*Objetivo\s+general\s*:?\s*(.*)$', re.I)
_RE_APARTAT_NUM = re.compile(r'^\d+\.(\d+\.?)*\s*\S')
_RE_PO_PRES = re.compile(r'^Presencial\s*:[\s.…]*(\d+(?:[.,]\d+)?)', re.I)
_RE_PO_TOTAL = re.compile(r'^Horas totales\s*:?\s*(\d+(?:[.,]\d+)?)', re.I)
_RE_PO_TELE = re.compile(r'^Teleformaci[oó]n\s*:[\s.…]*(\d+(?:[.,]\d+)?)', re.I)

TOLERANCIA_HORES = 1


def _num(text):
    value = float(text.replace(',', '.'))
    return int(value) if value.is_integer() else value


def _linies(text: str) -> list:
    """Línies netes, sense buides ni peus de pàgina «Página N»."""
    out = []
    for line in (text or '').splitlines():
        line = _RE_WS.sub(' ', line).strip()
        if line and not _RE_PAGINA.match(line):
            out.append(line)
    return out


def _uneix(lines: list):
    """Junta línies partides; una línia que comença amb guió o pic obre línia nova."""
    parts: list = []
    for line in lines:
        # Un guió sol en una línia («-» i el text a la següent) també compta com a pic.
        if not parts or (line[:1] in '-•–·' and parts[-1] not in ('-', '•', '–', '·')):
            parts.append(line)
        elif parts[-1].endswith('-') and line[:1].islower() and parts[-1][-2:-1].isalpha():
            parts[-1] = f'{parts[-1]}{line}'      # «tutores-» + «formadores»
        else:
            parts[-1] = f'{parts[-1]} {line}'
    text = '\n'.join(parts).strip()
    return text or None


def detect_format(text: str):
    """'modern' | 'po' | 'antic' | None."""
    if not text:
        return None
    upper = text.upper()
    if 'IDENTIFICACIÓN DE LA ESPECIALIDAD' in upper and 'Objetivo general' in text:
        return 'modern'
    if not any(_RE_OBJ_NUM.match(line) for line in _linies(text)):
        return None
    # La frase pot sortir partida en dues línies («…A TRABAJADORES / OCUPADOS»).
    if 'PRIORITARIAMENTE A TRABAJADORES' in upper or 'Distribución de hora' in text:
        return 'po'
    return 'antic'


# ---------------------------------------------------------------------------
# Plantilla moderna
# ---------------------------------------------------------------------------

def _seccions(lines: list) -> dict:
    """{títol d'apartat en minúscules: [línies]} fins a «DESARROLLO MODULAR»."""
    out: dict = {}
    actual = None
    for line in lines:
        key = line.lower()
        # Comparació exacta: «modalidad de impartición» en minúscula és text, no un títol.
        if line in _SECCIONS:
            if key == 'desarrollo modular':
                break
            actual = key
            out.setdefault(actual, [])
        elif actual:
            out[actual].append(line)
    return out


def _reparteix_simetric(lines: list, idx: list):
    """[(abans, despres)] per mòdul suposant la cel·la del nom centrada en vertical:
    la línia «Módulo N … horas» queda al mig, amb tantes línies del nom abans com després.
    Les línies entre dos mòduls es reparteixen començant pel primer. None si no quadra."""
    parts = []
    abans = idx[0]                      # línies del nom del primer mòdul per sobre
    for k, i in enumerate(idx):
        fi = idx[k + 1] if k + 1 < len(idx) else len(lines)
        entre = fi - i - 1              # línies fins al mòdul següent (o fins al final)
        if abans > entre:
            return None
        parts.append((abans, abans))
        abans = entre - abans
    return parts if abans == 0 else None


def _reparteix_minuscules(lines: list, idx: list):
    """[(abans, despres)] per a noms en majúscules i minúscules, quan el nom no surt centrat:
    entre dos mòduls, les línies que comencen en minúscula continuen el nom del de dalt
    i la resta comencen el del de baix."""
    parts = []
    abans = idx[0]
    for k, i in enumerate(idx):
        fi = idx[k + 1] if k + 1 < len(idx) else len(lines)
        gap = lines[i + 1:fi]
        despres = len(gap) if k + 1 == len(idx) else next(
            (n for n, line in enumerate(gap) if not line[:1].islower()), len(gap))
        parts.append((abans, despres))
        abans = len(gap) - despres
    return parts


def _construeix(lines: list, idx: list, parts: list):
    moduls = []
    for i, (abans, despres) in zip(idx, parts):
        mig = _RE_MODUL.match(lines[i]).group(2)
        # Les hores solen anar a la línia del «Módulo N»; si no, a la línia del nom que les porti.
        m = _RE_HORES_FI.search(mig)
        hores = _num(m.group(1)) if m else None
        if m:
            mig = mig[:m.start()].strip()
        noms = lines[i - abans:i] + ([mig] if mig else []) + lines[i + 1:i + 1 + despres]
        if hores is None:
            for n, text in enumerate(noms):
                m = _RE_HORES_FI.search(text)
                if m:
                    hores, noms[n] = _num(m.group(1)), text[:m.start()].strip()
                    break
        nom = ' '.join(t for t in noms if t)
        if hores is None or not nom or nom[:1].islower():   # un nom no comença a mitja frase
            return None
        moduls.append({'nom': nom, 'hores': hores})
    return moduls


def parse_moduls(lines: list):
    """[{nom, hores}] de la taula «Relación de módulos de formación», o None si no s'entén.

    pdfplumber escriu la cel·la del nom en diverses línies al voltant de la del «Módulo N».
    Es prova primer el repartiment de cel·la centrada i, si no quadra, el de majúscules
    (vegeu les dues funcions _reparteix_*)."""
    idx = [i for i, line in enumerate(lines) if _RE_MODUL.match(line)]
    if not idx or [int(_RE_MODUL.match(lines[i]).group(1)) for i in idx] != list(range(1, len(idx) + 1)):
        return None
    for reparteix in (_reparteix_simetric, _reparteix_minuscules):
        parts = reparteix(lines, idx)
        moduls = _construeix(lines, idx, parts) if parts else None
        if moduls:
            return moduls
    return None


def _requisits(lines: list):
    """[{tipus, text}] dels requisits d'accés (titulacio, experiencia, altres).

    La fila «Modalidad de teleformación/mixta» (destreses per fer servir la plataforma)
    no es desa: és un text genèric de totes les especialitats en línia.
    """
    if not lines:
        return None
    items: list = []
    actual = None
    cont = None
    cont_linies = 0
    for line in lines:
        retol = next(((rx, tipus, c) for rx, tipus, c in _REQ_RETOLS if rx.match(line)), None)
        if retol:
            rx, tipus, cont = retol
            line = rx.sub('', line, count=1)
            cont_linies = 2
            if not (actual and actual['tipus'] == tipus):   # rètol repetit en canviar de pàgina
                actual = {'tipus': tipus, 'linies': []}
                items.append(actual)
        elif cont is not None and cont_linies > 0:
            cont_linies -= 1
            if cont.match(line):
                line = cont.sub('', line, count=1)
                cont_linies = 0
        if actual is None:
            actual = {'tipus': 'text', 'linies': []}
            items.append(actual)
        if line:
            actual['linies'].append(line)
    out = [{'tipus': it['tipus'], 'text': _uneix(it['linies'])} for it in items
           if it['tipus'] != 'modalitat' and it['linies']]
    return out or None


def _parse_modern(lines: list) -> dict:
    sec = _seccions(lines)
    durada = sec.get('duración de la formación', [])
    durada_text = ' '.join(durada)
    tutories = _RE_TUTORIES.search(durada_text)
    presencial = _RE_PRESENCIAL_MIXTA.search(durada_text)
    total = next((_num(m.group(1)) for m in map(_RE_TOTAL_MODERN.match, durada) if m), None)
    return {
        'objectiu': _uneix(sec.get('objetivo general', [])),
        'moduls': parse_moduls(sec.get('relación de módulos de formación', [])),
        '_taula_moduls': any(_RE_MODUL.match(line) for line in sec.get('relación de módulos de formación', [])),
        'requisits_acces': _requisits(sec.get('requisitos de acceso del alumnado', [])),
        'tutories_presencials_h': _num(tutories.group(1)) if tutories else None,
        'vinculacions': _uneix(sec.get('vinculaciones con capacitaciones profesionales', [])),
        'hores_presencial': _num(presencial.group(1)) if presencial else None,
        'hores_teleformacio': None,
        '_hores_total': total,
    }


# ---------------------------------------------------------------------------
# Plantilles numerades («po» i antiga)
# ---------------------------------------------------------------------------

def _objectiu_numerat(lines: list):
    for i, line in enumerate(lines):
        m = _RE_OBJ_NUM.match(line)
        if not m:
            continue
        out = [m.group(1)] if m.group(1) else []
        for seg in lines[i + 1:]:
            if _RE_APARTAT_NUM.match(seg):
                break
            out.append(seg)
        return _uneix(out)
    return None


def _hores_po(lines: list) -> tuple:
    """(presencial, teleformació) només quan el programa reparteix les hores entre totes dues.

    «Modalidad: Indistinta» posa les hores totals a cada línia (presencial 32, teleformació 32):
    vol dir «en qualsevol de les dues», no un repartiment, i llavors no es desa res. Tampoc
    quan una val 0: la modalitat del catàleg ja ho diu."""
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith('Distribución de hora'))
    except StopIteration:
        return None, None
    total = next((_num(m.group(1)) for m in map(_RE_PO_TOTAL.match, lines[max(start - 3, 0):start]) if m), None)
    pres = tele = None
    for line in lines[start + 1:start + 6]:
        m = _RE_PO_PRES.match(line)
        if m and pres is None:
            pres = _num(m.group(1))
        m = _RE_PO_TELE.match(line)
        if m and tele is None:
            tele = _num(m.group(1))
    if not (pres and tele and total is not None and abs(pres + tele - total) <= TOLERANCIA_HORES):
        return None, None
    return pres, tele


def _buit() -> dict:
    return {'objectiu': None, 'moduls': None, 'requisits_acces': None, 'tutories_presencials_h': None,
            'vinculacions': None, 'hores_presencial': None, 'hores_teleformacio': None}


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

def parse_programa(text: str, hores_cataleg=None):
    """Contingut del programa, o None si no s'hi reconeix cap plantilla ni cap objectiu.

    Retorna {format, objectiu, moduls: [{nom, hores}] | None, moduls_ok, moduls_error,
    requisits_acces: [{tipus, text}] | None, tutories_presencials_h, vinculacions,
    hores_presencial, hores_teleformacio}. Els camps que no hi són valen None.

    Validació: si hi ha mòduls, la suma d'hores ha de coincidir (±1) amb `hores_cataleg`
    (o, sense, amb la durada total que diu el mateix programa). Si no quadra, els mòduls
    es descarten (`moduls_ok` False i `moduls_error` = 'suma') i es conserva la resta.
    `moduls_error` = 'format' vol dir que hi ha la taula però no s'ha pogut llegir.
    """
    fmt = detect_format(text)
    if fmt is None:
        return None
    lines = _linies(text)
    out = _buit()
    total_pdf = None
    if fmt == 'modern':
        out.update(_parse_modern(lines))
        total_pdf = out.pop('_hores_total')
        taula_moduls = out.pop('_taula_moduls')
    else:
        if fmt == 'antic':
            lines = [line for line in lines if not _RE_NUM_SOL.match(line)]   # números de pàgina
        out['objectiu'] = _objectiu_numerat(lines)
        if fmt == 'po':
            out['hores_presencial'], out['hores_teleformacio'] = _hores_po(lines)

    moduls_error = None
    if fmt == 'modern' and out['moduls'] is None and taula_moduls:
        moduls_error = 'format'
    if out['moduls']:
        referencia = hores_cataleg if hores_cataleg is not None else total_pdf
        suma = sum(m['hores'] for m in out['moduls'])
        if referencia is None or abs(suma - referencia) > TOLERANCIA_HORES:
            out['moduls'] = None
            moduls_error = 'suma'
    out['moduls_ok'] = bool(out['moduls'])
    out['moduls_error'] = moduls_error

    if not out['objectiu'] and not out['moduls']:
        return None
    return {'format': fmt, **out}
