"""OCR du dossier scanné : pages, suggestions d'extraction, contrôle de fidélité.

- pages()      : rasterise le PDF scanné et applique la rotation de chaque page
- extraire()   : propose les références trouvées par motifs (conteneur, MRN, D10, B/L…)
- fidelite()   : relit chaque référence du dossier sur l'image et la compare caractère par caractère
"""
import difflib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps
import pytesseract

NORM = lambda s: re.sub(r"[^0-9A-Z]", "", str(s).upper())

MOTIFS = {
    "conteneur": r"\b[A-Z]{4}\s?\d{7}\b",
    "mrn_manifeste": r"\b\d{2}A\d{10,11}[A-Z0-9]{0,3}\b",
    "d10": r"\b\d{13}DED\d{6}[A-Z0-9]\b",
    "bl": r"\bIST\d{9}\b|\b[A-Z]{3,4}\d{8,10}\b",
    "nif": r"\b\d{15}\b",
    "date": r"\b\d{2}[./-]\d{2}[./-]\d{4}\b",
    "montant_usd": r"\b\d{1,3}(?:[ .,]\d{3})*[.,]\d{2}\s?(?:USD|\$)",
    "code_sh": r"\b\d{4}[.]?\d{2}[.]?\d{2}[.]?\d{2}\b",
}


def pages(d, out_dir):
    """Rasterise le scan → {page: chemin PNG tourné}."""
    sc = d["scan"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dpi = sc.get("dpi", 300)
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", sc["fichier"], str(out / "raw")], check=True)
    res = {}
    for f in sorted(out.glob("raw-*.png")):
        p = int(f.stem.split("-")[-1])
        im = Image.open(f).rotate(sc.get("rotations", {}).get(str(p), 0), expand=True)
        dst = out / f"page{p}.png"
        im.save(dst)
        f.unlink()
        res[p] = dst
    return res


_OCR_CACHE = {}


def ocr_page(png, lang="fra+eng", bandes=6):
    """OCR par bandes (plus fiable sur les scans de documents denses). Mis en cache par page."""
    cle = (str(png), Path(png).stat().st_mtime, lang, bandes)
    if cle not in _OCR_CACHE:
        _OCR_CACHE[cle] = _ocr_page(png, lang, bandes)
    return _OCR_CACHE[cle]


def _fenetres(mots, n_max=6):
    """Groupes de 1 à n_max mots consécutifs d'une même ligne : (texte, x0, y0, x1, y1)."""
    out = []
    for i, m in enumerate(mots):
        x0, y0, x1, y1, txt = m[1], m[2], m[1] + m[3], m[2] + m[4], m[0]
        out.append((txt, x0, y0, x1, y1))
        for k in range(1, n_max):
            if i + k >= len(mots):
                break
            w = mots[i + k]
            if abs(w[2] - m[2]) > max(12, m[4]) or w[1] < x1 - 5 or w[1] - x1 > 3 * max(m[4], 20):
                break
            txt += " " + w[0]
            x1, y0, y1 = w[1] + w[3], min(y0, w[2]), max(y1, w[2] + w[4])
            out.append((txt, x0, y0, x1, y1))
    return out


def _ocr_page(png, lang="fra+eng", bandes=6):
    g = ImageOps.autocontrast(Image.open(png).convert("L"))
    W, H = g.size
    mots, step = [], H // bandes
    for b in range(bandes):
        y0, y1 = max(0, b * step - 80), min(H, (b + 1) * step + 80)
        for x0, x1 in ((0, W // 2 + 100), (W // 2 - 100, W), (0, W)):
            t = pytesseract.image_to_data(g.crop((x0, y0, x1, y1)), lang=lang, config="--psm 6",
                                          output_type=pytesseract.Output.DICT)
            for i, w in enumerate(t["text"]):
                if w.strip():
                    mots.append([w.strip(), x0 + t["left"][i], y0 + t["top"][i], t["width"][i], t["height"][i]])
    return mots


def extraire(pngs):
    """Suggestions de références par motif, page par page (à valider à l'œil)."""
    sugg = {}
    for p, png in pngs.items():
        texte = " ".join(m[0] for m in ocr_page(png))
        for nom, rx in MOTIFS.items():
            for v in set(re.findall(rx, texte)):
                sugg.setdefault(nom, []).append({"valeur": v, "page": p})
    return sugg


def _lire_zone(im, zone):
    crop = im.crop(tuple(zone))
    big = ImageOps.autocontrast(crop).resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    txts = [pytesseract.image_to_string(big, lang="eng", config=f"--psm {p}").strip() for p in ("7", "6", "13")]
    return crop, txts


def fidelite(d, pngs, snip_dir):
    """Compare chaque référence du dossier à sa zone sur l'image scannée.

    Résultat par référence : score (0–1), texte OCR, chemin de l'extrait d'image.
    score ≥ 0,95 → identique ; sinon → à confirmer visuellement (l'extrait est fourni).
    """
    snip = Path(snip_dir)
    snip.mkdir(parents=True, exist_ok=True)
    cache, res = {}, []
    for r in d.get("references_scan", []):
        p = r["page"]
        if p not in cache:
            cache[p] = Image.open(pngs[p]).convert("L")
        im = cache[p]
        if r.get("zone"):
            crop, txts = _lire_zone(im, r["zone"])
        else:  # pas de zone : recherche dans l'OCR de la page
            nv0 = NORM(r["valeur"])
            best = max(_fenetres(ocr_page(pngs[p])),
                       key=lambda f: difflib.SequenceMatcher(None, nv0, NORM(f[0])).ratio() - 0.002 * abs(len(NORM(f[0])) - len(nv0)))
            z = [best[1] - 14, best[2] - 10, best[3] + 14, best[4] + 10]
            crop, txts = _lire_zone(im, z)
        nv = NORM(r["valeur"])
        score = max(1.0 if nv and nv in NORM(t) else difflib.SequenceMatcher(None, nv, NORM(t)).ratio() for t in txts)
        h = 64
        crop.resize((max(1, int(crop.width * h / crop.height)), h)).save(snip / f"{r['id']}.jpg", quality=70)
        res.append({"id": r["id"], "label": r["label"], "valeur": r["valeur"], "page": p,
                    "score": round(score, 3), "ocr": " | ".join(t.replace("\n", " ") for t in txts),
                    "extrait": str(snip / f"{r['id']}.jpg"),
                    "resultat": "identique" if score >= 0.95 else "à confirmer visuellement"})
    return res


def corpus(pngs, cache_json=None):
    """Texte OCR normalisé de toutes les pages (pour la relecture du PDF produit)."""
    if cache_json and Path(cache_json).exists():
        return json.loads(Path(cache_json).read_text())
    c = {str(p): NORM("".join(m[0] for m in ocr_page(png))) for p, png in pngs.items()}
    if cache_json:
        Path(cache_json).write_text(json.dumps(c))
    return c
