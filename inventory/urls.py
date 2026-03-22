from django.urls import path
from .views import *

urlpatterns = [
    path("locations/", LocationListCreateView.as_view(), name="inventory-location-list-create"),
    path("locations/<int:pk>/", LocationDetailView.as_view(), name="inventory-location-detail"),
    path("items/", InventoryListCreateView.as_view(), name="inventory-item-list-create"),
    path("items/<int:pk>/", InventoryDetailView.as_view(), name="inventory-item-detail"),
    path("items/<int:pk>/actions/", InventoryActionView.as_view(), name="inventory-item-actions"),
    path("movements/", StockMovementListCreateView.as_view(), name="inventory-movement-list-create"),
]
