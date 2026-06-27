"""Minimal stdlib HS256 JWT encoder (no PyJWT dependency).

Issue-only: fleet-api signs a portable token at login. Verifying a Bearer token
to derive a CallerContext is deferred to the mobile feature.
"""
import base64
import hashlib
import hmac
import json


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def encode_jwt(claims: dict, secret: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = _b64url(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"
