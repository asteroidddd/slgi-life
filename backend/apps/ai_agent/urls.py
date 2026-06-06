from django.urls import path

from .views import (
    AIContextPreferenceView,
    agent_query,
    clear_conversation,
    demo_visualization_response,
)

app_name = "ai_agent"

urlpatterns = [
    path("agent/query", agent_query, name="agent-query"),
    path("agent/demo/visualization", demo_visualization_response, name="agent-demo-visualization"),
    path("agent/conversation/<str:conversation_id>", clear_conversation, name="agent-conversation-clear"),
    path("agent/context-preferences", AIContextPreferenceView.as_view(), name="agent-context-preferences"),
]
