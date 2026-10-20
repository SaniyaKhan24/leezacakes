from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", include("apps.common.urls")),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/catalog/", include("apps.catalog.urls")),
    path("api/v1/customization/", include("apps.customization.urls")),
    path("api/v1/cart/", include("apps.cart.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/search/", include("apps.search.urls")),
]
if settings.API_DOCS_ENABLED:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"
        ),
        path("api/docs/scalar/", TemplateView.as_view(template_name="scalar.html"), name="scalar"),
    ]
