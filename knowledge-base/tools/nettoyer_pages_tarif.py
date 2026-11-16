"""Retire des libellés du tarif 2016 le numéro de page du PDF resté collé à la dernière ligne de chaque page.

Exemple : « Autres 218 » (3926.90.99.00, page 218) → « Autres ». Les numéros de page croissent dans l'ordre
des lignes : seul un nombre final qui prolonge cette suite est retiré (« Animaux morts du Chapitre 1 » est conservé).
Idempotent. Usage : python knowledge-base/tools/nettoyer_pages_tarif.py [--appliquer]
"""
import json
import re
import sys
from pathlib import Path

F = Path(__file__).resolve().parent.parent / "data" / "tarif_2016.json"


def nettoyer(lignes, saut_max=12):
    page, faits = 0, []
    for l in lignes:
        m = re.search(r"^(.*\D) (\d{1,3})$", l.get("label", ""))
        if not m:
            continue
        nv = int(m[2])
        if page < nv <= page + saut_max:
            faits.append((l["code"], l["label"], nv))
            l["label"] = m[1].rstrip()
            if l.get("full_label", "").endswith(f" {nv}"):
                l["full_label"] = l["full_label"][: -len(f" {nv}")].rstrip()
            page = nv
    return faits


if __name__ == "__main__":
    base = json.loads(F.read_text(encoding="utf-8"))
    faits = nettoyer(base["lines"])
    if len(faits) < 50:     # fichier déjà propre : les rares nombres finaux restants sont de vrais libellés (« du Chapitre 8 »)
        print("rien à nettoyer")
        sys.exit(0)
    print(f"{len(faits)} libellés nettoyés (pages {faits[0][2]} à {faits[-1][2]})")
    if "--appliquer" in sys.argv:
        F.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
        print("écrit :", F)
