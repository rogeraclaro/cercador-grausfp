"""
sepe_entity_alerts_service.py — alertes d'entitats autoritzades noves del SEPE (Pla 102).

  entity_key(entitat)                     → str        — clau estable d'una entitat dins d'una especialitat
  match(alert, entitat)                   → bool       — l'entitat encaixa amb els filtres de l'alerta
  load_snapshot / save_snapshot           — instantània d'entitats conegudes per especialitat
  check_new_entities(data_dir, base_url)  → int        — correus enviats (un per usuari i refresc)

És una alerta **aproximada**: el SEPE no publica quan s'autoritza una entitat, només la llista
actual. Es compara cada setmana amb la instantània i s'avisa de les que no hi eren. L'avís diu
que l'entitat està *autoritzada*; no vol dir que tingui cap curs amb dates.
"""
import json
import logging
import os
import time
import unicodedata
from urllib.parse import quote

import alerts_service
import db as _db
import email_service
from scrapers import sepe_scraper

logger = logging.getLogger(__name__)

ALERTS_MAX_PER_USER = 10        # files, comptant les pausades
MAX_ENTITATS_PER_ALERTA = 20    # la resta es resumeix amb «… i N més»
TOKEN_KIND = "sepeent"
TOKEN_TYPE = "sepe_entity_alert_unsubscribe"
PAUSE_S = 1.0                   # entre especialitats, per no atabalar el SEPE

_TIPUS_LABEL = {"teleformacio": "teleformació", "presencial": "presencial"}


def entity_key(entitat: dict) -> str:
    """Id + tipus: una entitat ja autoritzada en presencial que s'autoritza també per a teleformació és nova."""
    return f"{entitat.get('id')}|{entitat.get('tipus')}"


def _norm(text) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().strip()


def match(alert, entitat: dict) -> bool:
    """`alert` és una fila de sepe_entity_alerts. Província NULL = qualsevol."""
    if alert["provincia"] and _norm(entitat.get("provincia")) != _norm(alert["provincia"]):
        return False
    if alert["nomes_teleformacio"] and entitat.get("tipus") != "teleformacio":
        return False
    return True


def load_snapshot(conn, codi: str):
    """Conjunt de claus d'entitat conegudes per a l'especialitat, o None si no n'hi ha instantània."""
    row = _db.query_one(conn, "SELECT entitat_keys FROM sepe_entity_snapshots WHERE codi = ?", (codi,))
    if not row:
        return None
    try:
        return set(json.loads(row["entitat_keys"]))
    except (ValueError, TypeError):
        return None


def save_snapshot(conn, codi: str, keys) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sepe_entity_snapshots (codi, entitat_keys, updated_at) "
        "VALUES (?, ?, datetime('now'))", (codi, json.dumps(sorted(keys))))
    conn.commit()


def _read_catalogue(data_dir: str) -> dict:
    """{codi: fila} de sepe_especs.json. {} si falta o és il·legible (el pas queda en no-op)."""
    try:
        with open(os.path.join(data_dir, "sepe_especs.json"), encoding="utf-8") as f:
            rows = json.load(f)
    except (OSError, ValueError):
        return {}
    return {r["codi"]: r for r in rows if isinstance(r, dict) and r.get("codi")} if isinstance(rows, list) else {}


def describe(alert, row: dict) -> str:
    title = row.get("titol_mostra") or row.get("titol_es") or alert["codi"]
    parts = [f"{title} ({alert['codi']})"]
    if alert["provincia"]:
        parts.append(f"província: {alert['provincia']}")
    if alert["nomes_teleformacio"]:
        parts.append("només teleformació")
    return " · ".join(parts)


def _entity_lines(entitat: dict) -> str:
    # Mai el correu de l'entitat (només per a administradors) ni dades fiscals.
    tipus = _TIPUS_LABEL.get(entitat.get("tipus"), entitat.get("tipus") or "")
    lines = [f"  • {entitat.get('nom') or entitat.get('id')}",
             "    " + " · ".join(p for p in (tipus, entitat.get("provincia")) if p)]
    if entitat.get("telefon"):
        lines.append(f"    Tel. {entitat['telefon']}")
    web = entitat.get("web") or ""
    if web.startswith(("http://", "https://")):
        lines.append(f"    {web}")
    return "\n".join(lines)


def _build_email_body(sections: list, site_url: str) -> str:
    """`sections`: [(descripció, codi, [entitats], url_de_baixa)], una per alerta amb entitats noves."""
    blocks = []
    for description, codi, entitats, unsubscribe_url in sections:
        shown = entitats[:MAX_ENTITATS_PER_ALERTA]
        block = f"Alerta «{description}» — {len(entitats)} entitats noves:\n\n" + "\n\n".join(map(_entity_lines, shown))
        if len(entitats) > len(shown):
            block += f"\n\n  … i {len(entitats) - len(shown)} més al cercador."
        block += (f"\n\nConsulta l'especialitat i totes les entitats:\n"
                  f"{site_url}/index.html?grado=SEPE&q={quote(codi)}")
        block += f"\n\nPer deixar de rebre aquesta alerta (sense necessitat d'entrar):\n{unsubscribe_url}"
        blocks.append(block)
    return (
        "Hola,\n\n"
        "El SEPE ha autoritzat entitats noves per impartir especialitats de les teves alertes. "
        "Una entitat autoritzada és una entitat amb permís per impartir l'especialitat: això no vol dir "
        "que tingui cap curs programat ni dates d'inici. Cal contactar-hi per saber si n'ofereix.\n\n"
        + "\n\n---\n\n".join(blocks)
        + f"\n\n---\nGrausFP · {site_url}"
    )


def _new_entities_by_codi(conn, codis: dict, pause_s: float) -> dict:
    """{codi: [entitats noves]} per a cada especialitat amb alerta. `codis` = {codi: idSepe}.
    Desa la instantània (unió) de cada especialitat; un error del SEPE la deixa intacta."""
    new_by_codi: dict = {}
    for n, (codi, id_sepe) in enumerate(codis.items()):
        if n and pause_s:
            time.sleep(pause_s)
        try:
            current = sepe_scraper.fetch_entitats(id_sepe)
        except Exception as exc:  # una especialitat que falla no ha de deixar les altres sense avís
            logger.warning("sepe_entity_alerts: %s: error del SEPE: %s", codi, exc)
            continue
        known = load_snapshot(conn, codi)
        current_keys = {entity_key(e) for e in current if isinstance(e, dict)}
        if known is not None:
            new_by_codi[codi] = [e for e in current if isinstance(e, dict) and entity_key(e) not in known]
        # Primera passada: només s'enregistra, sense avisar. Sempre unió: una entitat que
        # desapareix de la llista i torna no s'anuncia dues vegades.
        save_snapshot(conn, codi, (known or set()) | current_keys)
    return new_by_codi


def check_new_entities(data_dir: str, base_url: str = "https://grausfp.es", site_url: str | None = None,
                       pause_s: float = PAUSE_S) -> int:
    """
    Torna a demanar al SEPE les entitats de les especialitats amb alguna alerta activa, les compara
    amb la instantània i envia un sol correu per usuari amb les noves que encaixen amb les seves
    alertes. Retorna els correus enviats. Un error amb un usuari no atura els altres.
    """
    site_url = (site_url or base_url).rstrip("/")
    base_url = base_url.rstrip("/")
    catalogue = _read_catalogue(data_dir)
    conn = _db.get_db()
    sent = 0
    try:
        alerts = _db.query_all(
            conn,
            "SELECT a.id, a.user_id, a.codi, a.provincia, a.nomes_teleformacio, u.email "
            "FROM sepe_entity_alerts a JOIN users u ON u.id = a.user_id "
            "WHERE a.active = 1 AND u.verified = 1 AND u.is_active = 1 AND u.deleted_at IS NULL "
            "ORDER BY a.user_id, a.id",
        )
        codis = {a["codi"]: catalogue[a["codi"]]["idSepe"] for a in alerts
                 if a["codi"] in catalogue and catalogue[a["codi"]].get("idSepe")}
        new_by_codi = _new_entities_by_codi(conn, codis, pause_s)

        by_user: dict = {}
        for alert in alerts:
            by_user.setdefault(alert["user_id"], []).append(alert)
        for user_id, user_alerts in by_user.items():
            try:
                sections, ids = [], []
                for alert in user_alerts:
                    matched = [e for e in new_by_codi.get(alert["codi"], []) if match(alert, e)]
                    if not matched:
                        continue
                    token = alerts_service._get_or_create_unsubscribe_token(
                        conn, alert["id"], user_id, kind=TOKEN_KIND, token_type=TOKEN_TYPE)
                    sections.append((describe(alert, catalogue[alert["codi"]]), alert["codi"], matched,
                                     f"{base_url}/api/sepe/entity-alerts/{alert['id']}/unsubscribe?token={token}"))
                    ids.append(alert["id"])
                if not sections:
                    continue
                n = sum(len(entitats) for _, _, entitats, _ in sections)
                email_service.send_email(user_alerts[0]["email"],
                                         f"Entitats noves autoritzades pel SEPE — {n} que encaixen amb les teves alertes",
                                         _build_email_body(sections, site_url))
                conn.executemany("UPDATE sepe_entity_alerts SET last_sent_at = datetime('now') WHERE id = ?",
                                 [(i,) for i in ids])
                conn.commit()
                sent += 1
            except Exception as exc:  # un usuari amb problemes no ha de deixar els altres sense avís
                logger.error("sepe_entity_alerts: error amb l'usuari id=%s: %s", user_id, exc)
        # Sense cap fila d'alerta (activa o en pausa) la instantània ja no serveix.
        conn.execute("DELETE FROM sepe_entity_snapshots WHERE codi NOT IN (SELECT codi FROM sepe_entity_alerts)")
        conn.commit()
    finally:
        conn.close()
    return sent
