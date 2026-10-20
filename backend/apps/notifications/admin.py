from django.contrib import admin

from .models import DeliveryAttempt, Notification, NotificationPreference

admin.site.register((Notification, DeliveryAttempt, NotificationPreference))
