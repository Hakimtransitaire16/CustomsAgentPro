"""Loads reference data: tariff lines and binding rulings (RTC / BTI)."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .models import Ruling, TariffLine
from .text import tokens

DATA_DIR = Path(__file__).parent / "data"


class Tariff:
    def __init__(self, lines: list[TariffLine]):
        self.lines = {l.code: l for l in lines}
        self._index = {l.code: tokens(" ".join(l.keywords + [l.label_fr, l.label_ar])) for l in lines}

    @classmethod
    def load(cls, path: Path = DATA_DIR / "tariff_sample.json") -> "Tariff":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls([TariffLine(**l) for l in raw["lines"]])

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
