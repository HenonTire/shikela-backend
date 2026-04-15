from django.test import TestCase
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from account.models import PaymentMethod, User
from account.badge_logic import resolve_badge
from account.serializers import PaymentMethodSerializer


class UserModelTests(TestCase):
    def test_create_user_hashes_password(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="Pass123!",
        )

        self.assertNotEqual(user.password, "Pass123!")
        self.assertTrue(user.check_password("Pass123!"))

    def test_create_user_requires_email(self):
        with self.assertRaisesMessage(ValueError, "Users must have an email"):
            User.objects.create_user(
                email="",
                password="Pass123!",
            )


class PaymentMethodSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.shop_owner = User.objects.create_user(
            email="owner@example.com",
            password="Pass123!",
            role="SHOP_OWNER",
        )
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="Pass123!",
            role="CUSTOMER",
        )

    def test_bank_payment_requires_account_number(self):
        request = self.factory.post("/auth/create-payment-method/")
        request.user = self.shop_owner
        serializer = PaymentMethodSerializer(
            data={"payment_type": "BANK", "phone_number": "0911223344"},
            context={"request": request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("account_number", serializer.errors)

    def test_mobile_payment_requires_phone_number(self):
        request = self.factory.post("/auth/create-payment-method/")
        request.user = self.shop_owner
        serializer = PaymentMethodSerializer(
            data={"payment_type": "TELEBIRR", "account_number": "123456"},
            context={"request": request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("phone_number", serializer.errors)

    def test_serializer_assigns_shop_owner_from_request_user(self):
        request = self.factory.post("/auth/create-payment-method/")
        request.user = self.shop_owner
        serializer = PaymentMethodSerializer(
            data={"payment_type": "BANK", "account_number": "100200300"},
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        payment_method = serializer.save()

        self.assertEqual(payment_method.shop_owner_id, self.shop_owner.id)
        self.assertEqual(PaymentMethod.objects.count(), 1)

    def test_non_shop_owner_cannot_create_payment_method(self):
        request = self.factory.post("/auth/create-payment-method/")
        request.user = self.customer
        serializer = PaymentMethodSerializer(
            data={"payment_type": "BANK", "account_number": "100200300"},
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(ValidationError):
            serializer.save()


class BadgeLogicTests(TestCase):
    def test_verified_badge_requires_license_document(self):
        user = User.objects.create_user(
            email="badge@example.com",
            password="Pass123!",
            role="SUPPLIER",
        )

        self.assertEqual(resolve_badge(user, persist=False), "none")

        user.license_document = SimpleUploadedFile("license.pdf", b"fake-license", content_type="application/pdf")
        self.assertEqual(resolve_badge(user, persist=False), "verified")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_VERIFICATION_ENABLED=True,
    EMAIL_VERIFICATION_BACKEND_BASE_URL="http://testserver",
)
class EmailVerificationFlowTests(TestCase):
    def test_register_sends_verification_email(self):
        payload = {
            "email": "verifyme@example.com",
            "password": "Pass123!",
            "first_name": "Verify",
            "last_name": "Me",
        }
        response = self.client.post("/auth/register/", payload)

        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(email="verifyme@example.com")
        self.assertFalse(user.is_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/auth/verify-email/", mail.outbox[0].body)

    def test_verify_email_endpoint_marks_user_verified(self):
        user = User.objects.create_user(email="pending@example.com", password="Pass123!")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.get(f"/auth/verify-email/?uid={uid}&token={token}")

        self.assertEqual(response.status_code, 200, response.content)
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_login_requires_verified_email(self):
        user = User.objects.create_user(email="blocked@example.com", password="Pass123!")

        blocked_response = self.client.post(
            "/auth/login/",
            {"email": "blocked@example.com", "password": "Pass123!"},
        )
        self.assertEqual(blocked_response.status_code, 401, blocked_response.content)

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        allowed_response = self.client.post(
            "/auth/login/",
            {"email": "blocked@example.com", "password": "Pass123!"},
        )
        self.assertEqual(allowed_response.status_code, 200, allowed_response.content)
        self.assertIn("access", allowed_response.json())

