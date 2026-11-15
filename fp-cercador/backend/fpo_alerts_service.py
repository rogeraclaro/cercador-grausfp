"""
fpo_alerts_service.py — alertes de cursos FPO nous (Pla 086).

  match(alert, curs)                 → bool  — el curs encaixa amb l'alerta
  dispatch(nous_cursos, base_url)    → int   — correus enviats (un per usuari i refresc)

Només avisa de cursos que **apareixen** en un refresc; no hi ha recordatoris.
"""
import logging

import alerts_service
import db as _db
import email_service
import fpo_agenda

logger = logging.getLogger(__name__)

ALERTS_MAX_PER_USER = 10      # files, comptant les pausades
MAX_CURSOS_PER_ALERTA = 20    # la resta es resumeix amb «i N més»
TOKEN_KIND = "fpoalert"
TOKEN_TYPE = "fpo_alert_unsubscribe"


def _same(a, b) -> bool:
    return (a or "").strip().casefold() == (b or "").strip().casefold()


def match(alert, curs: dict) -> bool:
    """`curs` és una fila de fpo_agenda.row. Cada camp de l'alerta que és NULL accepta qualsevol valor."""
    if alert["comarca"] and not (_same(curs.get("comarca"), alert["comarca"])
                                 or (curs.get("enLinia") and alert["inclou_en_linia"])):
        return False
    if alert["familia_codi"] and (curs.get("familia") or {}).get("codi") != alert["familia_codi"]:
        return False
    if alert["espec_codi"] and (curs.get("especialitat") or {}).get("codi") != alert["espec_codi"]:
        return False
    return True


def describe(alert, families: dict | None = None) -> str:
    """Text llegible de l'alerta, per al correu."""
    parts = []
    if alert["comarca"]:
        parts.append(alert["comarca"].title() + (" i en línia" if alert["inclou_en_linia"] else ""))
    if alert["familia_codi"]:
        parts.append(((families or {}).get(alert["familia_codi"]) or {}).get("ca") or alert["familia_codi"])
    if alert["espec_codi"]:
        parts.append(alert["espec_codi"])
    return " · ".join(parts)


def _fmt_date(iso) -> str:
    y, _, rest = (iso or "").partition("-")
    m, _, d = rest.partition("-")
    return f"{d}/{m}/{y}" if y and m and d else "sense data"


def _curs_lines(curs: dict) -> str:
    lloc = ", ".join(p for p in (curs.get("centreNom"), (curs.get("municipi") or "").title()) if p)
    detall = " · ".join(p for p in (
        "Comença: " + _fmt_date(curs.get("dataInici")),
        lloc,
        "en línia" if curs.get("enLinia") else "",
    ) if p)
    lines = [f"  • {(curs.get('titol') or {}).get('ca') or curs.get('idCurs')}", f"    {detall}"]
    if curs.get("fitxaUrl"):
        lines.append(f"    {curs['fitxaUrl']}")
    return "\n".join(lines)


def _build_email_body(sections: list, base_url: str, site_url: str) -> str:
    """`sections`: [(descripció, [cursos], url_de_baixa)], una per alerta amb cursos nous."""
    blocks = []
    for description, cursos, unsubscribe_url in sections:
        shown = cursos[:MAX_CURSOS_PER_ALERTA]
        block = f"Alerta «{description}» — {len(cursos)} cursos nous:\n\n" + "\n\n".join(map(_curs_lines, shown))
        if len(cursos) > len(shown):
            block += f"\n\n  … i {len(cursos) - len(shown)} més a l'agenda."
        block += f"\n\nPer deixar de rebre aquesta alerta (sense necessitat d'entrar):\n{unsubscribe_url}"
        blocks.append(block)
    return (
        "Hola,\n\n"
        "Han aparegut cursos nous de formació per a l'ocupació que encaixen amb les teves alertes.\n\n"
        + "\n\n---\n\n".join(blocks)
        + f"\n\n---\nTots els cursos que comencen aviat:\n{site_url}/index.html?mode=fpo&vista=agenda\n\n"
        f"GrausFP · {site_url}"
    )


def dispatch(nous_cursos: list, base_url: str = "https://grausfp.es", families: dict | None = None,
             site_url: str | None = None) -> int:
    """
    Envia un sol correu per usuari amb els cursos nous que encaixen amb les seves alertes
    actives, agrupats per alerta. `nous_cursos` són cursos tal com surten dels fitxers
    (soc_cursos.json / ext_cursos.json). Un error amb un usuari no atura els altres.
    """
    if not nous_cursos:
        return 0
    families = families or {}
    site_url = (site_url or base_url).rstrip("/")
    rows = [fpo_agenda.row(c, families) for c in nous_cursos if isinstance(c, dict)]
    conn = _db.get_db()
    sent = 0
    try:
        alerts = _db.query_all(
            conn,
            "SELECT a.id, a.user_id, a.comarca, a.familia_codi, a.espec_codi, a.inclou_en_linia, u.email "
            "FROM fpo_alerts a JOIN users u ON u.id = a.user_id "
            "WHERE a.active = 1 AND u.verified = 1 AND u.is_active = 1 AND u.deleted_at IS NULL "
            "ORDER BY a.user_id, a.id",
        )
        by_user: dict = {}
        for alert in alerts:
            by_user.setdefault(alert["user_id"], []).append(alert)
        for user_id, user_alerts in by_user.items():
            try:
                sections, ids = [], []
                for alert in user_alerts:
                    matched = [r for r in rows if match(alert, r)]
                    if not matched:
                        continue
                    token = alerts_service._get_or_create_unsubscribe_token(
                        conn, alert["id"], user_id, kind=TOKEN_KIND, token_type=TOKEN_TYPE)
                    sections.append((describe(alert, families), matched,
                                     f"{base_url}/api/fpo/alerts/{alert['id']}/unsubscribe?token={token}"))
                    ids.append(alert["id"])
                if not sections:
                    continue
                n = len({r["idCurs"] for _, matched, _ in sections for r in matched})
                email_service.send_email(user_alerts[0]["email"],
                                         f"Cursos FPO nous — {n} que encaixen amb les teves alertes",
                                         _build_email_body(sections, base_url, site_url))
                conn.executemany("UPDATE fpo_alerts SET last_sent_at = datetime('now') WHERE id = ?",
                                 [(i,) for i in ids])
                conn.commit()
                sent += 1
            except Exception as exc:  # un usuari amb problemes no ha de deixar els altres sense avís
                logger.error("fpo_alerts_service: error amb l'usuari id=%s: %s", user_id, exc)
    finally:
        conn.close()
    return sent
