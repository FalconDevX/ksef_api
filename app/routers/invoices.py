from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func, or_
from sqlmodel import col, select
from app.database import SessionDep
from app.ksef.client import SUBJECT_TYPES, auth, redeem_token, wait_for_auth
from app.ksef.invoices import ( get_all_invoices_metadata, get_invoice_by_num, get_invoices_metadata_for_subject, )
from app.models import InvoiceMetadata
from app.models.invoice import InvoiceSubjectType
from app.repositories.invoices import ( get_last_permanent_storage_date, save_new_invoices, )
router = APIRouter(prefix="/invoices", tags=["invoices"])


def _get_tokens():
    auth_data = auth()
    wait_for_auth(auth_data)
    return redeem_token(auth_data)


@router.post("/sync")
def sync_invoices(session: SessionDep):
    date_to = datetime.now(timezone.utc)
    tokens = _get_tokens()

    total_saved = 0

    for subject_type in InvoiceSubjectType:
        last_storage_date = get_last_permanent_storage_date(
            session=session,
            subject_type=subject_type,
        )

        if last_storage_date is None:
            date_from = date_to - timedelta(days=7)
        else:
            date_from = last_storage_date - timedelta(minutes=5)

        print(
            f"{subject_type.value}: "
            f"date_from={date_from}, date_to={date_to}"
        )

        invoices = get_invoices_metadata_for_subject(
            tokens=tokens,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
            subject_type=subject_type.value,
        )
        saved = save_new_invoices(
            session=session,
            invoices=invoices,
            subject_type=subject_type,
        )

        total_saved += saved

    return {"saved": total_saved}


@router.get("/metadata")
def list_invoice_metadata(
    days: int = Query(default=1, ge=1),
) -> list[dict]:
    tokens = _get_tokens()
    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=days)

    return get_all_invoices_metadata(
        tokens=tokens,
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
    )


@router.get("")
def get_invoices(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(
        default=None,
        min_length=2,
        max_length=100,
    ),
    subject_type: InvoiceSubjectType | None = None,
    currency: str | None = None,
    issue_date_from: date | None = None,
    issue_date_to: date | None = None,
):
    offset = (page - 1) * page_size
    filters = []

    if subject_type is not None:
        filters.append(col(InvoiceMetadata.subject_type) == subject_type)

    if currency is not None:
        filters.append(col(InvoiceMetadata.currency) == currency)

    if issue_date_from is not None:
        filters.append(col(InvoiceMetadata.issue_date) >= issue_date_from)

    if issue_date_to is not None:
        filters.append(col(InvoiceMetadata.issue_date) <= issue_date_to)

    similarity_rank = None

    if search:
        search = search.strip()
        pattern = f"%{search}%"

        similarity_rank = func.greatest(
            func.similarity(
                func.coalesce(col(InvoiceMetadata.invoice_number), ""),
                search,
            ),
            func.similarity(
                func.coalesce(col(InvoiceMetadata.seller_name), ""),
                search,
            ),
            func.similarity(
                func.coalesce(col(InvoiceMetadata.buyer_name), ""),
                search,
            ),
            func.similarity(
                func.coalesce(col(InvoiceMetadata.ksef_number), ""),
                search,
            ),
        )

        search_filter = or_(
            col(InvoiceMetadata.invoice_number).ilike(pattern),
            col(InvoiceMetadata.ksef_number).ilike(pattern),
            col(InvoiceMetadata.seller_nip).ilike(pattern),
            col(InvoiceMetadata.seller_name).ilike(pattern),
            col(InvoiceMetadata.buyer_identifier_value).ilike(pattern),
            col(InvoiceMetadata.buyer_name).ilike(pattern),
            func.similarity(
                col(InvoiceMetadata.invoice_number),
                search,
            ) >= 0.2,
            func.similarity(
                col(InvoiceMetadata.seller_name),
                search,
            ) >= 0.2,
            func.similarity(
                col(InvoiceMetadata.buyer_name),
                search,
            ) >= 0.2,
        )

        filters.append(search_filter)

    statement = select(InvoiceMetadata).where(*filters)

    if similarity_rank is not None:
        statement = statement.order_by(
            similarity_rank.desc(),
            col(InvoiceMetadata.issue_date).desc(),
        )
    else:
        statement = statement.order_by(
            col(InvoiceMetadata.issue_date).desc()
        )

    count_statement = (
        select(func.count())
        .select_from(InvoiceMetadata)
        .where(*filters)
    )

    total = session.exec(count_statement).one()
    invoices = session.exec(
        statement.offset(offset).limit(page_size)
    ).all()

    return {
        "items": invoices,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
@router.get("/{ksef_number}")
def get_invoice(ksef_number: str) -> str:
    tokens = _get_tokens()
    return get_invoice_by_num(tokens, ksef_number)
