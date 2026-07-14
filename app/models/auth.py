from dataclasses import dataclass


@dataclass
class Token:
    token: str
    validUntil: str


@dataclass
class TokenPair:
    accessToken: Token
    refreshToken: Token


@dataclass
class Challenge:
    challenge: str
    timestamp_ms: int


@dataclass
class Auth:
    refNum: str
    authToken: str
