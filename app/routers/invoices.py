from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.ksef.client import (
    auth,
    get_all_invoices_metadata,
    get_invoice_by_num,
    redeem_token,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _get_tokens():
    return redeem_token(auth())


@router.get("/metadata")
def list_invoice_metadata(
    days: int = Query(default=1, ge=1),
    subject_type: str = Query(default="Subject1"),
) -> list[dict]:
    tokens = _get_tokens()
    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=days)

    return get_all_invoices_metadata(
        tokens=tokens,
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        subject_type=subject_type,
    )


@router.get("/{ksef_number}")
def get_invoice(ksef_number: str) -> str:
    tokens = _get_tokens()
    return get_invoice_by_num(tokens, ksef_number)
