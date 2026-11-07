"""Loads reference data: tariff lines and binding rulings (RTC / BTI)."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .models import Ruling, TariffLine
from .text import tokens

DATA_DIR = Path(__file__).parent / "data"
# Official documents parsed by knowledge-base/tools/build_kb.py
KB_DATA = Path(__file__).resolve().parents[2] / "knowledge-base" / "data"
# The 2016 tariff carries customs duty (D.D) only. VAT is not in it: the standard
# 19 % rate is assumed and flagged in every cost line (reduced 9 % not distinguished).
DEFAULT_VAT = 0.19


class Tariff:
    def __init__(self, lines: list[TariffLine]):
        self.lines = {l.code: l for l in lines}
        self._index = {l.code: tokens(" ".join(l.keywords + [l.label_fr, l.label_ar])) for l in lines}

    @classmethod
    def load(cls, path: Path = DATA_DIR / "tariff_sample.json") -> "Tariff":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls([TariffLine(**l) for l in raw["lines"]])

    @classmethod
    def load_official(cls, path: Path = KB_DATA / "tarif_2016.json",
                      measures: Path = KB_DATA / "mesures_tarifaires_lf2026.json") -> "Tariff":
        """DGD tariff, 2016 edition (15 946 ten-digit lines, D.D rate), updated with the
        unconditional duty rates of the 2026 finance law (exact codes, no attestation needed).
        Conditional measures (ex-codes, attestations, quotas) are left to the broker."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        lines = {l["code"]: TariffLine(code=l["code"], label_fr=l["full_label"], label_ar="", keywords=[],
                                       duty_rate=l["dd_rate"], vat_rate=DEFAULT_VAT, source="dgd-2016")
                 for l in raw["lines"]}
        if measures.exists():
            for m in json.loads(measures.read_text(encoding="utf-8"))["measures"]:
                if not m["apply"]:
                    continue
                note = f'{m["source"]} : {m["measure"]}'
                for c in m["codes"]:
                    if c["ex"]:
                        continue
                    line = lines.get(c["code"])
                    if line is None:  # code created after 2016 (HS 2022): the law gives code, scope and rate
                        line = lines[c["code"]] = TariffLine(code=c["code"], label_fr=m["scope"], label_ar="",
                                                             keywords=[], duty_rate=m["dd_rate"],
                                                             vat_rate=DEFAULT_VAT, source="lf-2026")
                    line.duty_rate = m["dd_rate"]
                    line.rate_note = note
        return cls(list(lines.values()))

    def get(self, code: str | None) -> TariffLine | None:
        return self.lines.get(code) if code else None

    def index(self, code: str) -> set[str]:
        return self._index[code]


class RulingRegistry:
    def __init__(self, rulings: list[Ruling]):
        self.rulings = rulings
        self._index = {r.reference: tokens(r.description) for r in rulings}

    @classmethod
    def load(cls, path: Path = DATA_DIR / "rulings_sample.json") -> "RulingRegistry":
        raw = json.loads(path.read_text(encoding="utf-8"))
        demo = "DEMO" in raw.get("_notice", "")
        rulings = [
            Ruling(
                **{**r, "valid_from": date.fromisoformat(r["valid_from"]), "valid_to": date.fromisoformat(r["valid_to"])},
                demo=demo,
            )
            for r in raw["rulings"]
        ]
        return cls(rulings)

    @classmethod
    def load_official(cls, folder: Path = KB_DATA) -> "RulingRegistry":
        """Real DGD decisions from every published collection in knowledge-base/data
        (decisions_classement_<year>.json): RTC, modèle 110, D40 and notes.
        Holders are not published, so these serve as classification precedents only.
        Decisions without a validity period (modèle 110, D40) are kept open-ended;
        decisions without a retained code (general guidance notes) are skipped."""
        rulings = []
        for path in sorted(folder.glob("decisions_classement_*.json")):
            for r in json.loads(path.read_text(encoding="utf-8"))["decisions"]:
                if not r["hs_codes"]:
                    continue
                start = date.fromisoformat(r.get("valid_from") or r["decision_date"])
                end = date.fromisoformat(r["valid_to"]) if r.get("valid_to") else date.max
                for code in r["hs_codes"]:
                    rulings.append(Ruling(
                        reference=r["reference"] if len(r["hs_codes"]) == 1 else f'{r["reference"]} [{code}]',
                        kind="classification", source="DGD", holder_nif=None,
                        description=r["designation"],  # short title: the long text would match any query
                        hs_code=code, valid_from=start, valid_to=end,
                    ))
        return cls(rulings)

    def get(self, reference: str | None) -> Ruling | None:
        return next((r for r in self.rulings if r.reference == reference), None)

    def index(self, reference: str) -> set[str]:
        return self._index[reference]

    def held_by(self, nif: str | None, on: date) -> list[Ruling]:
        if not nif:
            return []
        return [r for r in self.rulings if r.holder_nif == nif and r.is_valid(on)]

    def expiring(self, nif: str, on: date, within_days: int = 30) -> list[Ruling]:
        limit = on + timedelta(days=within_days)
        return [r for r in self.held_by(nif, on) if r.valid_to <= limit]
