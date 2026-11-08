"""Application unique : fiche + visite + contrôles + registre + données, dans un seul fichier HTML.

- Fonctionne hors ligne (téléphone et ordinateur), aucune dépendance externe.
- La fiche technique est intégrée telle quelle (impression A4 → PDF depuis le navigateur).
- Les saisies de la visite (procès-verbal, photos) remplissent la fiche en direct.
- Les données (dossier JSON, registre CSV, visite JSON) se téléchargent depuis l'onglet Données.
"""
import csv
import io
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from . import calc, render
from .data import n, sh
from .mobile import SLOTS
from .registry import CHAMPS, ligne
from .render import TPL, checklist


def _script_json(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def construire(d, fidelite=None, pngs=None, registre=None):
    fiche = render.html(d, fidelite=fidelite, pngs=pngs, live=True)
    ctrls = calc.controles(d)
    rows = registre if registre is not None else [ligne(d)]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CHAMPS, delimiter=";")
    w.writeheader()
    w.writerows(rows)
    comptages = [("Colis / palettes", d["declaration"]["nb_colis"])] + [
        (f"{a['designation']} — {a['quantite'].get('unite', '')}", a["quantite"]["nombre"])
        for a in d["articles"] if a.get("quantite", {}).get("nombre")]
    slots = SLOTS + [f"Étiquette {a['designation']}" for a in d["articles"]] + ["Pesée de contrôle"]
    tot_v = sum(r["valeur_da"] for r in rows)
    tot_d = sum(r["droits_da"] for r in rows)
    delais = [r["delai_accostage_d10"] for r in rows if r["delai_accostage_d10"] != ""]
    kpi = {"dossiers": len(rows), "valeur": tot_v, "droits": tot_d, "pression": tot_d / tot_v * 100 if tot_v else 0,
           "rouge": sum(1 for r in rows if r["circuit"] == "rouge") / len(rows) * 100 if rows else 0,
           "delai": sum(delais) / len(delais) if delais else 0}
    fid = fidelite or []
    env = Environment(loader=FileSystemLoader(TPL), autoescape=False)
    env.filters.update(n=n, sh=sh)
    dossier_pur = {k: v for k, v in d.items() if not k.startswith("_")}
    return env.get_template("cockpit.html.j2").render(
        d=d, fiche=fiche, ctrls=ctrls, resume=calc.resume(ctrls), rows=rows, kpi=kpi,
        checklist=checklist(d), comptages=comptages, slots=slots,
        fid=fid, fid_ok=sum(1 for f in fid if f["score"] >= 0.95),
        dossier_json=_script_json(dossier_pur), csv_text=_script_json(buf.getvalue()),
        dossier_pretty=json.dumps(dossier_pur, ensure_ascii=False, indent=1),
    )
