from django.urls import path

from .views import AIAPIKeyDetailView, AIAPIKeyUnlockView, AIAPIKeyView, agent_query

app_name = "ai_agent"

urlpatterns = [
    path("agent/query", agent_query, name="agent-query"),
    path("agent/api-keys", AIAPIKeyView.as_view(), name="agent-api-keys"),
    path("agent/api-keys/unlock", AIAPIKeyUnlockView.as_view(), name="agent-api-keys-unlock"),
    path("agent/api-keys/<str:provider>", AIAPIKeyDetailView.as_view(), name="agent-api-key-detail"),
]
