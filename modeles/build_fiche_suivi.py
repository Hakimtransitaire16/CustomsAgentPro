"""Formulaire SV — fiche de suivi véhicules, dédouanement jusqu'à livraison (2 pages A4, à remplir à la main).

Conception :
- cases numérotées sur le modèle du document administratif unique européen (DAU) ;
- mise en page DIN 5008 : marge de classement de 22 mm à gauche, repère de perforation (148,5 mm),
  repères de pliage (105 et 210 mm) ;
- trois phases en couleur (douane, règlement, livraison) ;

Page 1 : le conteneur (cases 1 à 16) et les 4 véhicules.
Page 2 : les 4 VIN, puis les 8 étapes × 4 véhicules et les totaux.

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


def case(no, label, body='', span=6):
    return (f'<div class="case" style="grid-column:span {span}"><div class="lb"><span class="no">{no}</span>{label}</div>'
            f'<div class="bd">{body}</div></div>')


def marques():
    """Repères DIN 5008 : perforation à 148,5 mm, pliage à 105 et 210 mm."""
    return '<i class="mk fold" style="top:105mm"></i><i class="mk punch" style="top:148.5mm"></i><i class="mk fold" style="top:210mm"></i>'


def tete(sous_titre, page):
    return f'''
  <header>
    <div class="hl">
      <div class="brand">{TRANSITAIRE}</div>
      <div class="who">{DECLARANT}<br>déclarant en douane</div>
    </div>
    <div class="hm"><div class="kick">Dédouanement jusqu'à livraison</div><h1>Suivi véhicules</h1><p>{sous_titre}</p></div>
    <div class="hrs"><div class="hr"><div class="lb">Réf. dossier</div><div class="v"></div><div class="pg">Page {page}</div></div>
      <div class="hr"><div class="lb">N° D10</div><div class="v"></div></div></div>
  </header>
  <div class="stripe"><i></i></div>'''


def tete_suite():
    """En-tête courant de la page de suite : une ligne, sans bandeau."""
    return f'''
  <div class="run"><span><b>{TRANSITAIRE}</b> · Suivi véhicules · feuille étapes</span><span class="rr">Réf. dossier <i></i><b>Page 2 / 2</b></span></div>'''


def pied(gauche):
    return f'<footer><span>{gauche}</span></footer>'


def page1():
    vin = comb(17, tint=range(12, 18))
    vehs = ''.join(f'<tr><td class="n">{k}</td><td><div class="w"></div></td><td><div class="w"></div></td><td>{vin}</td></tr>' for k in range(1, 5))
    return f'''
<section>{marques()}{tete("Feuille conteneur", "1 / 2")}
  <div class="body">
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
    {case(8, "Nom de l'entrepôt", '', 6)}
    {case(9, "Lieu d'entreposage", '', 6)}
    {case(10, "État de dépotage · date", opts("Dépoté", "Non dépoté") + '<span class="gap"></span>' + DATE, 6)}
    {case(11, "Groupeur", '', 3)}
    {case(12, "Relâche groupeur", opts("Oui", "Non"), 3)}
  </div>
  <div class="sec"><span class="sl">C</span>TC vide</div>
  <div class="grid">
    {case(13, "Facturation du TC vide", DATE, 6)}
    {case(14, "Livraison du TC vide", DATE, 6)}
  </div>
  <div class="sec"><span class="sl">D</span>Client et véhicules sur le TC</div>
  <div class="grid">{case(15, "Nom du client", '', 8)}{case(16, "Tél. client", '', 4)}</div>
  <table class="veh">
    <thead><tr><th>N°</th><th>Marque</th><th>Modèle · couleur</th><th>N° de châssis (VIN) <span class="hint">6 derniers caractères en jaune = référence du véhicule</span></th></tr></thead>
    <tbody>{vehs}</tbody>
  </table>
  <div class="sec"><span class="sl">E</span>Observations</div>
  <div class="obs"><i></i><i></i><i></i><i></i></div>
  </div>
  {pied("VIN : 17 caractères, jamais I, O ni Q · dates portées à la main à chaque étape")}
</section>'''


PHASES = [
    ("Douane", "c1", [
        ("Déclaration D10", ["N° D10", "EPC", "APC"]),
        ("Liquidation avec l'inspecteur", ["Inspecteur", "Montant DA"]),
        ("Dédouanement · mainlevée", ["N° D10", "EPC"]),
    ]),
    ("Règlement", "c2", [
        ("Avis de paiement · quittance", ["N° quittance", "Montant DA"]),
        ("Facturation", ["N° facture", "Montant DA"]),
    ]),
    ("Livraison et 846", "c3", [
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
    head = ''.join(f'<th><div class="vh">Véhicule {k}</div><div class="vr">VIN : voir case V{k}</div></th>' for k in range(1, 5))
    vins = ''.join(f'<div class="case vin"><div class="lb"><span class="no">V{k}</span>Véhicule {k} · N° de châssis (VIN)</div><div class="bd">{comb(17, tint=range(12, 18))}</div></div>' for k in range(1, 5))
    rows, k = '', 0
    for phase, c, etapes in PHASES:
        rows += f'<tr class="ph {c}"><td colspan="5"><span>{phase}</span></td></tr>'
        for titre, champs in etapes:
            k += 1
            rows += f'<tr class="st {c}"><th class="rail"><span class="dot">{k}</span><span class="tt">{titre}</span></th>' + cellule(champs) * 4 + '</tr>'
    tot = '<td><div class="fl"><span>Payé DA</span><i></i></div><div class="fl"><span>Facturé DA</span><i></i></div></td>' * 4
    return f'''
<section>{marques()}{tete_suite()}
  <div class="body">
  <div class="p2ref"><div class="case" style="flex:1.25"><div class="lb"><span class="no">4</span>N° du TC</div><div class="bd">{comb(11, sep=5)}</div></div>
    <div class="case" style="flex:1"><div class="lb"><span class="no">15</span>Client</div><div class="bd"></div></div></div>
  <div class="vins">{vins}</div>
  <table class="mx"><colgroup><col style="width:31mm"><col><col><col><col></colgroup>
    <thead><tr><th class="rh">Étape</th>{head}</tr></thead>
    <tbody>{rows}</tbody>
    <tfoot><tr class="tot"><th class="rail"><span class="tt">Totaux du véhicule</span></th>{tot}</tr></tfoot></table>
  </div>
  {pied("Une ligne = une étape pour les 4 véhicules · une colonne = le parcours d'un véhicule · cocher le rond quand l'étape est faite")}
</section>'''


CSS = '''
@page{size:A4 portrait;margin:0}
:root{--navy:#003399;--navy2:#2B2F33;--ink:#0B0C0C;--mute:#505A5F;--ghost:#A3AAB0;--rule:#B1B4B6;--hair:#D9DBDD;--tint:#F3F2F1;
  --c1:#003399;--c1l:#FFF4C2;--c2:#003399;--c2l:#FFF4C2;--c3:#003399;--c3l:#FFF4C2;--gold:#FFFFFF;--eu:#003399;--yellow:#FFCC00}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,"DejaVu Sans",sans-serif;color:var(--ink);font-size:8pt;line-height:1.3;-webkit-print-color-adjust:exact;print-color-adjust:exact;font-feature-settings:"tnum" 1,"cv11" 1}
section{position:relative;width:210mm;height:297mm;display:flex;flex-direction:column;break-after:page;overflow:hidden}
section:last-child{break-after:auto}
.body{flex:1;display:flex;flex-direction:column;padding:0 10mm 0 22mm}
/* Repères DIN 5008 */
.mk{position:absolute;left:0;height:0;border-top:.6pt solid #8C99AA}
.mk.fold{width:4mm}.mk.punch{width:7mm}
/* En-tête pleine largeur */
header{background:var(--navy);color:#fff;display:grid;grid-template-columns:50mm 1fr 42mm;align-items:end;gap:6mm;padding:9mm 10mm 6mm 22mm}
.brand{font:800 15pt/1 "Inter Display",Inter,sans-serif;letter-spacing:.1em}
.who{font-size:6.2pt;letter-spacing:.08em;text-transform:uppercase;color:#FFFFFF;margin-top:2mm;line-height:1.45}
.kick{font-size:6.2pt;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--yellow)}
.hm h1{font:700 24pt/1 "Inter Display",Inter,sans-serif;letter-spacing:-.03em;margin-top:1.4mm}
.hm p{font-size:7.6pt;color:#FFFFFF;margin-top:1.4mm}
.hrs{display:flex;flex-direction:column;gap:1.6mm}
.hr{background:#fff;color:var(--ink);border-radius:0;padding:1.8mm 2.6mm 2mm;position:relative}
.hr .lb{font-size:5.8pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--navy)}
.hr .v{height:6.4mm;border-bottom:1.2px solid var(--navy)}
.hr .pg{position:absolute;top:1.8mm;right:2.6mm;font-size:5.8pt;font-weight:600;color:var(--mute)}
.stripe{display:flex;height:2mm;flex:none}
header,footer{flex:none}
.mx tr.st{height:22mm}
.stripe i{flex:1;background:var(--yellow)}
/* Sections */
.sec{display:flex;align-items:center;gap:2.8mm;margin:4mm 0 2mm;font-size:9.4pt;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--navy)}
.sec::after{content:"";flex:1;height:1.4px;background:var(--ink)}
.sl{width:6.6mm;height:6.6mm;font-size:9pt!important;border-radius:0;background:var(--eu);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:7pt;letter-spacing:0}
/* Cases numérotées */
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:2mm}
.case{border:.9px solid var(--rule);border-top:1.6px solid var(--ink);border-radius:0;background:#fff;padding:1.5mm 2.2mm 1.8mm;min-height:13mm;display:flex;flex-direction:column}
.case .lb{display:flex;align-items:center;gap:1.6mm;font-size:6.6pt;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--ink)}
.no{min-width:4.2mm;height:4.2mm;padding:0 .8mm;border-radius:0;background:var(--navy);color:#fff;font-size:6pt;letter-spacing:0;display:inline-flex;align-items:center;justify-content:center}
.bd{flex:1;display:flex;align-items:flex-end;gap:2mm;padding-top:1.4mm;flex-wrap:wrap}
.pre{font-weight:800;font-size:10pt;color:var(--navy);letter-spacing:.06em}
.gap{flex:1}
.date{display:inline-flex;align-items:flex-end;gap:.8mm;color:var(--ghost);font-size:6.4pt;font-weight:600;letter-spacing:.06em}
.date span{display:inline-block;width:6.6mm;text-align:center;border-bottom:1px solid var(--ink);padding-bottom:.3mm}
.date span.y{width:10.4mm}
.comb{display:inline-flex;gap:.55mm}
.comb i{display:block;width:4.4mm;height:6mm;border:1px solid var(--rule);border-bottom:1.3px solid var(--ink);border-radius:0;background:#fff}
.comb i.s{margin-left:1.6mm}
.comb i.t{background:var(--c1l);border-color:#E6C34D;border-bottom-color:var(--ink)}
.opts{display:inline-flex;gap:4.4mm;font-size:7.6pt;font-weight:500}
.opts span{display:inline-flex;align-items:center;gap:1.4mm}
.opts span::before{content:"";width:3.4mm;height:3.4mm;border:1.2px solid var(--navy);border-radius:0}
/* Véhicules */
table{border-collapse:separate;border-spacing:0;width:100%}
.veh{margin-top:2mm;border:1px solid var(--rule);border-radius:0;overflow:hidden}
.veh th{background:var(--navy);text-align:left;font-size:5.8pt;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#fff;padding:1.9mm 2.2mm}
.veh th .hint{text-transform:none;letter-spacing:0;font-weight:500;color:#FFFFFF;margin-left:1.4mm}
.veh td{padding:2.2mm 2.2mm;border-top:1px solid var(--hair);vertical-align:bottom;height:12.4mm}
.veh tbody tr:first-child td{border-top:0}
.veh td.n{width:9mm;font:800 13pt "Inter Display",Inter,sans-serif;color:var(--navy);vertical-align:middle;text-align:center;background:var(--tint)}
.veh th:nth-child(2){width:26mm}.veh th:nth-child(3){width:27mm}
.veh .w{height:5mm;border-bottom:1px solid var(--rule)}
.veh .comb i{width:4.05mm}
.obs{flex:1;border:1px solid var(--rule);background:#fff;min-height:14mm;display:flex;flex-direction:column;justify-content:space-evenly;padding:0 2.2mm}
.obs i{display:block;height:0;border-bottom:1px solid var(--hair)}
footer{display:flex;justify-content:space-between;gap:6mm;margin:3mm 10mm 7mm 22mm;padding-top:2mm;border-top:1px solid var(--rule);font-size:6pt;color:var(--mute)}
footer .ver{font-weight:700;color:var(--navy);white-space:nowrap}
/* Page 2 */
.p2ref{display:flex;gap:2mm;margin-top:3.6mm}
.p2ref .case{min-height:12mm}
.vins{display:grid;grid-template-columns:1fr 1fr;gap:2mm;margin-top:2mm}
.vins .case{min-height:12mm}
.vins .comb{gap:.5mm}.vins .comb i{width:4.25mm;height:5.6mm}
.mx{margin-top:3mm;table-layout:fixed}
.mx thead th{background:var(--navy);color:#fff;text-align:left;padding:2mm 2mm;vertical-align:top}
.mx thead th:first-child{border-top-left-radius:0}
.mx thead th:last-child{border-top-right-radius:0}
.mx th.rh{font-size:6pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;vertical-align:bottom;color:#FFFFFF}
.vh{font:700 8.6pt "Inter Display",Inter,sans-serif}
.vr{display:flex;align-items:center;gap:1mm;font-size:5.8pt;color:#FFFFFF;margin-top:1.4mm;white-space:nowrap}
.vr .comb{gap:.35mm}
.vr .comb i{width:3.4mm;height:4.4mm;border-color:#FFFFFF;border-bottom-color:#fff;background:transparent}
.mx tr.ph td{padding:1.3mm 2mm .9mm;border-left:1px solid var(--rule);border-right:1px solid var(--rule)}
.mx tr.ph span{font-size:6pt;font-weight:800;letter-spacing:.2em;text-transform:uppercase}
.mx tr.ph.c1 td{background:var(--c1l)}.mx tr.ph.c1 span{color:var(--navy)}
.mx tr.ph.c2 td{background:var(--c2l)}.mx tr.ph.c2 span{color:var(--navy)}
.mx tr.ph.c3 td{background:var(--c3l)}.mx tr.ph.c3 span{color:var(--navy)}
.mx tr.st{height:22mm}
.mx tr.st td,.mx tr.st th{border-top:1px solid var(--rule)}
.mx tr.st td{border-left:1px solid var(--hair);padding:1.5mm 1.8mm 1.2mm;vertical-align:top}
.mx tr.st td:last-child,.mx tr.tot td:last-child{border-right:1px solid var(--rule)}
.rail{position:relative;text-align:left;vertical-align:top;padding:1.6mm 1.6mm 1.2mm 0;background:#fff;border-left:3px solid var(--navy)}
.mx tr.c1 .rail{border-left-color:var(--c1)}.mx tr.c2 .rail{border-left-color:var(--c2)}.mx tr.c3 .rail{border-left-color:var(--c3)}
.rail .dot{position:absolute;left:1.8mm;top:1.6mm;width:5.8mm;height:5.8mm;border-radius:50%;color:#fff;font-size:7.2pt;font-weight:800;display:flex;align-items:center;justify-content:center}
.mx tr.c1 .dot{background:var(--c1)}.mx tr.c2 .dot{background:var(--c2)}.mx tr.c3 .dot{background:var(--c3)}
.rail .tt{display:block;padding-left:9.2mm;font-size:7.3pt;font-weight:700;line-height:1.22;color:var(--navy)}
.mx .top{display:flex;align-items:flex-end;justify-content:space-between;gap:1mm}
.mx .date{font-size:5.6pt;gap:.45mm}
.mx .date span{width:4.9mm}.mx .date span.y{width:8.2mm}
.tick{width:4mm;height:4mm;border:1.4px solid var(--navy);border-radius:50%;flex:none}
.mx tr.c1 .tick{border-color:var(--c1)}.mx tr.c2 .tick{border-color:var(--c2)}.mx tr.c3 .tick{border-color:var(--c3)}
.fl{display:flex;align-items:flex-end;gap:1.2mm;margin-top:1.5mm;font-size:5.6pt;font-weight:700;letter-spacing:.05em;color:var(--mute);text-transform:uppercase}
.fl span{white-space:nowrap}
.fl i{flex:1;height:3.4mm;border-bottom:1px solid var(--rule)}
.mx tr.tot th,.mx tr.tot td{border-top:1.6px solid var(--navy);border-bottom:1px solid var(--rule);background:var(--tint);vertical-align:top;padding:1.4mm 1.8mm 1.8mm}
.mx tr.tot td{border-left:1px solid var(--hair)}
.mx tr.tot .rail{border-left-color:var(--navy);background:var(--tint)}
.mx tr.tot .tt{padding-left:1.8mm;font-size:6.4pt;letter-spacing:.1em;text-transform:uppercase}
.mx tfoot tr th{border-bottom-left-radius:0}.mx tfoot tr td:last-child{border-bottom-right-radius:0}
.ctl{display:grid;grid-template-columns:1fr 1fr .9fr;gap:2mm;margin-top:auto;padding-top:3mm}
.cb{border:1px solid var(--rule);border-radius:0;padding:1.6mm 2.2mm 2mm;display:flex;flex-direction:column;gap:1.6mm}
.cb .lb{font-size:5.8pt;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--navy)}
.cb.cl{background:var(--tint)}
.sig{display:flex;align-items:flex-end;gap:1.4mm;font-size:6pt;color:var(--mute);font-weight:600}
.sig i{flex:1;height:4mm;border-bottom:1px solid var(--rule)}
.sig .date{font-size:5.6pt}.sig .date span{width:4.9mm}.sig .date span.y{width:8.2mm}

.run{flex:none;display:flex;justify-content:space-between;align-items:flex-end;gap:6mm;margin:9mm 10mm 0 22mm;padding-bottom:1.8mm;border-bottom:1.6px solid var(--navy);font-size:7pt;color:var(--mute)}
.run b{color:var(--navy);font-weight:800;letter-spacing:.04em}
.run .rr{display:flex;align-items:flex-end;gap:2mm}
.run .rr i{display:block;width:32mm;border-bottom:1px solid var(--ink);height:4mm;margin-right:3mm}
'''


def html():
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Suivi véhicules — {TRANSITAIRE}</title>'
            f'<style>{CSS}</style></head><body>{page1()}{page2()}</body></html>')


def construire(sortie: Path) -> Path:
    sortie.mkdir(parents=True, exist_ok=True)
    f = sortie / '_fiche_suivi.html'
    f.write_text(html(), encoding='utf-8')
    out = sortie / 'Fiche_suivi_vehicules.pdf'
    subprocess.run(['node', '-e', f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{f.resolve()}');await p.waitForTimeout(300);
const o=await p.evaluate(()=>[...document.querySelectorAll('section')].map(s=>{{const b=s.querySelector('.body');return Math.max(0,b.scrollHeight-b.clientHeight)}}));if(o.some(x=>x>1))console.log('  ! débordement (px) :',o);
await p.pdf({{path:'{out.resolve()}',preferCSSPageSize:true,printBackground:true}});await b.close();}})()"""], check=True)
    n = len(PdfReader(str(out)).pages)
    if n != 2:
        print(f'  ! {n} pages au lieu de 2')
    f.unlink()
    return out


if __name__ == '__main__':
    print(construire(Path(sys.argv[1] if len(sys.argv) > 1 else '.')))
