from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView, PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from shop.models import Shop

from .models import *
from .serializers import *
from .services import send_verification_email

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
    serializer_class = EmailVerificationTokenObtainPairSerializer

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


class RegisterUserWithEmailVerificationMixin:
    def perform_create(self, serializer):
        user = serializer.save()
        send_verification_email(user=user, request=self.request)


class RegisterUserView(RegisterUserWithEmailVerificationMixin, ListCreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer


class UserDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        # Staff users can access all users; regular users only their own record
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(pk=user.pk)


class RegisterShopOwnerView(RegisterUserWithEmailVerificationMixin, ListCreateAPIView):
    queryset = User.objects.filter(role='SHOP_OWNER')
    permission_classes = [permissions.AllowAny]
    serializer_class = ShopOwnerSerializer


class RegisterSupplierView(RegisterUserWithEmailVerificationMixin, ListCreateAPIView):
    queryset = User.objects.filter(role='SUPPLIER')
    permission_classes = [permissions.AllowAny]
    serializer_class = SupplierSerializer


class RegisterCourierView(RegisterUserWithEmailVerificationMixin, ListCreateAPIView):
    queryset = User.objects.filter(role='COURIER')
    permission_classes = [permissions.AllowAny]
    serializer_class = CourierSerializer


class MyPaymentMethodsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        methods = PaymentMethod.objects.filter(shop_owner=request.user)
        data = {m.payment_type.lower(): PaymentMethodSerializer(m).data for m in methods}
        for key in ('bank', 'telebirr'):
            data.setdefault(key, None)
        return Response(data)


class PaymentMethodView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _normalized_type(self, payment_type):
        normalized = payment_type.upper()
        if normalized not in dict(PaymentMethod.PAYMENT_CHOICES):
            return None
        return normalized

    def get(self, request, payment_type):
        normalized = self._normalized_type(payment_type)
        if normalized is None:
            return Response({"detail": "Invalid payment type."}, status=status.HTTP_400_BAD_REQUEST)

        method = PaymentMethod.objects.filter(shop_owner=request.user, payment_type=normalized).first()
        if not method:
            return Response({"detail": "No payment method set."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentMethodSerializer(method).data)

    def put(self, request, payment_type):
        normalized = self._normalized_type(payment_type)
        if normalized is None:
            return Response({"detail": "Invalid payment type."}, status=status.HTTP_400_BAD_REQUEST)

        defaults = {}
        if normalized == "BANK":
            provider_name = str(request.data.get('provider_name', '')).strip()
            account_number = str(request.data.get('account_number', '')).strip()
            if not provider_name or not account_number:
                return Response(
                    {"detail": "provider_name and account_number are required for bank."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            defaults = {'provider_name': provider_name, 'account_number': account_number, 'is_verified': False}
        elif normalized == "TELEBIRR":
            phone_number = str(request.data.get('phone_number', '')).strip()
            if not phone_number:
                return Response({"phone_number": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
            defaults = {'phone_number': phone_number, 'is_verified': False}
        else:
            return Response({"detail": "This payment type isn't supported yet."}, status=status.HTTP_400_BAD_REQUEST)

        method, _ = PaymentMethod.objects.update_or_create(
            shop_owner=request.user,
            payment_type=normalized,
            defaults=defaults,
        )
        return Response(PaymentMethodSerializer(method).data)
        

    def delete(self, request, payment_type):
        normalized = self._normalized_type(payment_type)
        if normalized is None:
            return Response({"detail": "Invalid payment type."}, status=status.HTTP_400_BAD_REQUEST)

        PaymentMethod.objects.filter(shop_owner=request.user, payment_type=normalized).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        uid = request.query_params.get("uid")
        token = request.query_params.get("token")
        if not uid or not token:
            return Response({"detail": "Missing uid or token."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired verification link."}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_verified:
            return Response({"detail": "Email is already verified."}, status=status.HTTP_200_OK)

        user.is_verified = True
        user.save(update_fields=["is_verified", "updated_at"])
        return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)


class ResendVerificationEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ResendVerificationEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email).first()
        if user and not user.is_verified:
            send_verification_email(user=user, request=request)

        return Response(
            {"detail": "If an account with that email exists, a verification email has been sent."},
            status=status.HTTP_200_OK,
        )
class UserMeView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
  # add to existing import if not present
class MyAddressesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        data = {a.address_type.lower(): AddressSerializer(a).data for a in addresses}
        for key in ('shipping', 'billing'):
            data.setdefault(key, None)
        return Response(data)


class AddressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _normalized_type(self, address_type):
        normalized = address_type.upper()
        if normalized not in dict(Address.ADDRESS_TYPE_CHOICES):
            return None
        return normalized

    def get(self, request, address_type):
        normalized = self._normalized_type(address_type)
        if normalized is None:
            return Response({"detail": "Invalid address type."}, status=status.HTTP_400_BAD_REQUEST)

        address = Address.objects.filter(user=request.user, address_type=normalized).first()
        if not address:
            return Response({"detail": "No address set."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AddressSerializer(address).data)

    def put(self, request, address_type):
        normalized = self._normalized_type(address_type)
        if normalized is None:
            return Response({"detail": "Invalid address type."}, status=status.HTTP_400_BAD_REQUEST)

        full_address = str(request.data.get('full_address', '')).strip()
        if not full_address:
            return Response({"full_address": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        address, _ = Address.objects.update_or_create(
            user=request.user,
            address_type=normalized,
            defaults={'full_address': full_address},
        )
        return Response(AddressSerializer(address).data)

    def delete(self, request, address_type):
        normalized = self._normalized_type(address_type)
        if normalized is None:
            return Response({"detail": "Invalid address type."}, status=status.HTTP_400_BAD_REQUEST)

        Address.objects.filter(user=request.user, address_type=normalized).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ShopDeliverySettingsMeView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShopDeliverySettingsSerializer

    def get_object(self):
        shop = getattr(self.request.user, "owned_shop", None)
        if not shop:
            raise PermissionDenied("You don't own a shop yet.")
        settings, _ = ShopDeliverySettings.objects.get_or_create(shop=shop)
        return settings
class NotificationSettingsMeView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSettingsSerializer

    def get_object(self):
        settings, _ = NotificationSettings.objects.get_or_create(user=self.request.user)
        return settings