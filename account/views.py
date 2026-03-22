from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import *
from .serializers import *

User = get_user_model()


def _refresh_cookie_kwargs():
    refresh_lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    return {
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "path": "/auth/refresh/",
        "max_age": int(refresh_lifetime.total_seconds()),
    }


class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response: Response = super().post(request, *args, **kwargs)
        refresh = response.data.get("refresh") if response.data else None
        if refresh:
            response.set_cookie("refresh_token", refresh, **_refresh_cookie_kwargs())
            response.data.pop("refresh", None)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        if not data.get("refresh"):
            data["refresh"] = request.COOKIES.get("refresh_token", "")
        request._full_data = data
        response: Response = super().post(request, *args, **kwargs)
        refresh = response.data.get("refresh") if response.data else None
        if refresh:
            response.set_cookie("refresh_token", refresh, **_refresh_cookie_kwargs())
            response.data.pop("refresh", None)
        return response


class RegisterUserView(ListCreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer
class UserDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer
class RegisterShopOwnerView(ListCreateAPIView):
    queryset = User.objects.filter(role='SHOP_OWNER')
    permission_classes = [permissions.AllowAny]
    serializer_class = ShopOwnerSerializer
class RegisterSupplierView(ListCreateAPIView):
    queryset = User.objects.filter(role='SUPPLIER')
    permission_classes = [permissions.AllowAny]
    serializer_class = SupplierSerializer
class RegisterCourierView(ListCreateAPIView):
    queryset = User.objects.filter(role='COURIER')
    permission_classes = [permissions.AllowAny]
    serializer_class = CourierSerializer
class CreatePaymentMethodView(ListCreateAPIView):
    queryset = PaymentMethod.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentMethodSerializer
