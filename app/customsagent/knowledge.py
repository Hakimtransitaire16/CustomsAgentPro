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
    def load_official(cls, path: Path = KB_DATA / "tarif_2016.json") -> "Tariff":
        """DGD tariff, 2016 edition: 15 946 ten-digit lines with their D.D rate."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls([
            TariffLine(code=l["code"], label_fr=l["full_label"], label_ar="", keywords=[],
                       duty_rate=l["dd_rate"], vat_rate=DEFAULT_VAT, source="dgd-2016")
            for l in raw["lines"]
        ])

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
    def load_official(cls, path: Path = KB_DATA / "decisions_classement_2025.json") -> "RulingRegistry":
        """Real DGD decisions published in the 2025 collection (77 RTC + 6 modèle 110).
        Holders are not published, so these serve as classification precedents only.
        Modèle 110 decisions carry no validity period: they are kept open-ended."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        rulings = []
        for r in raw["decisions"]:
            start = date.fromisoformat(r.get("valid_from") or r["decision_date"])
            end = date.fromisoformat(r["valid_to"]) if r.get("valid_to") else date.max
            for code in r["hs_codes"] or [r["hs_code"]]:
                rulings.append(Ruling(
                    reference=r["reference"] if len(r["hs_codes"]) <= 1 else f'{r["reference"]} [{code}]',
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
