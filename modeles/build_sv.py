"""Construit le jeu imprimable d'un conteneur : SV-01 (fiche conteneur, 4 véhicules, paysage) puis 4 fiches SV-02 numérotées (portrait).
Usage : python modeles/build_sv.py <dossier de sortie>"""
import re, subprocess, sys, tempfile
from pathlib import Path
from pypdf import PdfReader, PdfWriter

ICI = Path(__file__).parent
DT = '<span class="dt"><i></i><i></i><em>/</em><i></i><i></i><em>/</em><i></i><i></i><i></i><i></i></span>'

def cellule(i):
    h = '<td><div class="cell"><div>Date</div>' + DT + '<div class="r">N°<i></i></div>'
    if i in (0, 2): h += '<div class="r">EPC<i></i></div>'
    if i == 0: h += '<div class="r">APC<i></i></div>'
    if i in (1, 3, 4): h += '<div class="r">DA<i></i></div>'
    if i == 1: h += '<div class="r">Insp.<i></i></div>'
    if i in (5, 7): h += '<div class="r">Sign.<i></i></div>'
    return h + '<div class="r">Obs.<i></i></div></div></td>'

def html(lignes=4):
    t = (ICI / "suivi_vehicules.html").read_text(encoding="utf-8")
    t = t.replace('</style>', '.mx .dt{gap:0}.mx .dt i{width:2.25mm;height:3.8mm;border-bottom:1px solid var(--navy);margin-right:.15mm}.mx .dt em{font-size:6pt;padding:0 .3mm}\n</style>', 1)
    rows = ''
    for n in range(1, lignes + 1):
        rows += f'<tr><td class="v"><div class="vn"><b>{n}</b><div class="vin">' + '<i></i>' * 17 + '</div></div>'
        rows += '<div class="fl">Marque · modèle<i></i></div><div class="fl">Client · tél.<i></i></div>'
        rows += '<div class="fl">Couleur<i></i>1re immat.<i></i></div>'
        rows += '<div class="ck"><span>Neuf</span><span>&lt; 3 ans</span><span>Photos</span></div></td>'
        rows += ''.join(cellule(i) for i in range(8)) + '</tr>\n'
    reg = ''.join('<tr><td>V-</td>' + '<td></td>' * 11 + '</tr>' for _ in range(19))
    return t.replace('__REG__', reg).replace('__ROWS__', rows).replace('__VIN17__', '<i></i>' * 17).replace('__DATE__', DT)

def _tete(head, cls):
    page = '@page{size:A4 portrait;margin:10mm 11mm}' if cls == 'port' else '@page{size:A4 landscape;margin:9mm 10mm}'
    return re.sub(r'@page land\{[^}]*\}\n@page port\{[^}]*\}', page, head)

def _pdf(html_text, out):
    f = out.with_suffix('.html'); f.write_text(html_text, encoding='utf-8')
    subprocess.run(['node', '-e', f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{f}');await p.waitForTimeout(300);await p.pdf({{path:'{out}',preferCSSPageSize:true,printBackground:true}});await b.close();}})()"""], check=True)
    n = len(PdfReader(str(out)).pages)
    if n != 1: print(f'  ! débordement : {out.name} sur {n} pages')

def construire(sortie: Path) -> Path:
    t = html()
    head, body = t.split('<body>', 1)
    parts = re.findall(r'(<section class="(land|port|reg)">.*?</section>)', body, re.S)
    regs = [p for p in parts if p[1] == 'reg']
    land = [p for p in parts if p[1] == 'land']
    port = [p for p in parts if p[1] == 'port'][0]
    parts = land + [(port[0].replace('__NUM__', str(k)), 'port') for k in range(1, 5)]
    tmp = Path(tempfile.mkdtemp())
    pdfs = []
    for sec, cls in parts:
        h = _tete(head, cls)
        f = tmp / f'{cls}{len(pdfs)}.html'; f.write_text(h + '<body>' + sec + '</body></html>', encoding='utf-8')
        out = tmp / f'{cls}{len(pdfs)}.pdf'
        subprocess.run(['node', '-e', f"""const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{f}');await p.waitForTimeout(300);await p.pdf({{path:'{out}',preferCSSPageSize:true,printBackground:true}});await b.close();}})()"""], check=True)
        n = len(PdfReader(str(out)).pages)
        if n != 1: print(f'  ! débordement : {cls} sur {n} pages')
        pdfs.append(out)
    w = PdfWriter()
    for f in pdfs:
        for p in PdfReader(str(f)).pages: w.add_page(p)
    w.add_metadata({'/Title': 'Suivi de dédouanement — un conteneur, 4 véhicules (SV-01 + 4 × SV-02)', '/Author': 'ABDEL HAKIM HADJALLAH'})
    sortie.mkdir(parents=True, exist_ok=True)
    out = sortie / 'Suivi_vehicules_SV.pdf'
    with open(out, 'wb') as fh: w.write(fh)
    for sec, cls in regs:
        r = sortie / 'Registre_conteneurs_SV-03.pdf'
        _pdf(_tete(head, cls) + '<body>' + sec + '</body></html>', r)
    return out

if __name__ == '__main__':
    print(construire(Path(sys.argv[1] if len(sys.argv) > 1 else '.')))
