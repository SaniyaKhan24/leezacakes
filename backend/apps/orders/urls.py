from django.urls import path

from .views import (
    CustomerOrderDetailView,
    CustomerOrderListCreateView,
    StaffOrderDetailView,
    StaffOrderListView,
    StaffOrderTransitionView,
)

app_name = "orders"
urlpatterns = [
    path("", CustomerOrderListCreateView.as_view(), name="orders"),
    path("<uuid:order_id>/", CustomerOrderDetailView.as_view(), name="order-detail"),
    path("staff/", StaffOrderListView.as_view(), name="staff-orders"),
    path("staff/<uuid:order_id>/", StaffOrderDetailView.as_view(), name="staff-order-detail"),
    path(
        "staff/<uuid:order_id>/transitions/",
        StaffOrderTransitionView.as_view(),
        name="staff-order-transition",
    ),
]
