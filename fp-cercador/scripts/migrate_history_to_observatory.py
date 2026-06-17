#!/usr/bin/env python3
"""
One-shot: migra les entrades de refresh_history.json a observatory_snapshots.
Idempotent: INSERT OR IGNORE per ts UNIQUE.
Executa des de la rel del projecte: python scripts/migrate_history_to_observatory.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import init_db

HISTORY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "backend", "data", "refresh_history.json"
)


def main():
    with open(HISTORY_PATH, encoding="utf-8") as f:
        history = json.load(f)

    conn = init_db()
    inserted = 0
    skipped = 0

    for entry in reversed(history):  # ordre cronològic
        changes = entry.get("changes") or {}
        by_grado = entry.get("by_grado") or {}
        new_denoms = changes.get("new_denominacions") or []
        removed_denoms = changes.get("removed_denominacions") or []
        new_by_grado = changes.get("new_by_grado") or {}
        families_amb_altes = sorted(new_by_grado.keys()) if new_by_grado else []

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO observatory_snapshots
                (ts, total, total_a, total_b, total_c, total_d, total_e,
                 n_altes, n_baixes, families_amb_altes, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'history_migration')
            """,
            (
                entry["ts"],
                entry.get("total") or 0,
                by_grado.get("A") or 0,
                by_grado.get("B") or 0,
                by_grado.get("C") or 0,
                by_grado.get("D") or 0,
                by_grado.get("E") or 0,
                len(new_denoms),
                len(removed_denoms),
                json.dumps(families_amb_altes, ensure_ascii=False) if families_amb_altes else None,
            ),
        )
        if cursor.rowcount:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    conn.close()
    print(f"Migració completada: {inserted} inserts, {skipped} ignorats (ja existien).")


if __name__ == "__main__":
    main()
