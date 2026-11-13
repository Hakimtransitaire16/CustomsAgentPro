"""Application unique : fiche + visite + contrôles + registre + données, dans un seul fichier HTML.

- Fonctionne hors ligne (téléphone et ordinateur), aucune dépendance externe.
- La fiche technique est intégrée telle quelle (impression A4 → PDF depuis le navigateur).
- Les saisies de la visite (procès-verbal, photos) remplissent la fiche en direct.
- Les données (dossier JSON, registre CSV, visite JSON) se téléchargent depuis l'onglet Données.
- La note de risques (déclarant seul) est dans l'onglet « Note privée », masquée par défaut et jamais imprimée.
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


def _note_html(d, ctrls):
    import markdown
    from . import moteur
    md = moteur.note_risques(d, ctrls)
    md = md.split("\n", 1)[1] if md.startswith("# ") else md  # le titre est déjà dans l'onglet
    return markdown.markdown(md, extensions=["fenced_code", "tables"])


def construire(d, fidelite=None, pngs=None, registre=None, note=True, partage=False):
    """partage=True : version à transmettre (fiche + visite seulement ; ni contrôles, ni registre, ni données, ni note)."""
    note = note and not partage
    fiche = render.html(d, fidelite=fidelite, pngs=pngs, live=True)
    ctrls = calc.controles(d)
    try:
        note_html = _note_html(d, ctrls) if note else ""
    except Exception as e:  # la note ne doit jamais empêcher l'application de se construire
        note_html = f"<p>Note indisponible : {e}</p>"
    rows = registre if registre is not None and not partage else [ligne(d)]  # jamais le registre des autres clients
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
    # réservé au déclarant : jamais dans la version transmise (risques, note interne, frais, hypothèses de travail)
    PRIVES = {"risques_declarant", "note_interne", "scan", "frais_locaux", "programme"}
    dossier_pur = {k: v for k, v in d.items() if not k.startswith("_") and not (partage and k in PRIVES)}
    if partage:
        dossier_pur["meta"] = {k: v for k, v in d["meta"].items() if k != "hypotheses"}
        dossier_pur["transport"] = {k: v for k, v in d["transport"].items() if k != "surestaries" and not k.startswith("_")}
    return env.get_template("cockpit.html.j2").render(
        d=d, fiche=fiche, ctrls=ctrls, resume=calc.resume(ctrls), rows=rows, kpi=kpi,
        checklist=checklist(d), comptages=comptages, slots=slots,
        fid=fid, fid_ok=sum(1 for f in fid if f["score"] >= 0.95),
        dossier_json=_script_json(dossier_pur), csv_text=_script_json(buf.getvalue()),
        dossier_pretty="" if partage else json.dumps(dossier_pur, ensure_ascii=False, indent=1), note_html=note_html, partage=partage,
    )
