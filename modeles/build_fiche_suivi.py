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

# Fiche remplie : valeurs transcrites depuis la fiche papier (même schéma que la copie électronique).
# Vide = formulaire vierge. Ce qui est saisi s'imprime en bleu « encre ».
V = {}


def C(cle):
    return str((V.get("conteneur") or {}).get(cle) or "")


def VH(i):
    vs = V.get("vehicules") or []
    return vs[i] if i < len(vs) else {}


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hw(t):
    return f'<span class="hw">{esc(t)}</span>' if t else ''


def date(v=""):
    import re as _re
    m = _re.match(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\s*$", v or "")
    if not m:
        return DATE
    j, mo, a = m.groups()
    a = a if len(a) == 4 else "20" + a
    return f'<span class="date f"><span>{int(j):02d}</span>/<span>{int(mo):02d}</span>/<span class="y">{a}</span></span>'


def comb(n, sep=None, tint=(), txt=""):
    txt = (txt or "").replace(" ", "")
    out = ''
    for k in range(1, n + 1):
        cls = []
        if k in tint: cls.append('t')
        if sep and k == sep: cls.append('s')
        c = esc(txt[k - 1]) if k <= len(txt) else ''
        out += f'<i class="{" ".join(cls)}">{c}</i>'
    return f'<span class="comb{" f" if txt else ""}">{out}</span>'


def opts(*o, choix=""):
    return '<span class="opts">' + ''.join(f'<span class="{"on" if choix and choix.lower().startswith(x.lower()[:5]) else ""}">{x}</span>' for x in o) + '</span>'


def case(no, label, body='', span=6):
    return (f'<div class="case" style="grid-column:span {span}"><div class="lb"><span class="no">{no}</span>{label}</div>'
            f'<div class="bd">{body}</div></div>')


def _mix(a, b, t):
    a, b = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * t):02X}' for x, y in zip(a, b))


# Fil de sécurité irisé (façon billet de banque) : argent, bleu glacier, vert d'eau, or pâle, avec des éclats
# de lumière. Construit en tranches de couleur unie (aucun dégradé ni motif PDF) : rendu identique sur téléphone,
# sur écran et à l'impression. Aucune teinte rose.
IRIS = ["#A9B2BE", "#86C3E0", "#93D3B8", "#E2CF8E", "#B3BDCA", "#82AEDD", "#A9B2BE"]


def fil(n=150):
    import math
    out = []
    for i in range(n):
        t = i / (n - 1) * (len(IRIS) - 1)
        k = min(int(t), len(IRIS) - 2)
        c = _mix(IRIS[k], IRIS[k + 1], t - k)
        eclat = max(0.0, math.sin(i / n * math.pi * 9)) ** 6
        if eclat > .05:
            c = _mix(c, "#FFFFFF", .75 * eclat)
        out.append(f'<i style="background:{c}"></i>')
    return '<div class="fil">' + ''.join(out) + '</div>'


def marques():
    """Repères DIN 5008 (perforation 148,5 mm, pliage 105 et 210 mm) et fil de sécurité irisé."""
    return ('<i class="mk fold" style="top:105mm"></i><i class="mk punch" style="top:148.5mm"></i><i class="mk fold" style="top:210mm"></i>'
            + fil())


# Application de suivi : le code QR ouvre la fiche (ses 4 véhicules) dans l'application, accès réservé au propriétaire.
APP = "https://claude.ai/artifact/X8uFgUARsXywWx1xEgdRM1"
# Copie électronique publique : le code QR porte le numéro de fiche et sa clé de déchiffrement (128 bits, tirée au hasard
# à l'impression et conservée nulle part ailleurs que sur le papier). Sans le code QR, la fiche reste illisible.
VIEWER = "https://claude.ai/artifact/9x4ffQjpySXHDyooHYMVHN"
SERIE = {"n": None, "cle": None}   # numéro de fiche en cours (carnet numéroté)


def luhn(num: str) -> int:
    """Chiffre de contrôle de Luhn (celui des cartes bancaires) : une faute de frappe sur le numéro est détectée."""
    s = 0
    for i, d in enumerate(reversed(num)):
        d = int(d) * (2 if i % 2 == 0 else 1)
        s += d - 9 if d > 9 else d
    return (10 - s % 10) % 10


def numero(n: int, annee: int) -> str:
    base = f"{annee % 100:02d}{n:05d}"
    return f"GM-{annee % 100:02d}-{n:05d}-{luhn(base)}"


def qr(texte: str, taille_mm: float = 17) -> str:
    """Code QR vectoriel (reportlab), lisible par n'importe quel téléphone."""
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderSVG
    w = QrCodeWidget(texte, barLevel='L')
    x1, y1, x2, y2 = w.getBounds()
    d = Drawing(x2 - x1, y2 - y1)
    d.add(w)
    svg = renderSVG.drawToString(d)
    svg = svg[svg.index('<svg'):]
    return f'<span class="qr" style="width:{taille_mm}mm;height:{taille_mm}mm">{svg}</span>'


def serie(page):
    n = SERIE["n"]
    if not n:
        return ''
    return (f'<div class="ser">{qr(VIEWER + "#f-" + n + "-" + SERIE["cle"])}'
            f'<div class="sn"><span>N° de fiche</span><b>{n}</b></div></div>')


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
    {serie(page)}
    <dl class="meta">
      <dt>Réf. dossier</dt><dd>{hw(C("ref_dossier"))}</dd>
      <dt>N° facture</dt><dd>{hw(C("n_facture"))}</dd>
      <dt>N° facture TC vide</dt><dd>{hw(C("n_facture_tc_vide"))}</dd>
    </dl>
  </header>'''


def tete_suite():
    """En-tête courant de la page de suite."""
    return f'''
  <header class="inv suite">
    <div class="from"><div class="brand">{TRANSITAIRE}</div><p>Suivi véhicules · feuille étapes</p></div>
    {serie("2 / 2")}
    <dl class="meta"><dt>Réf. dossier</dt><dd>{hw(C("ref_dossier"))}</dd></dl>
  </header>'''


def guilloche(largeur=178, hauteur=4.6, n=14):
    """Bande guillochée (lignes fines entrelacées, comme sur les billets et les chèques). Tracés vectoriels simples, sans motif ni dégradé."""
    import math
    pts = 360
    chemins = []
    for k in range(n):
        ph = 2 * math.pi * k / n
        xs = []
        for i in range(pts + 1):
            x = largeur * i / pts
            t = 2 * math.pi * x / 9.0
            y = hauteur / 2 + (hauteur / 2 - .25) * (0.62 * math.sin(t + ph) + 0.38 * math.sin(2.7 * t - ph))
            xs.append(f"{x:.2f},{y:.2f}")
        chemins.append(f'<polyline points="{" ".join(xs)}"/>')
    return (f'<svg viewBox="0 0 {largeur} {hauteur}" width="{largeur}mm" height="{hauteur}mm" preserveAspectRatio="none">'
            f'<g fill="none" stroke="#8E9BAC" stroke-width=".09">{"".join(chemins)}</g></svg>')


def microtexte():
    """Ligne en microtexte : lisible à la loupe, elle se brouille à la photocopie."""
    motif = f"{TRANSITAIRE} · DÉCLARANT {DECLARANT} · SUIVI VÉHICULES · "
    return f'<div class="micro">{motif * 14}</div>'


def pied(gauche, page="1 / 2"):
    return f'''<footer><div class="note">{gauche}</div>{microtexte()}<div class="cols">
    <div><b>Transitaire</b>{TRANSITAIRE}</div>
    <div><b>Déclarant en douane</b>{DECLARANT}</div>
    <div><b>Document</b>Suivi véhicules · dédouanement jusqu'à livraison</div>
    <div class="pg"><b>Page</b>{page}</div></div></footer>'''


def page1():
    def ligne(k):
        v = VH(k - 1)
        etat = opts("Neuf", "Moins de 3 ans · avec PV d'expertise", choix=v.get("etat", ""))
        return (f'<tr class="va"><td class="n" rowspan="2">{k}</td><td><div class="il"><span class="k">Marque</span>{hw(v.get("marque")) or "<i></i>"}</div></td>'
                f'<td><div class="il"><span class="k">Modèle · couleur</span>{hw(v.get("modele")) or "<i></i>"}</div></td><td class="et">{etat}</td></tr>'
                f'<tr class="vb"><td colspan="3">{comb(17, tint=range(12, 18), txt=v.get("vin", ""))}</td></tr>')
    vehs = ''.join(ligne(k) for k in range(1, 5))
    return f'''
<section>{marques()}{tete("Feuille conteneur", "1 / 2")}
  <div class="guiw">{guilloche()}</div>
  <div class="body">
  <div class="sec"><span class="sl">A</span>Conteneur et transport</div>
  <div class="grid">
    {case(1, "Transitaire", f'<span class="pre">{TRANSITAIRE}</span>', 4)}
    {case(2, "Compagnie maritime", hw(C("compagnie")), 4)}
    {case(3, "CRN", hw(C("crn")), 4)}
    {case(4, "N° du TC · date", '<span class="big">' + comb(11, sep=5, txt=C("tc")) + '</span>' + '<span class="gap"></span>' + date(C("tc_date")), 8)}
    {case(5, "N° B/L", hw(C("bl")), 4)}
    {case(6, "Bon à délivrer", opts("Récupéré", "Non récupéré", choix=C("bad")) + '<span class="gap"></span>' + date(C("bad_date")), 7)}
    {case(7, "Bureau de douane", hw(C("bureau")), 5)}
  </div>
  <div class="sec"><span class="sl">B</span>Entreposage et dépotage</div>
  <div class="grid">
    {case(8, "Entrepôt", hw(C("entrepot")), 5)}
    {case(9, "État de dépotage · date", opts("Dépoté", "Non dépoté", choix=C("depotage")) + '<span class="gap"></span>' + date(C("depotage_date")), 7)}
    {case(10, "Groupeur", hw(C("groupeur")), 7)}
    {case(11, "Relâche du groupeur", opts("Oui", "Non", choix=C("relache")), 5)}
  </div>
  <div class="sec"><span class="sl">C</span>TC vide</div>
  <div class="grid">
    {case(12, "Facturation du TC vide", date(C("tc_vide_facturation")), 4)}
    {case(13, "Livraison du TC vide", date(C("tc_vide_livraison")), 4)}
    {case(14, "Montant facturation TC", hw(C("tc_vide_montant")) + '<span class="gap"></span><span class="unit">DA</span>', 4)}
  </div>
  <div class="sec"><span class="sl">D</span>Client et véhicules sur le TC</div>
  <div class="grid">{case(15, "Nom du client", hw(C("client")), 8)}{case(16, "Tél. client", hw(C("tel")), 4)}</div>
  <table class="veh">
    <thead><tr><th>N°</th><th colspan="3">Véhicules sur le TC · marque, modèle, état et n° de châssis (VIN) <span class="hint">· 6 dernières cases teintées = référence</span></th></tr></thead>
    <tbody>{vehs}</tbody>
  </table>
  <div class="sec"><span class="sl">E</span>Observations</div>
  <div class="obsrow"><div class="obs">{('<p class="hwo">' + esc(C("observations")) + '</p>') if C("observations") else '<i></i><i></i>'}</div><div class="holo"><span>Hologramme<br>de sécurité</span></div></div>
  </div>
  {pied("VIN : 17 caractères, jamais I, O ni Q · dates portées à la main à chaque étape")}
</section>'''


PHASES = [
    ("Douane", "c1", [
        ("decl", "Déclaration D10", [("N° D10", "n_d10"), ("EPC", "epc"), ("APC", "apc")]),
        ("liq", "Liquidation avec l'inspecteur et l'agent", [("Inspecteur", "inspecteur"), ("Montant DA", "montant_inspecteur"), ("Agent", "agent"), ("Montant DA", "montant_agent")]),
        ("dedo", "Dédouanement", [("Paiement", "paiement", ["Chèque", "Paiement électronique"])]),
    ]),
    ("Règlement", "c2", [
        ("bae", "Bon à enlever · quittance", [("N° bon à enlever", "n_bae"), ("N° quittance", "n_quittance"), ("Montant DA", "montant")]),
        ("fact", "Facturation", [("N° facture", "n_facture"), ("Montant DA", "montant")]),
    ]),
    ("Livraison et 846", "c3", [
        ("livr", "Livraison au propriétaire", [("Transporteur", "transporteur"), ("Reçu par", "recu_par")]),
        ("d846", "Demande du 846", [("N° de dépôt", "n_depot")]),
        ("p846", "846 prêt et remis", [("N° 846", "n_846"), ("Remis à", "remis_a")]),
    ]),
]


def cellule(champs, x=None):
    x = x or {}
    fait = x.get("fait") or x.get("date")
    h = f'<td><div class="top">{date(x.get("date", ""))}<span class="tick{" on" if fait else ""}"></span></div>'
    for c in champs:
        if len(c) == 3:
            choix = x.get(c[1], "")
            h += f'<div class="fl"><span>{c[0]}</span></div><div class="ops">' + ''.join(
                f'<span class="{"on" if choix and choix.lower().startswith(o.lower()[:5]) else ""}">{o}</span>' for o in c[2]) + '</div>'
        else:
            h += f'<div class="fl"><span>{c[0]}</span>{hw(x.get(c[1])) or "<i></i>"}</div>'
    return h + '</td>'


def page2():
    head = ''.join(f'<th><div class="vh">Véhicule {k}</div><div class="vr">VIN : voir case V{k}</div></th>' for k in range(1, 5))
    vins = ''.join(f'<div class="case vin"><div class="lb"><span class="no">V{k}</span>Véhicule {k} · N° de châssis (VIN)</div><div class="bd">{comb(17, tint=range(12, 18), txt=VH(k - 1).get("vin", ""))}</div></div>' for k in range(1, 5))
    rows, k = '', 0
    for phase, c, etapes in PHASES:
        rows += f'<tr class="ph {c}"><td colspan="5"><span>{phase}</span></td></tr>'
        for cle, titre, champs in etapes:
            k += 1
            rows += (f'<tr class="st {c}"><th class="rail"><span class="dot">{k}</span><span class="tt">{titre}</span></th>'
                     + ''.join(cellule(champs, (VH(i).get("etapes") or {}).get(cle)) for i in range(4)) + '</tr>')
    tot = ''.join(f'<td><div class="fl"><span>Payé DA</span>{hw((VH(i).get("totaux") or {}).get("paye")) or "<i></i>"}</div>'
                  f'<div class="fl"><span>Facturé DA</span>{hw((VH(i).get("totaux") or {}).get("facture")) or "<i></i>"}</div></td>' for i in range(4))
    return f'''
<section>{marques()}{tete_suite()}
  <div class="body">
  <div class="p2ref"><div class="case" style="flex:1.25"><div class="lb"><span class="no">4</span>N° du TC</div><div class="bd">{comb(11, sep=5, txt=C("tc"))}</div></div></div>
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
header.inv{padding-top:17mm!important}
header.inv:not(.suite) h1{margin-top:1.6mm!important;font-size:22pt!important}
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
.mx tr.st{height:17.8mm}
'''

SECURITE = '''
.guiw{flex:none;margin:1.8mm 10mm 0 22mm;height:4.6mm;overflow:hidden;border-top:1px solid var(--hair);border-bottom:1px solid var(--hair)}
.guiw svg{display:block}
.micro{font-size:2.3pt;line-height:1;letter-spacing:.02em;color:var(--mute);white-space:nowrap;overflow:hidden;border-top:1px solid var(--rule);padding:.5mm 0 .4mm}
footer .cols{border-top:0!important;padding-top:1.2mm!important}
.obsrow{flex:1;display:flex;gap:2mm;min-height:13mm}
.case{min-height:9.6mm!important}
.sec{margin-top:2.6mm!important;margin-bottom:1.3mm!important}
.veh td{height:auto}
.veh tr.va td{padding-top:1.2mm!important;padding-bottom:.4mm!important}
.veh tr.vb td{padding-top:.6mm!important;padding-bottom:1.4mm!important}
.obsrow .obs{flex:1}
header.inv{grid-template-columns:1fr auto 62mm!important}
.ser{display:flex;flex-direction:column;align-items:center;gap:.8mm;align-self:end}
.qr{display:block}.qr svg{width:100%;height:100%;display:block}
.sn{text-align:center;line-height:1.15}
.sn span{display:block;font-size:4.8pt;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--mute)}
.sn b{font:700 7pt "DejaVu Sans Mono",monospace;color:var(--navy);letter-spacing:.02em}
header.inv.suite .qr{width:14mm!important;height:14mm!important}
header.inv.suite .ser{flex-direction:row;gap:2mm}
header.inv.suite .sn{text-align:left}
header.inv.suite{padding-top:5mm!important}
/* Saisie : encre bleue */
.hw{color:#123E8C;font-weight:700;font-size:9pt;letter-spacing:.02em;line-height:1.15;flex:1;min-width:0}
.fl .hw,.il .hw{font-size:6.8pt;border-bottom:1px solid var(--rule);padding-bottom:.2mm}
.meta dd .hw{display:block;padding-top:2.2mm;font-size:8pt}
.comb.f i{display:flex;align-items:center;justify-content:center;font:700 8pt "DejaVu Sans Mono",monospace;color:#123E8C}
.date.f{color:#123E8C}.date.f span{border-bottom-color:#123E8C}
.opts span.on::before,.ops span.on::before{content:"✓";background:#123E8C;border-color:#123E8C!important;color:#fff;font-size:6.6pt;font-weight:800;display:inline-flex;align-items:center;justify-content:center}
.tick.on{background:#123E8C;border-color:#123E8C!important}
.hwo{margin:0;padding:1.6mm 2.2mm;color:#123E8C;font-weight:700;font-size:8.6pt}
.fil{position:absolute;left:15.2mm;top:0;width:4mm;height:297mm;display:flex;flex-direction:column;z-index:5}
.fil i{flex:1;display:block}
.holo{flex:none;width:22mm;border:1px dashed var(--mute);display:flex;align-items:center;justify-content:center;text-align:center;font-size:5.6pt;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);line-height:1.4}
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


def html(palette="facture-ue", numeros=(None,)):
    corps = ''
    import secrets
    for n in numeros:
        SERIE["n"], SERIE["cle"] = n, secrets.token_hex(16)
        corps += page1() + page2()
    SERIE["n"] = None
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Suivi véhicules — {TRANSITAIRE}</title>'
            f'<style>{CSS}{PALETTES[palette]}{SECURITE}</style></head><body>{corps}</body></html>')


def remplie(donnees: dict, sortie: Path, numero: str, cle: str, palette: str = "britannique") -> Path:
    """Fiche remplie (saisie en bleu) au numéro et à la clé donnés : son code QR ouvre sa copie électronique."""
    global V
    V = donnees
    try:
        sortie.mkdir(parents=True, exist_ok=True)
        f = sortie / '_fiche_remplie.html'
        SERIE["n"], SERIE["cle"] = numero, cle
        corps = page1() + page2()
        SERIE["n"] = SERIE["cle"] = None
        f.write_text(f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Fiche {numero}</title><style>{CSS}{PALETTES[palette]}{SECURITE}</style></head><body>{corps}</body></html>', encoding='utf-8')
        out = sortie / f'Fiche_suivi_vehicules_{numero}_remplie.pdf'
        subprocess.run(['node', '-e', f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{f.resolve()}');await p.waitForTimeout(300);
const o=await p.evaluate(()=>[...document.querySelectorAll('section')].map(s=>{{const b=s.querySelector('.body');return Math.max(0,b.scrollHeight-b.clientHeight)}}));if(o.some(x=>x>1))console.log('  ! débordement (px) :',o);
await p.pdf({{path:'{out.resolve()}',preferCSSPageSize:true,printBackground:true}});await b.close();}})()"""], check=True)
        f.unlink()
        return out
    finally:
        V = {}


def construire(sortie: Path, palette: str = "britannique", debut: int = 0, nombre: int = 1, annee: int = 2026) -> Path:
    """debut = 0 : fiche sans numéro. debut >= 1 : carnet de `nombre` fiches numérotées à partir de `debut`."""
    sortie.mkdir(parents=True, exist_ok=True)
    f = sortie / '_fiche_suivi.html'
    nums = [numero(debut + k, annee) for k in range(nombre)] if debut else [None]
    f.write_text(html(palette, nums), encoding='utf-8')
    suffixe = '' if palette == "facture-ue" else f'_{palette}'
    if debut:
        suffixe += f'_carnet_{nums[0]}_a_{nums[-1]}'
    out = sortie / f'Fiche_suivi_vehicules{suffixe}.pdf'
    subprocess.run(['node', '-e', f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{f.resolve()}');await p.waitForTimeout(300);
const o=await p.evaluate(()=>[...document.querySelectorAll('section')].map(s=>{{const f=s.querySelector('footer');return Math.max(0,Math.round(f.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom))}}));if(o.some(x=>x>1))console.log('  ! débordement (px) :',o);
await p.pdf({{path:'{out.resolve()}',preferCSSPageSize:true,printBackground:true}});await b.close();}})()"""], check=True)
    n = len(PdfReader(str(out)).pages)
    if n != 2 * len(nums):
        print(f'  ! {n} pages au lieu de {2 * len(nums)}')
    f.unlink()
    return out


if __name__ == '__main__':
    a = sys.argv
    print(construire(Path(a[1] if len(a) > 1 else '.'), a[2] if len(a) > 2 else "britannique",
                     int(a[3]) if len(a) > 3 else 0, int(a[4]) if len(a) > 4 else 1))
