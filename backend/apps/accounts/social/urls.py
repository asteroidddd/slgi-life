from django.urls import path

from apps.accounts.social.views import KakaoCallbackView, KakaoStartView, KakaoWebhookView

urlpatterns = [
    path("auth/kakao/start", KakaoStartView.as_view(), name="auth-kakao-start"),
    path("auth/kakao/callback", KakaoCallbackView.as_view(), name="auth-kakao-callback"),
    path("auth/kakao/webhook", KakaoWebhookView.as_view(), name="auth-kakao-webhook"),
]
