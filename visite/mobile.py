"""Page de visite pour téléphone : check-list, comptages, photos, constatations.

La page fonctionne hors ligne (un seul fichier HTML). Le bouton « Exporter la visite »
télécharge visite_<id>.json, que la commande `pv` réinjecte dans la fiche PDF.
"""
from jinja2 import Environment, FileSystemLoader

from .data import n
from .render import TPL, checklist

SLOTS = ["Porte et scellé", "Chargement à l'ouverture", "Palette ouverte"]


def page(d):
    env = Environment(loader=FileSystemLoader(TPL), autoescape=False)
    env.filters["n"] = n
    comptages = [("Colis / palettes", d["declaration"]["nb_colis"])]
    for a in d["articles"]:
        q = a.get("quantite", {})
        if q.get("nombre"):
            comptages.append((f"{a['designation']} — {q.get('unite', '')}", q["nombre"]))
    slots = SLOTS + [f"Étiquette {a['designation']}" for a in d["articles"]] + ["Pesée de contrôle"]
    return env.get_template("visite.html.j2").render(d=d, checklist=checklist(d), comptages=comptages, slots=slots)
