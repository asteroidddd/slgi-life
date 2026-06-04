from __future__ import annotations

import json
import logging
import os
import secrets
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

import jwt
from django.contrib.auth import login
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from jwt import PyJWKClient
from jwt.exceptions import (
    DecodeError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    PyJWKClientError,
)
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.profile.models import get_user_profile
from apps.accounts.social.models import SocialAccount
from apps.accounts.user.models import User


logger = logging.getLogger(__name__)

KAKAO_AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_ME_URL = "https://kapi.kakao.com/v2/user/me"
KAKAO_SSF_ISSUER = "https://kauth.kakao.com"
KAKAO_SSF_JWKS_URL = "https://kauth.kakao.com/.well-known/jwks.json"
KAKAO_EVENT_USER_LINKED = "https://schemas.openid.net/secevent/oauth/event-type/user-linked"
KAKAO_EVENT_USER_UNLINKED = "https://schemas.openid.net/secevent/oauth/event-type/user-unlinked"
KAKAO_EVENT_SCOPE_CONSENT = "https://schemas.openid.net/secevent/oauth/event-type/user-scope-consent"
KAKAO_EVENT_SCOPE_WITHDRAW = "https://schemas.openid.net/secevent/oauth/event-type/user-scope-withdraw"
_KAKAO_JWK_CLIENT = PyJWKClient(KAKAO_SSF_JWKS_URL, cache_jwk_set=True)


class KakaoWebhookValidationError(Exception):
    def __init__(self, err: str, description: str) -> None:
        self.err = err
        self.description = description
        super().__init__(description)


def _frontend_url(path: str = "") -> str:
    base = (os.environ.get("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
    if not path:
        return base
    return f"{base}/{path.lstrip('/')}"


def _redirect_frontend(path: str, **params: str) -> HttpResponseRedirect:
    query = urlencode({k: v for k, v in params.items() if v})
    suffix = f"?{query}" if query else ""
    return HttpResponseRedirect(f"{_frontend_url(path)}{suffix}")


def _kakao_redirect_uri() -> str:
    return (os.environ.get("KAKAO_REDIRECT_URI") or "").strip()


def _kakao_rest_api_key() -> str:
    return (os.environ.get("KAKAO_REST_API_KEY") or "").strip()


def _urlopen_json(req: UrlRequest, timeout: int = 8) -> dict:
    with urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))


def _exchange_kakao_code(code: str) -> str:
    data = urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": _kakao_rest_api_key(),
            "redirect_uri": _kakao_redirect_uri(),
            "code": code,
        }
    ).encode("utf-8")
    req = UrlRequest(
        KAKAO_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        method="POST",
    )
    payload = _urlopen_json(req)
    token = str(payload.get("access_token") or "")
    if not token:
        raise ValueError("Kakao token response has no access_token.")
    return token


def _fetch_kakao_user(access_token: str) -> dict:
    req = UrlRequest(
        KAKAO_USER_ME_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        },
    )
    return _urlopen_json(req)


def _unique_kakao_username(provider_user_id: str) -> str:
    base = f"kakao_{provider_user_id}"[:150]
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        tail = f"_{suffix}"
        username = f"{base[:150 - len(tail)]}{tail}"
        suffix += 1
    return username


def _get_or_create_kakao_user(*, provider_user_id: str, nickname: str) -> User:
    social = SocialAccount.objects.select_related("user").filter(
        provider=SocialAccount.PROVIDER_KAKAO,
        provider_user_id=provider_user_id,
    ).first()
    if social:
        user = social.user
        profile = get_user_profile(user)
        update_profile_fields: list[str] = []
        if nickname and not profile.nickname:
            profile.nickname = nickname[:30]
            update_profile_fields.append("nickname")
        if update_profile_fields:
            profile.save(update_fields=update_profile_fields)
        social.nickname = nickname
        social.save(update_fields=["nickname", "updated_at"])
        return user

    user = User(username=_unique_kakao_username(provider_user_id), email="")
    user.set_unusable_password()
    user.save()
    profile = get_user_profile(user)
    if nickname:
        profile.nickname = nickname[:30]
        profile.save(update_fields=["nickname"])
    SocialAccount.objects.create(
        user=user,
        provider=SocialAccount.PROVIDER_KAKAO,
        provider_user_id=provider_user_id,
        email="",
        nickname=nickname,
    )
    return user


def _decode_kakao_security_event_token(token: str) -> dict:
    if not token or token.count(".") != 2:
        raise KakaoWebhookValidationError("invalid_request", "SET is not a valid JWT.")
    if not _kakao_rest_api_key():
        raise KakaoWebhookValidationError("invalid_audience", "Kakao REST API key is not configured.")
    try:
        header = jwt.get_unverified_header(token)
    except DecodeError as exc:
        raise KakaoWebhookValidationError("invalid_request", "SET header is invalid.") from exc
    if header.get("alg") != "RS256" or header.get("typ") != "secevent+jwt":
        raise KakaoWebhookValidationError("invalid_request", "SET header is not supported.")
    try:
        signing_key = _KAKAO_JWK_CLIENT.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=_kakao_rest_api_key(),
            issuer=KAKAO_SSF_ISSUER,
            options={"require": ["iss", "aud", "sub", "iat", "jti", "events"]},
        )
    except InvalidIssuerError as exc:
        raise KakaoWebhookValidationError("invalid_issuer", "SET issuer is invalid.") from exc
    except InvalidAudienceError as exc:
        raise KakaoWebhookValidationError("invalid_audience", "SET audience is invalid.") from exc
    except (PyJWKClientError, InvalidSignatureError) as exc:
        raise KakaoWebhookValidationError("invalid_key", "SET signature key is invalid.") from exc
    except InvalidTokenError as exc:
        raise KakaoWebhookValidationError("invalid_request", "SET is invalid.") from exc
    if not isinstance(payload.get("events"), dict):
        raise KakaoWebhookValidationError("invalid_request", "SET events payload is invalid.")
    return payload


def _event_subject_sub(payload: dict, event_payload: object) -> str:
    if isinstance(event_payload, dict):
        subject = event_payload.get("subject")
        if isinstance(subject, dict) and subject.get("sub"):
            return str(subject["sub"])
    return str(payload.get("sub") or "")


def _clear_kakao_email(provider_user_id: str) -> None:
    social = SocialAccount.objects.select_related("user").filter(
        provider=SocialAccount.PROVIDER_KAKAO,
        provider_user_id=provider_user_id,
    ).first()
    if not social:
        return
    user = social.user
    social.email = ""
    social.save(update_fields=["email", "updated_at"])
    if user.email:
        user.email = ""
        user.save(update_fields=["email"])


def _delete_kakao_user(provider_user_id: str) -> int:
    social = SocialAccount.objects.select_related("user").filter(
        provider=SocialAccount.PROVIDER_KAKAO,
        provider_user_id=provider_user_id,
    ).first()
    if not social:
        return 0
    user = social.user
    user.delete()
    return 1


def _handle_kakao_webhook_payload(payload: dict) -> None:
    events = payload.get("events") or {}
    for event_type, event_payload in events.items():
        provider_user_id = _event_subject_sub(payload, event_payload)
        if not provider_user_id:
            continue
        if event_type == KAKAO_EVENT_USER_UNLINKED:
            deleted = _delete_kakao_user(provider_user_id)
            logger.info("kakao webhook user_unlinked processed deleted=%s", deleted)
        elif event_type == KAKAO_EVENT_SCOPE_WITHDRAW:
            logger.info("kakao webhook scope_withdraw accepted")
        elif event_type in {KAKAO_EVENT_USER_LINKED, KAKAO_EVENT_SCOPE_CONSENT}:
            logger.info("kakao webhook event accepted event_type=%s", event_type.rsplit("/", 1)[-1])
        else:
            logger.info("kakao webhook unsupported event ignored event_type=%s", event_type)


@extend_schema(tags=["auth"], summary="Start Kakao login")
@method_decorator(csrf_exempt, name="dispatch")
class KakaoStartView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request: Request) -> HttpResponseRedirect:
        if not _kakao_rest_api_key() or not _kakao_redirect_uri():
            return _redirect_frontend("login", error="kakao_not_configured")
        state = secrets.token_urlsafe(24)
        request.session["kakao_oauth_state"] = state
        params = {
            "client_id": _kakao_rest_api_key(),
            "redirect_uri": _kakao_redirect_uri(),
            "response_type": "code",
            "state": state,
        }
        return HttpResponseRedirect(f"{KAKAO_AUTHORIZE_URL}?{urlencode(params)}")


@extend_schema(tags=["auth"], summary="Kakao login callback")
@method_decorator(csrf_exempt, name="dispatch")
class KakaoCallbackView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request: Request) -> HttpResponseRedirect:
        error = str(request.query_params.get("error") or "")
        if error:
            return _redirect_frontend("login", error="kakao_cancelled")
        code = str(request.query_params.get("code") or "")
        state = str(request.query_params.get("state") or "")
        expected_state = str(request.session.pop("kakao_oauth_state", "") or "")
        if not code or not state or state != expected_state:
            return _redirect_frontend("login", error="kakao_state_invalid")

        try:
            access_token = _exchange_kakao_code(code)
            payload = _fetch_kakao_user(access_token)
            provider_user_id = str(payload.get("id") or "")
            kakao_account = payload.get("kakao_account") or {}
            profile = kakao_account.get("profile") or {}
            nickname = str(profile.get("nickname") or "").strip()
            if not provider_user_id:
                return _redirect_frontend("login", error="kakao_user_missing")
            with transaction.atomic():
                user = _get_or_create_kakao_user(
                    provider_user_id=provider_user_id,
                    nickname=nickname,
                )
            if not user.is_active:
                return _redirect_frontend("login", error="inactive_user")
            login(request, user)
            return _redirect_frontend("login")
        except Exception:
            return _redirect_frontend("login", error="kakao_failed")


@extend_schema(tags=["auth"], summary="Kakao account status webhook")
@method_decorator(csrf_exempt, name="dispatch")
class KakaoWebhookView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        token = (request.body or b"").decode("utf-8", errors="replace").strip()
        try:
            payload = _decode_kakao_security_event_token(token)
            with transaction.atomic():
                _handle_kakao_webhook_payload(payload)
        except KakaoWebhookValidationError as exc:
            return Response(
                {"err": exc.err, "description": exc.description},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_202_ACCEPTED)
