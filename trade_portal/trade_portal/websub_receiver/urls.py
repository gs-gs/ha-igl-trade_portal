from django.urls import path

from .views import (
    MessageThinPing, ConversationPingView,
)

app_name = "websub_receiver"
urlpatterns = [
    path(
        "messages/<str:sender_ref>/",
        view=MessageThinPing.as_view(),
        name="message-thin-ping"
    ),
    path(
        "conversation/<str:subject>/",
        view=ConversationPingView.as_view(),
        name="conversation-ping"
    ),
]
