"""Moteur unique : une question, un code, une désignation ou un dossier → toutes les sources à la fois.

    python -m visite demande "3506.99.90.00"
    python -m visite demande "colle polyuréthane pour profilés"
    python -m visite demande "article 16 du code des douanes"
    python -m visite demande "واش هي شروط القبول المؤقت ؟"

Ce que fait le moteur, sans qu'on lui désigne un fichier :
1. prépare la base : intègre les PDF déposés dans knowledge-base/inbox/, reconstruit l'index s'il est périmé ;
2. lit la demande : codes SH, articles de loi, thèmes (valeur, origine, régimes, DAPS, TVA…), mots en arabe
   traduits en termes douaniers français (les sources sont en français) ;
3. consulte en une fois : tarif 2016 + mise à jour 2020 + SH 2022 + LF 2026 + DAPS (taux), notes de section
   et de chapitre, décisions de classement 2020-2025, code des douanes consolidé, loi 17-04, code des TCA,
   lois de finances, décrets, guides DGD (valeur, origine, régimes), contrôle aux frontières, veille ;
4. répond avec chaque élément cité (document, article, page de texte) et la liste des sources consultées.
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from . import tarif

KB = Path(__file__).resolve().parent.parent / "knowledge-base"
DB = KB / "kb.sqlite"
INBOX = KB / "inbox"

# ------------------------------------------------------------------ lecture de la demande
CODE_RE = re.compile(r"(?<![\d.,])(\d{4}\.\d{2}(?:\.\d{2}){0,2}|\d{2}\.\d{2}(?![\d.])|\d{4}(?:\d{2}){0,3})(?![\d.,%])")
ART_RE = re.compile(r"\b(?:art(?:icle)?s?\.?|المادة|مادة)\s*(\d{1,3})\s*(bis|ter|quater|quinquies|sexies|septies|octies)?"
                    r"(?:\s*(\d))?", re.I)
INSTRUMENTS = [  # mot-clé dans la demande → instrument visé par « article N »
    (r"tca|chiffre d.affaires|tva|القيمة المضافة", "Code des taxes sur le chiffre d'affaires"),
    (r"10-288|commissionnaire|وكيل|معشر", "Décret exécutif n° 10-288"),
    (r"18-165|décision anticipée|قرار مسبق", "Décret exécutif 18-165"),
    (r"loi de finances 2026|lf 2026|25-17|قانون المالية 2026", "Loi 25-17"),
    (r"18-13|lfc 2018", "Loi n° 18-13"),
    (r"17-04", "Loi 17-04"),
    (r".", "Code des douanes — loi n° 79-07"),  # défaut : code des douanes consolidé
]

# arabe (et darija courante) → termes français des sources
GLOSSAIRE = {
    "تعريفة": "tarif", "بند": "position tarifaire", "تصنيف": "classement", "فصل": "chapitre", "قسم": "section",
    "قيمة": "valeur en douane", "منشأ": "origine", "شهادة المنشأ": "certificat d'origine", "يورو 1": "EUR.1",
    "قبول مؤقت": "admission temporaire", "القبول المؤقت": "admission temporaire", "مستودع": "entrepôt",
    "عبور": "transit", "ترانزيت": "transit", "تحسين": "perfectionnement actif", "حقوق جمركية": "droits de douane",
    "حق جمركي": "droit de douane", "رسم": "droit taxe", "الضريبة على القيمة المضافة": "TVA", "تيفا": "TVA",
    "إعفاء": "exonération", "اعفاء": "exonération", "وكيل": "commissionnaire en douane", "معشر": "commissionnaire",
    "مصرح": "déclarant", "اعتماد": "agrément", "رخصة": "agrément autorisation", "مطابقة": "conformité",
    "رقابة": "contrôle", "معاينة": "visite", "فيزيت": "visite", "مخالفة": "infraction", "غرامة": "amende",
    "منازعة": "contentieux", "توطين": "domiciliation bancaire", "تضامن": "contribution de solidarité",
    "الحق الإضافي": "DAPS droit additionnel provisoire de sauvegarde", "دابس": "DAPS", "تهريب": "contrebande",
    "تصدير": "exportation", "استيراد": "importation", "نظام اقتصادي": "régime économique", "مهلة": "délai",
    "آجال": "délai", "حاوية": "conteneur", "بيان": "manifeste", "تصريح": "déclaration en détail",
    "فاتورة": "facture", "تأمين": "assurance", "نقل": "fret transport", "غراء": "colle adhésif",
    "لاصق": "adhésif", "قطع غيار": "parties pièces détachées", "سيارة": "véhicule automobile",
    "سيارات": "véhicules automobiles", "مستعمل": "usagé occasion", "أدوية": "médicaments", "دواء": "médicament",
    "مواد غذائية": "produits alimentaires", "حليب": "lait", "قمح": "blé", "حديد": "fer acier", "ألمنيوم": "aluminium",
    "بلاستيك": "matières plastiques", "دهن": "peinture", "طلاء": "peinture vernis", "مصلب": "durcisseur",
    "هاتف": "téléphone", "مكيف": "climatiseur", "ثلاجة": "réfrigérateur", "عجلات": "pneumatiques", "إطارات": "pneumatiques",
    "زيوت": "huiles lubrifiantes", "قرار تصنيف": "décision de classement", "سوابق": "décision de classement",
}
THEMES = {  # thème → mots déclencheurs (FR) et requête de recherche
    "valeur": (r"valeur|cif|fret|assurance|transaction|redevance|قيمة|تأمين", "valeur en douane transaction fret assurance"),
    "origine": (r"origine|eur\.?1|préférenti|zale|gzale|cumul|منشأ", "origine certificat preuve règles préférentiel"),
    "regimes": (r"admission temporaire|entrepôt|transit|perfectionnement|régime|قبول مؤقت|مستودع|عبور",
                "régime économique admission temporaire entrepôt apurement caution"),
    "daps": (r"daps|sauvegarde|دابس|الحق الإضافي", "droit additionnel provisoire de sauvegarde DAPS"),
    "tva": (r"\btva\b|taux réduit|القيمة المضافة|تيفا", "taxe sur la valeur ajoutée taux réduit exonération importation"),
    "commissionnaire": (r"commissionnaire|déclarant|agrément|وكيل|معشر|مصرح|اعتماد",
                        "commissionnaire en douane agrément déclarant obligations"),
    "conformite": (r"conformité|frontières|05-467|مطابقة", "contrôle conformité frontières produits importés"),
    "contentieux": (r"infraction|amende|contentieux|saisie|مخالفة|غرامة|منازعة", "infraction douanière amende contentieux"),
    "classement": (r"classement|rgi|position|تصنيف|بند", "classement règle générale interprétation note"),
    "delais": (r"délai|dépôt temporaire|magasin|aire de dédouanement|مهلة|آجال",
               "délai dépôt temporaire magasins aires de dédouanement"),
}
STOP = set("""le la les de des du un une et ou en à au aux pour par sur dans avec sans est sont quel quelle quels quelles
comment que qui quoi quand où ce cette ces son sa ses leur leurs il elle on nous vous je tu me te se y a ai as avons
avez ont être faire fait peut doit plus moins très tout tous toute toutes autre autres code article art loi n°
douane douanes douanier douanière quoi quel est-ce dois faut donne donner explique expliquer svp merci""".split())


NONPROD = set("""montant prix facture factures valeur délai date dossier déclaration déclarations taux droit droits taxe
taxes paiement banque domiciliation document documents question réponse total combien calcul calculer liquidation
importer importation exporter exportation client fournisseur conteneur visite inspecteur bureau""".split())


def traduire(q: str) -> str:
    """Ajoute à la demande les termes français correspondant aux mots arabes reconnus."""
    ajouts = [fr for ar, fr in sorted(GLOSSAIRE.items(), key=lambda x: -len(x[0])) if ar in q]
    return q + (" " + " ".join(dict.fromkeys(ajouts)) if ajouts else "")


def lire(q: str) -> dict:
    qf = traduire(q)
    codes = []
    for m in CODE_RE.finditer(q):
        c = tarif.chiffres(m.group(1))
        if len(c) in (4, 6, 8, 10) and not (len(c) == 4 and 1900 <= int(c) <= 2100 and "." not in m.group(1)) \
                and not (len(c) == 4 and re.search(r"\b(art(icle)?\.?|المادة)\s*$", q[:m.start()], re.I)):
            suite = q[m.end():m.end() + 6].lower()
            if 1 <= int(c[:2]) <= 97 and not re.match(r"\s*((da|dzd|eur|usd|kg|t|tonnes?|dinars?|ans?)\b|€|\$|%)", suite) \
                    and tarif.chercher(c)[0] != "absent":
                codes.append(c)
    arts = []
    for m in ART_RE.finditer(q):
        num = m.group(1) + (f" {m.group(2).lower()}" if m.group(2) else "")
        instr = next(lab for pat, lab in INSTRUMENTS if re.search(pat, q, re.I))
        arts.append((num, instr))
    themes = [t for t, (pat, _) in THEMES.items() if re.search(pat, qf, re.I)]
    mots = [w for w in re.findall(r"[A-Za-zÀ-ÿ'’.-]{3,}", qf) if w.lower() not in STOP]
    return {"demande": q, "traduite": qf, "codes": list(dict.fromkeys(codes)), "articles": arts,
            "themes": themes, "mots": mots}


# ------------------------------------------------------------------ préparation automatique de la base
def preparer(silencieux=False, ingestion=True) -> list[str]:
    """Intègre les PDF de knowledge-base/inbox/ et reconstruit l'index s'il manque ou s'il est périmé."""
    notes = []
    attente = sorted(INBOX.glob("*.pdf")) if INBOX.exists() else []
    if attente and ingestion:
        r = subprocess.run([sys.executable, str(KB / "tools" / "ingest.py"), *map(str, attente)],
                           capture_output=True, text=True)
        (INBOX / "integres").mkdir(exist_ok=True)
        for f in attente:
            f.rename(INBOX / "integres" / f.name)
        notes.append(f"{len(attente)} document(s) de inbox/ intégré(s)")
        if not silencieux:
            print(r.stdout[-3000:])
    elif attente:
        notes.append(f"{len(attente)} document(s) en attente dans knowledge-base/inbox/ (python -m visite demande pour les intégrer)")
    data = list((KB / "data").rglob("*.json"))
    if not DB.exists() or (data and max(f.stat().st_mtime for f in data) > DB.stat().st_mtime + 1):
        if ingestion:
            subprocess.run([sys.executable, str(KB / "tools" / "build_kb.py")], capture_output=True, text=True)
            notes.append("index reconstruit")
    _db.cache_clear()
    tarif._kb.cache_clear()
    return notes


@lru_cache(maxsize=1)
def _db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def _fts(mots: list[str]) -> str:
    termes = [re.sub(r"[^\wÀ-ÿ]", "", w) for w in mots]
    return " OR ".join(f'"{t}"*' for t in dict.fromkeys(termes) if len(t) >= 3)


# ------------------------------------------------------------------ consultation
def passages(requete_mots: list[str], kinds=("article", "texte", "decision"), limite=8) -> list[dict]:
    q = _fts(requete_mots)
    if not q or not DB.exists():
        return []
    rows = _db().execute(
        f"SELECT kind, ref, title, snippet(search, 3, '«', '»', ' … ', 30) AS extrait, bm25(search, 0, 2, 4, 1) AS score "
        f"FROM search WHERE search MATCH ? AND kind IN ({','.join('?' * len(kinds))}) ORDER BY score LIMIT ?",
        (q, *kinds, limite * 3)).fetchall()
    out, vus = [], set()
    for r in rows:
        source = r["title"] if r["kind"] == "texte" else r["ref"]
        cle = (r["kind"], source.split(" #")[0], r["extrait"][:60])
        if cle in vus:
            continue
        vus.add(cle)
        out.append({"type": r["kind"], "source": source, "reference": r["ref"], "extrait": re.sub(r"\s+", " ", r["extrait"])})
        if len(out) >= limite:
            break
    return out


def article(num: str, instrument: str) -> list[dict]:
    if not DB.exists():
        return []
    rows = _db().execute("SELECT instrument, article, text FROM articles WHERE lower(article) = lower(?)", (num,)).fetchall()
    rows = sorted(rows, key=lambda r: (instrument.lower()[:20] not in r["instrument"].lower(), len(r["text"]) < 40))
    return [{"instrument": r["instrument"], "article": r["article"], "texte": r["text"]} for r in rows[:3]]


def _sans_accent(w: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", w.lower()) if unicodedata.category(c) != "Mn")


def _forme_ok(base: str, texte: str) -> bool:
    """Le mot cherché figure-t-il vraiment dans le texte ? (« colle » ≠ « collés », « boitier » = « boîtier »)"""
    b = _sans_accent(base)
    for w in re.findall(r"[\wÀ-ÿ]+", texte):
        if _sans_accent(w) in (b, b + "s", b + "x"):
            if not (w.lower().endswith(("é", "és", "ée", "ées")) and not base.endswith("é")):
                return True
    return False


def candidats(mots: list[str], n=3) -> list[dict]:
    """Positions candidates pour une désignation.

    Chaque mot de la désignation est cherché seul dans le tarif (2016, 2020, SH 2022) et dans les décisions de
    classement ; une position gagne le poids (rareté) de chaque mot qu'elle couvre, le premier mot (le nom de la
    marchandise) compte double, et une décision de classement vaut plus qu'un libellé de tarif.
    """
    import math
    if not DB.exists():
        return []
    termes = [re.sub(r"[^\wÀ-ÿ]", "", w).lower() for w in mots]
    termes = [t for t in dict.fromkeys(termes) if len(t) >= 3 and t not in STOP and t not in NONPROD][:8]
    couverture, info, nb, lignes, tete = {}, {}, {}, {}, set()
    for i, t in enumerate(termes):
        pos_t = {}
        base = t[:-1] if t.endswith(("s", "x")) and len(t) > 4 else t
        formes = {base, base + "s", base + "x"} | ({base[:-2] + "*"} if len(base) >= 8 else set())
        match = " OR ".join(f'"{f[:-1]}"*' if f.endswith("*") else f'"{f}"' for f in formes)
        for r in _db().execute("SELECT kind, ref, title, substr(body, 1, 600) AS body FROM search WHERE search MATCH ? "
                               "AND kind IN ('tarif','decision') LIMIT 400", (match,)):
            if len(base) < 8 and not _forme_ok(base, f"{r['title']} {r['body']}"):
                continue
            code = r["ref"] if r["kind"] == "tarif" else (re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", r["title"]) or [""])[0]
            if not code:
                continue
            p = tarif.chiffres(code)[:4]
            pos_t[p] = pos_t.get(p, 0) + (1.6 if r["kind"] == "decision" else 1.0)
            ligne = lignes.setdefault((r["kind"], r["ref"]), {"p": p, "t": set()})
            ligne["t"].add(i)
            e = info.setdefault(p, {"codes": [], "decisions": []})
            if r["kind"] == "decision":
                e["decisions"].append(r["ref"])
            elif code not in e["codes"]:
                e["codes"].append(code)
        if not pos_t:
            continue
        idf = math.log(1 + 1200 / len(pos_t))
        for p, w in pos_t.items():
            couverture[p] = couverture.get(p, 0) + idf * (1 + math.log(w)) * (3 if i == 0 else 1)
            nb[p] = nb.get(p, 0) + 1
            if i == 0:
                tete.add(p)
    # une même ligne (libellé ou décision) qui réunit plusieurs mots de la désignation est un indice fort
    for l in lignes.values():
        if len(l["t"]) > 1:
            couverture[l["p"]] *= 1 + 0.6 * (len(l["t"]) - 1)
    seuil = min(2, len(termes))
    retenues = [(p, sc) for p, sc in couverture.items() if nb[p] >= seuil or p in tete] or list(couverture.items())
    top = sorted(retenues, key=lambda x: -x[1])[:n]
    return [{"position": f"{p[:2]}.{p[2:]}", "score": round(sc, 2), **info[p]} for p, sc in top]


def veille(mots: list[str]) -> list[dict]:
    f = KB / "data" / "veille_secondaire.json"
    if not f.exists():
        return []
    ms = {m.lower() for m in mots if len(m) > 4 and m.lower() not in STOP}
    faits = json.loads(f.read_text(encoding="utf-8"))["faits"]
    sc = [(len(ms & set(re.findall(r"\w{5,}", (x["sujet"] + " " + x["fait"]).lower()))), x) for x in faits]
    return [x for n, x in sorted(sc, key=lambda t: -t[0]) if n >= 2][:3]


def analyser(q: str, preparation=True) -> dict:
    notes = preparer(silencieux=True, ingestion=preparation)
    L = lire(q)
    res = {"lecture": L, "notes": notes, "positions": [], "candidats": [], "articles": [], "passages": [],
           "veille": [], "sources": set()}
    for c in L["codes"][:4]:
        f = tarif.fiche(c)
        res["positions"].append(f)
        res["sources"].update(["tarif DGD 2016 (notes, sections, RGI)", "mise à jour du tarif 2020",
                               "table de corrélation SH 2022", "LF 2026", "liste DAPS 2019",
                               "décisions de classement 2020-2025"])
    if not L["codes"] and L["mots"] and ("classement" in L["themes"] or not L["themes"] and not L["articles"]):
        res["candidats"] = candidats(L["mots"])
        for e in res["candidats"]:
            e["fiche"] = tarif.fiche(e["position"].replace(".", ""))
        res["sources"].update(["tarif DGD 2016", "décisions de classement 2020-2025"])
    for num, instr in L["articles"][:3]:
        res["articles"] += article(num, instr)
    requete = L["mots"] + [w for t in L["themes"] for w in THEMES[t][1].split()]
    if requete:
        res["passages"] = passages(requete, limite=6 if res["positions"] or res["candidats"] else 10)
    res["veille"] = veille(requete)
    for p in res["passages"]:
        res["sources"].add(p["source"].split(" art. ")[0].split(" #")[0])
    for a in res["articles"]:
        res["sources"].add(a["instrument"])
    res["sources"] = sorted(res["sources"])
    return res


# ------------------------------------------------------------------ rendu
def _fiche_courte(f: dict) -> list[str]:
    s, ch, p, l = f["section"], f["chapitre"], f["position"], f["ligne"]
    L = [f"■ {f['code']} [{f['statut']}]" + (f" — {f['remarque']}" if f["remarque"] else "")]
    if s:
        L.append(f"  Section {s['numero']} — {s['titre'][:110]}")
    if ch:
        L.append(f"  Chapitre {ch['numero']} — {ch['titre'][:110]}")
    L.append(f"  Position {p['code']} — {p['libelle'][:220]}")
    if l:
        L.append(f"  Ligne {l['code']} ({l['unite']}) — {' > '.join(l['hierarchie'] + [l['libelle']])[:200]}")
    if f["droit_douane"] is not None:
        L.append(f"  DD {f['droit_douane']:g} % ({f['droit_douane_source']}) · TVA {f['tva']:g} % ({f['tva_source']})"
                 + (f" · autres : {f['autres_taxes']}" if f["autres_taxes"] else "") + (f" · FAP : {f['fap']}" if f["fap"] else ""))
    if f.get("daps"):
        d = f["daps"]
        L.append(f"  DAPS {d['taux']} % (arrêté 26/01/2019, n° {d['ordre']}{', EX' if d['ex'] else ''}) — liste initiale, à vérifier")
    if f.get("daps_sous_code"):
        dl = f["daps_sous_code"]
        taux = sorted({x["taux"] for x in dl})
        L.append(f"  DAPS : {len(dl)} ligne(s) de {f['code']} sur la liste du 26/01/2019 (taux {', '.join(map(str, taux))} %) : "
                 + ", ".join(f"{x['code']} {x['taux']} %" for x in dl[:6]) + (" …" if len(dl) > 6 else ""))
    for x in (s or {}).get("notes_citant_position", [])[:2] + (ch or {}).get("notes_citant_position", [])[:2]:
        L.append(f"  Note : {x[:300]}")
    for m in f["mesures_lf2026"][:2]:
        L.append(f"  LF 2026 art. {m['article']} : {m['mesure']}" + (f" — condition : {m['condition']}" if m.get("condition") else ""))
    for r in f["decisions"][:3]:
        L.append(f"  Décision : {r['reference']} → {r['code']} — {r['designation'][:80]}")
    return L


def texte(res: dict, max_car: int | None = None) -> str:
    L = []
    lec = res["lecture"]
    if res["notes"]:
        L.append("Base : " + " ; ".join(res["notes"]))
    if res["positions"]:
        L.append("POSITIONS TARIFAIRES")
        for f in res["positions"]:
            L += _fiche_courte(f)
    if res["candidats"]:
        L.append("POSITIONS CANDIDATES (d'après le tarif et les décisions de classement — à confirmer par la désignation exacte)")
        for e in res["candidats"]:
            L += _fiche_courte(e["fiche"])
            if e["decisions"]:
                L.append(f"  Décisions voisines : {', '.join(dict.fromkeys(e['decisions']))[:200]}")
    if res["articles"]:
        L.append("ARTICLES")
        for a in res["articles"]:
            L.append(f"■ {a['instrument']}, art. {a['article']} : {a['texte'][:900]}")
    if res["passages"]:
        L.append("PASSAGES DES SOURCES" + (f" (thèmes : {', '.join(lec['themes'])})" if lec["themes"] else ""))
        for p in res["passages"]:
            L.append(f"■ [{p['type']}] {p['reference'][:120]} : {p['extrait'][:380]}")
    if res["veille"]:
        L.append("VEILLE (sources secondaires, à confirmer au texte officiel)")
        for v in res["veille"]:
            L.append(f"■ {v['sujet']} : {v['fait'][:300]} — {v['source']}")
    L.append("Sources consultées : " + ("; ".join(res["sources"]) or "aucune correspondance"))
    out = "\n".join(L)
    return out if not max_car or len(out) <= max_car else out[:max_car] + "\n… (tronqué)"


def utile(q: str) -> bool:
    """La demande touche-t-elle la douane ? (pour le déclenchement automatique)"""
    L = lire(q)
    return bool(L["codes"] or L["articles"] or L["themes"] or
                re.search(r"douan|tarif|import|export|dédouan|جمارك|جمرك|ديوان|تعريف|استيراد|تصدير|سلعة|بضاعة", q, re.I))


# ------------------------------------------------------------------ note de risques d'un dossier (pour le déclarant seul)
RISQUES = {  # préfixe du contrôle → (mots de recherche dans les sources, ce qu'il faut préparer)
    "FAM": ([],
            "Comparer la désignation, la FDS et la composition avec le libellé des deux sous-positions ; la plus "
            "spécifique l'emporte (RGI 3 a), comparaison au même niveau (RGI 6). Préparer la FDS et l'argumentaire."),
    "TAR": ([],
            "Confirmer la ligne dans le tarif en vigueur ; garder la table de corrélation SH 2022 sous la main."),
    "DD": (["taux", "droit", "douane"], "Rectifier la quotité ou justifier le taux (avantage, accord, LF)."),
    "TVA": (["taux", "réduit", "valeur", "ajoutée"], "Rectifier la TVA ou citer la base du taux réduit / de l'exonération."),
    "DAPS": (["droit", "additionnel", "provisoire", "sauvegarde"],
             "Vérifier la liste DAPS en vigueur pour cette ligne et une éventuelle exemption (origine préférentielle, "
             "intrants) ; à défaut, liquider le DAPS."),
    "VAL": (["valeur", "assurance", "fret", "transaction"],
            "Préparer la police ou l'attestation d'assurance, ou une déclaration de non-assurance : la valeur ne retient que "
            "des frais réels, sur données objectives et quantifiables (art. 16 octies § 2) ; pas de forfait (guide de la valeur DGD)."),
    "DAT": ([], "Vérifier que la marchandise n'est pas inscrite en dépôt de douane ni proposée à la vente ; calculer "
                "surestaries et frais de magasinage ; préparer la justification du retard."),
    "ISO": (["conteneur"], "Revérifier le numéro de conteneur sur le B/L et la porte du conteneur."),
    "ORI": (["origine", "certificat", "preuve"],
            "Obtenir le certificat d'origine du pays d'exportation ; indispensable pour toute préférence tarifaire, "
            "utile si l'inspecteur demande la preuve de l'origine déclarée."),
    "EXO": (["exonération", "exonérés", "droits", "taxes"], "Joindre la pièce qui fonde l'exonération et citer le texte."),
}
ARTICLES_RISQUE = {  # textes à citer en entier pour un contrôle : (instrument, article)
    "DAT": [("Code des douanes — loi n° 79-07", "71"), ("Loi 25-17", "123"), ("Code des douanes — loi n° 79-07", "209"),
            ("Code des douanes — loi n° 79-07", "210")],
}


def note_risques(d: dict, ctrls: list[dict]) -> str:
    preparer(silencieux=True)
    L = [f"# Note de risques — dossier {d['meta']['id']}", "",
         "Document interne au déclarant, **à ne pas joindre à la fiche de l'inspecteur**. "
         "Établi automatiquement par le moteur à partir des contrôles et des sources de knowledge-base/.", ""]
    alertes = [c for c in ctrls if c["statut"] != "ok"]
    L += [f"**{sum(1 for c in ctrls if c['statut'] == 'ok')} contrôles conformes · "
          f"{sum(1 for c in alertes if c['statut'] == 'alerte')} alertes · "
          f"{sum(1 for c in alertes if c['statut'] == 'erreur')} erreurs**", ""]
    for c in sorted(alertes, key=lambda c: c["statut"] != "erreur"):
        pre = c["id"].split("-")[0]
        mots, prep = RISQUES.get(pre, ([], "Revoir la transcription et la déclaration."))
        L += [f"## {'✕' if c['statut'] == 'erreur' else '!'} {c['id']} — {c['titre']}", "", c["detail"], "",
              f"**À préparer :** {prep}", ""]
        if pre == "FAM":
            num = int(c["id"].split("-")[1])
            a = next(x for x in d["articles"] if x["num"] == num)
            for lab, code in (("D10", a["code_sh"]), ("pays d'origine", a.get("code_origine", ""))):
                if code:
                    c6 = tarif.chiffres(code)[:6]
                    L.append(f"- {lab} `{c6[:4]}.{c6[4:]}` — {tarif.libelle_sh6(c6)} "
                             f"(position {c6[:2]}.{c6[2:4]} : {tarif.fiche(c6[:4])['position']['libelle'][:160]})")
            rgi = json.loads((KB / "data" / "tarif_2016_sections.json").read_text(encoding="utf-8")).get("rgi", "")
            for regle in ("3. ", "6. "):
                i = rgi.find(regle)
                if i >= 0:
                    L.append(f"- RGI {regle.strip()} : {re.sub(chr(10), ' ', rgi[i + 3:i + 420])}…")
            L.append("")
        if pre == "TAR":
            num = int(c["id"].split("-")[1])
            a = next(x for x in d["articles"] if x["num"] == num)
            for x in tarif._kb()["vers2022"].get(tarif.chiffres(a["code_sh"]), []):
                n2 = tarif._kb()["sh2022"].get(tarif.chiffres(x["nouveau"]), {})
                L.append(f"- SH 2022 : {'ex ' if x['partiel'] else ''}{tarif.fmt(a['code_sh'])} → {x['nouveau']} "
                         f"{n2.get('libelle', '')} (DD {n2.get('dd', '?')} %) — vérifier que la marchandise n'en relève pas")
            L.append("")
        for instr, num in ARTICLES_RISQUE.get(pre, []):
            a_ = next(iter(article(num, instr)), None)
            if a_:
                L.append(f"- **{a_['instrument'][:60]}, art. {a_['article']}** : {re.sub(r'[(][^)]*(modifié|institué)[^)]*[)]', '', a_['texte'])[:420].strip()}…")
        for p in passages(mots, limite=3) if mots else []:
            L.append(f"- *{p['reference'][:110]}* : {p['extrait'][:300]}")
        L.append("")
    for r in d.get("risques_declarant", []):
        L += [f"## ! {r['titre']}", "", r["detail"], ""]
        if r.get("preparer"):
            L += [f"**À préparer :** {r['preparer']}", ""]
    L += ["## Classement de chaque article", ""]
    for a in d["articles"]:
        L += ["```", *_fiche_courte(tarif.fiche(a["code_sh"])), "```", ""]
    return "\n".join(L)
