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
    return normaliser(d)


def conteneurs(d):
    """Liste des conteneurs du dossier : transport.conteneurs, sinon le conteneur unique."""
    t = d.get("transport", {})
    if t.get("_conteneurs") or t.get("conteneurs"):
        return t.get("_conteneurs") or t["conteneurs"]
    if t.get("conteneur"):
        return [{"numero": t["conteneur"], "scelle": t.get("scelle", ""), "type": t.get("type_conteneur", ""), "tare": t.get("tare")}]
    return []


def normaliser(d):
    """Complète le dossier chargé pour que les modèles n'aient qu'une forme à lire.

    Plusieurs conteneurs : transport.conteneur et transport.scelle deviennent la liste affichée
    (« A · B · C ») ; les contrôles lisent toujours la liste d'origine avec conteneurs(d).
    Pièces absentes (BAD, avis d'arrivée) : blocs vides plutôt qu'une erreur de rendu.
    """
    t = d.setdefault("transport", {})
    lst = t.get("conteneurs")
    if lst:
        t["_conteneurs"] = lst
        t["conteneur"] = " · ".join(c["numero"] for c in lst)
        if any(c.get("scelle") for c in lst):
            t["scelle"] = " · ".join(c.get("scelle", "—") for c in lst)
        types = sorted({c["type"] for c in lst if c.get("type")})
        t.setdefault("type_conteneur", f"{len(lst)} × {types[0]}" if len(types) == 1 else f"{len(lst)} conteneurs")
    t.setdefault("bad", {})
    for k in ("reference", "date", "gros", "agent"):
        t["bad"].setdefault(k, "")
    d.setdefault("arrivee", {})
    for k in ("provenance", "accostage", "crn", "tares"):
        d["arrivee"].setdefault(k, "")
    d.setdefault("visite", {})
    return d


def save(d, path):
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    tr = dict(out.get("transport", {}))
    if tr.pop("_conteneurs", None):     # valeurs déduites au chargement : on ne les réécrit pas
        tr.pop("conteneur", None), tr.pop("scelle", None)
    out["transport"] = tr
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
