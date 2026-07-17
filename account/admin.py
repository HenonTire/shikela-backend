from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(User)
from django.contrib import admin
from .models import PaymentMethod


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('shop_owner', 'payment_type', 'get_identifier', 'is_verified', 'updated_at')
    list_filter = ('payment_type', 'is_verified')
    search_fields = ('shop_owner__email', 'provider_name', 'account_number', 'phone_number')
    actions = ['mark_verified', 'mark_unverified']

    def mark_verified(self, request, queryset):
        queryset.update(is_verified=True)
    mark_verified.short_description = "Mark selected as verified"

    def mark_unverified(self, request, queryset):
        queryset.update(is_verified=False)
    mark_unverified.short_description = "Mark selected as unverified"