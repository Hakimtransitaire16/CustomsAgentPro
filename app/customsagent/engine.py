"""Single entry point: dossier in, full analysis out."""
from __future__ import annotations

from datetime import date

from .classifier import classify
from .compliance import check
from .duties import landed_cost
from .knowledge import RulingRegistry, Tariff
from .models import Direction, Dossier, Severity


class Engine:
    def __init__(self, tariff: Tariff | None = None, rulings: RulingRegistry | None = None):
        self.tariff = tariff or Tariff.load()
        self.rulings = rulings or RulingRegistry.load()

    @classmethod
    def official(cls) -> "Engine":
        """Engine on the official DGD documents (knowledge-base/) instead of the samples."""
        return cls(Tariff.load_official(), RulingRegistry.load_official())

    def classify(self, description: str) -> list[dict]:
        return [s.to_dict() for s in classify(description, self.tariff, self.rulings)]

    def analyze(self, dossier: Dossier, today: date | None = None) -> dict:
        today = today or date.today()
        findings = check(dossier, self.tariff, self.rulings, today)  # may fill missing HS codes
        blocking = [x for x in findings if x.severity == Severity.BLOCKING]
        result = {
            "reference": dossier.reference,
            "status": "blocked" if blocking else ("review" if findings else "ready"),
            "findings": [x.to_dict() for x in findings],
            "items": [{"description": i.description, "hs_code": i.hs_code} for i in dossier.items],
        }
        if dossier.direction == Direction.IMPORT:
            result["cost"] = landed_cost(dossier, self.tariff)
        return result

    def analyze_dict(self, data: dict, today: date | None = None) -> dict:
        return self.analyze(Dossier.from_dict(data), today)
