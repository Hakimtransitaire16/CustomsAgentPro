"""Extrait du tarif DGD 2016 : les 21 sections (titre, chapitres, notes) et les Règles générales (RGI).

Usage (depuis knowledge-base/) :
    python tools/build_sections.py

Entrée : text/tarif-douanier-2016-10-chiffres-pour-telechargement.txt
Sortie : data/tarif_2016_sections.json

- Titres et chapitres : table des matières du tarif.
- Notes de section : en-tête centré « Section X » du corps, jusqu'au premier « Chapitre N ».
  Les sections II et III n'ont pas de notes dans le texte extrait (champ vide).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TXT = ROOT / "text" / "tarif-douanier-2016-10-chiffres-pour-telechargement.txt"
OUT = ROOT / "data" / "tarif_2016_sections.json"

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV",
         "XVI", "XVII", "XVIII", "XIX", "XX", "XXI"]
TOC_SEC = re.compile(r"^SECTION\s+([IVXL]+)\s{2,}(\S.*?)\s*$")
TOC_CHAP = re.compile(r"^\s+Chapitre\s+(\d{1,2})\s{2,}")
BODY_SEC = re.compile(r"^\s{20,}Section\s+([IVXL]+)\s*$")
BODY_CHAP = re.compile(r"^\s{15,}Chapitre\s+(\d{1,2})\s*$")
NOISE = re.compile(r"DOUANES ALGERIENNES|TABLES? DES MATIERES|^\s*-?\s*\d+\s*-?\s*$|^\s*SECTION\s+[IVXL]+\s*$|^\s*CHAPITRE\s+\d+")


def clean_block(lines: list[str]) -> str:
    keep = [l.rstrip() for l in lines if l.strip() and not NOISE.search(l)]
    return "\n".join(re.sub(r"\s{2,}", " ", l).strip() for l in keep)


def main() -> None:
    lines = TXT.read_text(encoding="utf-8").splitlines()
    rgi_start = next(i for i, l in enumerate(lines) if l.strip() == "REGLES GENERALES")

    # 1. Table des matières
    sections, cur, in_title = {}, None, False
    for l in lines[:rgi_start]:
        if m := TOC_SEC.match(l):
            cur = m.group(1)
            sections[cur] = {"section": cur, "titre": m.group(2), "chapitres": [], "notes": ""}
            in_title = True
        elif cur and (m := TOC_CHAP.match(l)):
            sections[cur]["chapitres"].append(int(m.group(1)))
            in_title = False
        elif cur and in_title and l.strip() and not re.match(r"^\s*Notes?\b", l.strip()) and l.strip().isupper():
            sections[cur]["titre"] += " " + l.strip()
        elif l.strip().startswith("Note"):
            in_title = False
    for s in sections.values():
        s["titre"] = re.sub(r"\s+", " ", s["titre"]).strip()

    # 2. Notes de section dans le corps
    chap_at = [i for i, l in enumerate(lines) if BODY_CHAP.match(l)]
    for i, l in enumerate(lines):
        m = BODY_SEC.match(l)
        if not m or m.group(1) not in sections or sections[m.group(1)]["notes"]:
            continue
        end = next((j for j in chap_at if j > i), i + 200)
        block = lines[i + 1:end]
        k = next((x for x, b in enumerate(block) if re.match(r"^\s*Notes?\b", b.strip())), None)
        if k is not None:
            sections[m.group(1)]["notes"] = clean_block(block[k:])

    # 3. RGI
    rgi_end = next(i for i in range(rgi_start, len(lines)) if re.match(r"^\s*-\s*6\s*-\s*$", lines[i]))
    rgi = clean_block(lines[rgi_start + 1:rgi_end])

    ordered = [sections[r] for r in ROMAN if r in sections]
    OUT.write_text(json.dumps({"_source": "Tarif douanier DGD 2016 — table des matières, notes de sections, RGI",
                               "rgi": rgi, "sections": ordered}, ensure_ascii=False, indent=1), encoding="utf-8")
    for s in ordered:
        c = s["chapitres"]
        print(f'{s["section"]:>5}  ch. {c[0] if c else "?"}–{c[-1] if c else "?"}  notes {len(s["notes"]):>5} car.  {s["titre"][:70]}')


if __name__ == "__main__":
    main()
