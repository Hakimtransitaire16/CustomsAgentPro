"""Ligne de commande.

  python -m visite extraire  DOSSIER.json   # OCR du scan → suggestions de références
  python -m visite controler DOSSIER.json   # contrôles automatiques
  python -m visite fiche     DOSSIER.json   # OCR + fidélité + PDF + relecture
  python -m visite mobile    DOSSIER.json   # page de visite pour téléphone
  python -m visite pv        DOSSIER.json visite_XXX.json   # réinjecte la visite dans la fiche
  python -m visite registre  DOSSIER.json   # ajoute au registre + tableau de bord
  python -m visite app       DOSSIER.json   # application unique : fiche + visite + contrôles + registre + données
  python -m visite tout      DOSSIER.json   # contrôler + fiche + registre + application unique + note de risques
  python -m visite risques   DOSSIER.json   # note de risques pour le déclarant seul (alertes + sources)
  python -m visite tarif     3506.99.90.00 [--notes]   # position tarifaire : section, chapitre, position, notes, DD, LF 2026, décisions
  python -m visite tarif     DOSSIER.json [--notes]    # la même fiche pour chaque article + famille du code d'origine
  python -m visite demande   "question, code, désignation ou article"   # moteur unique : toutes les sources à la fois

Sorties dans DOSSIER/sortie/ ; registre dans le dossier parent : ../registre/.
"""
import argparse
import json
import sys
from pathlib import Path

from . import app as appmod, calc, data, mobile, moteur, ocr, registry, render, tarif, verify

SYM = {"ok": "✓", "alerte": "!", "erreur": "✕"}


def _sortie(d):
    s = Path(d["_dir"]) / "sortie"
    s.mkdir(exist_ok=True)
    return s


def _pages(d):
    s = _sortie(d) / "pages"
    existing = {int(p.stem[4:]): p for p in s.glob("page*.png")} if s.exists() else {}
    return existing or ocr.pages(d, s)


def cmd_extraire(d, a):
    sugg = ocr.extraire(_pages(d))
    f = _sortie(d) / "suggestions.json"
    f.write_text(json.dumps(sugg, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in sugg.items():
        print(f"{k:14}", ", ".join(sorted({x['valeur'] for x in v}))[:120])
    print("→", f)


def cmd_controler(d, a):
    ctrls = calc.controles(d)
    for c in ctrls:
        print(f" {SYM[c['statut']]} {c['id']:6} {c['titre']} — {c['detail']}")
    (_sortie(d) / "controles.json").write_text(json.dumps(ctrls, ensure_ascii=False, indent=1), encoding="utf-8")
    r = calc.resume(ctrls)
    print(f"\n{r['ok']} conformes · {r['alerte']} alertes · {r['erreur']} erreurs")
    return r


def cmd_fiche(d, a, visite=None):
    s = _sortie(d)
    pngs = _pages(d) if d.get("scan") else {}
    fid = ocr.fidelite(d, pngs, s / "extraits") if pngs else []
    (s / "fidelite.json").write_text(json.dumps(fid, ensure_ascii=False, indent=1), encoding="utf-8")
    html = render.html(d, fidelite=fid, visite=visite, pngs=pngs)
    pdf = s / f"Fiche_technique_{d['meta']['id']}.pdf"
    deb = render.pdf(html, pdf)
    corpus = "".join(ocr.corpus(pngs, s / "ocr_corpus.json").values()) if pngs else ""
    rel = verify.relire(pdf, d, corpus)
    (s / "relecture.json").write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for f in fid if f["score"] >= 0.95)
    print(f"PDF : {pdf} ({pdf.stat().st_size // 1024} Ko)")
    print(f"Fidélité : {ok}/{len(fid)} identiques, {len(fid) - ok} à confirmer visuellement")
    print(f"Relecture : {rel['references_presentes']}/{rel['references']} références présentes · nombres inconnus : {rel['nombres_inconnus'] or 'aucun'}")
    print("Mise en page :", "OK" if not deb else f"débordements {deb}")
    return pdf


def cmd_mobile(d, a):
    f = _sortie(d) / f"visite_{d['meta']['id']}.html"
    f.write_text(mobile.page(d), encoding="utf-8")
    print("Page de visite :", f)
    return f


def cmd_pv(d, a):
    v = json.loads(Path(a.visite).read_text(encoding="utf-8"))
    return cmd_fiche(d, a, visite=v)


def cmd_registre(d, a):
    reg = Path(d["_dir"]).parent / "registre"
    rows = registry.enregistrer(d, reg)
    kpi = registry.tableau_de_bord(reg, reg / "tableau_de_bord.html")
    print(f"Registre : {len(rows)} dossier(s) · {reg / 'registre.csv'} · {reg / 'tableau_de_bord.html'}")
    return kpi


def cmd_app(d, a):
    s = _sortie(d)
    pngs = _pages(d) if d.get("scan") else {}
    ff = s / "fidelite.json"
    fid = json.loads(ff.read_text(encoding="utf-8")) if ff.exists() else (ocr.fidelite(d, pngs, s / "extraits") if pngs else [])
    rj = Path(d["_dir"]).parent / "registre" / "registre.json"
    rows = json.loads(rj.read_text(encoding="utf-8")) if rj.exists() else None
    f = s / f"Dossier_{d['meta']['id']}.html"
    f.write_text(appmod.construire(d, fidelite=fid, pngs=pngs, registre=rows), encoding="utf-8")
    print(f"Application unique : {f} ({f.stat().st_size // 1024} Ko)")
    fp = s / f"Dossier_{d['meta']['id']}_partage.html"
    fp.write_text(appmod.construire(d, fidelite=fid, pngs=pngs, partage=True), encoding="utf-8")
    print(f"Version à transmettre (fiche + visite) : {fp} ({fp.stat().st_size // 1024} Ko)")
    return f


def cmd_risques(d, a):
    f = _sortie(d) / f"Note_risques_{d['meta']['id']}.md"
    f.write_text(moteur.note_risques(d, calc.controles(d)), encoding="utf-8")
    print("Note de risques (déclarant seul) :", f)
    return f


def cmd_manquants(d, a):
    """Pièces et informations à demander au déclarant, avec émetteur, valeur douanière et texte."""
    from . import exigences
    txt = exigences.texte(d)
    f = _sortie(d) / f"A_fournir_{d['meta']['id']}.md"
    f.write_text(txt, encoding="utf-8")
    m = exigences.manquants(d)
    print(f"\n=== À DEMANDER AU DÉCLARANT : {len(m)} élément(s) ===")
    for x in m:
        print(f"  [{x['niveau']}] {x['nom']} — {x['motif']}")
    print(f"Détail : {f}")
    return m


def cmd_complet(d, a, fiche=None):
    """Un seul PDF : couverture, fiche de visite (A), fiche de terrain (B), note interne (C)."""
    from . import complet
    s = _sortie(d)
    fiche = fiche or s / f"Fiche_technique_{d['meta']['id']}.pdf"
    if not Path(fiche).exists():
        fiche = cmd_fiche(d, a)
    out = complet.construire(d, Path(fiche), s)
    print(f"Dossier complet (un PDF) : {out} ({out.stat().st_size // 1024} Ko)")
    return out


def cmd_tout(d, a):
    moteur.preparer(silencieux=True)
    cmd_controler(d, a)
    f = cmd_fiche(d, a)
    cmd_registre(d, a)
    cmd_app(d, a)
    cmd_risques(d, a)
    cmd_complet(d, a, fiche=f)
    cmd_manquants(d, a)


def cmd_tarif(argv):
    notes = "--notes" in argv
    args = [x for x in argv if x != "--notes"]
    if not args:
        print(__doc__)
        return 2
    if not tarif.disponible():
        print("knowledge-base/data/tarif_2016.json introuvable.")
        return 2
    cible = " ".join(args)
    if cible.endswith(".json"):
        d = data.load(cible)
        for a in d["articles"]:
            print("=" * 100 + f"\nARTICLE {a['num']} — {a['designation']}  ({a.get('designation_claire', '')})")
            print(tarif.texte(tarif.fiche(a["code_sh"]), notes=notes))
            if a.get("code_origine"):
                fam = tarif.famille(a["code_sh"], a["code_origine"])
                print(f"\nCode du pays d'origine {a['code_origine']} : "
                      + ("même sous-position" if fam["sous_position"] else "même position, autre sous-position" if fam["position"]
                         else "même chapitre, autre position" if fam["chapitre"] else "autre chapitre")
                      + f" — {tarif.libelle_sh6(a['code_origine'])}")
        return 0
    print(tarif.texte(tarif.fiche(cible), notes=notes))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "tarif":
        return cmd_tarif(argv[1:])
    if argv and argv[0] == "demande":
        if len(argv) < 2:
            print(__doc__)
            return 2
        print(moteur.texte(moteur.analyser(" ".join(argv[1:]))))
        return 0
    p = argparse.ArgumentParser(prog="visite", description="Moteur visite douane — un dossier JSON, toutes les sorties")
    p.add_argument("commande", choices=["extraire", "controler", "fiche", "mobile", "pv", "registre", "app", "tout", "tarif", "risques", "complet", "manquants"])
    p.add_argument("dossier")
    p.add_argument("visite", nargs="?")
    a = p.parse_args(argv)
    try:
        d = data.load(a.dossier)
    except Exception as e:
        print("Dossier invalide :", e)
        return 2
    globals()[f"cmd_{a.commande}"](d, a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
