from .services import dispatch_notification


def deliver_notification(notification_id):
    dispatch_notification(notification_id)
