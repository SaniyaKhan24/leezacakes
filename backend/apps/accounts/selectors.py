from .models import Address


def user_addresses(user):
    return Address.objects.filter(user=user)


def owned_address(user, address_id):
    return Address.objects.filter(user=user, pk=address_id).first()
