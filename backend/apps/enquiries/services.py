from django.db import transaction

from .models import Enquiry


@transaction.atomic
def create_enquiry(**data):
    return Enquiry.objects.create(**data)


def set_status(queryset, status):
    return queryset.exclude(status=status).update(status=status)
