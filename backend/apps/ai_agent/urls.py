from django.urls import path

from .views import agent_query

app_name = "ai_agent"

urlpatterns = [
    path("agent/query", agent_query, name="agent-query"),
]
