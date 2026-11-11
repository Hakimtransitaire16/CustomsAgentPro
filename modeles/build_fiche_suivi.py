"""Fiche de suivi véhicules — dédouanement jusqu'à livraison (2 pages A4 portrait, à remplir à la main).

Page 1 : le conteneur (transitaire, TC, compagnie, CRN, B/L, BAD, entreposage, dépotage, groupeur,
TC vide, client) et les 4 véhicules (marque, n° de châssis).
Page 2 : les 8 étapes en lignes, les 4 véhicules en colonnes ; chaque case a sa date et une case à cocher.

Usage : python modeles/build_fiche_suivi.py <dossier de sortie>
"""
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

TRANSITAIRE = "SARL GMOR TRANS"
DECLARANT = "ABDEL HAKIM HADJALLAH"

DT = '<span class="dt"><i></i><i></i><em>/</em><i></i><i></i><em>/</em><i></i><i></i><i></i><i></i></span>'
TC = '<span class="tc">' + '<i></i>' * 4 + '<i class="s"></i>' + '<i></i>' * 6 + '</span>'
VIN = '<span class="vin">' + ''.join('<i class="c"></i>' if k == 8 else '<i></i>' for k in range(17)) + '</span>'


def ck(*opts):
    return '<span class="ck">' + ''.join(f'<span>{o}</span>' for o in opts) + '</span>'


def ln(label, contenu='<i></i>', cls=''):
    return f'<div class="f {cls}"><b>{label}</b>{contenu}</div>'


# Étapes : (titre, lignes de la case). Chaque ligne : libellé, puis « date », « ligne » ou une case à cocher.
ETAPES = [
    ("Déclaration D10", [("Date", "date"), ("N° D10", "ligne"), ("EPC", "ligne"), ("APC", "ligne")]),
    ("Liquidation avec l'inspecteur", [("Date", "date"), ("Inspecteur", "ligne"), ("Montant DA", "ligne")]),
    ("Dédouanement · mainlevée", [("Date", "date"), ("N° D10", "ligne"), ("EPC", "ligne")]),
    ("Avis de paiement · quittance", [("Date", "date"), ("N° quittance", "ligne"), ("Montant DA", "ligne")]),
    ("Facturation", [("Date", "date"), ("N° facture", "ligne"), ("Montant DA", "ligne")]),
    ("Livraison au propriétaire", [("Date", "date"), ("Transporteur", "ligne"), ("Reçu par", "ligne")]),
    ("Demande du 846", [("Date", "date"), ("N° de dépôt", "ligne")]),
    ("846 prêt et remis", [("Date", "date"), ("N° 846", "ligne"), ("Remis à", "ligne")]),
]


def case(lignes):
    h = '<td><span class="ok"></span>'
    for lib, kind in lignes:
        h += f'<div class="r"><b>{lib}</b>{DT if kind == "date" else "<i></i>"}</div>'
    return h + '<div class="r"><b>Obs.</b><i></i></div></td>'


def page1():
    vehs = ''.join(
        f'<tr><td class="n">{k}</td><td><i class="l"></i></td><td><i class="l"></i></td><td>{VIN}</td><td class="six"><i class="l"></i></td></tr>'
        for k in range(1, 5))
    return f'''
<section>
  <div class="band"><div class="mg">AH</div><div class="tt"><div class="k">{TRANSITAIRE} · {DECLARANT}, déclarant</div>
    <h1>Fiche de suivi véhicules</h1><div class="st">Dédouanement jusqu'à livraison · page 1/2 : conteneur</div></div>
    <div class="rx"><b>Réf.</b><i></i></div></div>

  <div class="grid">
    {ln("Nom du transitaire", f'<span class="pre">{TRANSITAIRE}</span>')}
    {ln("Compagnie maritime")}
    <div class="f wide"><b>N° du TC</b>{TC}<b class="g">Date d'arrivée</b>{DT}</div>
    {ln("CRN")}
    {ln("N° B/L")}
    <div class="f"><b>Bon à délivrer</b>{ck("Récupéré", "Non récupéré")}</div>
    <div class="f"><b>Date du BAD</b>{DT}</div>
  </div>

  <h2>Entreposage et dépotage</h2>
  <div class="grid">
    {ln("Lieu d'entreposage")}
    {ln("Bureau de douane")}
    <div class="f"><b>État de dépotage</b>{ck("Dépoté", "Non dépoté")}</div>
    <div class="f"><b>Date de dépotage</b>{DT}</div>
    {ln("Nom du groupeur")}
    <div class="f"><b>Relâche du groupeur</b>{ck("Oui", "Non")}</div>
  </div>

  <h2>TC vide</h2>
  <div class="grid">
    <div class="f"><b>Facturation du TC vide</b>{DT}</div>
    <div class="f"><b>Livraison du TC vide</b>{DT}</div>
  </div>

  <h2>Client et véhicules sur le TC</h2>
  <div class="grid">{ln("Nom du client", cls="wide")}</div>
  <table class="vh"><thead><tr><th>N°</th><th>Marque</th><th>Modèle · couleur</th><th>Numéro de châssis (VIN, 17 caractères)</th><th>6 derniers car.</th></tr></thead>
  <tbody>{vehs}</tbody></table>
  <p class="nb">Le 9e caractère du châssis (case bleue) est le chiffre de contrôle. Un châssis n'a jamais les lettres I, O ou Q : lire 1 et 0.</p>

  <h2>Observations</h2>
  <div class="obs"><i></i><i></i><i></i></div>
  <div class="ft"><span>Toutes les dates sont portées à la main au moment de chaque étape.</span><span>Page 1/2</span></div>
</section>'''


def page2():
    head = ''.join(f'<th>Véhicule {k}<span class="six">châssis : <i></i></span></th>' for k in range(1, 5))
    rows = ''
    for k, (titre, lignes) in enumerate(ETAPES, 1):
        rows += f'<tr><th class="et"><span class="no">{k}</span>{titre}</th>' + case(lignes) * 4 + '</tr>'
    return f'''
<section>
  <div class="band"><div class="mg">AH</div><div class="tt"><div class="k">{TRANSITAIRE} · {DECLARANT}, déclarant</div>
    <h1>Fiche de suivi véhicules</h1><div class="st">Dédouanement jusqu'à livraison · page 2/2 : étapes par véhicule</div></div>
    <div class="rx"><b>N° TC</b><i></i></div></div>
  <table class="mx"><thead><tr><th class="et">Étape</th>{head}</tr></thead><tbody>{rows}</tbody></table>
  <div class="ft"><span>Lecture : une ligne = une étape pour les 4 véhicules · cocher la case du coin quand l'étape est faite · la colonne d'un véhicule se lit de haut en bas.</span><span>Page 2/2</span></div>
</section>'''


CSS = '''
@page{size:A4 portrait;margin:10mm 11mm}
:root{--navy:#0F2D4F;--blue:#2C66A8;--panel:#F5F7FA;--ink:#14202E;--muted:#5B6878;--line:#C9D3DF}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,"DejaVu Sans",sans-serif;color:var(--ink);font-size:8pt;line-height:1.35;-webkit-print-color-adjust:exact;print-color-adjust:exact}
section{height:277mm;display:flex;flex-direction:column;break-after:page}
section:last-child{break-after:auto}
.band{display:flex;align-items:center;gap:4mm;background:var(--navy);color:#fff;padding:3.6mm 4.4mm}
.mg{width:10mm;height:10mm;border:1.2px solid #fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:8.4pt;letter-spacing:.06em;flex:none}
.tt{flex:1}
.tt .k{font-size:6.4pt;letter-spacing:.14em;text-transform:uppercase;opacity:.75}
.tt h1{font-size:17pt;font-weight:700;letter-spacing:-.02em;line-height:1.1;margin-top:.6mm}
.tt .st{font-size:7.6pt;opacity:.85;margin-top:.4mm}
.rx{display:flex;align-items:flex-end;gap:2mm;font-size:7pt;min-width:40mm}
.rx i{flex:1;height:6mm;border-bottom:1.2px solid #fff}
h2{font-size:7.4pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--navy);border-bottom:1.4px solid var(--navy);padding-bottom:1.2mm;margin-top:5mm}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:0 6mm}
.grid:first-of-type{margin-top:3mm}
.f{display:flex;align-items:flex-end;gap:2mm;min-height:9.6mm;padding:1.6mm 0;border-bottom:1px solid var(--line)}
.f.wide{grid-column:1/-1}
.f b{font-weight:600;font-size:7.6pt;white-space:nowrap}
.f b.g{margin-left:6mm}
.f>i{flex:1;height:5mm}
.pre{font:700 9.4pt Inter,sans-serif;color:var(--navy);letter-spacing:.02em}
.dt{display:inline-flex;align-items:flex-end}
.dt i{display:block;width:3.4mm;height:4.6mm;border-bottom:1px solid var(--navy);margin-right:.35mm}
.dt em{font-style:normal;color:var(--muted);padding:0 .6mm}
.tc,.vin{display:inline-flex;gap:.5mm}
.tc i,.vin i{display:block;width:5mm;height:6.4mm;border:1px solid var(--line);border-bottom:1.3px solid var(--navy)}
.tc i.s{margin-left:1.6mm}
.vin i{width:4.5mm;height:6mm}
.vin i.c{border-color:var(--blue);border-bottom-color:var(--blue);background:#EEF4FB}
.ck{display:inline-flex;gap:4mm;font-size:7.8pt}
.ck span{display:inline-flex;align-items:center;gap:1.4mm}
.ck span::before{content:"";width:3.2mm;height:3.2mm;border:1.1px solid var(--navy)}
table{border-collapse:collapse;width:100%}
.vh{margin-top:2.4mm}
.vh th{font-size:6.4pt;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);text-align:left;padding:1.4mm 1.4mm;border-bottom:1.2px solid var(--navy)}
.vh td{padding:2.6mm 1.4mm;border-bottom:1px solid var(--line);vertical-align:bottom;height:13mm}
.vh td.n{font:700 11pt Inter,sans-serif;color:var(--navy);width:7mm}
.vh .l{display:block;height:5mm;border-bottom:1px solid var(--line)}
.vh th:nth-child(2){width:24mm}.vh th:nth-child(3){width:26mm}.vh th:nth-child(5){width:24mm}
.nb{font-size:6.6pt;color:var(--muted);margin-top:1.6mm}
.obs{flex:1;display:flex;flex-direction:column;justify-content:space-evenly;min-height:14mm}
.obs i{display:block;border-bottom:1px solid var(--line);height:6mm}
.ft{display:flex;justify-content:space-between;gap:6mm;border-top:1px solid var(--line);padding-top:1.8mm;margin-top:2.4mm;font-size:6.4pt;color:var(--muted)}
/* page 2 */
.mx{margin-top:3mm;table-layout:fixed;flex:1}
.mx thead th{background:var(--navy);color:#fff;font-size:7.6pt;font-weight:700;text-align:left;padding:1.8mm 2mm;vertical-align:top}
.mx thead th .six{display:flex;align-items:flex-end;gap:1mm;font-size:6.2pt;font-weight:400;opacity:.85;margin-top:1mm}
.mx thead th .six i{flex:1;height:4mm;border-bottom:1px solid #fff}
.mx th.et{width:31mm}
.mx tbody th.et{background:var(--panel);color:var(--navy);font-size:7.6pt;font-weight:700;text-align:left;vertical-align:top;padding:2mm;border:1px solid var(--line);line-height:1.25}
.mx tbody th .no{display:block;font:700 13pt Inter,sans-serif;color:var(--blue);margin-bottom:.6mm}
.mx td{border:1px solid var(--line);vertical-align:top;padding:1.6mm 1.8mm;position:relative}
.mx tbody tr:nth-child(even) td{background:#FBFCFE}
.mx .ok{position:absolute;top:1.4mm;right:1.4mm;width:3.6mm;height:3.6mm;border:1.2px solid var(--navy);background:#fff}
.mx .r{display:flex;align-items:flex-end;gap:1.2mm;margin-top:1.3mm;font-size:6.4pt;color:var(--muted)}
.mx .r:first-of-type{margin-top:0;padding-right:5mm}
.mx .r b{font-weight:600;white-space:nowrap}
.mx .r>i{flex:1;height:3.8mm;border-bottom:1px solid var(--line)}
.mx .dt i{width:2.5mm;height:3.8mm;margin-right:.2mm}
.mx .dt em{padding:0 .3mm;font-size:6.4pt}
'''


def html():
    return f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Fiche de suivi véhicules — dédouanement jusqu\'à livraison</title><style>{CSS}</style></head><body>{page1()}{page2()}</body></html>'


def construire(sortie: Path) -> Path:
    sortie.mkdir(parents=True, exist_ok=True)
    f = sortie / '_fiche_suivi.html'
    f.write_text(html(), encoding='utf-8')
    out = sortie / 'Fiche_suivi_vehicules.pdf'
    subprocess.run(['node', '-e', f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{f.resolve()}');await p.waitForTimeout(300);await p.pdf({{path:'{out.resolve()}',preferCSSPageSize:true,printBackground:true}});await b.close();}})()"""], check=True)
    n = len(PdfReader(str(out)).pages)
    if n != 2:
        print(f'  ! {n} pages au lieu de 2 : débordement')
    f.unlink()
    return out


if __name__ == '__main__':
    print(construire(Path(sys.argv[1] if len(sys.argv) > 1 else '.')))
