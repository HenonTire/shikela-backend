from rest_framework import serializers

from .models import Shipment


class ShipmentSerializer(serializers.ModelSerializer):
    courier_email = serializers.EmailField(source="courier.email", read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "order",
            "courier",
            "courier_email",
            "assigned_at",
            "status",
            "last_event",
            "last_payload",
            "metadata",
            "created_at",
            "updated_at",
        ]


class ShipmentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Shipment.Status.choices)
    payload = serializers.JSONField(required=False)

    def validate_payload(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("payload must be a JSON object")
        return value
