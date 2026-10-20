from .models import Cart


def owned_cart(request):
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user, status=Cart.ACTIVE).first()
    return Cart.objects.filter(session_key=request.session.session_key, status=Cart.ACTIVE).first()
