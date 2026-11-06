"""HS classification suggestions with a confidence score and explanation.

Prototype scoring: token overlap between the goods description and
(a) tariff line keywords, (b) published rulings used as precedents.
Rulings weigh more because they are real classification decisions.
This is a decision aid for the licensed broker, never a final decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .knowledge import RulingRegistry, Tariff
from .text import tokens

PRECEDENT_WEIGHT = 1.5
LOW_CONFIDENCE = 0.6


@dataclass
class Suggestion:
    hs_code: str
    label_ar: str
    label_fr: str
    confidence: float
    matched_terms: list[str]
    precedents: list[str] = field(default_factory=list)

    def to_dict(self):
        return self.__dict__.copy()


def _overlap(query: set[str], target: set[str]) -> tuple[float, set[str]]:
    common = query & target
    if not query:
        return 0.0, common
    return len(common) / len(query), common


def classify(description: str, tariff: Tariff, rulings: RulingRegistry, top: int = 3) -> list[Suggestion]:
    query = tokens(description)
    scores: dict[str, float] = {}
    terms: dict[str, set[str]] = {}
    precedents: dict[str, list[str]] = {}

    for code in tariff.lines:
        score, common = _overlap(query, tariff.index(code))
        if score:
            scores[code] = score
            terms[code] = set(common)

    for r in rulings.rulings:
        score, common = _overlap(query, rulings.index(r.reference))
        if score and r.hs_code in tariff.lines:
            scores[r.hs_code] = scores.get(r.hs_code, 0) + score * PRECEDENT_WEIGHT
            terms.setdefault(r.hs_code, set()).update(common)
            precedents.setdefault(r.hs_code, []).append(r.reference)

    if not scores:
        return []

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best = ranked[0][1]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = (best - runner_up) / best
    out = []
    for rank, (code, score) in enumerate(ranked[:top]):
        # Confidence = match strength, penalised when the top candidates are
        # close to each other (ambiguous description). Alternatives are capped.
        strength = min(score, 1.0)
        confidence = strength * (0.5 + 0.5 * margin) if rank == 0 else strength * 0.5
        line = tariff.lines[code]
        out.append(Suggestion(
            hs_code=code,
            label_ar=line.label_ar,
            label_fr=line.label_fr,
            confidence=round(min(confidence, 0.99), 2),
            matched_terms=sorted(terms.get(code, [])),
            precedents=precedents.get(code, []),
        ))
    return out
