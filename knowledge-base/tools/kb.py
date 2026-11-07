"""Search the customs knowledge base from the command line.

    python tools/kb.py search "climatiseur split"        # full-text search, all documents
    python tools/kb.py code 8415.90                       # tariff lines + related decisions
    python tools/kb.py article "50 ter"                   # article of the Code / law / decree
    python tools/kb.py stats

The index (kb.sqlite) is rebuilt automatically from data/ when missing.
"""
from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "kb.sqlite"


def connect() -> sqlite3.Connection:
    if not DB.exists():
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_kb.py")], check=True)
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def fts_query(text: str) -> str:
    words = re.findall(r"\w+", text)
    return " ".join(f'"{w}"*' for w in words)


def search(q: str, limit: int = 10) -> None:
    db = connect()
    rows = db.execute(
        "SELECT kind, ref, title, snippet(search, 3, '[', ']', ' … ', 18) AS snip "
        "FROM search WHERE search MATCH ? ORDER BY bm25(search, 0, 2, 4, 1) LIMIT ?",
        (fts_query(q), limit),
    ).fetchall()
    if not rows:
        print("Aucun résultat. (Les textes sont en français/anglais : chercher en français.)")
    for r in rows:
        print(f"[{r['kind']}] {r['ref']} — {r['title'][:90]}\n    {r['snip']}\n")


def code(c: str) -> None:
    db = connect()
    d = re.sub(r"\D", "", c)
    lines = [r for r in db.execute("SELECT * FROM tarif ORDER BY code") if re.sub(r"\D", "", r["code"]).startswith(d)]
    print(f"Tarif 2016 — {len(lines)} ligne(s) commençant par {c}")
    for r in lines[:25]:
        rate = "exonéré" if r["dd_exempt"] else f"{int(r['dd_rate'] * 100)} %"
        print(f"  {r['code']}  {r['unit']:>5}  DD {rate:>8}  {r['full_label'][-110:]}")
    if len(lines) > 25:
        print(f"  … {len(lines) - 25} de plus")
    if not lines:
        print("  Absent du tarif 2016 : code créé ou modifié depuis (SH 2017/2022 ?). Vérifier le tarif en vigueur.")
    decs = [r for r in db.execute("SELECT * FROM decisions") if re.sub(r"\D", "", r["hs_code"] or "")[:4] == d[:4]]
    print(f"\nDécisions de classement 2025 sur la position {d[:4]} : {len(decs)}")
    for r in decs:
        print(f"  {r['hs_code']}  {r['reference']}  — {r['designation'][:70]}  (valide jusqu'au {r['valid_to'] or '-'})")


def article(num: str) -> None:
    db = connect()
    rows = db.execute("SELECT * FROM articles WHERE lower(article) = lower(?)", (num.strip(),)).fetchall()
    if not rows:
        print("Article non trouvé.")
    for r in rows:
        scope = "Code des douanes (rédaction loi 17-04)" if r["scope"] == "code_des_douanes" else r["instrument"]
        print(f"— Art. {r['article']} · {scope}\n{r['text']}\n")


def stats() -> None:
    db = connect()
    for t in ("tarif", "decisions", "articles", "search"):
        print(f"{t:10} {db.execute(f'SELECT count(*) FROM {t}').fetchone()[0]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd, args = sys.argv[1], " ".join(sys.argv[2:])
    {"search": lambda: search(args), "code": lambda: code(args),
     "article": lambda: article(args), "stats": stats}.get(cmd, lambda: print(__doc__))()
