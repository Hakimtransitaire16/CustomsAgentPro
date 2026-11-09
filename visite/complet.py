"""Dossier complet en un seul PDF : couverture et synthèse, fiche de visite, fiche de terrain, note interne.

La fiche de visite (partie A) et la fiche de terrain (partie B) peuvent être remises au service.
La note interne (partie C) est réservée au déclarant : elle est marquée comme telle sur chaque page.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pypdf import PdfReader, PdfWriter

from . import calc, moteur, render
from .data import n, sh
from .mobile import SLOTS

TPL = Path(__file__).parent / "templates"


def _date(s: str) -> dt.date | None:
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", s or "") or None
    if m:
        return dt.date(int(m[3]), int(m[2]), int(m[1]))
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return dt.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def _fr(x: dt.date | None) -> str:
    return x.strftime("%d/%m/%Y") if x else ""


def chronologie(d: dict) -> list[tuple[str, str, str]]:
    """Événements datés du dossier, triés (date, événement, pièce)."""
    ev = []
    for doc in d.get("documents", []):
        if doc.get("code") == "D10":
            continue  # le dépôt du D10 est daté plus bas, à l'heure près
        x = _date(doc.get("date", ""))
        if x:
            ev.append((x, f"{doc['titre']} n° {doc.get('numero', '')}", doc.get("emetteur", "")))
    dom = d["declaration"].get("domiciliation", {})
    if _date(dom.get("date", "")):
        ev.append((_date(dom["date"]), f"Domiciliation bancaire {dom.get('numero', '')}", dom.get("banque", "")))
    arr = d.get("arrivee", {})
    if _date(arr.get("accostage", "")):
        ev.append((_date(arr["accostage"]), f"Accostage — {arr['accostage'][10:].strip(' à')}", "Avis d'arrivée"))
    if _date(d["declaration"].get("ligne_sommier", "")):
        ev.append((_date(d["declaration"]["ligne_sommier"]), "Inscription au sommier (case 30)", "D10"))
    if _date(d["declaration"].get("date_heure", "")):
        ev.append((_date(d["declaration"]["date_heure"]), f"Dépôt du D10 n° {d['declaration']['numero']}", "D10"))
    if _date(d["meta"].get("date_fiche", "")):
        ev.append((_date(d["meta"]["date_fiche"]), "Établissement de la fiche de visite", d["meta"]["declarant"]["nom"]))
    vu = set()
    out = []
    for x, e, p in sorted(ev, key=lambda t: t[0]):
        if (x, e) not in vu:
            vu.add((x, e))
            out.append((_fr(x), e, p))
    return out


def delais(d: dict) -> list[tuple[str, str, str, str]]:
    """Délais légaux calculés depuis l'accostage (art. 71, 74, 209 du code des douanes)."""
    acc = _date(d.get("arrivee", {}).get("accostage", ""))
    d10 = _date(d["declaration"].get("date_heure", ""))
    if not (acc and d10):
        return []
    fin71 = acc + dt.timedelta(days=21)
    m = fin71.month + 2
    try:
        fin209 = fin71.replace(year=fin71.year + (m - 1) // 12, month=(m - 1) % 12 + 1)
    except ValueError:
        fin209 = fin71 + dt.timedelta(days=61)
    etat = lambda lim: "dépassé" if d10 > lim else "respecté"
    return [
        ("Séjour en dépôt temporaire : 21 jours", "Art. 71", _fr(fin71), etat(fin71)),
        ("Puis constitution d'office en dépôt de douane", "Art. 74 (rédigé par l'art. 123 LF 2026)", _fr(fin71), "à vérifier"),
        ("Séjour en dépôt de douane : 2 mois", "Art. 209", f"≈ {_fr(fin209)}", etat(fin209)),
        ("Marchandises non enlevées : vente aux enchères", "Art. 210", f"après le {_fr(fin209)}", "risque"),
    ], (d10 - acc).days


def enjeux(d: dict) -> list[tuple[str, float, str]]:
    """Montants en jeu : payé, exonéré, et coût si l'exonération était refusée (estimation)."""
    v = d["declaration"]["valeur_da"]
    out = [("Droits et taxes payés (D10)", d["liquidation"]["total"], "récapitulatif du D10")]
    ex = sum(t["montant"] for a in d["articles"] for t in a.get("taxes", []) if t.get("exonere"))
    if ex:
        out.append(("Droits et taxes exonérés (DD + TVA)", ex, f"régime fiscal {d['declaration']['regime_fiscal']}"))
        cs = sum(t["montant"] for a in d["articles"] for t in a.get("taxes", []) if t["code"] == "CS")
        for a in d["articles"]:
            dd = next((t for t in a["taxes"] if t["code"] == "DD"), None)
            if dd:
                tva = round((v + dd["montant"] + cs) * 0.19, 2)
                out.append((f"Si l'exonération était refusée : DD {n(dd['quotite'])} % + TVA 19 % sur (valeur + DD + CS)",
                            dd["montant"] + tva, "estimation du moteur"))
                dd15 = round(v * 0.15, 2)
                out.append(("Si reclassement en ligne à 15 % sans exonération : DD 15 % + TVA",
                            dd15 + round((v + dd15 + cs) * 0.19, 2), "estimation du moteur"))
    return out


def construire(d: dict, fiche_pdf: Path, sortie: Path) -> Path:
    env = Environment(loader=FileSystemLoader(TPL), autoescape=False)
    env.filters.update(n=n, sh=sh)
    ctrls = calc.controles(d)
    dl = delais(d)
    textes = []
    for instr, num in [("Code des douanes — loi n° 79-07", "71"), ("Loi 25-17", "123"),
                       ("Code des douanes — loi n° 79-07", "209"), ("Code des douanes — loi n° 79-07", "210")]:
        a = next(iter(moteur.article(num, instr)), None)
        if a:
            t = re.sub(r"^\([^)]*\)\s*", "", a["texte"]).strip()
            t = re.split(r"\s(?:CHAPITRE|Section \d)\s", t)[0]
            textes.append((f"{'LF 2026' if instr.startswith('Loi') else 'Code des douanes'}, art. {a['article']}", t[:700] + ("…" if len(t) > 700 else "")))
    nb_fiche = len(PdfReader(str(fiche_pdf)).pages)
    ctx = dict(d=d, ctrls=ctrls, resume=calc.resume(ctrls), chrono=chronologie(d), delais=dl[0] if dl else [],
               jours=dl[1] if dl else None, enjeux=enjeux(d), textes=textes, checklist=render.checklist(d), slots=SLOTS + ["Étiquette d'une boîte", "Ampoules (gros plan)", "Pesée de contrôle"],
               css=(TPL / "style.css").read_text(encoding="utf-8"), initiales="".join(w[0] for w in d["meta"]["declarant"]["nom"].split()[:2]),
               nb_fiche=nb_fiche, date_fiche=render._date_fr(d["meta"].get("date_fiche", "")))
    parties = {}
    for part in ("couverture", "terrain", "note"):
        html = env.get_template("complet.html.j2").render(partie=part, **ctx)
        f = sortie / f"_complet_{part}.pdf"
        render.pdf(html, f)
        parties[part] = f
    w = PdfWriter()
    for f in (parties["couverture"], fiche_pdf, parties["terrain"], parties["note"]):
        for p in PdfReader(str(f)).pages:
            w.add_page(p)
    w.add_metadata({"/Title": f"Dossier de visite — {d['meta'].get('produit_titre', '')} — D10 {d['declaration']['numero']}",
                    "/Author": d["meta"]["declarant"]["nom"]})
    out = sortie / f"Dossier_complet_{d['meta']['id']}.pdf"
    with open(out, "wb") as fh:
        w.write(fh)
    for f in parties.values():
        f.unlink(missing_ok=True)
        f.with_suffix(".html").unlink(missing_ok=True)
    return out
