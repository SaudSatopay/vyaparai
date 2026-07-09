"""Core data models for the Quote-to-Cash Autopilot (India / GST)."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    EN = "en"
    HI = "hi"
    HINGLISH = "hinglish"
    OTHER = "other"


class Status(str, Enum):
    DRAFT = "draft"
    NEEDS_INFO = "needs_info"          # agent needs clarification from the customer
    PENDING_APPROVAL = "pending_approval"  # human-in-the-loop checkpoint
    APPROVED = "approved"
    SENT = "sent"


class ParsedItem(BaseModel):
    """A single line the customer asked for, as understood from free text."""
    query: str
    qty: float = 1
    unit_hint: Optional[str] = None


class Inquiry(BaseModel):
    """Structured form of a raw customer inquiry (EN / HI / Hinglish)."""
    raw_text: str
    language: Language = Language.EN
    customer_name: Optional[str] = None
    customer_gstin: Optional[str] = None
    items: list[ParsedItem] = Field(default_factory=list)
    clarifications_needed: list[str] = Field(default_factory=list)


class LineItem(BaseModel):
    product_id: str
    name: str
    hsn: str
    qty: float
    unit: str
    unit_price: float        # INR, GST-exclusive
    gst_rate: float          # percent, e.g. 18
    taxable_value: float     # qty * unit_price
    cgst: float = 0          # intra-state
    sgst: float = 0          # intra-state
    igst: float = 0          # inter-state
    line_total: float = 0    # taxable_value + taxes


class Quote(BaseModel):
    quote_id: str
    customer_name: Optional[str] = None
    customer_gstin: Optional[str] = None
    intra_state: bool = True  # True -> CGST+SGST, False -> IGST
    currency: str = "INR"
    lines: list[LineItem] = Field(default_factory=list)
    taxable_total: float = 0
    total_cgst: float = 0
    total_sgst: float = 0
    total_igst: float = 0
    grand_total: float = 0
    status: Status = Status.DRAFT
    detected_language: Optional[str] = None
    agent_trace: list[dict] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Invoice(BaseModel):
    invoice_no: str
    quote: Quote
    seller_gstin: str
    irn: Optional[str] = None       # Invoice Reference Number (NIC SHA-256 algorithm)
    ack_no: Optional[str] = None    # IRP acknowledgement number
    ack_dt: Optional[str] = None    # IRP acknowledgement timestamp
    qr_jws: Optional[str] = None    # signed QR payload (compact JWS)
    inv01: Optional[dict] = None    # full NIC INV-01 v1.1 registration payload
    signed_by: Optional[str] = None
    status: Status = Status.DRAFT
