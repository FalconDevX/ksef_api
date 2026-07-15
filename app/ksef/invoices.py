import time

import requests

from app.config import settings
from app.ksef.client import SUBJECT_TYPES
from app.models.auth import TokenPair

MAX_INVOICES_PER_SUBJECT = 100


def get_all_invoices_metadata(
    tokens: TokenPair,
    date_from: str,
    date_to: str,
) -> list[dict]:
    invoices_by_number: dict[str, dict] = {}

    for subject_type in SUBJECT_TYPES:
        invoices = get_invoices_metadata_for_subject(
            tokens=tokens,
            date_from=date_from,
            date_to=date_to,
            subject_type=subject_type,
        )

        for invoice in invoices:
            invoices_by_number[invoice["ksefNumber"]] = invoice

    return list(invoices_by_number.values())


def get_invoices_metadata_for_subject(
    tokens: TokenPair,
    date_from: str,
    date_to: str,
    subject_type: str,
    page_size: int = 100,
    max_records: int = MAX_INVOICES_PER_SUBJECT,
) -> list[dict]:
    invoices_by_number: dict[str, dict] = {}
    page_offset = 0
    retry_count = 0
    max_retries = 5

    payload = {
        "subjectType": subject_type,
        "dateRange": {
            "dateType": "PermanentStorage",
            "from": date_from,
            "to": date_to,
            "restrictToPermanentStorageHwmDate": True,
        },
        "sortOrder": "Asc",
    }

    headers = {
        "Authorization": f"Bearer {tokens.accessToken.token}",
    }

    while True:
        response = requests.post(
            f"{settings.ksef_base_url}/invoices/query/metadata",
            params={
                "pageOffset": page_offset,
                "pageSize": page_size,
            },
            headers=headers,
            json=payload,
            timeout=20,
        )

        if response.status_code == 429:
            retry_count += 1

            if retry_count > max_retries:
                raise RuntimeError(
                    "KSeF rate limit exceeded after multiple retries"
                )

            retry_after = int(response.headers.get("Retry-After", "10"))

            print(
                f"KSeF rate limit reached. "
                f"Waiting {retry_after} seconds..."
            )

            time.sleep(retry_after)
            continue

        response.raise_for_status()
        retry_count = 0

        data = response.json()

        for invoice in data.get("invoices", []):
            if len(invoices_by_number) >= max_records:
                break
            invoices_by_number[invoice["ksefNumber"]] = invoice

        print(
            f"{subject_type}: page {page_offset}, "
            f"received {len(data.get('invoices', []))} invoices, "
            f"total {len(invoices_by_number)}/{max_records}"
        )

        if len(invoices_by_number) >= max_records:
            break

        if not data.get("hasMore", False):
            break

        page_offset += 1

    return list(invoices_by_number.values())


def get_invoice_by_num(tokens: TokenPair, ksef_number: str) -> str:
    response = requests.get(
        f"{settings.ksef_base_url}/invoices/ksef/{ksef_number}",
        headers={"Authorization": f"Bearer {tokens.accessToken.token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.text


def get_invoice_bytes_by_num(
    tokens: TokenPair,
    ksef_number: str,
) -> bytes:
    response = requests.get(
        f"{settings.ksef_base_url}/invoices/ksef/{ksef_number}",
        headers={
            "Authorization": f"Bearer {tokens.accessToken.token}",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.content
