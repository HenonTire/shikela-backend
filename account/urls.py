from django.urls import path
from .views import *

urlpatterns = [
    path("register/", RegisterUserView.as_view(), name="register"),
    path("login/", CookieTokenObtainPairView.as_view(), name="login"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="refresh"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationEmailView.as_view(), name="resend-verification"),
    path("user/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("register-shop-owner/", RegisterShopOwnerView.as_view(), name="register-shop-owner"),
    path("register-supplier/", RegisterSupplierView.as_view(), name="register-supplier"),
    path("register-courier/", RegisterCourierView.as_view(), name="register-courier"),
    path('payment-methods/', MyPaymentMethodsView.as_view(), name="my-payment-methods"),
    path('payment-methods/<str:payment_type>/', PaymentMethodView.as_view(), name="payment-method-detail"),
    path("user/me/", UserMeView.as_view(), name="user-me"),
    path("addresses/", MyAddressesView.as_view(), name="my-addresses"),
    path("addresses/<str:address_type>/", AddressView.as_view(), name="address-detail"),
    path("me/delivery/", ShopDeliverySettingsMeView.as_view(), name="shop-delivery-me"),
    path("notifications/me/", NotificationSettingsMeView.as_view(), name="notification-settings-me"),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('logout-all/', LogoutAllDevicesView.as_view(), name='logout-all'),
    path('delete-account/', DeleteMyAccountView.as_view(), name='delete-account'),
    path('identity-verification/', MyIdentityVerificationView.as_view(), name='identity-verification'),
    
    ]
