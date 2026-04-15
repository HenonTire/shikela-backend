from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .badge_logic import resolve_badge
from .models import *

User = get_user_model()

class MerchantIdRepresentationMixin:
    def to_representation(self, instance):
        resolve_badge(instance, persist=True)
        return super().to_representation(instance)


class UserSerializer(MerchantIdRepresentationMixin, ModelSerializer):
    class Meta:
        model = User
        fields = ['id','first_name', 'last_name', 'email', 'phone_number', 'location', 'badge', 'created_at', 'updated_at',  'password']
        extra_kwargs = {
            'password': {'write_only': True},}
        read_only_fields = ('id', 'created_at', 'updated_at')        
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            role = validated_data.get('role', 'CUSTOMER')
            user.role = role
            status = validated_data.get('status', 'new')
            user.status = status
            user.save()
        return user
    
class ShopOwnerSerializer(MerchantIdRepresentationMixin, ModelSerializer):
    class Meta:
        model = User
        fields = ['id','first_name', 'last_name', 'email', 'phone_number', 'created_at', 'updated_at', 'badge',  'avatar', 'license_document', 'password']
        extra_kwargs = {
            'password': {'write_only': True},}
        read_only_fields = ('id', 'created_at', 'updated_at')        
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            role = 'SHOP_OWNER'
            user.role = role
            user.save()
        return user

class SupplierSerializer(MerchantIdRepresentationMixin, ModelSerializer):
    class Meta:
        model = User
        fields = ['id','company_name',  'email', 'phone_number', 'location', 'created_at', 'updated_at', 'badge',  'avatar', 'license_document', 'policy', 'password', 'bank_account', 'bank_account_number']
        extra_kwargs = {
            'password': {'write_only': True},}
        read_only_fields = ('id', 'created_at', 'updated_at')        
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            role = 'SUPPLIER'
            user.role = role
            user.save()
        return user
class CourierSerializer(MerchantIdRepresentationMixin, ModelSerializer):
    class Meta:
        model = User
        fields = ['id','company_name', 'email', 'phone_number', 'location', 'created_at', 'updated_at', 'badge',  'avatar', 'license_document', 'is_available', 'password']
        extra_kwargs = {
            'password': {'write_only': True},}
        read_only_fields = ('id', 'created_at', 'updated_at')        
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            role = 'COURIER'
            user.role = role
            user.save()
        return user



class PaymentMethodSerializer(ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["payment_type", "account_number", "phone_number"]

    def validate(self, attrs):
        payment_type = attrs.get("payment_type")
        account_number = attrs.get("account_number")
        phone_number = attrs.get("phone_number")
        user = self.context["request"].user

        if payment_type == "BANK" and not account_number:
            raise serializers.ValidationError({"account_number": "Bank account number is required."})
        elif payment_type in ["TELEBIRR", "MPESA"] and not phone_number:
            raise serializers.ValidationError({"phone_number": "Phone number is required for this payment type."})

        if PaymentMethod.objects.filter(shop_owner=user, payment_type=payment_type).exists():
            raise serializers.ValidationError({"payment_type": "Payment method already exists for this user."})
        
        return attrs
    def create(self, validated_data):
        # Always assign the shop_owner from the logged-in user
        user = self.context['request'].user

        # Check that the user is really a ShopOwner
        if user.role != "SHOP_OWNER":
            raise serializers.ValidationError("Only shop owners can add payment methods.")

        validated_data['shop_owner'] = user
        return super().create(validated_data)


class EmailVerificationTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if getattr(settings, "EMAIL_VERIFICATION_REQUIRED_FOR_LOGIN", True) and not getattr(self.user, "is_verified", False):
            raise AuthenticationFailed("Please verify your email before logging in.")
        return data


class ResendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
