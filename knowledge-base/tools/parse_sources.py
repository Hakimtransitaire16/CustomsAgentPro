"""Parseurs dédiés aux tableaux des sources DGD (appelés par build_kb.py quand le texte existe).

- mise à jour du tarif 2020        → data/tarif_maj_2020.json   (DD, TVA, autres taxes, FAP par ligne)
- table de corrélation SH 2022      → data/correlation_sh2022.json (nouvelles lignes, anciens codes, DD, TVA)
- arrêté DAPS du 26/01/2019         → data/daps_2019.json        (liste initiale, taux par ligne)

Chaque sortie garde la source, et chaque ligne est vérifiable dans le PDF (numéro de ligne du texte).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT, DATA, SRC = ROOT / "text", ROOT / "data", ROOT / "sources"
C10 = r"\d{4}\.\d{2}\.\d{2}\.\d{2}"
RATE = r"(?:ex|\d{1,3})"


def _rate(x: str):
    return 0 if x.lower() == "ex" else int(x)


# ------------------------------------------------------------------ mise à jour du tarif 2020
MAJ_RE = re.compile(rf"^\s*({C10})\s+([A-Z])\s*(\d)\s+(\S+)\s+(.*)$")


def tarif_maj_2020() -> dict | None:
    f = TEXT / "mise_a_jour_du_tarif_2020.txt"
    if not f.exists():
        return None
    lignes = {}
    for no, l in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        m = MAJ_RE.match(l)
        if not m:
            continue
        code, cle, gus, unite, reste = m.groups()
        toks = [t for t in re.split(r"\s{2,}", reste.strip()) if t]
        toks = [x for t in toks for x in (re.split(r"\s+(?=\d{1,3}$)", t) if re.search(r"\(\*\)\s*\d", t) else [t])]
        i = next((k for k in range(1, len(toks) - 1)
                  if re.fullmatch(rf"{RATE}(\s*\(\*+\))?", toks[k]) and re.fullmatch(RATE, toks[k + 1])), None)
        if i is None:
            continue
        dd = re.match(RATE, toks[i]).group(0)
        autres = toks[i + 2] if len(toks) > i + 2 and toks[i + 2] != "-" else ""
        fap = toks[i + 3] if len(toks) > i + 3 and toks[i + 3] != "-" else ""
        if not fap and autres and re.fullmatch(r"[A-Z.;\s]+", autres) and "." in autres and autres.count(".") <= 4 \
                and not re.search(r"T\.I\.C|T\.E\.E|T\.C\.E|DAPS|T\.C\b", autres):
            autres, fap = "", autres
        lignes[code] = {"code": code, "cle": cle, "gus": int(gus), "unite": unite,
                        "libelle": " ".join(toks[:i]).strip(), "dd": _rate(dd), "tva": _rate(toks[i + 1]),
                        "renvoi": "(*)" in toks[i], "autres_taxes": autres, "fap": fap, "ligne_texte": no}
    return {"_source": "DGD — Mise à jour du tarif douanier et de ses annexes (LF 2020), mise_a_jour_du_tarif_2020.pdf",
            "count": len(lignes), "lignes": lignes}


# ------------------------------------------------------------------ table de corrélation SH 2022
NEW_RE = re.compile(rf"({C10})\s+([A-Z])\s+(-.*?)\s+({RATE})\s+({RATE})(?=\s{{2,}}|\s*$)")
OLD_RE = re.compile(rf"^({C10})\s+(-.*?)\s+({RATE})\s+({RATE})(?=\s{{2,}}|\s*$)")
EQ_RE = re.compile(rf"\[?\s*({C10})\s*=\s*\(?\s*((?:(?:ex\s*)?\d{{4}}(?:\.\d{{1,2}}){{0,3}}(?!\d|\.\d|\s*=)\s*[;,]?\s*(?:et\s*)?)+)", re.I)
OBS_COL = 145  # colonne « Observation » dans le texte -layout


def correlation_sh2022() -> dict | None:
    f = TEXT / "amendements_systeme_harmonise_2022_table_de_correlation_nationale_.txt"
    if not f.exists():
        return None
    nouvelles, anciennes, obs = {}, {}, []
    for no, l in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        m = OLD_RE.match(l)
        if m:
            anciennes[m.group(1)] = {"code": m.group(1), "libelle": m.group(2).strip(), "dd": _rate(m.group(3)),
                                     "tva": _rate(m.group(4)), "ligne_texte": no}
        start = m.end() if m else 0
        n = NEW_RE.search(l, start)
        if n:
            nouvelles[n.group(1)] = {"code": n.group(1), "cle": n.group(2), "libelle": n.group(3).strip(),
                                     "dd": _rate(n.group(4)), "tva": _rate(n.group(5)), "anciens": [],
                                     "ligne_texte": no}
            obs.append(l[n.end():])
        elif m:
            obs.append(l[m.end():])
        elif re.match(r"^\s{60,}\S", l):  # colonne de droite seule (observation ou suite de libellé)
            obs.append(l.strip())
        elif len(l) > OBS_COL and l[OBS_COL:].strip():  # suite de la colonne Observation
            obs.append(l[OBS_COL - 5:].strip())
    flux = re.sub(r"\s+", " ", " ".join(obs))
    for eq in EQ_RE.finditer(flux):
        new = eq.group(1)
        for ex, code in re.findall(r"(ex\s*)?(\d{4}(?:\.\d{1,2}){0,3})", eq.group(2), re.I):
            if code == new:
                continue
            item = {"code": code, "partiel": bool(ex)}
            nouvelles.setdefault(new, {"code": new, "anciens": []})
            if item not in nouvelles[new]["anciens"]:
                nouvelles[new]["anciens"].append(item)
    supprimes = sorted(set(re.findall(rf"Suppression de la sous[- ]position ({C10})", flux)))
    inverse = {}
    for c, v in nouvelles.items():
        for a in v.get("anciens", []):
            inverse.setdefault(a["code"], []).append({"nouveau": c, "partiel": a["partiel"]})
    return {"_source": "DGD — Amendements du SH 2022, table de corrélation nationale (structure tarif 2021 → 2022), "
                       "amendements_systeme_harmonise_2022_table_de_correlation_nationale_.pdf",
            "nouvelles": nouvelles, "anciennes": anciennes, "supprimees": supprimes, "ancien_vers_nouveau": inverse,
            "count": {"nouvelles": len(nouvelles), "anciennes": len(anciennes), "supprimees": len(supprimes),
                      "correspondances": sum(len(v.get("anciens", [])) for v in nouvelles.values())}}


# ------------------------------------------------------------------ DAPS (arrêté du 26/01/2019)
ORDRE_RE = re.compile(r"^\s{1,10}(\d{1,4})\s{2,}(.*)$")
TITRE_RE = re.compile(r"^\s*\d{2}\.\d{2}\s{2,}")
CODE_DAPS = re.compile(r"(EX\s+)?(\d{3,4}\.\d{2}\.\d{2}\.\d{2}|\d{4}\.\d{2}(?:\.\d{2})?)", re.I)


def daps_2019() -> dict | None:
    pdf = SRC / "arreteedu_26_janvier_2019_fr.pdf"
    if not pdf.exists():
        return None
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    blocs, cur = [], None
    for no, l in enumerate(txt.splitlines(), 1):
        m = ORDRE_RE.match(l)
        if m and int(m.group(1)) <= 1200:
            if blocs and blocs[-1]["ordre"] is None and not CODE_DAPS.search(m.group(2)):
                blocs[-1]["ordre"] = int(m.group(1))  # n° d'ordre imprimé sous le code
                blocs[-1]["lignes"].append(m.group(2))
                continue
            cur = {"ordre": int(m.group(1)), "lignes": [m.group(2)], "no": no}
            blocs.append(cur)
        elif re.match(rf"^\s{{8,}}(EX\s+)?{C10}\s", l):  # code sans n° d'ordre sur la ligne
            cur = {"ordre": None, "lignes": [l.strip()], "no": no}
            blocs.append(cur)
        elif TITRE_RE.match(l) or "JOURNAL OFFICIEL" in l:
            cur = None
        elif cur is not None and l.strip() and len(cur["lignes"]) < 5:
            cur["lignes"].append(l.strip())
    lignes = []
    for b in blocs:
        texte = "  ".join(b["lignes"])
        c = CODE_DAPS.search(texte)
        taux = re.findall(r"(\d{1,3})\s*%\s*(?=\s{2,}|$)", texte)
        if not c or not taux or b["ordre"] is None:
            continue
        code = c.group(2)
        if re.fullmatch(r"\d{3}\.\d{2}\.\d{2}\.\d{2}", code):  # zéro initial omis dans le JO
            code = "0" + code
        lib = re.sub(r"\s{2,}", " ", texte[c.end():]).strip()
        lib = re.sub(r"\s*\d{1,3}\s*%\s*$", "", lib).replace(f" {taux[-1]} % ", " ")
        lignes.append({"ordre": b["ordre"], "ex": bool(c.group(1)), "code": code, "libelle": lib,
                       "taux": int(taux[-1]), "ligne_texte": b["no"]})
    return {"_source": "Arrêté du 26/01/2019 fixant la liste des marchandises soumises au DAPS (JO n° 06 du 27/01/2019)",
            "_avertissement": "Liste initiale. Modifiée par l'arrêté du 8/04/2019 et étendue ensuite : vérifier "
                              "la liste en vigueur avant toute liquidation.",
            "count": len(lignes), "lignes": lignes}


def main() -> list[str]:
    out = []
    for name, fn in (("tarif_maj_2020.json", tarif_maj_2020), ("correlation_sh2022.json", correlation_sh2022),
                     ("daps_2019.json", daps_2019)):
        res = fn()
        if res is None:
            continue
        (DATA / name).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        out.append(f"{name}: {res['count']}")
    return out


if __name__ == "__main__":
    for r in main():
        print(r)
