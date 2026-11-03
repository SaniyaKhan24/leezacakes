from .models import Cart


def active_cart_for_request(request):
    """Return the request's active cart without creating a cart or a session."""
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user, status=Cart.ACTIVE).first()
    session_key = request.session.session_key
    if not session_key:
        return None
    return Cart.objects.filter(session_key=session_key, status=Cart.ACTIVE).first()


# Backwards-compatible name.
owned_cart = active_cart_for_request
