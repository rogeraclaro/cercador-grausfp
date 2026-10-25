"""
test_pipeline_remap.py — d_modulos.json i ce_acces.json van per id de registre, i els id
es reassignen a cada refresc. Si el scraper d'un d'ells falla, el pipeline conserva el
fitxer anterior traduint-ne els id vells als nous per ficha_url (única per als D i E).
"""
from scrapers.pipeline import id_remap_by_ficha, remap_ce_acces, remap_d_modulos

URL = "https://www.todofp.es/{}.html"


def rec(id_, grado, slug):
    return {"id": id_, "grado": grado, "ficha_url": URL.format(slug)}


OLD = [rec(10, "C", "c1"), rec(20, "D", "d1"), rec(21, "D", "d2"), rec(22, "D", "d3"), rec(30, "E", "e1")]
# Un registre nou abans dels D: tots els id es desplacen; d3 desapareix del catàleg.
NEW = [rec(10, "C", "c1"), rec(11, "C", "c2"), rec(21, "D", "d1"), rec(22, "D", "d2"), rec(31, "E", "e1")]


def test_remap_tradueix_els_id_d_i_e_per_ficha_url():
    assert id_remap_by_ficha(OLD, NEW) == {20: 21, 21: 22, 30: 31}


def test_remap_ignora_els_altres_graus():
    # 10 és un C: el seu id no es tradueix encara que coincideixi.
    assert 10 not in id_remap_by_ficha(OLD, NEW)


def test_d_modulos_conserva_les_entrades_amb_els_id_nous():
    old_index = {"20": {"modulos": ["m1"]}, "21": {"modulos": ["m2"]}, "22": {"modulos": ["m3"]}}
    assert remap_d_modulos(old_index, id_remap_by_ficha(OLD, NEW)) == {
        "21": {"modulos": ["m1"]},
        "22": {"modulos": ["m2"]},
    }


def test_ce_acces_tradueix_la_clau_e_i_els_d_ids():
    old_index = {"30": {"d_ids": [20, 22, 21], "unmatched": ["X"]}}
    assert remap_ce_acces(old_index, id_remap_by_ficha(OLD, NEW)) == {
        "31": {"d_ids": [21, 22], "unmatched": ["X"]},
    }


def test_sense_cataleg_anterior_no_conserva_res():
    assert remap_d_modulos({"20": {"modulos": []}}, id_remap_by_ficha([], NEW)) == {}
