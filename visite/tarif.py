"""Position tarifaire : lecture du tarif douanier et des sources officielles de knowledge-base/.

Pour un code SH, renvoie la fiche complète tirée des documents fournis :
section (titre, notes), chapitre (titre, notes), position (libellé), sous-position et ligne nationale
(libellé hiérarchique, unité, droit de douane), mesures de la loi de finances 2026, décisions de
classement 2020 et 2025 sur la même position, notes de section ou de chapitre qui citent la position.

    python -m visite tarif 3506.99.90.00
    python -m visite tarif 3824999999 --notes      # avec le texte intégral des notes

Le tarif de référence est l'édition DGD 2016 (nomenclature SH 2012). Un code créé depuis
(SH 2017 / SH 2022) n'y figure pas : on cherche la ligne 2016 correspondante et on le signale.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

KB = Path(__file__).resolve().parent.parent / "knowledge-base" / "data"

# Sous-positions SH 2017 / SH 2022 absentes de l'édition 2016 → sous-position SH 2012 d'origine
# (tables de corrélation OMD). Compléter au besoin ; à défaut, recherche par position + suffixe national.
CORRESPONDANCES = {
    "382491": "382490", "382492": "382490", "382499": "382490",
    "382481": "382490", "382482": "382490", "382483": "382490", "382484": "382490",
    "382485": "382490", "382486": "382490", "382487": "382490", "382488": "382490",
    "382489": "382490",
    "293214": "293219", "381225": "381230", "381226": "381230",
    "850760": "850780", "852352": "852390",
}


def chiffres(code: str) -> str:
    return re.sub(r"\D", "", str(code or ""))


def fmt(code: str) -> str:
    c = chiffres(code)
    parts = [c[0:4], c[4:6], c[6:8], c[8:10]]
    return ".".join(p for p in parts if p)


def pos(code: str) -> str:
    c = chiffres(code)
    return f"{c[:2]}.{c[2:4]}" if len(c) >= 4 else c


def disponible() -> bool:
    return (KB / "tarif_2016.json").exists()


@lru_cache(maxsize=1)
def _kb():
    def load(name, key=None):
        f = KB / name
        if not f.exists():
            return [] if key else {}
        o = json.loads(f.read_text(encoding="utf-8"))
        return o.get(key, []) if key else o

    lines = load("tarif_2016.json", "lines")
    notes = load("tarif_2016_notes.json")
    secs = load("tarif_2016_sections.json")
    decisions = []
    for f in sorted(KB.glob("decisions_classement_*.json")):
        an = f.stem.removeprefix("decisions_classement_")
        for r in load(f.name, "decisions"):
            decisions.append(dict(r, recueil=an))
    return {
        "lignes": {chiffres(l["code"]): l for l in lines},
        "par_position": _grouper(lines),
        "titres_positions": notes.get("headings", {}),
        "notes_chapitres": notes.get("chapter_notes", {}),
        "sections": secs.get("sections", []),
        "rgi": secs.get("rgi", ""),
        "decisions": decisions,
        "mesures": load("mesures_tarifaires_lf2026.json", "measures"),
    }


def _grouper(lines):
    g = {}
    for l in lines:
        g.setdefault(chiffres(l["code"])[:4], []).append(l)
    return g


def _section(chap: int):
    return next((s for s in _kb()["sections"] if chap in s["chapitres"]), None)


def _cite(texte: str, position: str) -> list[str]:
    """Paragraphes numérotés d'une note qui citent la position (ex. « 35.06 »)."""
    if not texte:
        return []
    paras = re.split(r"\n(?=\s*\d{1,2}\s*[.\-]\s*[-–]?\s)", texte)
    return [re.sub(r"\s+", " ", p).strip() for p in paras if re.search(rf"(?<![\d.]){re.escape(position)}(?![\d])", p)]


def chercher(code: str):
    """Trouve la ligne du tarif 2016 : (statut, ligne, remarque).

    statut : exact | correspondance | position | absent
    """
    k = _kb()
    c = chiffres(code)
    if len(c) < 4:
        return "absent", None, "code trop court"
    if c in k["lignes"]:
        return "exact", k["lignes"][c], ""
    if len(c) < 10:  # code partiel : première ligne qui commence par ces chiffres
        l = next((x for d, x in k["lignes"].items() if d.startswith(c)), None)
        if l:
            return "position", l, f"code partiel {fmt(c)} : {sum(1 for d in k['lignes'] if d.startswith(c))} ligne(s) nationale(s)"
    hs6 = c[:6]
    anc = CORRESPONDANCES.get(hs6)
    if anc:
        cand = anc + c[6:]
        if cand in k["lignes"]:
            return "correspondance", k["lignes"][cand], (
                f"sous-position {hs6[:4]}.{hs6[4:]} créée après 2016 (SH 2017/2022) ; "
                f"ligne correspondante de l'édition 2016 : {fmt(cand)}")
    meme_pos = k["par_position"].get(c[:4], [])
    meme_sh6 = [l for l in meme_pos if chiffres(l["code"]).startswith(hs6)]
    if len(c) < 10 and meme_sh6:
        return "position", meme_sh6[0], f"{fmt(c)} absent de l'édition 2016 ; la sous-position {hs6[:4]}.{hs6[4:]} existe ({len(meme_sh6)} ligne(s))"
    suffixe = [l for l in meme_pos if chiffres(l["code"])[6:] == c[6:]]
    if suffixe:
        l = suffixe[-1]
        return "correspondance", l, (
            f"{fmt(c)} absent de l'édition 2016 ; ligne la plus proche (même position, même suffixe national) : "
            f"{l['code']} — à confirmer dans le tarif en vigueur")
    if meme_pos:
        return "position", meme_pos[0], f"{fmt(c)} absent de l'édition 2016 ; la position {pos(c)} existe ({len(meme_pos)} lignes)"
    return "absent", None, f"position {pos(c)} absente du tarif 2016"


def mesures_lf2026(code: str):
    c = chiffres(code)
    out = []
    for m in _kb()["mesures"]:
        for x in m.get("codes", []):
            d = chiffres(x["code"])
            if c.startswith(d) or (len(c) < 10 and d.startswith(c)):
                out.append({"article": m["article"], "mesure": m["measure"], "portee": m.get("scope", ""),
                            "condition": m.get("condition"), "taux": m.get("dd_rate"), "applicable": m.get("apply", False),
                            "ex": x.get("ex", False), "code": x["code"]})
                break
    return out


def decisions(code: str):
    c = chiffres(code)
    out = []
    for r in _kb()["decisions"]:
        codes = [chiffres(x) for x in (r.get("hs_codes") or [r.get("hs_code")]) if x]
        if any(x[:4] == c[:4] for x in codes):
            out.append({"reference": r["reference"], "recueil": r["recueil"], "code": r.get("hs_code"),
                        "designation": r.get("designation", ""), "valide_jusqu_au": r.get("valid_to"),
                        "meme_sous_position": any(x[:6] == c[:6] for x in codes),
                        "meme_ligne": any(x == c for x in codes)})
    out.sort(key=lambda r: (not r["meme_ligne"], not r["meme_sous_position"], r["recueil"]))
    return out


def taux_dd(ligne, code=None):
    """Droit de douane de la ligne, après les mesures inconditionnelles de la LF 2026."""
    if not ligne:
        return None, ""
    for m in mesures_lf2026(code or ligne["code"]):
        if m["applicable"] and m["taux"] is not None and not m["ex"]:
            return round(m["taux"] * 100, 2), f"LF 2026 art. {m['article']}"
    return (0.0 if ligne["dd_exempt"] else round(ligne["dd_rate"] * 100, 2)), "tarif 2016"


def fiche(code: str) -> dict:
    """Fiche complète d'une position tarifaire, tirée des sources officielles."""
    k = _kb()
    c = chiffres(code)
    statut, ligne, remarque = chercher(c)
    chap = int(c[:2]) if len(c) >= 2 else None
    sec = _section(chap) if chap else None
    p = pos(c)
    notes_chap = k["notes_chapitres"].get(str(chap), "")
    dd, dd_src = taux_dd(ligne, c) if statut in ("exact", "correspondance") else (None, "")
    return {
        "code": fmt(c), "statut": statut, "remarque": remarque,
        "section": {"numero": sec["section"], "titre": sec["titre"], "chapitres": sec["chapitres"],
                    "notes": sec["notes"], "notes_citant_position": _cite(sec["notes"], p)} if sec else None,
        "chapitre": {"numero": chap, "titre": notes_chap.split("\n", 1)[0].strip(), "notes": notes_chap,
                     "notes_citant_position": _cite(notes_chap, p)} if chap else None,
        "position": {"code": p, "libelle": k["titres_positions"].get(p, (ligne or {}).get("heading_label", ""))},
        "sous_position": f"{c[:4]}.{c[4:6]}" if len(c) >= 6 else None,
        "ligne": {"code": ligne["code"], "unite": ligne["unit"], "libelle": ligne["label"],
                  "hierarchie": ligne.get("context", []), "libelle_complet": ligne["full_label"]} if ligne else None,
        "droit_douane": dd, "droit_douane_source": dd_src,
        "lignes_position": [{"code": l["code"], "libelle": " > ".join(l.get("context", [])[1:] + [l["label"]]),
                             "dd": 0 if l["dd_exempt"] else round(l["dd_rate"] * 100)}
                            for l in k["par_position"].get(c[:4], [])],
        "mesures_lf2026": mesures_lf2026(c),
        "decisions": decisions(c),
        "avertissement": "Tarif DGD édition 2016 (SH 2012) : vérifier la ligne et le taux dans le tarif en vigueur.",
    }


def famille(declare: str, autre: str) -> dict:
    """Compare deux codes : même chapitre, même position, même sous-position SH6 (SH 2012 ou correspondance)."""
    a, b = chiffres(declare), chiffres(autre)
    n6 = lambda x: CORRESPONDANCES.get(x[:6], x[:6])
    return {"chapitre": a[:2] == b[:2], "position": a[:4] == b[:4],
            "sous_position": a[:6] == b[:6] or n6(a) == n6(b), "a": fmt(a), "b": fmt(b)}


def libelle_sh6(code: str) -> str:
    c = chiffres(code)
    c6 = CORRESPONDANCES.get(c[:6], c[:6])
    l = next((x for d, x in _kb()["lignes"].items() if d.startswith(c6)), None)
    if not l:
        return ""
    ctx = (l.get("context") or []) + [l["label"]]
    # 1 tiret = 5e chiffre ; 2 tirets = 6e chiffre non nul
    return ctx[1] if c6[5] != "0" and len(ctx) > 1 else ctx[0]


def classement(a: dict) -> str:
    """Ligne courte pour la fiche : « Section VI · Chapitre 35 · Position 35.06 »."""
    if not disponible():
        return ""
    f = fiche(a["code_sh"])
    if not f["section"]:
        return ""
    return f"Section {f['section']['numero']} · Ch. {f['chapitre']['numero']} · Pos. {f['position']['code']}"


def texte(f: dict, notes=False) -> str:
    """Rendu texte d'une fiche (ligne de commande)."""
    L = []
    s, ch, p, l = f["section"], f["chapitre"], f["position"], f["ligne"]
    L.append(f"POSITION TARIFAIRE {f['code']}   [{f['statut']}]")
    if f["remarque"]:
        L.append(f"  ⚠ {f['remarque']}")
    if s:
        L.append(f"\nSECTION {s['numero']} — {s['titre']} (chapitres {s['chapitres'][0]} à {s['chapitres'][-1]})")
        for x in s["notes_citant_position"]:
            L.append(f"  Note de section citant {p['code']} : {x}")
    if ch:
        L.append(f"CHAPITRE {ch['numero']} — {ch['titre']}")
        for x in ch["notes_citant_position"]:
            L.append(f"  Note de chapitre citant {p['code']} : {x}")
    L.append(f"POSITION {p['code']} — {p['libelle']}")
    if l:
        L.append(f"LIGNE {l['code']} ({l['unite']}) — {' > '.join(l['hierarchie'] + [l['libelle']])}")
    if f["droit_douane"] is not None:
        L.append(f"DROIT DE DOUANE : {f['droit_douane']:g} %  ({f['droit_douane_source']})")
    L.append(f"\nLignes nationales de la position {p['code']} ({len(f['lignes_position'])}) :")
    for x in f["lignes_position"][:30]:
        mark = "→" if l and x["code"] == l["code"] else " "
        L.append(f" {mark} {x['code']}  {x['dd']:>3} %  {x['libelle'][:100]}")
    for m in f["mesures_lf2026"]:
        L.append(f"\nLoi de finances 2026, art. {m['article']} : {m['mesure']} — {m['portee'][:160]}"
                 + (f" — condition : {m['condition']}" if m.get("condition") else ""))
    L.append(f"\nDécisions de classement sur la position {p['code']} : {len(f['decisions'])}")
    for r in f["decisions"][:12]:
        tag = "même ligne" if r["meme_ligne"] else "même SH6" if r["meme_sous_position"] else ""
        L.append(f"  {r['code']}  {r['reference']} (recueil {r['recueil']}) — {r['designation'][:70]} {('· ' + tag) if tag else ''}")
    if notes:
        if s and s["notes"]:
            L.append(f"\n— Notes de la section {s['numero']} —\n{s['notes']}")
        if ch and ch["notes"]:
            L.append(f"\n— Notes du chapitre {ch['numero']} —\n{ch['notes']}")
    L.append(f"\n{f['avertissement']}")
    return "\n".join(L)
