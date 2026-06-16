from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

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
    queryset = User.objects.all()
    serializer_class = UserSerializer


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


class CreatePaymentMethodView(ListCreateAPIView):
    queryset = PaymentMethod.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentMethodSerializer


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
