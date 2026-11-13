"""Ce qui manque à un dossier : pièces, informations de visite, hypothèses à confirmer.

S'appuie sur knowledge-base/data/pieces_dossier.json (émetteur, valeur douanière et texte de chaque pièce).
Le résultat est rendu au déclarant à chaque `python -m visite tout` : il sait quoi demander, à qui, et pourquoi.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REF = Path(__file__).resolve().parent.parent / "knowledge-base" / "data" / "pieces_dossier.json"
INCOTERMS_SANS_ASSURANCE = {"EXW", "FCA", "FAS", "FOB", "CFR", "CPT"}


@lru_cache(maxsize=1)
def referentiel() -> dict:
    return json.loads(REF.read_text(encoding="utf-8"))


def _piece(code: str) -> dict:
    return next(p for p in referentiel()["pieces"] if p["code"] == code)


def _presentes(d: dict) -> set[str]:
    codes = {doc.get("code", "") for doc in d.get("documents", [])}
    codes |= set(d.get("pieces_presentes", []))
    if (d.get("origine") or {}).get("certificat"):
        codes.add("CO")
    return codes


def requises(d: dict) -> list[tuple[str, str, str]]:
    """(code, niveau, motif) des pièces attendues pour ce dossier."""
    dec, tr = d["declaration"], d.get("transport", {})
    out = [("D10", "obligatoire", "déclaration"), ("FAC", "obligatoire", "valeur"), ("PL", "obligatoire", "comptage et pesée")]
    if tr.get("bl"):
        out += [("BL", "obligatoire", "transport maritime"), ("AA", "obligatoire", "arrivée et délais"),
                ("BAD", "obligatoire", "enlèvement après mainlevée")]
    port = (tr.get("port_dechargement") or "").split(",")[0].split("(")[0].strip().lower()
    if port and port not in (dec.get("bureau") or "").lower():
        bureau = (dec.get("bureau") or "").split("—")[-1].strip()
        out.append(("TRF", "obligatoire", f"dédouanement au {bureau}, pas au port de débarquement ({port.title()})"))
    if not (dec.get("domiciliation") or {}).get("numero"):
        out.append(("DOM", "obligatoire", "paiement à l'étranger"))
    if d.get("parties", {}).get("declarant_societe", {}).get("agrement"):
        out.append(("MAN", "obligatoire", "déclaration par un commissionnaire"))
    orig = d.get("origine") or {}
    pref = (orig.get("preference") or "").lower()
    if pref and not pref.startswith("aucune"):
        out.append(("CO", "obligatoire", "préférence tarifaire demandée"))
    else:
        out.append(("CO", "recommandé", "le service peut l'exiger (art. 14 quater)"))
    if (dec.get("incoterm") or "").upper() in INCOTERMS_SANS_ASSURANCE:
        out.append(("ASS", "obligatoire", f"vente {dec.get('incoterm')} : prime réelle à ajouter ou non-assurance à justifier"))
    out.append(("FT", "recommandé", "classement et identification à la visite"))
    # FDS : substances et mélanges (ch. 28 à 38) et matières sous formes primaires (39.01–39.14, 40.01–40.05),
    # pas les ouvrages finis en plastique ou en caoutchouc (39.15 et suivants, 40.06 et suivants)
    pos4 = {int(str(a.get("code_sh", "0000")).replace(".", "")[:4] or 0) for a in d.get("articles", [])}
    if any(2801 <= x <= 3899 or 3901 <= x <= 3914 or 4001 <= x <= 4005 for x in pos4):
        out.append(("FDS", "obligatoire", "produit chimique"))
    if str(dec.get("regime_fiscal", "")).startswith("401"):
        out.append(("PPI", "obligatoire", "régime fiscal 401 : exonération des intrants pharmaceutiques"))
    return out


def manquants(d: dict) -> list[dict]:
    """Tout ce qu'il faut demander au déclarant, pièce par pièce puis information par information."""
    ici = _presentes(d)
    res = []
    for code, niveau, motif in requises(d):
        if code in ici:
            continue
        p = _piece(code)
        res.append(dict(type="pièce", code=code, nom=p["nom"], niveau=niveau, motif=motif,
                        emetteur=p["emetteur"], preuve=p["preuve"], base=p["base"]))
    vis = d.get("visite") or {}
    hyp = set((d.get("meta") or {}).get("hypotheses", []))
    for v in referentiel()["visite"]:
        cle = f"visite.{v['champ']}"
        if not vis.get(v["champ"]):
            res.append(dict(type="visite", code=cle, nom=v["nom"], niveau="obligatoire", motif=v["pourquoi"],
                            emetteur="déclarant", preuve="", base=""))
        elif cle in hyp:
            res.append(dict(type="hypothèse", code=cle, nom=f"{v['nom']} : « {vis[v['champ']]} »", niveau="à confirmer",
                            motif="valeur retenue par hypothèse", emetteur="déclarant", preuve="", base=""))
    for cle in sorted(hyp - {f"visite.{v['champ']}" for v in referentiel()["visite"]}):
        res.append(dict(type="hypothèse", code=cle, nom=cle, niveau="à confirmer", motif="valeur retenue par hypothèse",
                        emetteur="déclarant", preuve="", base=""))
    return res


def texte(d: dict) -> str:
    m = manquants(d)
    L = [f"# À fournir — dossier {d['meta']['id']}", ""]
    if not m:
        return "\n".join(L + ["Rien ne manque.", ""])
    for titre, typ in (("Pièces", "pièce"), ("Informations de visite", "visite"), ("Hypothèses à confirmer", "hypothèse")):
        lot = [x for x in m if x["type"] == typ]
        if not lot:
            continue
        L += [f"## {titre}", ""]
        for x in lot:
            L.append(f"- **{x['nom']}** ({x['niveau']}) — {x['motif']}.")
            if x["emetteur"] and typ == "pièce":
                L.append(f"  Émetteur : {x['emetteur']}. Valeur douanière : {x['preuve']} Base : {x['base']}.")
        L.append("")
    return "\n".join(L)
