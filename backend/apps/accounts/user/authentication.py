from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):  # type: ignore[no-untyped-def]
        return


class AuthRequiredMixin:
    authentication_classes = [CsrfExemptSessionAuthentication]
    UNAUTH_DETAIL = "Login is required."

    def dispatch(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        drf_request = self.initialize_request(request, *args, **kwargs)
        self.request = drf_request
        self.headers = self.default_response_headers
        try:
            self.initial(drf_request, *args, **kwargs)
            if not drf_request.user.is_authenticated:
                response = Response({"detail": self.UNAUTH_DETAIL}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
                response = handler(drf_request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)
        self.response = self.finalize_response(drf_request, response, *args, **kwargs)
        return self.response
