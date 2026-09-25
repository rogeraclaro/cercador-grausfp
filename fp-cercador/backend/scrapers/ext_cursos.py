"""
ext_cursos.py — Snapshot dels cursos FPO externs (PIMEC, Foment) (Pla 062).

`data/ext_cursos.json` és una llista; cada element és una edició, amb el mateix
format que `soc_cursos.json` més:
  font ('pimec'|'foment'), tipus, area (str de la font), certCodi (str),
  fitxaUrl (str), horariText (str, només Foment).
`estat` es guarda sempre buit: `finalitzat` es deriva en llegir (Pla 063).
"""
import json
import os
import tempfile

EXT_FILE = 'ext_cursos.json'


def is_plausible(prev_font: list, fresh: list) -> bool:
    """Una font es dóna per bona si retorna algun curs i no menys de la meitat dels anteriors."""
    return bool(fresh) and len(fresh) >= len(prev_font) / 2


def write_ext(cursos: list, data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                     dir=data_dir, delete=False) as tmp:
        json.dump(cursos, tmp, ensure_ascii=False, indent=1)
        tmp_path = tmp.name
    os.replace(tmp_path, os.path.join(data_dir, EXT_FILE))
