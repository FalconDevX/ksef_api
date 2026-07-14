from datetime import date, datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel


class InvoiceMetadata(SQLModel, table=True):
    ksef_number: str = Field(primary_key=True, max_length=50)
    invoice_number: str = Field(max_length=100)

    issue_date: date
    invoicing_date: datetime | None = None
    acquisition_date: datetime | None = None
    permanent_storage_date: datetime | None = None

    seller_nip: str | None = Field(default=None, max_length=10)
    seller_name: str | None = None

    buyer_identifier_type: str | None = Field(default=None, max_length=30)
    buyer_identifier_value: str | None = Field(default=None, max_length=50)
    buyer_name: str | None = None

    net_amount: Decimal | None = Field(default=None, decimal_places=2)
    gross_amount: Decimal | None = Field(default=None, decimal_places=2)
    vat_amount: Decimal | None = Field(default=None, decimal_places=2)

    currency: str | None = Field(default=None, max_length=3)
    invoicing_mode: str | None = Field(default=None, max_length=30)
    invoice_type: str | None = Field(default=None, max_length=30)

    form_system_code: str | None = Field(default=None, max_length=30)
    form_schema_version: str | None = Field(default=None, max_length=20)
    form_value: str | None = Field(default=None, max_length=20)

    is_self_invoicing: bool = False
    has_attachment: bool = False

    invoice_hash: str | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
