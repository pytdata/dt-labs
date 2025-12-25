import base64
import datetime as dt
import hmac
import hashlib
import json
import time
from typing import Any, Iterable


class JWTError(Exception):
    """Exception raised for JWT validation errors."""


_ALGORITHMS = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding)
    except Exception as exc:  # pragma: no cover - defensive
        raise JWTError("Invalid base64 encoding") from exc


def _json_dumps(value: Any) -> bytes:
    def _default_encoder(obj: Any) -> int:
        if isinstance(obj, dt.datetime):
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=dt.timezone.utc)
            return int(obj.timestamp())
        if isinstance(obj, dt.date):
            return int(dt.datetime.combine(obj, dt.time()).replace(tzinfo=dt.timezone.utc).timestamp())
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    return json.dumps(value, separators=(",", ":"), sort_keys=True, default=_default_encoder).encode()


def _json_loads(data: str) -> dict[str, Any]:
    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise JWTError("Invalid JSON payload") from exc


def _get_signer(algorithm: str):
    try:
        return _ALGORITHMS[algorithm]
    except KeyError as exc:  # pragma: no cover - defensive
        raise JWTError(f"Unsupported algorithm: {algorithm}") from exc


def _get_secret_bytes(secret: str | bytes) -> bytes:
    return secret if isinstance(secret, bytes) else secret.encode()


def encode(payload: dict[str, Any], secret: str | bytes, algorithm: str = "HS256") -> str:
    signer = _get_signer(algorithm)
    header = {"alg": algorithm, "typ": "JWT"}

    encoded_header = _b64url_encode(_json_dumps(header))
    encoded_payload = _b64url_encode(_json_dumps(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode()

    signature = hmac.new(_get_secret_bytes(secret), signing_input, signer).digest()
    encoded_signature = _b64url_encode(signature)
    return ".".join([encoded_header, encoded_payload, encoded_signature])


def decode(token: str, secret: str | bytes, algorithms: Iterable[str] | str) -> dict[str, Any]:
    allowed_algorithms = {algorithms} if isinstance(algorithms, str) else set(algorithms)

    parts = token.split(".")
    if len(parts) != 3:
        raise JWTError("Invalid token format")

    encoded_header, encoded_payload, encoded_signature = parts
    header = _json_loads(_b64url_decode(encoded_header).decode())

    algorithm = header.get("alg")
    if algorithm not in allowed_algorithms:
        raise JWTError("Token signed with an unapproved algorithm")

    signer = _get_signer(algorithm)
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    expected_signature = hmac.new(_get_secret_bytes(secret), signing_input, signer).digest()

    if not hmac.compare_digest(expected_signature, _b64url_decode(encoded_signature)):
        raise JWTError("Invalid token signature")

    payload = _json_loads(_b64url_decode(encoded_payload).decode())
    exp = payload.get("exp")
    if exp is not None:
        try:
            exp_ts = float(exp)
        except (TypeError, ValueError) as exc:
            raise JWTError("Invalid exp claim") from exc
        if exp_ts < time.time():
            raise JWTError("Token has expired")

    return payload
