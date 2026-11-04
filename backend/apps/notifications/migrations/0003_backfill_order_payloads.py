"""Fill order fields into notification payloads written before the inbox existed.

Older rows only stored ``order_number``; the inbox renders links and copy from
``order_id``, ``customer_name``, ``grand_total`` and ``pickup``.
"""

from django.db import migrations


def backfill(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Order = apps.get_model("orders", "Order")
    for notification in Notification.objects.exclude(payload__has_key="order_id").iterator():
        payload = dict(notification.payload or {})
        number = payload.get("order_number")
        if not number:
            continue
        order = Order.objects.filter(order_number=number).first()
        if order is None:
            # seed_demo re-dates order numbers (LZ-<date>-<suffix>); match on the suffix.
            suffix = number.rpartition("-")[2]
            matches = list(Order.objects.filter(order_number__endswith=f"-{suffix}")[:2])
            order = matches[0] if len(matches) == 1 else None
        if order is None:
            continue
        payload.update(
            {
                "order_id": str(order.pk),
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "grand_total": None if order.grand_total is None else str(order.grand_total),
                "pickup": order.pickup_slot_start.isoformat(),
            }
        )
        notification.payload = payload
        notification.save(update_fields=["payload"])


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_inbox_audience_and_delivery_recipient"),
        ("orders", "0001_initial"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
