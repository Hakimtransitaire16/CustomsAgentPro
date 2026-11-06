"""Data model for a shipment dossier.

Inspired by the WCO Data Model / EU Customs Data Model (EUCDM): one dossier is
the single source of truth from which classification, duty calculation,
compliance checks and the draft declaration are all derived ("once only").
The `eucdm` comments give the approximate EUCDM data-element group.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import Any


class Direction(str, Enum):
    IMPORT = "import"
    EXPORT = "export"


class Severity(str, Enum):
    BLOCKING = "blocking"   # مانع
    WARNING = "warning"     # تحذير
    INFO = "info"           # معلومة


@dataclass
class Party:  # eucdm group 13
    name: str
    role: str  # importer | exporter | declarant | representative
    nif: str | None = None
    rc: str | None = None
    eori: str | None = None


@dataclass
class Document:  # eucdm group 12
    type: str  # invoice | transport | eur1 | rtc | dds | cbam_emissions | licence | packing_list
    number: str
    issued: date | None = None


@dataclass
class GoodsItem:  # eucdm group 18
    description: str
    hs_code: str | None = None
    quantity: float = 0
    net_kg: float = 0
    gross_kg: float = 0
    value: float = 0  # invoice value in dossier currency
    origin: str | None = None  # ISO country code
    ruling_ref: str | None = None  # RTC / BTI reference quoted for this item
    geolocation: str | None = None  # EUDR: plot coordinates or postal address


@dataclass
class Dossier:  # eucdm groups 11, 14, 16, 19
    reference: str
    direction: Direction
    holder_nif: str | None  # operator who holds rulings (importer/exporter)
    origin_country: str
    destination_country: str
    incoterm: str = "FOB"
    currency: str = "EUR"
    exchange_rate: float = 1.0  # 1 unit of currency in DZD
    freight: float = 0
    insurance: float = 0
    items: list[GoodsItem] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    parties: list[Party] = field(default_factory=list)

    def has_document(self, doc_type: str) -> bool:
        return any(d.type == doc_type for d in self.documents)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Dossier":
        def to_date(v):
            return date.fromisoformat(v) if v else None

        return Dossier(
            reference=data.get("reference", "DRAFT"),
            direction=Direction(data.get("direction", "import")),
            holder_nif=data.get("holder_nif"),
            origin_country=data.get("origin_country", "").upper(),
            destination_country=data.get("destination_country", "").upper(),
            incoterm=data.get("incoterm", "FOB"),
            currency=data.get("currency", "EUR"),
            exchange_rate=float(data.get("exchange_rate", 1.0)),
            freight=float(data.get("freight", 0)),
            insurance=float(data.get("insurance", 0)),
            items=[GoodsItem(**i) for i in data.get("items", [])],
            documents=[
                Document(type=d["type"], number=d.get("number", ""), issued=to_date(d.get("issued")))
                for d in data.get("documents", [])
            ],
            parties=[Party(**p) for p in data.get("parties", [])],
        )


@dataclass
class Ruling:
    """A binding ruling: Algerian RTC or EU BTI."""
    reference: str
    kind: str  # classification | origin
    source: str  # DGD | EBTI
    holder_nif: str | None
    description: str
    hs_code: str
    valid_from: date
    valid_to: date
    demo: bool = False

    def is_valid(self, on: date) -> bool:
        return self.valid_from <= on <= self.valid_to


@dataclass
class TariffLine:
    code: str
    label_fr: str
    label_ar: str
    keywords: list[str]
    duty_rate: float
    vat_rate: float
    daps_rate: float = 0.0
    licence_required: bool = False


@dataclass
class Finding:
    rule: str
    severity: Severity
    message: str
    item: int | None = None  # index of the goods item, if any

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d
