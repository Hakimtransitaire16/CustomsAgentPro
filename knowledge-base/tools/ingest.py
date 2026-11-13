"""Intègre de nouveaux documents dans la base de connaissances, en une commande.

    python tools/ingest.py ~/Téléchargements/douane/           # un dossier
    python tools/ingest.py fichier1.pdf fichier2.pdf           # des fichiers
    python tools/ingest.py --rapport                           # état du référentiel, sans rien importer

Pour chaque PDF :
1. identification dans le référentiel (nom officiel du fichier, sinon titre lu en première page) ;
2. copie dans sources/ sous son nom officiel (l'original n'est pas modifié) ;
3. extraction du texte dans text/ : pdftotext, et OCR (fra + ara, 300 dpi) si le PDF est un scan ;
4. reconstruction de data/ et de l'index (tools/build_kb.py) puis du référentiel (REFERENTIEL.md).

Un PDF absent du référentiel est intégré comme document de recherche, sous un id dérivé de son nom,
et listé dans data/sources_ajoutees.json.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from referentiel import catalogue  # noqa: E402

AJOUTS = ROOT / "data" / "sources_ajoutees.json"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"^[0-9a-f]{8}-", "", s)                 # préfixe ajouté par l'envoi en pièce jointe
    s = re.sub(r"\s*\(\d+\)$|[-_]\d$|_+$", "", s)       # « fichier (1) », « fichier-2 », « fichier_1 »
    return re.sub(r"[^a-z0-9]+", "", s)


def premiere_page(pdf: Path) -> str:
    r = subprocess.run(["pdftotext", "-l", "2", str(pdf), "-"], capture_output=True, text=True)
    txt = re.sub(r"\s+", " ", r.stdout).strip()
    if len(txt) < 100:  # scan : OCR de la première page pour l'identifier
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["pdftoppm", "-r", "200", "-l", "1", "-gray", "-png", str(pdf), f"{tmp}/p"], check=False)
            png = next(Path(tmp).glob("p-*.png"), None)
            if png:
                txt = re.sub(r"\s+", " ", subprocess.run(["tesseract", str(png), "-", "-l", "fra+ara"],
                                                         capture_output=True, text=True).stdout).strip()
    return txt[:3000]


def identifier(pdf: Path) -> dict | None:
    cat = [s for s in catalogue() if s["fichier"]]
    stem = norm(pdf.stem)
    for s in cat:
        if norm(Path(s["fichier"]).stem) == stem:
            return s
    for s in cat:  # nom raccourci ou allongé par le navigateur
        f = norm(Path(s["fichier"]).stem)
        if len(stem) > 8 and (f.startswith(stem) or stem.startswith(f)):
            return s
    texte = norm(premiere_page(pdf))
    meilleur, score = None, 0
    for s in cat:
        mots = [norm(m) for m in re.findall(r"\w{5,}", s["titre"])]
        nums = re.findall(r"\d{2}-\d{2,3}|\d{4}", s["titre"])
        sc = sum(1 for m in mots if m and m in texte) + 3 * sum(1 for n in nums if norm(n) in texte)
        if sc > score:
            meilleur, score = s, sc
    return meilleur if score >= 6 else None


def extraire(pdf: Path, typ: str, out: Path) -> tuple[str, int]:
    """Texte du PDF ; OCR si la couche texte est vide. Renvoie (méthode, nb de caractères)."""
    opts = [] if typ == "texte" else ["-layout"]  # JO en deux colonnes : ordre de lecture
    subprocess.run(["pdftotext", *opts, str(pdf), str(out)], check=False)
    pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True,
                                                             text=True).stdout or "Pages: 1").group(1))
    txt = out.read_text(encoding="utf-8", errors="ignore") if out.exists() else ""
    arabe = arabe_dominant(txt) or arabe_dominant(premiere_page(pdf))
    # Couche texte arabe des PDF officiels : glyphes de présentation, « ك » rendu « آ », mots coupés
    # par la justification → l'OCR arabe donne un texte bien plus fidèle (contrôlé sur le code de commerce).
    if len(txt.strip()) >= 200 * max(pages, 1) * 0.3 and not arabe:
        return "pdftotext", len(txt)
    from concurrent.futures import ThreadPoolExecutor
    langue = "ara" if arabe else "fra+ara"
    # Scan sans couche texte (Journal officiel en deux colonnes) : segmentation automatique des colonnes (psm 3) ;
    # PDF à une colonne avec couche texte défaillante : bloc unique (psm 4)
    psm = "4" if len(txt.strip()) >= 200 * max(pages, 1) * 0.3 else "3"
    with tempfile.TemporaryDirectory() as tmp:  # OCR page par page, en parallèle
        subprocess.run(["pdftoppm", "-r", "300", "-gray", "-png", str(pdf), f"{tmp}/p"], check=True)
        pngs = sorted(Path(tmp).glob("p-*.png"), key=lambda p: int(re.search(r"(\d+)\.png$", p.name).group(1)))
        ocr = lambda png: subprocess.run(["tesseract", str(png), "-", "-l", langue, "--psm", psm],
                                         capture_output=True, text=True).stdout
        with ThreadPoolExecutor(max_workers=2) as ex:
            parts = list(ex.map(ocr, pngs))
        txt = "\n\f".join(parts)
    out.write_text(txt, encoding="utf-8")
    return "ocr-" + langue, len(txt)


def arabe_dominant(txt: str) -> bool:
    lettres = re.findall(r"[^\W\d_]", txt)
    return len(lettres) > 200 and len(re.findall(r"[\u0600-\u06FF\uFB50-\uFEFF]", txt)) > 0.5 * len(lettres)


def nb_pages(pdf: Path) -> int:
    m = re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout)
    return int(m.group(1)) if m else 0


def meme_fichier(a: Path, b: Path) -> bool:
    import hashlib
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    return a.stat().st_size == b.stat().st_size and h(a) == h(b)


def ingerer(fichiers: list[Path]) -> list[dict]:
    ajouts = json.loads(AJOUTS.read_text(encoding="utf-8")) if AJOUTS.exists() else []
    rapport = []
    for pdf in fichiers:
        src = identifier(pdf)
        if src:
            nom, typ, sid = src["fichier"], src["type"], src["id"]
            dest = ROOT / "sources" / nom
            if dest.exists() and pdf.resolve() != dest.resolve():
                if meme_fichier(pdf, dest):
                    rapport.append({"fichier": pdf.name, "id": sid, "type": typ, "extraction": "déjà présent",
                                    "caracteres": 0, "reconnu": True})
                    continue
                if nb_pages(pdf) <= nb_pages(dest):  # ne jamais remplacer une version complète par un extrait
                    src = None
        if not src:
            nom = re.sub(r"[^\w.-]+", "_", pdf.name)
            typ, sid = "guide", "ajout-" + norm(pdf.stem)[:40]
            titre = premiere_page(pdf)[:120].strip() or pdf.stem
            if not any(a["id"] == sid for a in ajouts):
                ajouts.append({"id": sid, "fichier": nom, "titre": titre, "type": typ})
        dest = ROOT / "sources" / nom
        if pdf.resolve() != dest.resolve():
            shutil.copy2(pdf, dest)
        methode, n = extraire(dest, typ, ROOT / "text" / (Path(nom).stem + ".txt"))
        rapport.append({"fichier": pdf.name, "id": sid, "type": typ, "extraction": methode, "caracteres": n,
                        "reconnu": bool(src)})
    AJOUTS.write_text(json.dumps(ajouts, ensure_ascii=False, indent=1), encoding="utf-8")
    return rapport


def main(argv: list[str]) -> int:
    if "--rapport" not in argv:
        fichiers = []
        for a in argv:
            p = Path(a).expanduser()
            fichiers += sorted(p.rglob("*.pdf")) if p.is_dir() else [p]
        if not fichiers:
            print(__doc__)
            return 1
        for r in ingerer(fichiers):
            etat = r["id"] if r["reconnu"] else f"{r['id']} (hors référentiel, indexé pour la recherche)"
            nb = f"{r['caracteres']:,}".replace(",", " ")
            print(f"  {r['fichier']:<60} → {etat} · {r['extraction']} · {nb} car.")
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_kb.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "referentiel.py")], check=True)
    manquants = [s for s in catalogue() if s["statut"] != "base" and s["priorite"] == 1]
    if manquants:
        print(f"\nÀ télécharger en priorité ({len(manquants)}) :")
        for s in manquants:
            print(f"  {s['titre'][:80]}\n    {s['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
