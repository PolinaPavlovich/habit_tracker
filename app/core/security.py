"""Verification of Telegram Mini App ``initData``.

Standard library only, and deliberately free of FastAPI imports: this module
answers "is this payload genuinely from Telegram, and who does it name?" and
nothing else. Translating a failure into an HTTP status is the dependency
layer's job, in :mod:`app.api.deps`.
"""

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import parse_qsl

import jwt


class InitDataError(Exception):
    """Raised when ``initData`` is malformed, unsigned, forged, or stale."""


@dataclass(frozen=True, slots=True)
class VerifiedTelegramUser:
    """A Telegram identity the signature check has vouched for.

    Only constructed after the HMAC matches, so ``telegram_id`` carries the
    same weight the ``X-Telegram-Id`` header does *behind* the shared secret —
    the caller did not get to choose it.
    """

    telegram_id: int
    username: str | None


@lru_cache(maxsize=4)
def _secret_key(bot_token: str) -> bytes:
    """Derive Telegram's signing key from the bot token.

    Note the inverted argument order: the literal ``WebAppData`` is the HMAC
    *key* and the bot token is the message, not the other way round. Getting
    this backwards produces a plausible-looking digest that never matches.
    """
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def _data_check_string(pairs: list[tuple[str, str]]) -> str:
    """Build the string Telegram signed: every field but ``hash``, sorted, newline joined."""
    return "\n".join(f"{key}={value}" for key, value in sorted(pairs) if key != "hash")


def verify_init_data(
    raw: str,
    *,
    bot_token: str,
    max_age_seconds: int,
    now: float | None = None,
) -> VerifiedTelegramUser:
    """Validate ``initData`` and return the identity it names.

    Raises :class:`InitDataError` for every failure — forged signature, missing
    field, stale timestamp — with no distinction between them. Callers must not
    tell a client which one it was: "bad hash" versus "expired" is a probing
    oracle.
    """
    try:
        pairs = parse_qsl(raw, strict_parsing=True, keep_blank_values=True)
    except ValueError as exc:
        raise InitDataError("initData is not a valid query string.") from exc

    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise InitDataError("initData contains duplicate fields.")

    fields = dict(pairs)
    received_hash = fields.get("hash")
    if not received_hash:
        raise InitDataError("initData carries no hash.")

    expected = hmac.new(
        _secret_key(bot_token),
        _data_check_string(pairs).encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("initData signature does not match.")

    try:
        auth_date = int(fields["auth_date"])
    except (KeyError, ValueError) as exc:
        raise InitDataError("initData has no usable auth_date.") from exc

    current = time.time() if now is None else now
    age = current - auth_date
    # A future timestamp means a forged or badly skewed payload. The 60s of
    # slack absorbs ordinary clock drift between Telegram and this host.
    if age < -60 or age > max_age_seconds:
        raise InitDataError("initData is outside its validity window.")

    try:
        user = json.loads(fields["user"])
        telegram_id = int(user["id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InitDataError("initData names no usable user.") from exc

    username = user.get("username")
    return VerifiedTelegramUser(
        telegram_id=telegram_id,
        username=username if isinstance(username, str) else None,
    )


class TokenError(Exception):
    """Raised when a TV access token is absent, malformed, expired, or foreign."""


JWT_ALGORITHM = "HS256"
JWT_ISSUER = "habit-tracker"
JWT_AUDIENCE_TV = "tv"


def create_tv_token(
    *,
    user_id: int,
    secret: str,
    ttl_seconds: int,
    now: int | None = None,
) -> str:
    """Mint the bearer token a Smart TV uses after its session is approved.

    ``sub`` is the *internal* user id, and it is the only identity in here. The
    Telegram id is deliberately absent: it has no business inside a token a TV
    keeps for a month — it would hand the account to anyone who read the
    device's storage — and nothing downstream joins on it anyway.

    There is no revocation list. Rotating ``jwt_secret`` invalidates every
    issued token at once, and that is the only kill switch — a deliberate
    trade, since the alternative is a database read on every request.
    """
    issued_at = int(time.time()) if now is None else now
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "iss": JWT_ISSUER,
        "typ": JWT_AUDIENCE_TV,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_tv_token(token: str, *, secret: str) -> int:
    """Return the internal user id a valid TV token names.

    The algorithm is pinned to a single value: leaving it open is how a token
    signed with ``alg: none`` — or one an attacker signed with the public half
    of an asymmetric pair — gets accepted.
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Token is not valid.") from exc

    if payload.get("typ") != JWT_AUDIENCE_TV:
        raise TokenError("Token is not a TV token.")
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("Token names no usable subject.") from exc
