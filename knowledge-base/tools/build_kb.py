"""Build the structured knowledge base from the extracted texts.

Usage (from the knowledge-base folder):
    python tools/build_kb.py

Inputs : text/*.txt  (made by tools/extract_text.sh from sources/*.pdf)
Outputs: data/tarif_2016.json, data/tarif_2016.csv, data/tarif_2016_notes.json,
         data/decisions_classement_<année>.json, data/loi_17-04_code_douanes.json,
         data/loi_finances_2026.json, data/mesures_tarifaires_lf2026.json,
         data/decret_18-165.json, data/references.json, kb.sqlite (full-text search)
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / "text"
DATA = ROOT / "data"

TARIF_TXT = TEXT / "tarif-douanier-2016-10-chiffres-pour-telechargement.txt"
LF2026_TXT = TEXT / "loi_de_finances_2026.txt"
LOI_TXT = TEXT / "loi_no_17-04_du_16_fevrier_2017_code_des_douanes.txt"
DECRET_TXT = TEXT / "decret_executif_no_18-165_du_14_juin2018.txt"
EBTI_TXT = TEXT / "ebti_general_information_en.txt"
SMART_TXT = TEXT / "smart-customs_public_report_fr_1.txt"


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def digits(code: str) -> str:
    return re.sub(r"\D", "", code)


# --------------------------------------------------------------------------- tariff
CODE_RE = re.compile(r"^\s{0,8}(\d{4}\.\d{2}\.\d{2}\.\d{2})\s+(\S+(?:\(\*\))?)\s+(.*?)\s*$")
HEADING_RE = re.compile(r"^\s{0,8}(\d{2}\.\d{2})\s{3,}(\S.*?)\s*$")
RATE_TAIL_RE = re.compile(r"^(.*?)\s{2,}(ex|\d{1,3})\s*$")
RATE_ONLY_RE = re.compile(r"^\s{40,}(ex|\d{1,3})\s*$")
CHAPTER_RE = re.compile(r"^\s{20,}Chapitre\s+(\d{1,2})\s*$")
TABLE_HEAD_RE = re.compile(r"Désignation des Produits|U\.Q\.N|^\s*Position\s*$|^\s*&\s*$|^\s*Sous\s*$")
NOISE_RE = re.compile(r"DOUANES ALGERIENNES|^\s*-\s*\d+\s*-\s*$|^\s*CHAPITRE\s+\d+|^\s*SECTION\s+[IVXL]+")


def dash_level(text: str) -> tuple[int, str]:
    m = re.match(r"^((?:-\s*)+)", text)
    if not m:
        return 0, text.strip()
    return m.group(1).count("-"), text[m.end():].strip()


def parse_tariff() -> tuple[list[dict], dict]:
    lines = TARIF_TXT.read_text(encoding="utf-8").splitlines()
    items: list[dict] = []
    notes: dict[str, list[str]] = {}
    chapter = None
    heading = None
    headings: dict[str, str] = {}
    stack: dict[int, str] = {}  # dash level -> header text
    last = None  # ("item", dict) | ("header", level) | ("heading", code)
    in_notes = False

    for raw in lines:
        if not raw.strip():
            continue
        m = CHAPTER_RE.match(raw)
        if m:
            chapter = int(m.group(1))
            notes.setdefault(str(chapter), [])
            in_notes = True
            last = None
            continue
        if TABLE_HEAD_RE.search(raw):
            in_notes = False
            last = None
            continue
        if NOISE_RE.search(raw):
            continue

        m = CODE_RE.match(raw)
        if m:
            in_notes = False
            code, unit, rest = m.groups()
            rate = None
            t = RATE_TAIL_RE.match(rest)
            if t:
                rest, rate = t.group(1), t.group(2)
            level, label = dash_level(rest)
            ctx = [stack[k] for k in sorted(stack) if k < level]
            item = {
                "code": code,
                "hs6": code[:7],
                "chapter": int(code[:2]),
                "heading": code[:2] + "." + code[2:4],
                "unit": unit,
                "label": label,
                "context": ctx,
                "rate_raw": rate,
            }
            items.append(item)
            last = ("item", item)
            continue

        m = HEADING_RE.match(raw)
        if m and not in_notes:
            heading = m.group(1)
            headings[heading] = clean(m.group(2))
            stack = {}
            last = ("heading", heading)
            continue

        r = RATE_ONLY_RE.match(raw)
        if r and last and last[0] == "item" and last[1]["rate_raw"] is None:
            last[1]["rate_raw"] = r.group(1)
            continue

        if in_notes and chapter is not None:
            notes[str(chapter)].append(raw.strip())
            continue

        indent = len(raw) - len(raw.lstrip())
        text = raw.strip()
        if indent < 18:
            continue
        if text.startswith("-"):
            level, label = dash_level(text)
            for k in [k for k in stack if k >= level]:
                del stack[k]
            stack[level] = label
            last = ("header", level)
        elif last:
            # continuation of the previous line
            t = RATE_TAIL_RE.match(text)
            if t and last[0] == "item" and last[1]["rate_raw"] is None:
                text, last[1]["rate_raw"] = t.group(1), t.group(2)
            if last[0] == "item":
                last[1]["label"] = clean(last[1]["label"] + " " + text)
            elif last[0] == "header":
                stack[last[1]] = clean(stack[last[1]] + " " + text)
            elif last[0] == "heading":
                headings[last[1]] = clean(headings[last[1]] + " " + text)

    for it in items:
        it["heading_label"] = headings.get(it["heading"], "")
        raw_rate = it.pop("rate_raw")
        it["dd_rate"] = 0.0 if raw_rate == "ex" else (int(raw_rate) / 100 if raw_rate else None)
        it["dd_exempt"] = raw_rate == "ex"
        it["label"] = clean(it["label"].rstrip(":"))
        it["context"] = [clean(c.rstrip(":")) for c in it["context"]]
        parts = [it["heading_label"]] + it["context"] + [it["label"]]
        it["full_label"] = " > ".join(p for p in parts if p)
    notes = {k: "\n".join(v) for k, v in notes.items() if v}
    return items, {"headings": headings, "chapter_notes": notes}


# ---------------------------------------------------------- classification decisions
PAGE_NOISE = re.compile(
    r"Direction Générale des Douanes|Sous -Direction des Bases|Recueil de Décisions de Classement|"
    r"^\s*\d{1,3}\s*$|^\s*(JANVIER|Janvier)?\s*20\d\d\s*$"
)
CODE10 = r"\d{4}\.\d{2}\.\d{2}\.\d{2}"
CODE_ANY = r"\d{4}\.\d{2}\.\d{2}\.\d{2}|\b\d{2}\.\d{2}\b"  # 10-digit code or 4-digit heading


def strip_pages(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not PAGE_NOISE.search(l))


def section(block: str, start: str, ends: list[str]) -> str:
    m = re.search(re.escape(start) + r"\s*:?(.*?)(?=" + "|".join(re.escape(e) for e in ends) + r"|\Z)", block, re.S)
    return clean(m.group(1)) if m else ""


def regex_section(block: str, start: str, end: str) -> str:
    m = re.search("(?:" + start + r")(.*?)(?=" + end + ")", block, re.S)
    return clean(m.group(1)) if m else ""


def check_consistency(rulings: list[dict]) -> None:
    """Flag a likely typo: the retained code never appears in the reasoning, while a code that
    differs from it by one or two digits does (e.g. 4221.91.99.00 in the header, 4421.91.99.00 in the text)."""
    for r in rulings:
        text = r.get("justification") or ""
        cited = set(re.findall(CODE10, text))
        for code in r.get("hs_codes") or []:
            if code in cited:
                continue
            near = [c for c in cited if sum(a != b for a, b in zip(c, code)) <= 2]
            if near:
                r.setdefault("warnings", []).append(
                    f"Code retenu {code} absent de la motivation, qui cite {', '.join(sorted(near))}. "
                    "Probable erreur de saisie dans le recueil : vérifier la décision originale.")


def dmy(s: str) -> str | None:
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", s or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def parse_recueil(path: Path, source: str) -> list[dict]:
    """One yearly collection: RTC decisions, then other decisions (modèle 110, D40)."""
    text = strip_pages(path.read_text(encoding="utf-8"))
    out = []
    for b in re.split(r"(?=REFERENCE RTC\s*:)", text):
        if not b.startswith("REFERENCE RTC"):
            continue
        b = b.split("Référence de la décision")[0]
        ref = re.search(r"(?:N°)?\s*(\d+/DGD)\s+DU\s+([\d.]+)", b)
        codes = re.findall(CODE_ANY, section(b, "SOUS-POSITION RETENUE", ["DESCRIPTION DU PRODUIT"]))
        rgi = re.search(r"(Application d[ue]s? .*?(?:du SH|SH)\.?)", b.replace("\n", " "))
        out.append({
            "type": "RTC",
            "reference": f"RTC {ref.group(1)} du {ref.group(2)}" if ref else None,
            "number": int(ref.group(1).split("/")[0]) if ref else None,
            "decision_date": dmy(ref.group(2)) if ref else None,
            "valid_from": dmy(section(b, "DEBUT DE VALIDITE", ["DATE DE FIN"])),  # "DATE" missing once in 2020
            "valid_to": dmy(section(b, "DATE DE FIN DE VALIDITE", ["DESIGNATION"])),
            "designation": section(b, "DESIGNATION DU PRODUIT", ["SOUS-POSITION RETENUE"]),
            "hs_code": codes[0] if codes else None,
            "hs_codes": codes,
            "description": section(b, "DESCRIPTION DU PRODUIT", ["JUSTIFICATIF DU CLASSEMENT"]),
            "justification": section(b, "JUSTIFICATIF DU CLASSEMENT", ["ILLUSTRATION", "REFERENCE RTC"]),
            "rules_applied": clean(rgi.group(1)) if rgi else None,
            "source": source,
        })

    for b in re.split(r"(?=Référence de la décision\s*:)", text)[1:]:
        b = b.split("REFERENCE RTC")[0]
        head = b.split("\n", 1)[0]
        kind = ("Modèle 110" if "110" in head else "Modèle D40" if re.search(r"D\s*40", head)
                else "Note DGD" if "Note" in head else "Décision DGD")
        ref = re.search(r"n°\s*(\S+)\s+du\s+([\d.]+)", head)
        retained = list(dict.fromkeys(re.findall(CODE_ANY, regex_section(
            b, r"tarifaire\(s\) retenue\(s\)\s*:", r"\d\.\s*Description|Justificatif|\n\s*\n|\Z"))))
        envis = re.search(r"envisagée ?\(s\)\s*:\s*(.*?)\n\s*\n", b, re.S)
        body = b.split("DECISION DE L’ADMINISTRATION CENTRALE", 1)[-1]
        out.append({
            "type": kind,
            "reference": f"{kind} n° {ref.group(1)} du {ref.group(2)}" if ref else clean(head),
            "decision_date": dmy(ref.group(2)) if ref else None,
            "requesting_service": section(b, "Service demandeur", ["Description du produit"]),
            "designation": section(b, "Description du produit", ["Position(s)", "Position (s)"]),
            "codes_considered": re.findall(CODE10, envis.group(1)) if envis else [],
            "hs_code": retained[0] if retained else None,
            "hs_codes": retained,
            "description": regex_section(body, r"\d\.\s*Description d(?:u|es) produits?\s*:",
                                         r"\d\.\s*Sous positions? envisagées?|\d\.\s*Classement"),
            "justification": regex_section(body, r"\d\.\s*Classement tarifaire\s*:|Justificatif\s*:", r"\Z"),
            "source": source,
        })
    check_consistency(out)
    return out


# ------------------------------------------------------------------ legal texts
JO_NOISE = re.compile(r"JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE|^\s*\d{1,2}\s*$|"
                      r"^\s*\d{1,2} \S+ \d{4}\s*$|^\s*\d{1,2} (Joumada|Chaoual|Ramadhan|Safar|Rajab|Chaâbane)\S* .*\d{4}\s*$")
ART_RE = re.compile(
    r"^(«\s*)?(Art(?:icle)?\.?\s*(\d+)\s*(er)?\s*((?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|"
    r"decies|undecies|duodecies)(?:\s+\d+)?)?)\s*\.?\s*[—–-]", re.M)


def parse_articles(path: Path, instrument: str) -> list[dict]:
    text = "\n".join(l for l in path.read_text(encoding="utf-8").splitlines() if not JO_NOISE.search(l))
    matches = list(ART_RE.finditer(text))
    arts = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = clean(text[m.end():end])
        num = m.group(3) + (" " + m.group(5).strip() if m.group(5) else "")
        arts.append({
            "instrument": instrument,
            "scope": "code_des_douanes" if m.group(1) else "texte",
            "article": num,
            "text": body,
        })
    return arts


# ------------------------------------------------------------ loi de finances 2026
LF_DOMAINS = [
    ("code des douanes", "douanes"), ("code des impôts directs", "impôts directs"),
    ("code de l’enregistrement", "enregistrement"), ("code de l'enregistrement", "enregistrement"),
    ("code du timbre", "timbre"), ("code des taxes sur le chiffre d’affaires", "TVA / taxes sur le CA"),
    ("code des impôts indirects", "impôts indirects"), ("code des procédures fiscales", "procédures fiscales"),
]
CUSTOMS_HINTS = re.compile(r"droits? de douane|sous-position tarifaire|position tarifaire|dédouan|"
                           r"importation|code des douanes|droit additionnel provisoire|contribution de solidarité")
LF_TOP_ART = re.compile(r"^(Article 1er|Art\.\s*(\d+))\s*\.?\s*[—–-]", re.M)

# Tariff measures of the 2026 finance law, summarised from the text (codes are extracted
# from the article itself). apply=True: unconditional rate on exact codes, used by the engine.
LF2026_MEASURES = {
    121: {"measure": "Exemption DD, TVA, taxe de domiciliation bancaire, contribution de solidarité et précompte",
          "scope": "Ovins vivants pour l'abattage (Aïd El Adha) du 15.04.2025 au 30.06.2026 ; bovins vivants pour "
                   "l'abattage du 15.11.2025 au 30.06.2026", "valid_to": "2026-06-30", "apply": False},
    131: {"measure": "Droit de douane 15 %", "scope": "Chauffe-eau solaires à usage domestique",
          "dd_rate": 0.15, "apply": True},
    132: {"measure": "Exonération des droits de douane", "scope": "Électrolyseurs pour la production d'hydrogène (ex-code)",
          "dd_rate": 0.0, "apply": False},
    133: {"measure": "Droit de douane réduit 5 %", "scope": "Intrants pour la fabrication de panneaux solaires "
          "photovoltaïques (ex-codes) et cellules photovoltaïques", "dd_rate": 0.05,
          "condition": "Attestation des services du ministère chargé de l'énergie, exigible au dédouanement",
          "apply": False},
    135: {"measure": "Exonération de tous droits et taxes (y compris DAPS, contribution de solidarité, précompte)",
          "scope": "Véhicules de transport de 10 personnes ou plus (87.02), dans la limite de 10 000 unités, "
                   "finis ou en kit ; à compter du 01.10.2025",
          "condition": "Autorisation du ministère chargé de l'industrie, avec fiche des quantités", "apply": False},
    136: {"measure": "Nouvelles exceptions à la contribution de solidarité (3 %)",
          "scope": "Importations du wakf public exonérées ; importations des dispositifs de soutien à l'investissement",
          "apply": False},
    137: {"measure": "Nouvelles exceptions au droit additionnel provisoire de sauvegarde (DAPS)",
          "scope": "Importations directes de l'agence algérienne de coopération internationale ; dons et biens "
                   "wakfs publics exonérés", "apply": False},
    138: {"measure": "Exemption DD et TVA au taux réduit", "scope": "Matières premières pour aliments d'aquaculture (ex-codes)",
          "dd_rate": 0.0, "condition": "Attestation des services du ministère chargé de la pêche", "apply": False},
    139: {"measure": "Droit de douane réduit 5 % jusqu'au 31.12.2026",
          "scope": "Bovins et ovins vivants pour l'abattage ; viandes bovines et ovines fraîches réfrigérées sous vide",
          "dd_rate": 0.05, "valid_to": "2026-12-31", "apply": True},
    140: {"measure": "Droit de douane réduit 5 % et exonération possible de TVA jusqu'au 31.12.2026",
          "scope": "Viandes blanches congelées", "dd_rate": 0.05, "valid_to": "2026-12-31", "apply": True},
}


def parse_finance_law() -> tuple[list[dict], list[dict]]:
    text = "\n".join(l for l in LF2026_TXT.read_text(encoding="utf-8").splitlines() if not JO_NOISE.search(l))
    found = list(LF_TOP_ART.finditer(text))
    arts, last = [], 0
    for i, m in enumerate(found):
        num = 1 if m.group(1).startswith("Article") else int(m.group(2))
        if num < last or num > last + 3:  # an article quoted inside an amended code, not a law article
            continue
        last = num
        end = next((f.start() for f in found[i + 1:]
                    if (1 if f.group(1).startswith("Article") else int(f.group(2))) in range(num + 1, num + 4)), len(text))
        body = clean(text[m.end():end])
        head = body[:250].lower()
        domain = next((d for k, d in LF_DOMAINS if k.lower() in head), "autres dispositions")
        if domain == "autres dispositions" and "79-07" in head:
            domain = "douanes"
        arts.append({
            "instrument": "Loi 25-17 du 14.12.2025 portant loi de finances pour 2026",
            "article": str(num), "domain": domain,
            "customs_relevant": domain == "douanes" or bool(CUSTOMS_HINTS.search(body)),
            "codes": sorted(set(re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", body))),
            "text": body,
        })
    measures = []
    for a in arts:
        meta = LF2026_MEASURES.get(int(a["article"]))
        if not meta:
            continue
        codes = re.findall(r"(EX\s*|Ex\s*)?(\d{4}\.\d{2}\.\d{2}\.\d{2})", a["text"])
        measures.append({"article": a["article"], **meta,
                         "codes": [{"code": c, "ex": bool(ex)} for ex, c in codes],
                         "source": "Loi de finances 2026, art. " + a["article"]})
    return arts, measures


# ---------------------------------------------------------------- full text
def paragraphs(path: Path, source: str, size: int = 1200) -> list[dict]:
    text = re.sub(r"[ \t]+", " ", path.read_text(encoding="utf-8"))
    chunks, buf = [], ""
    for para in re.split(r"\n\s*\n", text):
        para = clean(para)
        if not para:
            continue
        if len(buf) + len(para) > size and buf:
            chunks.append(buf)
            buf = ""
        buf = (buf + "\n" + para).strip()
    if buf:
        chunks.append(buf)
    return [{"source": source, "chunk": i, "text": c} for i, c in enumerate(chunks)]


def build_sqlite(tarif, rulings, loi, decret, extra_chunks):
    db_path = ROOT / "kb.sqlite"
    db_path.unlink(missing_ok=True)
    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE tarif (code TEXT PRIMARY KEY, hs6 TEXT, chapter INT, heading TEXT, unit TEXT,
                            label TEXT, full_label TEXT, dd_rate REAL, dd_exempt INT);
        CREATE TABLE decisions (reference TEXT, type TEXT, hs_code TEXT, designation TEXT,
                                decision_date TEXT, valid_from TEXT, valid_to TEXT,
                                description TEXT, justification TEXT);
        CREATE TABLE articles (instrument TEXT, scope TEXT, article TEXT, text TEXT);
        CREATE VIRTUAL TABLE search USING fts5(kind, ref, title, body, tokenize='unicode61 remove_diacritics 2');
    """)
    db.executemany("INSERT OR REPLACE INTO tarif VALUES (?,?,?,?,?,?,?,?,?)",
                   [(t["code"], t["hs6"], t["chapter"], t["heading"], t["unit"], t["label"], t["full_label"],
                     t["dd_rate"], int(t["dd_exempt"])) for t in tarif])
    db.executemany("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?)",
                   [(r["reference"], r["type"], r["hs_code"], r["designation"], r["decision_date"],
                     r.get("valid_from"), r.get("valid_to"), r["description"], r["justification"]) for r in rulings])
    db.executemany("INSERT INTO articles VALUES (?,?,?,?)",
                   [(a["instrument"], a["scope"], a["article"], a["text"]) for a in loi + decret])
    rows = []
    rows += [("tarif", t["code"], t["label"], t["full_label"]) for t in tarif]
    rows += [("decision", r["reference"], f'{r["designation"]} → {r["hs_code"]}',
              " ".join([r["description"], r["justification"]])) for r in rulings]
    rows += [("article", f'{a["instrument"]} art. {a["article"]}', a["scope"], a["text"]) for a in loi + decret]
    rows += [("texte", f'{c["source"]} #{c["chunk"]}', c["source"], c["text"]) for c in extra_chunks]
    db.executemany("INSERT INTO search VALUES (?,?,?,?)", rows)
    db.commit()
    db.close()
    return len(rows)


# ------------------------------------------------- sources du référentiel (tools/referentiel.py)
SPECIAL = {"tarif-2016", "loi-17-04", "lf-2026", "decret-18-165"}  # parseurs dédiés ci-dessus


def text_of(src: dict) -> Path:
    return TEXT / (Path(src["fichier"]).stem + ".txt")


def referentiel_sources():
    """Traite toute source présente dans sources/ selon son type : recueil → décisions,
    texte → articles, sinon → paragraphes pour la recherche plein texte."""
    sys.path.insert(0, str(Path(__file__).parent))
    from referentiel import catalogue
    recueils, textes, chunks, rapport = {}, {}, [], []
    for src in catalogue():
        if src["statut"] != "base" or src["id"] in SPECIAL or not text_of(src).exists():
            continue
        txt = text_of(src)
        if src["type"] == "recueil":
            rs = parse_recueil(txt, "DGD — " + src["titre"])
            if rs:
                recueils[src["id"].removeprefix("rtc-")] = rs
                rapport.append(f"{src['id']}: {len(rs)} décisions")
                continue
        if src["type"] == "texte":
            arts = parse_articles(txt, src["titre"])
            if len(arts) >= 3:
                textes[src["id"]] = arts
                rapport.append(f"{src['id']}: {len(arts)} articles")
                continue
        c = paragraphs(txt, src["titre"])
        chunks += c
        rapport.append(f"{src['id']}: {len(c)} paragraphes indexés")
    ajouts = DATA / "sources_ajoutees.json"
    for a in json.loads(ajouts.read_text(encoding="utf-8")) if ajouts.exists() else []:
        if text_of(a).exists():
            c = paragraphs(text_of(a), a["titre"])
            chunks += c
            rapport.append(f"{a['id']}: {len(c)} paragraphes indexés (hors référentiel)")
    veille = DATA / "veille_secondaire.json"
    if veille.exists():
        faits = json.loads(veille.read_text(encoding="utf-8"))["faits"]
        chunks += [{"source": f"Veille (secondaire) — {f['sujet']}", "chunk": i,
                    "text": f"{f['fait']} Source : {f['source']}. À confirmer : {f['officiel_a_verifier']}."}
                   for i, f in enumerate(faits)]
        rapport.append(f"veille secondaire: {len(faits)} faits sourcés")
    return recueils, textes, chunks, rapport


def main():
    DATA.mkdir(exist_ok=True)
    tarif, tarif_meta = parse_tariff()
    by_year, textes, chunks, rapport = referentiel_sources()
    rulings = [r for rs in by_year.values() for r in rs]
    lf_articles, lf_measures = parse_finance_law()
    loi = parse_articles(LOI_TXT, "Loi 17-04 du 16.02.2017")
    decret = parse_articles(DECRET_TXT, "Décret exécutif 18-165 du 14.06.2018")

    def dump(name, obj):
        (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=None if name.startswith("tarif_2016.") else 1), encoding="utf-8")

    notice = ("Tarif douanier DGD édition 2016 (droits de douane D.D uniquement). Les taux ont pu changer "
              "depuis (lois de finances, accords). Vérifier le tarif en vigueur avant toute liquidation.")
    dump("tarif_2016.json", {"_notice": notice, "count": len(tarif), "lines": tarif})
    dump("tarif_2016_notes.json", tarif_meta)
    with (DATA / "tarif_2016.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "chapter", "heading", "unit", "dd_rate", "dd_exempt", "label", "full_label"])
        for t in tarif:
            w.writerow([t["code"], t["chapter"], t["heading"], t["unit"], t["dd_rate"], t["dd_exempt"],
                        t["label"], t["full_label"]])
    for annee, rs in by_year.items():
        dump(f"decisions_classement_{annee}.json", {"count": len(rs), "decisions": rs})
    (DATA / "textes").mkdir(exist_ok=True)
    for sid, arts in textes.items():
        dump(f"textes/{sid}.json", {"count": len(arts), "articles": arts})
    dump("loi_finances_2026.json", {"count": len(lf_articles), "articles": lf_articles})
    dump("mesures_tarifaires_lf2026.json", {"count": len(lf_measures), "measures": lf_measures})
    dump("loi_17-04_code_douanes.json", {"count": len(loi), "articles": loi})
    dump("decret_18-165.json", {"count": len(decret), "articles": decret})

    lf_rows = [{"instrument": a["instrument"], "scope": a["domain"], "article": a["article"], "text": a["text"]}
               for a in lf_articles]
    import parse_sources
    rapport += [f"tableau {r}" for r in parse_sources.main()]
    autres = [a for arts in textes.values() for a in arts]
    n = build_sqlite(tarif, rulings, loi, decret + lf_rows + autres, chunks)
    print(f"tarif: {len(tarif)} lignes | décisions: {len(rulings)} "
          f"({', '.join(f'{y}: {len(r)}' for y, r in by_year.items())}) | loi 17-04: {len(loi)} | "
          f"décret 18-165: {len(decret)} | LF 2026: {len(lf_articles)} articles, {len(lf_measures)} mesures "
          f"tarifaires | index FTS: {n} entrées")
    for r in rapport:
        print("  ·", r)


if __name__ == "__main__":
    main()
