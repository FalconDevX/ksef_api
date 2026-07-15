import time

import requests

from app.config import settings
from app.ksef.crypto import encrypt_token
from app.models.auth import Auth, Challenge, Token, TokenPair
SUBJECT_TYPES = (
    "Subject1",
    "Subject2",
    "Subject3",
    "SubjectAuthorized",
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

