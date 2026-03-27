from django.urls import path

from .views import (
    CourierShipmentDetailView,
    CourierShipmentListView,
    CourierShipmentStatusUpdateView,
)


urlpatterns = [
    path("shipments/", CourierShipmentListView.as_view(), name="courier-shipment-list"),
    path("shipments/<uuid:pk>/", CourierShipmentDetailView.as_view(), name="courier-shipment-detail"),
    path("shipments/<uuid:pk>/status/", CourierShipmentStatusUpdateView.as_view(), name="courier-shipment-status"),
]
