from apps.notifications.models import WhatsAppSettings


def configure_whatsapp(**fields):
    """Update the WhatsApp & alert settings singleton like the admin would."""
    WhatsAppSettings.load()
    config = WhatsAppSettings.objects.get(pk=1)
    for secret in ("access_token", "app_secret"):
        if secret in fields:
            setattr(config, secret, fields.pop(secret))
    for name in ("staff_alert_emails", "staff_alert_numbers"):
        if isinstance(fields.get(name), list | tuple):
            fields[name] = "\n".join(fields[name])
    for name, value in fields.items():
        setattr(config, name, value)
    config.save()
    return WhatsAppSettings.load()
