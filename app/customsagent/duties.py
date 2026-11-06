"""Landed-cost calculation for imports into Algeria.

Formula (configurable, see docs/etude/04-synthese-et-modele.md §4.3):
    customs value (DZD) = (goods value + share of freight + insurance) x rate
    DD   = value x duty rate
    DAPS = value x DAPS rate
    VAT  = (value + DD + DAPS) x VAT rate
Rates come from the tariff file, which is ILLUSTRATIVE in this prototype.
"""
from __future__ import annotations

from .knowledge import Tariff
from .models import Dossier


def _r(x: float) -> float:
    return round(x, 2)


def landed_cost(dossier: Dossier, tariff: Tariff) -> dict:
    total_value = sum(i.value for i in dossier.items) or 1.0
    extras = dossier.freight + dossier.insurance if dossier.incoterm.upper() in {"EXW", "FCA", "FOB"} else 0.0
    lines = []
    totals = {"customs_value": 0.0, "duty": 0.0, "daps": 0.0, "vat": 0.0}

    for idx, item in enumerate(dossier.items):
        line = tariff.get(item.hs_code)
        share = item.value / total_value
        value_dzd = (item.value + extras * share) * dossier.exchange_rate
        if line is None:
            lines.append({"item": idx, "hs_code": item.hs_code, "customs_value": _r(value_dzd), "error": "unknown_tariff_line"})
            totals["customs_value"] += value_dzd
            continue
        duty = value_dzd * line.duty_rate
        daps = value_dzd * line.daps_rate
        vat = (value_dzd + duty + daps) * line.vat_rate
        lines.append({
            "item": idx, "hs_code": line.code, "customs_value": _r(value_dzd),
            "duty_rate": line.duty_rate, "duty": _r(duty),
            "daps_rate": line.daps_rate, "daps": _r(daps),
            "vat_rate": line.vat_rate, "vat": _r(vat),
            "taxes": _r(duty + daps + vat),
        })
        totals["customs_value"] += value_dzd
        totals["duty"] += duty
        totals["daps"] += daps
        totals["vat"] += vat

    totals = {k: _r(v) for k, v in totals.items()}
    totals["taxes"] = _r(totals["duty"] + totals["daps"] + totals["vat"])
    totals["landed"] = _r(totals["customs_value"] + totals["taxes"])
    return {"currency": "DZD", "illustrative_rates": True, "lines": lines, "totals": totals}
