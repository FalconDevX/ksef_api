import time
import requests

from app.config import settings
from app.ksef.crypto import encrypt_token
from app.models.auth import Auth, Challenge, Token, TokenPair

SUBJECT_TYPES = (
    "Subject1",
    # "Subject2",
    # "Subject3",
    # "SubjectAuthorized",
)

def get_auth_challenge() -> Challenge:
    response = requests.post(f"{settings.ksef_base_url}/auth/challenge", timeout=20)
    response.raise_for_status()

    data = response.json()
    return Challenge(
        challenge=data["challenge"],
        timestamp_ms=data["timestampMs"],
    )


def get_public_key_certificates() -> list[dict]:
    response = requests.get(
        f"{settings.ksef_base_url}/security/public-key-certificates",
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def auth_ksef_token(
    challenge: Challenge,
    encrypted_token: str,
    context_identifier_value: str,
) -> dict:
    payload = {
        "challenge": challenge.challenge,
        "contextIdentifier": {
            "type": "Nip",
            "value": context_identifier_value,
        },
        "encryptedToken": encrypted_token,
    }

    response = requests.post(
        f"{settings.ksef_base_url}/auth/ksef-token",
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def auth() -> Auth:
    challenge = get_auth_challenge()
    certificates = get_public_key_certificates()

    token_certificate = next(
        certificate
        for certificate in certificates
        if "KsefTokenEncryption" in certificate["usage"]
    )

    encrypted_token = encrypt_token(
        token=settings.ksef_token,
        timestamp_ms=challenge.timestamp_ms,
        certificate_base64=token_certificate["certificate"],
    )

    data = auth_ksef_token(
        challenge=challenge,
        encrypted_token=encrypted_token,
        context_identifier_value=settings.ksef_nip,
    )

    return Auth(
        refNum=data["referenceNumber"],
        authToken=data["authenticationToken"]["token"],
    )


def get_auth_status(auth_data: Auth) -> dict:
    response = requests.get(
        f"{settings.ksef_base_url}/auth/{auth_data.refNum}",
        headers={"Authorization": f"Bearer {auth_data.authToken}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()

def wait_for_auth(
    auth_data: Auth,
    max_attempts: int = 10,
) -> None:
    for _ in range(max_attempts):
        data = get_auth_status(auth_data)
        status_code = data["status"]["code"]

        if status_code == 200:
            return

        if status_code >= 400:
            raise RuntimeError(
                f"Authentication failed: {data['status']}"
            )

        time.sleep(1)

    raise TimeoutError("Authentication did not finish in time")


def redeem_token(auth_data: Auth) -> TokenPair:
    response = requests.post(
        f"{settings.ksef_base_url}/auth/token/redeem",
        headers={"Authorization": f"Bearer {auth_data.authToken}"},
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    return TokenPair(
        accessToken=Token(
            token=data["accessToken"]["token"],
            validUntil=data["accessToken"]["validUntil"],
        ),
        refreshToken=Token(
            token=data["refreshToken"]["token"],
            validUntil=data["refreshToken"]["validUntil"],
        ),
    )


def refresh_token(tokens: TokenPair) -> dict:
    response = requests.post(
        f"{settings.ksef_base_url}/auth/token/refresh",
        headers={"Authorization": f"Bearer {tokens.refreshToken.token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()

def get_all_invoices_metadata(
    tokens: TokenPair,
    date_from: str,
    date_to: str
) -> list[dict]:
    
    invoices_by_number: dict[str, dict] = {}
    
    for subject_type in SUBJECT_TYPES:
        invoices = get_invoices_metadata_for_subject(
            tokens=tokens,
            date_from=date_from,
            date_to=date_to,
            subject_type=subject_type,
        )

        #if there will be the same invoice only one will be saved
        for invoice in invoices:
            invoices_by_number[invoice["ksefNumber"]] = invoice

    return list(invoices_by_number.values())


import time
import requests


def get_invoices_metadata_for_subject(
    tokens: TokenPair,
    date_from: str,
    date_to: str,
    subject_type: str,
    page_size: int = 100,
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
            invoices_by_number[invoice["ksefNumber"]] = invoice

        print(
            f"{subject_type}: page {page_offset}, "
            f"received {len(data.get('invoices', []))} invoices"
        )

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
