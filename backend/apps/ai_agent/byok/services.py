from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from apps.ai_agent.models import UserAIAPIKey


UNLOCK_TTL_SECONDS = 30 * 60
PROVIDERS = {UserAIAPIKey.PROVIDER_OPENAI, UserAIAPIKey.PROVIDER_MINDLOGIC}
STALE_KEY_DAYS = 7


class BYOKError(Exception):
    code = "BYOK_ERROR"


class PassphraseRequired(BYOKError):
    code = "AI_API_KEY_LOCKED"


class InvalidPassphrase(BYOKError):
    code = "AI_API_KEY_UNLOCK_FAILED"


@dataclass(frozen=True)
class ProviderCredential:
    provider: str
    api_key: str
    base_url: str | None


def mask_key(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + ("*" * (len(value) - 4)) + value[-2:]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("ascii"))


def _derive(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 210_000, dklen=32)


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < length:
        chunks.append(hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    return b"".join(chunks)[:length]


def encrypt_api_key(api_key: str, passphrase: str) -> dict[str, str]:
    salt = os.urandom(16)
    nonce = os.urandom(16)
    key = _derive(passphrase, salt)
    plaintext = api_key.encode("utf-8")
    stream = _keystream(key, nonce, len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream, strict=True))
    tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return {
        "encrypted_api_key": _b64(ciphertext),
        "salt": _b64(salt),
        "nonce": _b64(nonce),
        "tag": _b64(tag),
    }


def decrypt_api_key(record: UserAIAPIKey, passphrase: str) -> str:
    salt = _unb64(record.salt)
    nonce = _unb64(record.nonce)
    ciphertext = _unb64(record.encrypted_api_key)
    expected_tag = _unb64(record.tag)
    key = _derive(passphrase, salt)
    actual_tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(actual_tag, expected_tag):
        raise InvalidPassphrase("Invalid passphrase.")
    stream = _keystream(key, nonce, len(ciphertext))
    plaintext = bytes(a ^ b for a, b in zip(ciphertext, stream, strict=True))
    return plaintext.decode("utf-8")


def cache_key(user_id: int, provider: str) -> str:
    return f"ai-byok:{user_id}:{provider}"


def save_user_key(*, user, provider: str, api_key: str, passphrase: str, priority: int) -> UserAIAPIKey:
    if provider not in PROVIDERS:
        raise ValueError("Unsupported provider.")
    encrypted = encrypt_api_key(api_key, passphrase)
    record, _ = UserAIAPIKey.objects.update_or_create(
        user=user,
        provider=provider,
        defaults={
            **encrypted,
            "masked_key": mask_key(api_key),
            "priority": max(1, int(priority)),
        },
    )
    cache.set(cache_key(user.id, provider), api_key, timeout=UNLOCK_TTL_SECONDS)
    return record


def unlock_user_keys(*, user, passphrase: str) -> list[str]:
    unlocked: list[str] = []
    for record in UserAIAPIKey.objects.filter(user=user).order_by("priority", "provider"):
        api_key = decrypt_api_key(record, passphrase)
        cache.set(cache_key(user.id, record.provider), api_key, timeout=UNLOCK_TTL_SECONDS)
        unlocked.append(record.provider)
    return unlocked


def status_for_user(user) -> list[dict]:
    records = {record.provider: record for record in UserAIAPIKey.objects.filter(user=user)}
    items = []
    for provider in (UserAIAPIKey.PROVIDER_MINDLOGIC, UserAIAPIKey.PROVIDER_OPENAI):
        record = records.get(provider)
        items.append(
            {
                "provider": provider,
                "configured": bool(record),
                "priority": record.priority if record else None,
                "masked_key": record.masked_key if record else "",
                "unlocked": bool(record and cache.get(cache_key(user.id, provider))),
            }
        )
    return items


def provider_base_url(provider: str) -> str | None:
    if provider == UserAIAPIKey.PROVIDER_MINDLOGIC:
        return os.environ.get("AI_AGENT_OPENAI_BASE_URL") or None
    return None


def get_unlocked_credentials(user) -> list[ProviderCredential]:
    credentials: list[ProviderCredential] = []
    for record in UserAIAPIKey.objects.filter(user=user).order_by("priority", "provider"):
        api_key = cache.get(cache_key(user.id, record.provider))
        if api_key:
            credentials.append(
                ProviderCredential(
                    provider=record.provider,
                    api_key=str(api_key),
                    base_url=provider_base_url(record.provider),
                )
            )
    if not credentials:
        raise PassphraseRequired("No unlocked AI API key.")
    return credentials


def purge_stale_user_keys(days: int = STALE_KEY_DAYS) -> int:
    cutoff = timezone.now() - timezone.timedelta(days=days)
    deleted, _ = UserAIAPIKey.objects.filter(
        Q(user__last_login__isnull=True) | Q(user__last_login__lt=cutoff)
    ).delete()
    return int(deleted)
