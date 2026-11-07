"""Build the structured knowledge base from the extracted texts.

Usage (from the knowledge-base folder):
    python tools/build_kb.py

Inputs : text/*.txt  (made by tools/extract_text.sh from sources/*.pdf)
Outputs: data/tarif_2016.json, data/tarif_2016.csv, data/tarif_2016_notes.json,
         data/decisions_classement_2025.json, data/loi_17-04_code_douanes.json,
         data/decret_18-165.json, data/references.json, kb.sqlite (full-text search)
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / "text"
DATA = ROOT / "data"

TARIF_TXT = TEXT / "tarif-douanier-2016-10-chiffres-pour-telechargement.txt"
RECUEIL_TXT = TEXT / "recueil_des_decisions_de_classement_tarifaire_2026.txt"
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


# ------------------------------------------------------------------- rulings 2025
PAGE_NOISE = re.compile(
    r"Direction Générale des Douanes|Sous -Direction des Bases|Recueil de Décisions de Classement|"
    r"^\s*\d{1,3}\s*$|^\s*(JANVIER|Janvier)?\s*2026\s*$"
)


def strip_pages(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not PAGE_NOISE.search(l))


def section(block: str, start: str, ends: list[str]) -> str:
    m = re.search(re.escape(start) + r"\s*:?(.*?)(?=" + "|".join(re.escape(e) for e in ends) + r"|\Z)", block, re.S)
    return clean(m.group(1)) if m else ""


def regex_section(block: str, start: str, end: str) -> str:
    m = re.search(start + r"(.*?)(?=" + end + ")", block, re.S)
    return clean(m.group(1)) if m else ""


def check_consistency(rulings: list[dict]) -> None:
    """Flag a likely typo: the retained code never appears in the reasoning, while a code that
    differs from it by one or two digits does (e.g. 4221.91.99.00 in the header, 4421.91.99.00 in the text)."""
    for r in rulings:
        text = r.get("justification") or ""
        cited = set(re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", text))
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


def parse_recueil() -> list[dict]:
    text = strip_pages(RECUEIL_TXT.read_text(encoding="utf-8"))
    out = []
    rtc_blocks = re.split(r"(?=REFERENCE RTC\s*:\s*N°)", text)
    for b in rtc_blocks:
        if not b.startswith("REFERENCE RTC"):
            continue
        b = b.split("Référence de la décision : Modèle 110")[0]
        ref = re.search(r"N°\s*(\d+/DGD)\s+DU\s+([\d.]+)", b)
        retained_txt = section(b, "SOUS-POSITION RETENUE", ["DESCRIPTION DU PRODUIT"])
        codes = re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", retained_txt)
        rgi = re.search(r"(Application d[ue]s? .*?(?:du SH|SH)\.?)", b.replace("\n", " "))
        out.append({
            "type": "RTC",
            "reference": f"RTC {ref.group(1)} du {ref.group(2)}" if ref else None,
            "number": int(ref.group(1).split("/")[0]) if ref else None,
            "decision_date": dmy(ref.group(2)) if ref else None,
            "valid_from": dmy(section(b, "DATE DE DEBUT DE VALIDITE", ["DATE DE FIN"])),
            "valid_to": dmy(section(b, "DATE DE FIN DE VALIDITE", ["DESIGNATION"])),
            "designation": section(b, "DESIGNATION DU PRODUIT", ["SOUS-POSITION RETENUE"]),
            "hs_code": codes[0] if codes else None,
            "hs_codes": codes,
            "description": section(b, "DESCRIPTION DU PRODUIT", ["JUSTIFICATIF DU CLASSEMENT"]),
            "justification": section(b, "JUSTIFICATIF DU CLASSEMENT", ["ILLUSTRATION", "REFERENCE RTC"]),
            "rules_applied": clean(rgi.group(1)) if rgi else None,
            "source": "DGD — Recueil des décisions de classement tarifaire 2025 (publié janvier 2026)",
        })

    for b in re.split(r"(?=Référence de la décision : Modèle 110)", text)[1:]:
        ref = re.search(r"Modèle 110, n°\s*(\S+)\s+du\s+([\d.]+)", b)
        retained = re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}",
                              regex_section(b, r"tarifaire\(s\) retenue\(s\)\s*:", r"\d\.\s*Description"))
        envis = re.search(r"envisagée \(s\)\s*:\s*(.*?)\n", b)
        body = b.split("DECISION DE L’ADMINISTRATION CENTRALE", 1)[-1]
        out.append({
            "type": "Modèle 110",
            "reference": f"Modèle 110 n° {ref.group(1)} du {ref.group(2)}" if ref else None,
            "decision_date": dmy(ref.group(2)) if ref else None,
            "requesting_service": section(b, "Service demandeur", ["Description du produit"]),
            "designation": section(b, "Description du produit", ["Position(s)"]),
            "codes_considered": re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", envis.group(1)) if envis else [],
            "hs_code": retained[0] if retained else None,
            "hs_codes": retained,
            "description": regex_section(body, r"\d\.\s*Description du produit\s*:", r"\d\.\s*Sous positions? envisagées?"),
            "justification": regex_section(body, r"\d\.\s*Classement tarifaire\s*:", r"\Z"),
            "source": "DGD — Recueil des décisions de classement tarifaire 2025 (publié janvier 2026)",
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


def main():
    DATA.mkdir(exist_ok=True)
    tarif, tarif_meta = parse_tariff()
    rulings = parse_recueil()
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
    dump("decisions_classement_2025.json", {"count": len(rulings), "decisions": rulings})
    dump("loi_17-04_code_douanes.json", {"count": len(loi), "articles": loi})
    dump("decret_18-165.json", {"count": len(decret), "articles": decret})

    chunks = paragraphs(EBTI_TXT, "EBTI — information générale BTI (UE)") + \
        paragraphs(SMART_TXT, "OMD — Enquête douanes intelligentes (juillet 2024)")
    n = build_sqlite(tarif, rulings, loi, decret, chunks)
    print(f"tarif: {len(tarif)} lignes | décisions: {len(rulings)} | loi 17-04: {len(loi)} articles | "
          f"décret 18-165: {len(decret)} articles | index FTS: {n} entrées")


if __name__ == "__main__":
    main()
