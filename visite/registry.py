"""Registre des dossiers (JSON + CSV, compatible Excel / Power BI) et tableau de bord HTML."""
import csv
import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from . import calc
from .data import date, n, sh
from .render import TPL

CHAMPS = ["id", "date_d10", "d10", "mrn", "importateur", "fournisseur", "origine", "codes_sh", "articles",
          "valeur_da", "droits_da", "taux_pression", "circuit", "delai_accostage_d10", "lieu_visite",
          "inspecteur", "controles_ok", "controles_alerte", "controles_erreur",
          # indicateurs pour l'analyse (un dossier = une ligne du jeu de données)
          "bureau", "regime_fiscal", "incoterm", "devise", "armateur", "transit_jours", "surestaries_da",
          "exonere_da", "cout_connu_da", "alertes", "pieces_manquantes", "maj"]


def ligne(d):
    dec, t = d["declaration"], d["transport"]
    r = calc.resume(calc.controles(d))
    acc, d10 = date(t.get("date_accostage")), date(dec.get("date_heure"))
    return {
        "id": d["meta"]["id"], "date_d10": d10.strftime("%Y-%m-%d") if d10 else "", "d10": dec["numero"], "mrn": dec["mrn"],
        "importateur": d["parties"]["importateur"]["nom"], "fournisseur": d["parties"]["fournisseur"]["nom"],
        "origine": (d.get("origine") or {}).get("code", ""), "codes_sh": " ".join(sh(a["code_sh"]) for a in d["articles"]),
        "articles": len(d["articles"]), "valeur_da": dec["valeur_da"], "droits_da": d["liquidation"]["total"],
        "taux_pression": round(d["liquidation"]["total"] / dec["valeur_da"] * 100, 1),
        "circuit": dec.get("circuit", ""), "delai_accostage_d10": (d10 - acc).days if acc and d10 else "",
        "lieu_visite": (d.get("visite") or {}).get("lieu", ""), "inspecteur": (d.get("visite") or {}).get("inspecteur", ""),
        "controles_ok": r["ok"], "controles_alerte": r["alerte"], "controles_erreur": r["erreur"],
        **indicateurs(d),
        "maj": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def indicateurs(d):
    """Variables d'analyse d'un dossier : délais, coûts, alertes. Sert de base aux statistiques et, plus tard, aux modèles."""
    from . import exigences, expertise
    dec, t = d["declaration"], d["transport"]
    bl, acc = date(t.get("date_bl")), date(t.get("date_accostage"))
    sur = expertise.surestaries(d)
    exo = sum(x["montant"] for a in d["articles"] for x in a.get("taxes", []) if x.get("exonere"))
    frais = sum(f.get("ht", 0) for f in d.get("frais_locaux", []))
    return {
        "bureau": (dec.get("bureau") or "").split("—")[0].strip(), "regime_fiscal": dec.get("regime_fiscal", ""),
        "incoterm": dec.get("incoterm", ""), "devise": dec.get("devise", ""),
        "armateur": (t.get("bad") or {}).get("agent", ""),
        "transit_jours": (acc - bl).days if acc and bl else "",
        "surestaries_da": round(sur["total_da"] + (sur["gestion_da"] or 0)) if sur and sur["total_da"] else "",
        "exonere_da": round(exo) if exo else "",
        "cout_connu_da": round(dec["valeur_da"] + d["liquidation"]["total"] + frais),
        "alertes": " ".join(c["id"] for c in calc.controles(d) if c["statut"] != "ok"),
        "pieces_manquantes": sum(1 for x in exigences.manquants(d) if x["type"] == "pièce" and x["niveau"] == "obligatoire"),
    }


def enregistrer(d, reg_dir):
    reg = Path(reg_dir)
    reg.mkdir(parents=True, exist_ok=True)
    fj = reg / "registre.json"
    rows = json.loads(fj.read_text(encoding="utf-8")) if fj.exists() else []
    new = ligne(d)
    rows = [x for x in rows if x["id"] != new["id"]] + [new]
    rows.sort(key=lambda x: x["date_d10"], reverse=True)
    fj.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(reg / "registre.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, delimiter=";")
        w.writeheader()
        w.writerows(rows)
    return rows


def tableau_de_bord(reg_dir, out_html):
    rows = json.loads((Path(reg_dir) / "registre.json").read_text(encoding="utf-8"))
    tot_v = sum(r["valeur_da"] for r in rows)
    tot_d = sum(r["droits_da"] for r in rows)
    delais = [r["delai_accostage_d10"] for r in rows if r["delai_accostage_d10"] != ""]
    rouge = sum(1 for r in rows if r["circuit"] == "rouge")
    par_origine, par_code = {}, {}
    for r in rows:
        par_origine[r["origine"]] = par_origine.get(r["origine"], 0) + r["valeur_da"]
        for c in r["codes_sh"].split():
            par_code[c] = par_code.get(c, 0) + 1
    kpi = {"dossiers": len(rows), "valeur": tot_v, "droits": tot_d, "pression": tot_d / tot_v * 100 if tot_v else 0,
           "rouge": rouge / len(rows) * 100 if rows else 0, "delai": sum(delais) / len(delais) if delais else 0}
    env = Environment(loader=FileSystemLoader(TPL), autoescape=True)
    env.filters["n"] = n
    html = env.get_template("dashboard.html.j2").render(rows=rows, kpi=kpi,
        origines=sorted(par_origine.items(), key=lambda x: -x[1]), codes=sorted(par_code.items(), key=lambda x: -x[1]),
        genere=datetime.now().strftime("%d/%m/%Y %H:%M"))
    Path(out_html).write_text(html, encoding="utf-8")
    return kpi
