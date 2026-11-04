from django.urls import path

from .views import (
    InboxMarkReadView,
    InboxUnreadCountView,
    InboxView,
    NotificationPreferenceView,
    WhatsAppWebhookView,
)

app_name = "notifications"

urlpatterns = [
    path("preferences/", NotificationPreferenceView.as_view(), name="preferences"),
    path("inbox/", InboxView.as_view(), name="inbox"),
    path("inbox/unread-count/", InboxUnreadCountView.as_view(), name="inbox-unread-count"),
    path("inbox/read/", InboxMarkReadView.as_view(), name="inbox-read"),
    path("whatsapp/webhook/", WhatsAppWebhookView.as_view(), name="whatsapp-webhook"),
]
