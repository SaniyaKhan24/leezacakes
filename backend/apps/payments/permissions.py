from rest_framework.permissions import BasePermission


class PaymentVerifierPermission(BasePermission):
    message = "Payment verification permission is required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.has_perm("payments.verify_payment"))
        )
