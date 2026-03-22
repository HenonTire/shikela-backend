

from django.contrib import admin
from django.urls import path, include



urlpatterns = [
    path("admin/", admin.site.urls),
    path('auth/', include('account.urls')),
    path('shops/', include('shop.urls')),
    path('catalog/', include('catalog.urls')),
    path('hub/', include('hub.urls')),
    path('order/', include('order.urls')),
    path('payment/', include('payment.urls')),
    path('logistics/', include('courier.urls')),
    path('supliers/', include('supliers.urls')),
    path('marketer/', include('marketer.urls')),
    path('analytics/', include('analytics.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('inventory/', include('inventory.urls')),
]
