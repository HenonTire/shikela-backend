from rest_framework import serializers

from catalog.models import ProductVariant
from .models import Inventory, Location, StockMovement
from .services import InventoryService


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name", "type", "contact"]


class InventorySerializer(serializers.ModelSerializer):
    variant_id = serializers.PrimaryKeyRelatedField(
        source="variant",
        queryset=ProductVariant.objects.all(),
        write_only=True,
    )
    location_id = serializers.PrimaryKeyRelatedField(
        source="location",
        queryset=Location.objects.all(),
        write_only=True,
        allow_null=True,
        required=False,
    )
    variant = serializers.SerializerMethodField(read_only=True)
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id",
            "variant_id",
            "location_id",
            "variant",
            "location",
            "quantity_available",
            "quantity_reserved",
            "last_updated",
        ]
        read_only_fields = ["id", "last_updated"]

    def get_variant(self, obj):
        return {
            "id": str(obj.variant_id),
            "variant_name": obj.variant.variant_name,
            "product_id": str(obj.variant.product_id),
            "product_name": obj.variant.product.name,
        }


class StockMovementSerializer(serializers.ModelSerializer):
    inventory_id = serializers.PrimaryKeyRelatedField(
        source="inventory",
        queryset=Inventory.objects.all(),
        write_only=True,
    )
    inventory = InventorySerializer(read_only=True)

    class Meta:
        model = StockMovement
        fields = ["id", "inventory_id", "inventory", "quantity", "reason", "created_at"]
        read_only_fields = ["id", "created_at", "inventory"]

    def create(self, validated_data):
        inventory = validated_data["inventory"]
        quantity = validated_data["quantity"]
        reason = validated_data.get("reason") or "Manual Adjustment"
        InventoryService.adjust_stock(inventory=inventory, qty=quantity, reason=reason)
        return StockMovement.objects.filter(inventory=inventory).order_by("-created_at", "-id").first()


class InventoryActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["reserve", "release", "confirm", "adjust"])
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
