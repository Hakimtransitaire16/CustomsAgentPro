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

TRANSITAIRE = "SARL TRANSIT GMOR"
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
    """En-tête de facture européenne : émetteur et titre à gauche, bloc de références à droite."""
    return f'''
  <header class="inv">
    <div class="from">
      <div class="brand">{TRANSITAIRE}</div>
      <div class="who">Déclarant : {DECLARANT}</div>
      <h1>Suivi véhicules</h1>
      <p>Dédouanement jusqu'à livraison · {sous_titre}</p>
    </div>
    <dl class="meta">
      <dt>Réf. dossier</dt><dd></dd>
      <dt>N° facture</dt><dd></dd>
      <dt>N° facture TC vide</dt><dd></dd>
    </dl>
  </header>'''


def tete_suite():
    """En-tête courant de la page de suite."""
    return f'''
  <header class="inv suite">
    <div class="from"><div class="brand">{TRANSITAIRE}</div><p>Suivi véhicules · feuille étapes</p></div>
    <dl class="meta"><dt>Réf. dossier</dt><dd></dd></dl>
  </header>'''


def pied(gauche, page="1 / 2"):
    return f'''<footer><div class="note">{gauche}</div><div class="cols">
    <div><b>Transitaire</b>{TRANSITAIRE}</div>
    <div><b>Déclarant en douane</b>{DECLARANT}</div>
    <div><b>Document</b>Suivi véhicules · dédouanement jusqu'à livraison</div>
    <div class="pg"><b>Page</b>{page}</div></div></footer>'''


def page1():
    vin = comb(17, tint=range(12, 18))
    etat = opts("Neuf", "Moins de 3 ans · avec PV d'expertise")
    vehs = ''.join(f'<tr class="va"><td class="n" rowspan="2">{k}</td><td><div class="il"><span class="k">Marque</span><i></i></div></td><td><div class="il"><span class="k">Modèle · couleur</span><i></i></div></td><td class="et">{etat}</td></tr>'
                   f'<tr class="vb"><td colspan="3">{vin}</td></tr>' for k in range(1, 5))
    return f'''
<section>{marques()}{tete("Feuille conteneur", "1 / 2")}
  <div class="body">
  <div class="sec"><span class="sl">A</span>Conteneur et transport</div>
  <div class="grid">
    {case(1, "Transitaire", f'<span class="pre">{TRANSITAIRE}</span>', 4)}
    {case(2, "Compagnie maritime", '', 4)}
    {case(3, "CRN", '', 4)}
    {case(4, "N° du TC · date", '<span class="big">' + comb(11, sep=5) + '</span>' + '<span class="gap"></span>' + DATE, 8)}
    {case(5, "N° B/L", '', 4)}
    {case(6, "Bon à délivrer", opts("Récupéré", "Non récupéré") + '<span class="gap"></span>' + DATE, 7)}
    {case(7, "Bureau de douane", '', 5)}
  </div>
  <div class="sec"><span class="sl">B</span>Entreposage et dépotage</div>
  <div class="grid">
    {case(8, "Entrepôt", '', 5)}
    {case(9, "État de dépotage · date", opts("Dépoté", "Non dépoté") + '<span class="gap"></span>' + DATE, 7)}
    {case(10, "Groupeur", '', 7)}
    {case(11, "Relâche du groupeur", opts("Oui", "Non"), 5)}
  </div>
  <div class="sec"><span class="sl">C</span>TC vide</div>
  <div class="grid">
    {case(12, "Facturation du TC vide", DATE, 4)}
    {case(13, "Livraison du TC vide", DATE, 4)}
    {case(14, "Montant facturation TC", '<span class="gap"></span><span class="unit">DA</span>', 4)}
  </div>
  <div class="sec"><span class="sl">D</span>Client et véhicules sur le TC</div>
  <div class="grid">{case(15, "Nom du client", '', 8)}{case(16, "Tél. client", '', 4)}</div>
  <table class="veh">
    <thead><tr><th>N°</th><th colspan="3">Véhicules sur le TC · marque, modèle, état et n° de châssis (VIN) <span class="hint">· 6 dernières cases teintées = référence</span></th></tr></thead>
    <tbody>{vehs}</tbody>
  </table>
  <div class="sec"><span class="sl">E</span>Observations</div>
  <div class="obs"><i></i><i></i></div>
  </div>
  {pied("VIN : 17 caractères, jamais I, O ni Q · dates portées à la main à chaque étape")}
</section>'''


PHASES = [
    ("Douane", "c1", [
        ("Déclaration D10", ["N° D10", "EPC", "APC"]),
        ("Liquidation avec l'inspecteur et l'agent", ["Inspecteur", "Montant DA", "Agent", "Montant DA"]),
        ("Dédouanement", [("Paiement", ["Chèque", "Paiement électronique"])]),
    ]),
    ("Règlement", "c2", [
        ("Bon à enlever · quittance", ["N° bon à enlever", "N° quittance", "Montant DA"]),
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
        if isinstance(c, tuple):
            h += f'<div class="fl"><span>{c[0]}</span></div><div class="ops">' + ''.join(f'<span>{o}</span>' for o in c[1]) + '</div>'
        else:
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
  <div class="p2ref"><div class="case" style="flex:1.25"><div class="lb"><span class="no">4</span>N° du TC</div><div class="bd">{comb(11, sep=5)}</div></div></div>
  <div class="vins">{vins}</div>
  <table class="mx"><colgroup><col style="width:31mm"><col><col><col><col></colgroup>
    <thead><tr><th class="rh">Étape</th>{head}</tr></thead>
    <tbody>{rows}</tbody>
    <tfoot><tr class="tot"><th class="rail"><span class="tt">Totaux du véhicule</span></th>{tot}</tr></tfoot></table>
  </div>
  {pied("Une ligne = une étape pour les 4 véhicules · une colonne = le parcours d'un véhicule · cocher le rond quand l'étape est faite", "2 / 2")}
</section>'''


CSS = '''
@page{size:A4 portrait;margin:0}
:root{--navy:#003399;--navy2:#2B2F33;--ink:#0B0C0C;--mute:#505A5F;--ghost:#A3AAB0;--rule:#B1B4B6;--hair:#D9DBDD;--tint:#F3F2F1;
  --c1:#003399;--c1l:#FFF4C2;--c2:#003399;--c2l:#FFF4C2;--c3:#003399;--c3l:#FFF4C2;--gold:#FFFFFF;--eu:#003399;--yellow:#FFCC00;--hl-line:#E6C34D}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,"DejaVu Sans",sans-serif;color:var(--ink);font-size:8pt;line-height:1.3;-webkit-print-color-adjust:exact;print-color-adjust:exact}
section{position:relative;width:210mm;height:297mm;display:flex;flex-direction:column;break-after:page;overflow:hidden}
section:last-child{break-after:auto}
.body{flex:1;display:flex;flex-direction:column;padding:0 10mm 0 22mm}
/* Repères DIN 5008 */
.mk{position:absolute;left:0;height:0;border-top:.6pt solid #8C99AA}
.mk.fold{width:4mm}.mk.punch{width:7mm}
/* En-tête pleine largeur */
header{background:var(--navy);color:#fff;display:grid;grid-template-columns:42mm 1fr 70mm;align-items:end;gap:4mm;padding:7mm 10mm 5mm 22mm}
.brand{font:800 15pt/1 "Inter Display",Inter,sans-serif;letter-spacing:.1em}
.who{font-size:6.2pt;letter-spacing:.08em;text-transform:uppercase;color:#FFFFFF;margin-top:2mm;line-height:1.45}
.kick{font-size:6.2pt;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--yellow)}
.hm h1{font:700 24pt/1 "Inter Display",Inter,sans-serif;letter-spacing:-.03em;margin-top:1.4mm}
.hm p{font-size:7.6pt;color:#FFFFFF;margin-top:1.4mm}
.hrs{display:flex;flex-direction:column;gap:1.2mm}
.hr2{display:grid;grid-template-columns:1fr 1fr;gap:1.2mm}
.hr{background:#fff;color:var(--ink);border-radius:0;padding:1.3mm 2.6mm 1.4mm;position:relative}
.hr .lb{font-size:5.8pt;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--navy)}
.hr .v{height:5mm;border-bottom:1.2px solid var(--navy)}
.hr .pg{position:absolute;top:1.3mm;right:2.6mm;font-size:5.8pt;font-weight:600;color:var(--mute)}
.stripe{display:flex;height:2mm;flex:none}
header,footer{flex:none}
.mx tr.st{height:18.6mm}
.stripe i{flex:1;background:var(--yellow)}
/* Sections */
.sec{display:flex;align-items:center;gap:2.8mm;margin:2.8mm 0 1.6mm;font-size:9.4pt;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--navy)}
.sec::after{content:"";flex:1;height:1.4px;background:var(--ink)}
.sl{width:6.6mm;height:6.6mm;font-size:9pt!important;border-radius:0;background:var(--eu);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:7pt;letter-spacing:0}
/* Cases numérotées */
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:2mm}
.case{border:.9px solid var(--rule);border-top:1.6px solid var(--ink);border-radius:0;background:#fff;padding:1.4mm 2.2mm 1.5mm;min-height:10.8mm;display:flex;flex-direction:column}
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
.comb i.t{background:var(--c1l);border-color:var(--hl-line);border-bottom-color:var(--ink)}
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
.obs{flex:1;border:1px solid var(--rule);background:#fff;min-height:9mm;display:flex;flex-direction:column;justify-content:space-evenly;padding:0 2.2mm}
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
.mx tr.st{height:18.6mm}
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

.big .comb i{width:5.4mm;height:7.2mm}
.unit{font-weight:700;color:var(--mute);font-size:7.6pt}
.veh tr.va td{border-top:1.4px solid var(--ink);height:auto;padding:1.4mm 2.2mm .8mm;vertical-align:bottom}
.veh tbody tr.va:first-child td{border-top:0}
.veh tr.vb td{border-top:0;height:auto;padding:.8mm 2.2mm 1.8mm}
.veh .k{font-size:5.8pt;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);white-space:nowrap}
.veh .il{display:flex;align-items:flex-end;gap:1.4mm}.veh .il i{flex:1;height:4.6mm;border-bottom:1px solid var(--rule)}
.veh td.et .opts{font-size:7.2pt;gap:3.6mm}
.veh tr.va td:nth-child(2){width:42mm}.veh tr.va td:nth-child(3){width:46mm}
.veh td.et .opts span{white-space:nowrap}
.veh td.n{vertical-align:middle!important}
.veh tr.vb .comb{gap:.75mm}.veh tr.vb .comb i{width:8.7mm;height:7mm;border-bottom-width:1.6px}
.veh td.n{border-right:1px solid var(--hair)}
.ops{display:flex;flex-direction:column;gap:1.2mm;margin-top:1.2mm;font-size:6.8pt;font-weight:600}
.ops span{display:inline-flex;align-items:center;gap:1.4mm}
.ops span::before{content:"";width:3.2mm;height:3.2mm;border:1.2px solid var(--navy);flex:none}
'''


# Palettes : chaque palette redéfinit les jetons de couleur (aucun dégradé, aucune teinte rosée).
FACTURE = '''
:root{--navy:#1F3A5F;--eu:#1F3A5F;--c1:#1F3A5F;--c2:#1F3A5F;--c3:#1F3A5F;--ink:#1A1D21;--mute:#626B76;--rule:#D3D8DE;--hair:#E4E7EB;--tint:#F4F6F8;
  --c1l:#F4F6F8;--c2l:#F4F6F8;--c3l:#F4F6F8;--hl-line:#AEB7C2;--yellow:#1F3A5F}
header.inv{background:#fff;color:var(--ink);display:grid;grid-template-columns:1fr 66mm;gap:8mm;align-items:end;padding:12mm 10mm 0 22mm;flex:none}
header.inv .brand{font:800 11pt/1 "Inter Display",Inter,sans-serif;letter-spacing:.12em;color:var(--navy)}
header.inv .who{font-size:7.6pt;font-weight:700;color:var(--ink);margin-top:1.6mm;letter-spacing:.06em;text-transform:uppercase}
header.inv h1{font:300 25pt/1 "Inter Display",Inter,sans-serif;letter-spacing:-.02em;color:var(--ink);margin-top:6mm}
header.inv p{font-size:7.6pt;color:var(--mute);margin-top:1.6mm}
header.inv .meta{display:grid;grid-template-columns:auto 1fr;border-top:1.6px solid var(--navy)}
header.inv .meta dt{font-size:6.4pt;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);padding:2.2mm 3mm 1.2mm 0;border-bottom:1px solid var(--hair)}
header.inv .meta dd{border-bottom:1px solid var(--hair);height:7.2mm}
header.inv.suite{grid-template-columns:1fr 66mm;padding-top:8mm}
.p2ref .case,.vins .case{min-height:10.4mm!important}
.p2ref{margin-top:2.4mm!important}
header.inv.suite p{margin-top:1.2mm}
header.inv + .body,header.inv + * {}
.body{padding-top:2mm}
.sec{font-size:8pt;font-weight:700;letter-spacing:.14em;color:var(--navy);margin:3.4mm 0 1.6mm}
.sec::after{height:1px;background:var(--rule)}
.sl{background:none!important;color:var(--navy)!important;width:auto!important;height:auto!important;font-size:8pt!important;font-weight:800}
.sl::after{content:"·";margin-left:2mm;color:var(--rule)}
.case{border:1px solid var(--rule)!important;border-top:1px solid var(--rule)!important;background:#fff}
.case .lb{font-size:6.2pt;font-weight:700;letter-spacing:.1em;color:var(--mute)}
.no{background:none!important;color:var(--navy)!important;font-weight:800;min-width:0!important;padding:0!important;font-size:6.6pt!important}
.no::after{content:"";display:inline-block;width:1px;height:3mm;background:var(--rule);margin-left:1.6mm}
.pre{font-size:9.6pt;letter-spacing:.06em}
.veh{border:0!important}
.veh th{background:#fff!important;color:var(--ink)!important;border-bottom:1.6px solid var(--navy);font-size:6.2pt}
.veh th .hint{color:var(--mute)!important}
.veh td{border-top:1px solid var(--hair)}
.veh td.n{background:#fff!important;color:var(--navy)}
.mx thead th{background:#fff!important;color:var(--ink)!important;border-bottom:1.6px solid var(--navy);border-top:1.6px solid var(--navy)}
.mx th.rh{color:var(--mute)!important}
.vr{color:var(--mute)!important}
.mx tr.ph td{background:var(--tint)!important}
.mx tr.ph span{color:var(--navy)!important}
.rail{border-left:1px solid var(--rule)!important}
footer{display:block!important;margin:3mm 10mm 7mm 22mm!important;padding-top:0!important;border-top:0!important}
footer .note{font-size:6pt;color:var(--mute);padding-bottom:1.6mm}
footer .cols{display:grid;grid-template-columns:1fr 1.2fr 1.6fr .5fr;gap:4mm;border-top:1px solid var(--rule);padding-top:1.8mm;font-size:6pt;color:var(--mute);line-height:1.4}
footer .cols b{display:block;color:var(--ink);font-weight:700}
footer .cols .pg{text-align:right}
'''

UK = r'''
/* Royaume-Uni : esprit des formulaires GOV.UK — noir, bleu, gris clair, libellés en minuscules et en gras */
:root{--navy:#0B0C0C;--eu:#1D70B8;--c1:#1D70B8;--c2:#1D70B8;--c3:#1D70B8;--ink:#0B0C0C;--mute:#505A5F;--rule:#B1B4B6;--hair:#D8DADB;--tint:#F3F2F1;
  --c1l:#F3F2F1;--c2l:#F3F2F1;--c3l:#F3F2F1;--hl-line:#B1B4B6}
header.inv{padding-top:19mm!important}
header.inv .brand{position:absolute;top:0;left:0;right:0;height:13mm;padding:4.4mm 10mm 0 22mm;background:#0B0C0C;color:#fff;border-bottom:2.2mm solid #1D70B8;font-size:12pt;letter-spacing:.06em}
header.inv.suite{padding-top:17mm!important}
header.inv h1{font-weight:700;font-size:24pt;letter-spacing:-.01em;margin-top:3mm}
header.inv .meta{border-top:2px solid #0B0C0C}
header.inv .meta dt{text-transform:none;letter-spacing:0;font-size:7pt;color:#0B0C0C}
.sec{text-transform:none;letter-spacing:0;font-size:11pt;color:#0B0C0C;margin:3mm 0 1.6mm}
.sec::after{display:none}
.sl{color:#1D70B8!important;font-size:11pt!important}
.sl::after{content:""!important;margin:0}
.case{border:1px solid var(--rule)!important;border-left:4px solid var(--rule)!important}
.case .lb{text-transform:none;letter-spacing:0;font-size:7pt;color:#0B0C0C}
.no{color:#1D70B8!important;font-size:7pt!important}
.opts span::before,.ops span::before{border:1.6px solid #0B0C0C!important}
.veh th,.mx thead th{border-bottom:2px solid #0B0C0C!important;text-transform:none!important;letter-spacing:0!important;font-size:7pt!important}
.mx thead th{border-top:2px solid #0B0C0C!important}
.mx tr.ph span{color:#0B0C0C!important;letter-spacing:.06em!important}
.tick{border-color:#0B0C0C!important}
.fl{text-transform:none!important;letter-spacing:0!important;font-size:6pt!important}
.mx tr.st{height:17.2mm}
.p2ref{margin-top:1.6mm!important}
.vins{margin-top:1.4mm!important}
.p2ref .case,.vins .case{min-height:9.8mm!important}
header.inv.suite{padding-top:9mm!important}
header.inv.suite .brand{position:static;height:auto;padding:0;background:none;color:#0B0C0C;border:0}
'''

US = r'''
/* États-Unis : esprit des formulaires fédéraux et des factures américaines — cases jointives, sections en bandeau */
:root{--navy:#0A3161;--eu:#0A3161;--c1:#0A3161;--c2:#0A3161;--c3:#0A3161;--ink:#111111;--mute:#4A4A4A;--rule:#1A1A1A;--hair:#BDBDBD;--tint:#E9EDF3;
  --c1l:#E9EDF3;--c2l:#E9EDF3;--c3l:#E9EDF3;--hl-line:#8A9BB4}
header.inv{border-bottom:2.4px solid #B31942;padding-bottom:3mm!important}
header.inv .brand{font-size:14pt;color:#111}
header.inv h1{text-transform:uppercase;font-weight:800;font-size:20pt;letter-spacing:.03em;color:#0A3161;margin-top:4mm}
header.inv .meta{border:1px solid #1A1A1A}
header.inv .meta dt{background:#E9EDF3;color:#111;padding:2mm 2.4mm 1.2mm;border-bottom:1px solid #1A1A1A;border-right:1px solid #1A1A1A}
header.inv .meta dd{border-bottom:1px solid #1A1A1A}
header.inv .meta dt:nth-last-of-type(1),header.inv .meta dd:last-of-type{border-bottom:0}
.sec{background:#0A3161;color:#fff;padding:1.3mm 2.2mm;margin:3mm 0 0;font-size:7.6pt;letter-spacing:.12em}
.sec::after{display:none}
.sl{color:#fff!important}
.sl::after{content:"—"!important;color:#fff!important}
.grid{gap:0!important;border-left:1px solid #1A1A1A;border-top:1px solid #1A1A1A}
.case{border:0!important;border-right:1px solid #1A1A1A!important;border-bottom:1px solid #1A1A1A!important}
.case .lb{color:#111;font-size:6pt}
.no{color:#111!important}
.no::after{content:"."!important;width:auto!important;height:auto!important;background:none!important;margin-left:.2mm!important}
.p2ref,.vins{gap:0!important}
.p2ref .case,.vins .case{border:1px solid #1A1A1A!important;margin:0 -1px -1px 0}
.veh{border:1px solid #1A1A1A!important;margin-top:0!important;border-top:0!important}
.veh th{background:#E9EDF3!important;border-bottom:1px solid #1A1A1A!important}
.mx thead th{background:#E9EDF3!important;border:1px solid #1A1A1A!important}
.mx tr.ph td{background:#0A3161!important}
.mx tr.ph span{color:#fff!important}
.obs{border:1px solid #1A1A1A!important;border-top:0!important}
.mx tr.st{height:18.2mm}
'''

PALETTES = {
    "facture-ue": FACTURE,
    "britannique": FACTURE + UK,
    "americaine": FACTURE + US,
    "bleu-jaune": "",
    "marine-argent": ":root{--navy:#0B2A4A;--eu:#0B2A4A;--c1:#0B2A4A;--c2:#0B2A4A;--c3:#0B2A4A;--yellow:#AEB7C2;"
                     "--c1l:#EDF0F3;--c2l:#EDF0F3;--c3l:#EDF0F3;--hl-line:#AEB7C2}",
    "marine-rouge": ":root{--navy:#0B2A4A;--eu:#0B2A4A;--c1:#0B2A4A;--c2:#0B2A4A;--c3:#0B2A4A;--yellow:#C8102E;"
                    "--c1l:#EDF0F3;--c2l:#EDF0F3;--c3l:#EDF0F3;--hl-line:#AEB7C2}"
                    ".kick{color:#FFFFFF!important}",
}


def html(palette="facture-ue"):
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Suivi véhicules — {TRANSITAIRE}</title>'
            f'<style>{CSS}{PALETTES[palette]}</style></head><body>{page1()}{page2()}</body></html>')


def construire(sortie: Path, palette: str = "facture-ue") -> Path:
    sortie.mkdir(parents=True, exist_ok=True)
    f = sortie / '_fiche_suivi.html'
    f.write_text(html(palette), encoding='utf-8')
    out = sortie / ('Fiche_suivi_vehicules.pdf' if palette == "facture-ue" else f'Fiche_suivi_vehicules_{palette}.pdf')
    subprocess.run(['node', '-e', f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{f.resolve()}');await p.waitForTimeout(300);
const o=await p.evaluate(()=>[...document.querySelectorAll('section')].map(s=>{{const f=s.querySelector('footer');return Math.max(0,Math.round(f.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom))}}));if(o.some(x=>x>1))console.log('  ! débordement (px) :',o);
await p.pdf({{path:'{out.resolve()}',preferCSSPageSize:true,printBackground:true}});await b.close();}})()"""], check=True)
    n = len(PdfReader(str(out)).pages)
    if n != 2:
        print(f'  ! {n} pages au lieu de 2')
    f.unlink()
    return out


if __name__ == '__main__':
    print(construire(Path(sys.argv[1] if len(sys.argv) > 1 else '.'), sys.argv[2] if len(sys.argv) > 2 else "facture-ue"))
