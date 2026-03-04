from rest_framework import permissions
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied

from .models import *
from .serializers import *

# Create your views here.

class ShopListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
class ShopDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer

class CreateThemeView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer
class CreateThemeSettingsView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = ShopThemeSettings.objects.all()
    serializer_class = ShopThemeSettingsSerializer

    def perform_create(self, serializer):
        shop = getattr(self.request.user, "owned_shop", None)
        if not shop:
            raise PermissionDenied("Create a shop before setting theme settings.")
        if hasattr(shop, "theme_settings"):
            raise PermissionDenied("Theme settings already exist for this shop.")
        serializer.save(shop=shop)
    
