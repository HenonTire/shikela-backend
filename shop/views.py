from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

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

    def _get_owned_shop(self):
        shop = getattr(self.request.user, "owned_shop", None)
        if not shop:
            raise PermissionDenied("Create a shop before setting theme settings.")
        return shop

    def get(self, request, *args, **kwargs):
        shop = self._get_owned_shop()
        if not hasattr(shop, "theme_settings"):
            return Response(
                {"detail": "Theme settings not found for this shop."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(shop.theme_settings)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        shop = self._get_owned_shop()
        if not hasattr(shop, "theme_settings"):
            return Response(
                {"detail": "Theme settings not found for this shop."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(
            shop.theme_settings,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def perform_create(self, serializer):
        shop = self._get_owned_shop()
        if hasattr(shop, "theme_settings"):
            raise PermissionDenied("Theme settings already exist for this shop.")
        serializer.save(shop=shop)
    
