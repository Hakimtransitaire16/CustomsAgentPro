"""Fiche de suivi véhicules — dédouanement jusqu'à livraison (2 pages A4 portrait, à remplir à la main).

Modèle des formulaires douaniers européens (DAU) : chaque information est une case numérotée,
libellé en petites capitales en haut de la case, zone d'écriture dessous.

Page 1 : le conteneur (cases 1 à 14) et les 4 véhicules.
Page 2 : les 8 étapes groupées en 3 phases (douane, règlement, livraison), une colonne par véhicule.

Usage : python modeles/build_fiche_suivi.py <dossier de sortie>
"""
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

TRANSITAIRE = "SARL GMOR"
DECLARANT = "ABDEL HAKIM HADJALLAH"

DATE = '<span class="date"><span>JJ</span>/<span>MM</span>/<span class="y">AAAA</span></span>'


def comb(n, sep=None, tint=()):
    out = ''
    for k in range(1, n + 1):
        cls = []
        if k in tint: cls.append('t')
        if sep and k == sep: cls.append('s')
        out += f'<i class="{" ".join(cls)}"></i>'
    return f'<span class="comb">{out}</span>'


def opts(*o):
    return '<span class="opts">' + ''.join(f'<span>{x}</span>' for x in o) + '</span>'


def case(no, label, body='', span=6, cls=''):
    return (f'<div class="case {cls}" style="grid-column:span {span}"><div class="lb"><span class="no">{no}</span>{label}</div>'
            f'<div class="bd">{body}</div></div>')


def tete(sous_titre, page):
    return f'''
  <header>
    <div class="id"><div class="brand">{TRANSITAIRE}</div><div class="who">{DECLARANT} · déclarant en douane</div></div>
    <div class="ttl"><h1>Suivi véhicules</h1><p>{sous_titre}</p></div>
    <div class="ref"><div class="lb">Réf. dossier</div><div class="v"></div><div class="pg">{page}</div></div>
  </header>'''


def page1():
    vin = comb(17, tint=range(12, 18))
    vehs = ''.join(f'''<tr><td class="n">{k}</td><td><div class="w"></div></td><td><div class="w"></div></td><td>{vin}</td></tr>''' for k in range(1, 5))
    return f'''
<section>{tete("Dédouanement jusqu'à livraison · conteneur", "1 / 2")}
  <div class="sec"><span class="sl">A</span>Conteneur et transport</div>
  <div class="grid">
    {case(1, "Transitaire", f'<span class="pre">{TRANSITAIRE}</span>', 4)}
    {case(2, "Compagnie maritime", '', 4)}
    {case(3, "CRN", '', 4)}
    {case(4, "N° du TC · date", comb(11, sep=5) + '<span class="gap"></span>' + DATE, 8)}
    {case(5, "N° B/L", '', 4)}
    {case(6, "Bon à délivrer", opts("Récupéré", "Non récupéré") + '<span class="gap"></span>' + DATE, 7)}
    {case(7, "Bureau de douane", '', 5)}
  </div>
  <div class="sec"><span class="sl">B</span>Entreposage et dépotage</div>
  <div class="grid">
    {case(8, "Lieu d'entreposage", '', 5)}
    {case(9, "État de dépotage · date", opts("Dépoté", "Non dépoté") + '<span class="gap"></span>' + DATE, 7)}
    {case(10, "Groupeur", '', 7)}
    {case(11, "Relâche du groupeur", opts("Oui", "Non"), 5)}
  </div>
  <div class="sec"><span class="sl">C</span>TC vide</div>
  <div class="grid">
    {case(12, "Facturation du TC vide", DATE, 6)}
    {case(13, "Livraison du TC vide", DATE, 6)}
  </div>
  <div class="sec"><span class="sl">D</span>Client et véhicules sur le TC</div>
  <div class="grid">{case(14, "Nom du client", '', 12)}</div>
  <table class="veh">
    <thead><tr><th>N°</th><th>Marque</th><th>Modèle · couleur</th><th>N° de châssis (VIN) <span class="hint">· 6 derniers caractères en bleu = référence de rappel</span></th></tr></thead>
    <tbody>{vehs}</tbody>
  </table>
  <div class="sec"><span class="sl">E</span>Observations</div>
  <div class="obs"></div>
  <footer><span>{TRANSITAIRE} · Suivi véhicules · dates portées à la main à chaque étape</span><span>VIN : 17 caractères, sans I, O ni Q</span></footer>
</section>'''


PHASES = [
    ("Douane", [
        ("Déclaration D10", ["N° D10", "EPC", "APC"]),
        ("Liquidation avec l'inspecteur", ["Inspecteur", "Montant DA"]),
        ("Dédouanement · mainlevée", ["N° D10", "EPC"]),
    ]),
    ("Règlement", [
        ("Avis de paiement · quittance", ["N° quittance", "Montant DA"]),
        ("Facturation", ["N° facture", "Montant DA"]),
    ]),
    ("Livraison et 846", [
        ("Livraison au propriétaire", ["Transporteur", "Reçu par"]),
        ("Demande du 846", ["N° de dépôt"]),
        ("846 prêt et remis", ["N° 846", "Remis à"]),
    ]),
]


def cellule(champs):
    h = f'<td><div class="top">{DATE}<span class="tick"></span></div>'
    for c in champs:
        h += f'<div class="fl"><span>{c}</span><i></i></div>'
    return h + '</td>'


def page2():
    head = ''.join(f'<th><div class="vh">Véhicule {k}</div><div class="vr"><span>VIN …</span>{comb(6)}</div></th>' for k in range(1, 5))
    rows, k = '', 0
    for phase, etapes in PHASES:
        rows += f'<tr class="ph"><td colspan="5"><span>{phase}</span></td></tr>'
        for titre, champs in etapes:
            k += 1
            last = ' last' if k == 8 else ''
            rows += f'<tr class="st"><th class="rail{last}"><span class="dot">{k}</span><span class="tt">{titre}</span></th>' + cellule(champs) * 4 + '</tr>'
    return f'''
<section>{tete("Dédouanement jusqu'à livraison · étapes par véhicule", "2 / 2")}
  <div class="p2ref"><div class="case" style="flex:1"><div class="lb"><span class="no">4</span>N° du TC</div><div class="bd">{comb(11, sep=5)}</div></div>
    <div class="case" style="flex:1"><div class="lb"><span class="no">14</span>Client</div><div class="bd"></div></div></div>
  <table class="mx"><colgroup><col style="width:33mm"><col><col><col><col></colgroup>
    <thead><tr><th class="rh">Étape</th>{head}</tr></thead><tbody>{rows}</tbody></table>
  <footer><span>Une ligne = une étape pour les 4 véhicules · une colonne = le parcours d'un véhicule · cocher le rond quand l'étape est faite</span><span>{TRANSITAIRE}</span></footer>
</section>'''


CSS = '''
@page{size:A4 portrait;margin:11mm 12mm 10mm}
:root{--navy:#0B2545;--blue:#1F5FAD;--sky:#E9F1FB;--tint:#F4F7FA;--ink:#101B2B;--mute:#677489;--ghost:#B4BFCC;--rule:#CFD8E3;--hair:#E3E9F0}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,"DejaVu Sans",sans-serif;color:var(--ink);font-size:8pt;line-height:1.3;-webkit-print-color-adjust:exact;print-color-adjust:exact;font-feature-settings:"tnum" 1,"cv11" 1}
section{height:276mm;display:flex;flex-direction:column;break-after:page}
section:last-child{break-after:auto}
/* En-tête */
header{display:grid;grid-template-columns:52mm 1fr 44mm;align-items:end;gap:6mm;padding-bottom:4mm;border-bottom:2px solid var(--navy)}
.brand{font:800 13pt "Inter Display",Inter,sans-serif;letter-spacing:.08em;color:var(--navy)}
.who{font-size:6.4pt;color:var(--mute);letter-spacing:.06em;text-transform:uppercase;margin-top:.8mm}
.ttl h1{font:700 21pt/1 "Inter Display",Inter,sans-serif;letter-spacing:-.025em;color:var(--navy)}
.ttl p{font-size:7.6pt;color:var(--mute);margin-top:1.4mm}
.ref{border:1.4px solid var(--navy);border-radius:1.6mm;padding:1.6mm 2.4mm;position:relative}
.ref .lb{font-size:5.8pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--navy)}
.ref .v{height:6.6mm}
.ref .pg{position:absolute;top:1.5mm;right:2.4mm;font-size:6pt;font-weight:600;color:var(--mute)}
/* Sections */
.sec{display:flex;align-items:center;gap:2.4mm;margin:4.4mm 0 2mm;font-size:7pt;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--navy)}
.sec::after{content:"";flex:1;height:1px;background:var(--rule)}
.sl{width:5mm;height:5mm;border-radius:1mm;background:var(--navy);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:7pt;letter-spacing:0}
/* Cases numérotées */
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:2mm}
.case{border:1px solid var(--rule);border-radius:1.6mm;background:#fff;padding:1.5mm 2.2mm 1.8mm;min-height:13.4mm;display:flex;flex-direction:column}
.case .lb{display:flex;align-items:center;gap:1.6mm;font-size:5.8pt;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--mute)}
.no{min-width:4mm;height:4mm;padding:0 .8mm;border-radius:.8mm;background:var(--sky);color:var(--blue);font-size:6pt;letter-spacing:0;display:inline-flex;align-items:center;justify-content:center}
.bd{flex:1;display:flex;align-items:flex-end;gap:2mm;padding-top:1.4mm;flex-wrap:wrap}
.pre{font-weight:700;font-size:10pt;color:var(--navy);letter-spacing:.04em}
.gap{flex:1}
.date{display:inline-flex;align-items:flex-end;gap:.8mm;color:var(--ghost);font-size:6.6pt;font-weight:600;letter-spacing:.06em}
.date span{display:inline-block;width:7mm;text-align:center;border-bottom:1px solid var(--ink);padding-bottom:.3mm}
.date span.y{width:11mm}
.comb{display:inline-flex;gap:.6mm}
.comb i{display:block;width:4.6mm;height:6mm;border:1px solid var(--rule);border-bottom:1.3px solid var(--ink);border-radius:.4mm;background:#fff}
.comb i.s{margin-left:1.6mm}
.comb i.t{background:var(--sky);border-color:#BFD3EC;border-bottom-color:var(--blue)}
.opts{display:inline-flex;gap:4.4mm;font-size:7.6pt;font-weight:500}
.opts span{display:inline-flex;align-items:center;gap:1.4mm}
.opts span::before{content:"";width:3.4mm;height:3.4mm;border:1.2px solid var(--navy);border-radius:.7mm}
/* Véhicules */
table{border-collapse:collapse;width:100%}
.veh{margin-top:2mm;border:1px solid var(--rule);border-radius:1.6mm;overflow:hidden}
.veh th{background:var(--tint);text-align:left;font-size:5.8pt;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--mute);padding:1.8mm 2.2mm;border-bottom:1px solid var(--rule)}
.veh th .hint{text-transform:none;letter-spacing:0;font-weight:500;color:var(--blue)}
.veh td{padding:2.2mm 2.2mm;border-top:1px solid var(--hair);vertical-align:bottom;height:12.6mm}
.veh td.n{width:9mm;font:700 13pt "Inter Display",Inter,sans-serif;color:var(--navy);vertical-align:middle}
.veh th:nth-child(2){width:28mm}.veh th:nth-child(3){width:30mm}
.veh .w{height:5mm;border-bottom:1px solid var(--rule)}
.veh .comb i{width:4.25mm}
.obs{flex:1;border:1px solid var(--rule);border-radius:1.6mm;background:repeating-linear-gradient(to bottom,transparent 0,transparent 7.4mm,var(--hair) 7.4mm,var(--hair) 7.6mm);min-height:16mm}
footer{margin-top:auto!important;display:flex;justify-content:space-between;gap:6mm;margin-top:3mm;padding-top:2mm;border-top:1px solid var(--rule);font-size:6.2pt;color:var(--mute)}
/* Page 2 */
.p2ref{display:flex;gap:2mm;margin-top:3.6mm}
.p2ref .case{min-height:12mm}
.mx{margin-top:3mm;table-layout:fixed}
.mx tr.st{height:23.6mm}
.mx tr.ph{height:6.6mm}
.mx thead th{background:var(--navy);color:#fff;text-align:left;padding:2mm 2.2mm;vertical-align:top}
.mx thead th:first-child{border-top-left-radius:1.6mm}
.mx thead th:last-child{border-top-right-radius:1.6mm}
.mx th.rh{font-size:6pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;vertical-align:bottom;color:#C9D6E8}
.vh{font:700 9pt "Inter Display",Inter,sans-serif}
.vr{display:flex;align-items:center;gap:1.2mm;font-size:6pt;color:#C9D6E8;margin-top:1.4mm;white-space:nowrap}
.vr .comb{gap:.4mm}
.vr .comb i{width:3.6mm;height:4.6mm;border-color:#5C7699;border-bottom-color:#fff;background:transparent}
.mx tr.ph td{padding:1.6mm 2.2mm .8mm;background:#fff}
.mx tr.ph span{font-size:6.2pt;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--blue)}
.mx tr.st td,.mx tr.st th{border-top:1px solid var(--rule)}
.mx tr.st td{border-left:1px solid var(--hair);padding:1.7mm 2mm 1.4mm;vertical-align:top}
.mx tr.st td:last-child{border-right:1px solid var(--rule)}
.rail{position:relative;text-align:left;vertical-align:top;padding:1.8mm 2mm 1.4mm 0;background:#fff;border-left:1px solid var(--rule)}
.rail .dot{position:absolute;left:2.2mm;top:1.8mm;width:6mm;height:6mm;border-radius:50%;background:var(--navy);color:#fff;font-size:7.4pt;font-weight:700;display:flex;align-items:center;justify-content:center}
.rail::before{content:"";position:absolute;left:5.1mm;top:8mm;bottom:-1px;width:1.2px;background:var(--rule)}
.rail.last::before{display:none}
.rail .tt{display:block;padding-left:10.2mm;font-size:7.6pt;font-weight:700;line-height:1.22;color:var(--navy)}
.mx .top{display:flex;align-items:flex-end;justify-content:space-between;gap:1mm}
.mx .date{font-size:5.8pt;gap:.5mm}
.mx .date span{width:5.2mm}.mx .date span.y{width:8.6mm}
.tick{width:4mm;height:4mm;border:1.3px solid var(--navy);border-radius:50%;flex:none}
.fl{display:flex;align-items:flex-end;gap:1.2mm;margin-top:1.9mm;font-size:5.8pt;font-weight:600;letter-spacing:.04em;color:var(--mute);text-transform:uppercase}
.fl span{white-space:nowrap}
.fl i{flex:1;height:3.6mm;border-bottom:1px solid var(--rule)}
.mx tbody tr:last-child td,.mx tbody tr:last-child th{border-bottom:1px solid var(--rule)}
'''


def html():
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Suivi véhicules — {TRANSITAIRE}</title>'
            f'<style>{CSS}</style></head><body>{page1()}{page2()}</body></html>')


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
