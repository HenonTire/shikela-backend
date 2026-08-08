from django.urls import path
from .views import ShopSupplierDirectoryView

urlpatterns = [
    path("dashboard/", ShopSupplierDirectoryView.as_view(), name="shop-supplier-directory"),
]