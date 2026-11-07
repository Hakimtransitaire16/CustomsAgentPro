"""Export a compact JSON bundle of the knowledge base for the presentation page.

    python tools/export_web.py   # -> docs/presentation/kb.json

The page fetches this file and runs the same engine logic in the browser.
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "knowledge-base" / "data"
OUT = ROOT / "docs" / "presentation" / "kb.json"


def main() -> None:
    tariff = json.loads((DATA / "tarif_2016.json").read_text(encoding="utf-8"))["lines"]
    # Every published collection, in the same order as RulingRegistry.load_official()
    decisions = []
    for path in sorted(DATA.glob("decisions_classement_*.json")):
        year = path.stem.rsplit("_", 1)[1]
        for d in json.loads(path.read_text(encoding="utf-8"))["decisions"]:
            decisions.append({**d, "_year": year})
    measures = json.loads((DATA / "mesures_tarifaires_lf2026.json").read_text(encoding="utf-8"))["measures"]

    # Heading labels are shared by many lines: store them once.
    headings = {}
    for l in tariff:
        headings.setdefault(l["heading"], l["heading_label"])
    lines = {l["code"]: [l["code"], round(l["dd_rate"] * 100), " > ".join(l["context"] + [l["label"]])] for l in tariff}
    codes = set(lines)
    # Unconditional rates of the 2026 finance law, as in Tariff.load_official():
    # 4th element = {"n": source note, "raw": True when the line is new (label = scope, no heading)}
    for m in measures:
        if not m["apply"]:
            continue
        note = f'{m["source"]} : {m["measure"]}'
        for c in m["codes"]:
            if c["ex"]:
                continue
            line = lines.get(c["code"])
            if line is None:
                line = lines[c["code"]] = [c["code"], 0, m["scope"], {"raw": True}]
            line[1] = round(m["dd_rate"] * 100)
            if len(line) < 4:
                line.append({})
            line[3]["n"] = note
    lines = list(lines.values())

    dec = []
    for d in decisions:
        dec.append({
            "ref": d["reference"],
            "year": d["_year"],
            "type": d["type"],
            "date": d["decision_date"],
            "from": d.get("valid_from"),
            "to": d.get("valid_to"),
            "title": d["designation"],
            "hs": d["hs_codes"],
            "rules": d.get("rules_applied") or "",
            "why": (d.get("justification") or "")[:600],
            "warn": d.get("warnings") or [],
        })

    chapters = collections.Counter(int(d["hs"][0][:2]) for d in dec if d["hs"])
    rates = collections.Counter(l[1] for l in lines)
    missing = sorted({c for d in dec for c in d["hs"] if c not in codes})
    years = sorted({d["year"] for d in dec})

    bundle = {
        "source": "DGD — Tarif douanier 2016 + taux LF 2026 (art. 131, 139, 140) · Recueils des décisions de classement 2020 et 2025",
        "headings": headings,
        "tariff": lines,
        "decisions": dec,
        "stats": {
            "tariff_lines": len(lines),
            "rtc": sum(d["type"] == "RTC" for d in dec),
            "m110": sum(d["type"] != "RTC" for d in dec),
            "chapters": chapters.most_common(8),
            "rates": sorted(rates.items(), key=lambda kv: -kv[0]),
            "missing_codes": missing,
            "years": {y: {"rtc": sum(d["year"] == y and d["type"] == "RTC" for d in dec),
                          "other": sum(d["year"] == y and d["type"] != "RTC" for d in dec)} for y in years},
            "lf2026_lines": sum(len(l) > 3 for l in lines),
            "flagged": [d["ref"] for d in dec if d["warn"]],
        },
    }
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1e6:.2f} MB, {len(lines)} lines, {len(dec)} decisions")
    print(json.dumps(bundle["stats"], ensure_ascii=False))


if __name__ == "__main__":
    main()
