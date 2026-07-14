import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def encrypt_token(token: str, timestamp_ms: int, certificate_base64: str) -> str:
    plaintext = f"{token}|{timestamp_ms}"
    der_bytes = base64.b64decode(certificate_base64)
    certificate = x509.load_der_x509_certificate(der_bytes)
    public_key = certificate.public_key()

    if not isinstance(public_key, rsa.RSAPublicKey):
        raise TypeError("Certificate does not contain an RSA public key")

    encrypted_token = public_key.encrypt(
        plaintext.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(encrypted_token).decode("utf-8")
