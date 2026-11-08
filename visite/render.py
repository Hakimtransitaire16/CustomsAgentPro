"""Rendu de la fiche technique : dossier.json → HTML → PDF (Chromium / Playwright)."""
import base64
import io
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from PIL import Image

from . import calc
from .data import n, sh

TPL = Path(__file__).parent / "templates"

ICONS = {
    'globe': '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
    'twok': '<path d="M8 4c3 4 4 6 4 8a4 4 0 0 1-8 0c0-2 1-4 4-8z"/><path d="M17 9c2 2.7 3 4 3 5.3a3 3 0 0 1-6 0c0-1.3 1-2.6 3-5.3z"/>',
    'ratio': '<path d="M12 3v18M5 7h14M5 7l-3 6h6zM19 7l-3 6h6z"/><path d="M8 21h8"/>',
    'box': '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    'profile': '<path d="M4 20V8h6V4h10v4h-6v12z"/>',
    'code': '<path d="M4 5v14M7 5v14M10 5v14M14 5v14M16 5v14M20 5v14"/>',
    'mix': '<path d="M6 3h12M8 3v6l-4 9a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-4-9V3"/><path d="M6 14h12"/>',
    'roll': '<rect x="3" y="4" width="14" height="6" rx="2"/><path d="M17 7h3v6h-8v8"/>',
    'heat': '<path d="M8 21c-3-3 1-6 0-9M12 21c-3-3 1-6 0-9M16 21c-3-3 1-6 0-9"/><path d="M4 7h16"/>',
    'press': '<circle cx="8" cy="8" r="4"/><circle cx="16" cy="16" r="4"/><path d="M2 20h20"/>',
}


def icon(name, s=20, col="#2C66A8"):
    return (f'<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{col}" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def b64img(path_or_img, max_w=None, q=68, gray=False):
    im = Image.open(path_or_img) if not isinstance(path_or_img, Image.Image) else path_or_img
    im = im.convert("L" if gray else "RGB")
    if max_w and im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def taxe(a, code):
    return next((t for t in a["taxes"] if t["code"] == code), None)


def checklist(d):
    t, dec = d["transport"], d["declaration"]
    out = [f"Scellé <b>{t.get('scelle')}</b> intact et conforme au connaissement.",
           f"Conteneur <b>{t.get('conteneur')}</b> ({t.get('type_conteneur', '')}, tare {n(t.get('tare'))} kg).",
           f"<b>{dec['nb_colis']} colis</b> à compter."]
    for c in d.get("colisage", []):
        out.append(f"Type {c['type']} : {c['palettes']} palette(s) — {c['contenu']}.")
    for a in d["articles"]:
        q = a.get("quantite", {})
        out.append(f"<b>{q.get('nombre', '')} {q.get('unite', '')}</b> de {a['designation']} ({n(a['poids_net'])} kg net).")
    out += ["Étiquettes : produit, fabricant, lot, dates, poids net, pays d'origine, pictogrammes.",
            "Photos : porte, scellé, chargement, étiquettes."]
    return out


def contexte(d, fidelite=None, visite=None, pngs=None, live=False):
    arts = d["articles"]
    ctrls = calc.controles(d)
    r = calc.resume(ctrls)
    nom = d["meta"]["declarant"]["nom"].split()
    pv_vals = (visite or {}).get("constatations", {})
    pv = [("lieu", "Lieu de la visite", f"<b>{d.get('visite', {}).get('lieu', '')}</b>")] + [
        (k, lab, pv_vals.get(k, "")) for k, lab in [
            ("date", "Date et heure de la visite"), ("scelle", f"État du scellé {d['transport'].get('scelle')}"),
            ("comptage", "Colis / unités comptés"), ("etiquettes", "Marquages et étiquettes"),
            ("pesee", "Pesée de contrôle"), ("echantillons", "Échantillons prélevés"), ("observations", "Observations")]]
    thumbs = {}
    if pngs:
        for p, png in pngs.items():
            thumbs[int(p)] = b64img(png, 300, 60)
    fid = []
    for f in fidelite or []:
        f = dict(f)
        if Path(f.get("extrait", "")).exists():
            f["src"] = b64img(f["extrait"], q=70, gray=True)
        fid.append(f)
    photos = [{"src": p["data"], "legende": p.get("legende", "")} for p in (visite or {}).get("photos", []) if p.get("data")]
    return dict(
        d=d, css=(TPL / "style.css").read_text(encoding="utf-8"),
        initiales="".join(x[0] for x in nom[:2]).upper(),
        poids_net=sum(a["poids_net"] for a in arts),
        nb_pieces=len(d.get("documents", [])),
        fidelite=fid, fid_tot=len(fid), fid_ok=sum(1 for f in fid if f["score"] >= 0.95),
        emballages=" · ".join(f"{a['quantite'].get('contenance_kg', '')} kg" for a in arts if a.get("quantite")),
        codes_sh=" · ".join(sh(a["code_sh"]) for a in arts),
        qtes=[f"{a['quantite'].get('nombre', '')} {a['quantite'].get('unite', '')}" for a in arts],
        pbruts=[f"{n(a.get('poids_brut'))} kg ({a.get('poids_brut_source', '')})" if a.get("poids_brut") else "—" for a in arts],
        checklist=checklist(d), pv=pv, thumbs=thumbs, photos=photos,
        ctrl_ok=r["ok"], ctrl_tot=len(ctrls), conformite=d.get("conformite"), live=live,
    )


def html(d, **kw):
    env = Environment(loader=FileSystemLoader(TPL), autoescape=False)
    env.filters.update(n=n, sh=sh, add_suffix=lambda s, suf: f"{s}{suf}")
    env.globals.update(icon=icon, taxe=taxe, total_art=lambda a: sum(t["montant"] for t in a["taxes"]))
    out = env.get_template("fiche.html.j2").render(**contexte(d, **kw))
    pages = out.count("{PAGE}")
    k = iter(range(1, pages + 1))
    return re.sub(r"\{PAGE\}", lambda m: f"{next(k)} / {pages}", out)


def pdf(html_text, out_pdf):
    """Imprime le HTML en PDF A4 et renvoie les débordements éventuels par page."""
    from playwright.sync_api import sync_playwright
    out_pdf = Path(out_pdf)
    tmp = out_pdf.with_suffix(".html")
    tmp.write_text(html_text, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(tmp.resolve().as_uri(), wait_until="networkidle")
        pg.pdf(path=str(out_pdf), prefer_css_page_size=True, print_background=True)
        debord = pg.evaluate("""() => [...document.querySelectorAll('.page')].map((p, i) =>
            ({page: i + 1, deborde: p.scrollHeight - p.clientHeight}))""")
        b.close()
    return [x for x in debord if x["deborde"] > 0]
