"""Relecture automatique du PDF produit : chaque référence doit y figurer à l'identique,
et chaque nombre long doit venir des scans, d'un calcul déclaré, ou d'une zone confirmée."""
import re
import subprocess

from .ocr import NORM


def relire(pdf_path, d, corpus=None):
    txt = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True).stdout
    # l'empreinte SHA-256 du pied de page est un contrôle d'intégrité, pas une donnée du dossier
    txt = re.sub(r"empreinte\s+SHA-256\s+(?:[0-9a-f]{8}\s*){1,4}", " ", txt)
    nt = NORM(txt)
    refs = d.get("references_scan", [])
    manquantes = [r["id"] for r in refs if NORM(r["valeur"]) not in nt]
    connus = {NORM(r["valeur"]) for r in refs}
    # nombres issus des données du dossier (ils ont été vérifiés ou sont calculés par calc.py)
    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                yield from walk(v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v)
        elif isinstance(x, (int, float, str)):
            yield str(x)
    donnees = NORM(" ".join(walk({k: v for k, v in d.items() if not k.startswith("_")})))
    nb = set()
    for t in re.findall(r"(?<![\w])[\dA-Z][\dA-Z]*(?:[ .,/-]?\d{3})*(?:[.,]\d+)?", txt):
        x = NORM(t)
        if sum(ch.isdigit() for ch in x) >= 6:
            nb.add(x)
    # totaux calculés par le moteur (somme des taxes de chaque article)
    from .data import n
    calcules = "".join(NORM(n(sum(t["montant"] for t in a["taxes"]), 2)) for a in d["articles"])
    sources = (corpus or "") + donnees + calcules
    inconnus = sorted(x for x in nb if x not in sources and x not in connus)
    return {"references": len(refs), "references_presentes": len(refs) - len(manquantes),
            "manquantes": manquantes, "nombres_longs": len(nb), "nombres_inconnus": inconnus}
