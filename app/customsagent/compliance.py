"""Business rules: RTC/BTI, EUDR, CBAM, documents, data sanity.

Rule codes match docs/etude/04-synthese-et-modele.md §4.2.
EUDR / CBAM scopes are SIMPLIFIED heading prefixes for the prototype; the
legal reference is Annex I of Regulation (EU) 2023/1115 (EUDR) and Annex I
of Regulation (EU) 2023/956 (CBAM).
"""
from __future__ import annotations

from datetime import date

from .classifier import LOW_CONFIDENCE, classify
from .knowledge import RulingRegistry, Tariff
from .models import Direction, Dossier, Finding, Severity
from .text import tokens

PRECEDENT_MATCH = 0.6  # share of the description's words found in a precedent's title

EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV",
    "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}

EUDR_SCOPE = {
    "cattle": ["0102", "0201", "0202", "4101", "4104", "4107"],
    "cocoa": ["1801", "1802", "1803", "1804", "1805", "1806"],
    "coffee": ["0901"],
    "oil_palm": ["1207.10", "1511", "1513.21", "1513.29"],
    "rubber": ["4001", "4005", "4006", "4007", "4008", "4010", "4011", "4012", "4013", "4015", "4016", "4017"],
    "soya": ["1201", "1208.10", "1507", "2304"],
    "wood": ["44", "47", "48", "9401", "9403", "9406"],
}

CBAM_SCOPE = {
    "cement": ["2507.00", "2523"],
    "electricity": ["2716"],
    "fertilisers": ["2808", "2814", "2834.21", "3102", "3105"],
    "iron_steel": ["72", "7301", "7302", "7303", "7304", "7305", "7306", "7307", "7308", "7309", "7310", "7311", "7318", "7326"],
    "aluminium": ["7601", "7603", "7604", "7605", "7606", "7607", "7608", "7609", "7610", "7611", "7612", "7613", "7614", "7616"],
    "hydrogen": ["2804.10"],
}

IMPORT_REQUIRED_DOCS = {"invoice": "الفاتورة التجارية", "transport": "وثيقة النقل (B/L أو LTA أو CMR)"}
EXPORT_REQUIRED_DOCS = {"invoice": "الفاتورة التجارية"}


def _digits(code: str) -> str:
    return code.replace(".", "").replace(" ", "")


def in_scope(hs_code: str | None, scope: dict[str, list[str]]) -> str | None:
    if not hs_code:
        return None
    code = _digits(hs_code)
    for commodity, prefixes in scope.items():
        if any(code.startswith(_digits(p)) for p in prefixes):
            return commodity
    return None


def check(dossier: Dossier, tariff: Tariff, rulings: RulingRegistry, today: date) -> list[Finding]:
    f: list[Finding] = []
    to_eu = dossier.direction == Direction.EXPORT and dossier.destination_country in EU_COUNTRIES
    has_dds = dossier.has_document("dds")
    has_cbam = dossier.has_document("cbam_emissions")

    # R-DOC-01 mandatory documents
    required = IMPORT_REQUIRED_DOCS if dossier.direction == Direction.IMPORT else EXPORT_REQUIRED_DOCS
    for doc_type, label in required.items():
        if not dossier.has_document(doc_type):
            f.append(Finding("R-DOC-01", Severity.BLOCKING, f"وثيقة إلزامية ناقصة: {label}"))

    if not dossier.items:
        f.append(Finding("R-VAL-01", Severity.BLOCKING, "الملف لا يحتوي على أي بند بضاعة"))

    held = rulings.held_by(dossier.holder_nif, today)

    for idx, item in enumerate(dossier.items):
        # R-VAL-01 data sanity
        if item.value <= 0:
            f.append(Finding("R-VAL-01", Severity.BLOCKING, "القيمة يجب أن تكون أكبر من صفر", idx))
        if item.net_kg < 0 or item.gross_kg < 0 or (item.gross_kg and item.net_kg > item.gross_kg):
            f.append(Finding("R-VAL-01", Severity.BLOCKING, "الوزن الصافي لا يمكن أن يتجاوز الوزن القائم", idx))

        # Classification: suggest when missing, warn when uncertain
        suggestions = classify(item.description, tariff, rulings)
        if not item.hs_code:
            if suggestions:
                s = suggestions[0]
                f.append(Finding("R-CLS-00", Severity.INFO,
                                 f"رمز مقترح: {s.hs_code} ({s.label_ar}) — ثقة {int(s.confidence * 100)}%", idx))
                item.hs_code = s.hs_code
            else:
                f.append(Finding("R-CLS-00", Severity.BLOCKING, "تعذّر اقتراح رمز تعريفة: الوصف غير كافٍ", idx))
                continue
            if s.confidence < LOW_CONFIDENCE:
                f.append(Finding("R-CLS-01", Severity.WARNING,
                                 "ثقة التصنيف منخفضة: نوصي بطلب RTC من المديرية العامة للجمارك قبل الشحن", idx))
        elif tariff.get(item.hs_code) is None:
            f.append(Finding("R-CLS-02", Severity.WARNING, f"الرمز {item.hs_code} غير موجود في التعريفة المحمّلة", idx))

        # R-RTC-02 quoted ruling must exist and be valid; it must also match the code
        if item.ruling_ref:
            r = rulings.get(item.ruling_ref)
            if r is None:
                f.append(Finding("R-RTC-02", Severity.BLOCKING, f"المرجع {item.ruling_ref} غير موجود في سجل القرارات", idx))
            elif not r.is_valid(today):
                f.append(Finding("R-RTC-02", Severity.BLOCKING, f"القرار {r.reference} منتهي الصلاحية منذ {r.valid_to}", idx))
            elif r.hs_code != item.hs_code:
                f.append(Finding("R-RTC-01", Severity.BLOCKING,
                                 f"الرمز المصرّح {item.hs_code} يخالف القرار {r.reference} ({r.hs_code})", idx))

        # R-RTC-01 holder has a valid ruling for similar goods with another code
        if suggestions:
            for r in held:
                if r.reference == item.ruling_ref:
                    continue
                if r.reference in suggestions[0].precedents and r.hs_code != item.hs_code:
                    f.append(Finding("R-RTC-01", Severity.BLOCKING,
                                     f"لديك قرار ساري {r.reference} لبضاعة مماثلة برمز {r.hs_code}، والرمز المصرّح {item.hs_code}", idx))

        # R-PRE-01 a published precedent classifies similar goods under another code
        if item.hs_code and not item.ruling_ref:
            query = tokens(item.description)
            shown = 0
            for r in rulings.rulings:
                if r.holder_nif and r.holder_nif == dossier.holder_nif:
                    continue  # the holder's own rulings are handled by R-RTC-01
                common = query & rulings.index(r.reference)
                if query and len(common) / len(query) >= PRECEDENT_MATCH and r.hs_code != item.hs_code:
                    f.append(Finding("R-PRE-01", Severity.WARNING,
                                     f"سابقة منشورة: القرار {r.reference} صنّف بضاعة مشابهة ({r.description[:70]}) "
                                     f"في الرمز {r.hs_code}، والرمز المصرّح {item.hs_code}. راجع التصنيف", idx))
                    shown += 1
                    if shown == 2:
                        break

        # Import licences
        line = tariff.get(item.hs_code)
        if dossier.direction == Direction.IMPORT and line and line.licence_required and not dossier.has_document("licence"):
            f.append(Finding("R-LIC-01", Severity.WARNING, "هذا البند قد يخضع لترخيص أو إجراء مسبق: تحقق من التنظيم الساري", idx))

        # EU market access: EUDR / CBAM
        if to_eu:
            eudr = in_scope(item.hs_code, EUDR_SCOPE)
            if eudr and not has_dds and not item.geolocation:
                f.append(Finding("R-EUDR-01", Severity.BLOCKING,
                                 f"البند في نطاق EUDR ({eudr}): يلزم مرجع DDS أو بيانات تحديد الموقع لتمكين المستورد الأوروبي", idx))
            cbam = in_scope(item.hs_code, CBAM_SCOPE)
            if cbam and not has_cbam:
                f.append(Finding("R-CBAM-01", Severity.WARNING,
                                 f"البند في نطاق CBAM ({cbam}): جهّز بيانات الانبعاثات المضمنة، وإلا تُطبق القيم الافتراضية", idx))

    # R-RTC-03 expiring rulings
    if dossier.holder_nif:
        for r in rulings.expiring(dossier.holder_nif, today):
            f.append(Finding("R-RTC-03", Severity.WARNING, f"القرار {r.reference} ينتهي في {r.valid_to}: جهّز طلب التجديد"))

    return f
