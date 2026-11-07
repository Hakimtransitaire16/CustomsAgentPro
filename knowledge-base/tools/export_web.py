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
    decisions = json.loads((DATA / "decisions_classement_2025.json").read_text(encoding="utf-8"))["decisions"]

    # Heading labels are shared by many lines: store them once.
    headings = {}
    for l in tariff:
        headings.setdefault(l["heading"], l["heading_label"])
    lines = [[l["code"], round(l["dd_rate"] * 100), " > ".join(l["context"] + [l["label"]])] for l in tariff]
    codes = {l["code"] for l in tariff}

    dec = []
    for d in decisions:
        dec.append({
            "ref": d["reference"],
            "type": d["type"],
            "date": d["decision_date"],
            "from": d.get("valid_from"),
            "to": d.get("valid_to"),
            "title": d["designation"],
            "hs": d["hs_codes"] or [d["hs_code"]],
            "rules": d.get("rules_applied") or "",
            "why": (d.get("justification") or "")[:600],
            "warn": d.get("warnings") or [],
        })

    chapters = collections.Counter(int(d["hs"][0][:2]) for d in dec)
    rates = collections.Counter(l[1] for l in lines)
    missing = sorted({c for d in dec for c in d["hs"] if c not in codes})
    durations = collections.Counter(
        d["to"] and d["from"] and (int(d["to"][:4]) - int(d["from"][:4])) for d in dec if d["type"] == "RTC")

    bundle = {
        "source": "DGD — Tarif douanier 2016 · Recueil des décisions de classement tarifaire 2025 (publié janvier 2026)",
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
            "rtc_years": dict(durations),
            "flagged": [d["ref"] for d in dec if d["warn"]],
        },
    }
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1e6:.2f} MB, {len(lines)} lines, {len(dec)} decisions")
    print(json.dumps(bundle["stats"], ensure_ascii=False))


if __name__ == "__main__":
    main()
