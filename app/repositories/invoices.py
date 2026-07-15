from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel, col
from app.models.invoice import InvoiceMetadata, InvoiceSubjectType

INVOICE_METADATA_TABLE: Table = SQLModel.metadata.tables["invoice_metadata"]

def map_invoice(
    invoice: dict,
    subject_type: InvoiceSubjectType,
) -> InvoiceMetadata:
    buyer = invoice.get("buyer") or {}
    buyer_identifier = buyer.get("identifier") or {}
    seller = invoice.get("seller") or {}
    form_code = invoice.get("formCode") or {}

    return InvoiceMetadata(
        ksef_number=invoice["ksefNumber"],
        subject_type=subject_type,
        invoice_number=invoice["invoiceNumber"],        
        issue_date=date.fromisoformat(invoice["issueDate"]),
        invoicing_date=_parse_datetime(invoice.get("invoicingDate")),
        acquisition_date=_parse_datetime(invoice.get("acquisitionDate")),
        permanent_storage_date=_parse_datetime(invoice.get("permanentStorageDate")),
        seller_nip=seller.get("nip"),
        seller_name=seller.get("name"),
        buyer_identifier_type=buyer_identifier.get("type"),
        buyer_identifier_value=buyer_identifier.get("value"),
        buyer_name=buyer.get("name"),
        net_amount=_parse_decimal(invoice.get("netAmount")),
        gross_amount=_parse_decimal(invoice.get("grossAmount")),
        vat_amount=_parse_decimal(invoice.get("vatAmount")),
        currency=invoice.get("currency"),
        invoicing_mode=invoice.get("invoicingMode"),
        invoice_type=invoice.get("invoiceType"),
        form_system_code=form_code.get("systemCode"),
        form_schema_version=form_code.get("schemaVersion"),
        form_value=form_code.get("value"),
        is_self_invoicing=invoice.get("isSelfInvoicing", False),
        has_attachment=invoice.get("hasAttachment", False),
        invoice_hash=invoice.get("invoiceHash"),
    )


def get_last_permanent_storage_date(
    session: Session,
    subject_type: InvoiceSubjectType,
) -> datetime | None:
    statement = select(func.max(InvoiceMetadata.permanent_storage_date)).where(
        col(InvoiceMetadata.subject_type) == subject_type
    )

    return session.scalar(statement)

def save_new_invoices(
    session: Session,
    invoices: list[dict],
    subject_type: InvoiceSubjectType,
) -> int:
    if not invoices:
        return 0

    rows = [
        map_invoice(invoice, subject_type).model_dump(
            exclude={"created_at", "updated_at"},
            mode="json",
        )
        for invoice in invoices
    ]

    statement = (
        insert(INVOICE_METADATA_TABLE)        .values(rows)
        .on_conflict_do_nothing(
            index_elements=[INVOICE_METADATA_TABLE.c.ksef_number]
        )
        .returning(INVOICE_METADATA_TABLE.c.ksef_number)
    )
    result = session.execute(statement)
    inserted_numbers = result.scalars().all()

    session.commit()

    return len(inserted_numbers)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _parse_decimal(value: int | float | str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
