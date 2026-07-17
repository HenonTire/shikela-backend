import re

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .badge_logic import resolve_badge, resolve_score
from .models import *

User = get_user_model()

class MerchantIdRepresentationMixin:
    def to_representation(self, instance):
        resolve_badge(instance, persist=True)
        resolve_score(instance, persist=True)   
        return super().to_representation(instance)


class UserSerializer(MerchantIdRepresentationMixin, ModelSerializer):
    class Meta:
        model = User
        fields = ['id','first_name', 'last_name', 'email', 'phone_number', 'location', 'badge', 'score', 'created_at', 'updated_at',  'password']
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
        fields = ['id','first_name', 'last_name', 'email', 'phone_number', 'created_at', 'updated_at', 'badge', 'score',  'avatar', 'license_document', 'password']
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
        fields = ['id','company_name',  'email', 'phone_number', 'location', 'created_at', 'updated_at', 'badge', 'score',  'avatar', 'license_document', 'policy', 'password', 'bank_account', 'bank_account_number']
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
        fields = ['id','company_name', 'email', 'phone_number', 'location', 'created_at', 'updated_at', 'badge', 'score',  'avatar', 'license_document', 'is_available', 'password']
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


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'payment_type', 'provider_name', 'account_number', 'phone_number', 'is_verified', 'created_at', 'updated_at']
        read_only_fields = ['id', 'payment_type', 'is_verified', 'created_at', 'updated_at']
        
class EmailVerificationTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if getattr(settings, "EMAIL_VERIFICATION_REQUIRED_FOR_LOGIN", True) and not getattr(self.user, "is_verified", False):
            raise AuthenticationFailed("Please verify your email before logging in.")

        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'name': f"{self.user.first_name} {self.user.last_name}".strip(),
            'shop_name': getattr(self.user, 'company_name', '') or '',
            'role': getattr(self.user, 'role', ''),
        }
        return data


class ResendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'address_type', 'full_address', 'created_at', 'updated_at']
        read_only_fields = ['id', 'address_type', 'created_at', 'updated_at']
class ShopDeliverySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopDeliverySettings
        fields = ['regions', 'fee', 'pickup_available', 'processing_time', 'updated_at']
        read_only_fields = ['updated_at']
class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = ['push_enabled', 'email_enabled', 'updated_at']
        read_only_fields = ['updated_at']