"""Pydantic schemas for AI I/O."""

from typing import Any

from pydantic import BaseModel, Field


class RFxDraftLineItem(BaseModel):
    sku_name: str
    qty: float
    unit: str
    target_price: float | None = None
    notes: str | None = None


class RFxDraft(BaseModel):
    title: str
    line_items: list[RFxDraftLineItem]
    delivery_window_start: str | None = None
    delivery_window_end: str | None = None
    response_deadline: str | None = None
    notes_for_vendors: str | None = None


class OfferLineItem(BaseModel):
    sku_name: str
    qty: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total: float | None = None
    lead_time_hours: float | None = None
    moq: float | None = None
    confidence_per_field: dict[str, float] = Field(default_factory=dict)


class ExtractedOffer(BaseModel):
    line_items: list[OfferLineItem]
    total_quote: float | None = None
    currency: str = "INR"
    lead_time_hours: float | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    validity_days: int | None = None
    tax_treatment: str | None = None
    gst_pct: float | None = None
    additional_charges: list[dict[str, Any]] | None = None
    vendor_remarks: str | None = None
    confidence_overall: float = 0.0


class ExtractionSnippet(BaseModel):
    source: str  # "pdf_page_1", "excel_sheet1", "email_body", "image"
    content: str
    mime_type: str = ""


class VendorSuggestion(BaseModel):
    vendor_id: int
    vendor_name: str
    email: str
    categories: list[str]
    score: float
    recommended_channel: str = "in_app"


class DispatchPlan(BaseModel):
    vendor_id: int
    vendor_name: str
    channel: str  # in_app, email, telegram
    channel_detail: str  # email address or telegram handle
