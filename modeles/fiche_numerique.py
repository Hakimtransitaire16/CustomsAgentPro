"""Copie électronique d'une fiche papier remplie à la main.

1. Le déclarant photographie la fiche remplie (pages 1 et 2) et l'envoie.
2. Les données sont transcrites dans un JSON (schéma : voir EXEMPLE ci-dessous) et relues avec lui.
3. `ajouter` lit le code QR sur la photo (numéro de fiche + clé), chiffre données et photos (AES-GCM 128 bits)
   et écrit f/<numéro>.bin, publié avec la page modeles/fiches_viewer/index.html.

La clé n'existe que dans le code QR imprimé : seul celui qui scanne la fiche (ou reçoit son code) la lit.
Les fichiers .bin sont des données clients chiffrées : ils ne vont jamais dans le dépôt.

Usage : python modeles/fiche_numerique.py <donnees.json> <dossier_sortie> <photo1.jpg> [photo2.jpg ...]
"""
import base64
import io
import json
import os
import re
import sys
from pathlib import Path

MOTIF = re.compile(r"#f-(GM-\d{2}-\d{5}-\d)-([0-9a-f]{32})$")


def lire_qr(photo: str):
    """Numéro et clé lus dans le code QR de la photo (plusieurs échelles, deux détecteurs)."""
    import cv2
    im = cv2.imread(photo)
    if im is None:
        raise SystemExit(f"photo illisible : {photo}")
    dets = [cv2.QRCodeDetector()]
    if hasattr(cv2, "QRCodeDetectorAruco"):
        dets.append(cv2.QRCodeDetectorAruco())
    h, w = im.shape[:2]
    zones = [im, im[0:int(h * .25), :]]
    for z in zones:
        for s in (1, .5, .75, 1.5):
            img = cv2.resize(z, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s != 1 else z
            for d in dets:
                v, _, _ = d.detectAndDecode(img)
                m = MOTIF.search(v or "")
                if m:
                    return m.group(1), m.group(2)
    return None


def jpeg(photo: str, cote=1600, q=80) -> str:
    from PIL import Image
    im = Image.open(photo).convert("RGB")
    im.thumbnail((cote, cote))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def chiffrer(cle_hex: str, donnees: dict) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    ct = AESGCM(bytes.fromhex(cle_hex)).encrypt(nonce, json.dumps(donnees, ensure_ascii=False).encode(), None)
    return base64.b64encode(nonce + ct).decode()


def ajouter(json_path: str, sortie: str, photos: list, numero=None, cle=None) -> Path:
    d = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if not (numero and cle):
        lu = None
        for p in photos:
            lu = lire_qr(p)
            if lu:
                break
        if not lu:
            raise SystemExit("code QR introuvable sur les photos : envoyer une photo nette du haut de la fiche")
        numero, cle = lu
    if d.get("fiche") and d["fiche"] != numero:
        raise SystemExit(f"le JSON parle de la fiche {d['fiche']} mais le code QR est celui de {numero}")
    d["fiche"] = numero
    d["photos"] = [jpeg(p) for p in photos]
    out = Path(sortie) / "f" / f"{numero}.bin"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(chiffrer(cle, d))
    return out


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    print(ajouter(sys.argv[1], sys.argv[2], sys.argv[3:]))
