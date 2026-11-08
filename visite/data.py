"""Chargement, validation et formatage du dossier JSON."""
import json
from datetime import datetime
from pathlib import Path

import jsonschema

SCHEMA = Path(__file__).parent / "schema" / "dossier.schema.json"


def load(path):
    """Charge et valide un dossier. Lève jsonschema.ValidationError si invalide."""
    path = Path(path)
    d = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(d, json.loads(SCHEMA.read_text(encoding="utf-8")))
    d["_dir"] = str(path.parent.resolve())
    return d


def save(d, path):
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- formatage français ----------
def n(x, dec=0):
    """1234567.8 -> '1 234 567,80' (espace fine insécable comme séparateur)."""
    if x is None or x == "":
        return "—"
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def sh(code):
    """3506999000 -> 3506.99.90.00"""
    c = str(code).replace(".", "")
    return ".".join([c[0:4], c[4:6], c[6:8], c[8:10]]) if len(c) == 10 else code


def date(s):
    """Accepte 'JJ/MM/AAAA[ HH:MM[:SS]]' ou 'AAAA-MM-JJ'."""
    s = (s or "").strip()
    for f in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, f)
        except ValueError:
            pass
    return None
