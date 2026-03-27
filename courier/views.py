from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Shipment
from .serializers import ShipmentSerializer, ShipmentStatusUpdateSerializer
from .services import LogisticsError, update_shipment_status


def _ensure_courier_user(user) -> None:
    if getattr(user, "role", "") != "COURIER":
        raise PermissionDenied("Only courier users can access courier shipment dashboard")


class CourierShipmentListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        _ensure_courier_user(request.user)
        queryset = (
            Shipment.objects.select_related("order", "courier")
            .filter(courier=request.user)
            .order_by("-updated_at")
        )
        serializer = ShipmentSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CourierShipmentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        _ensure_courier_user(request.user)
        shipment = get_object_or_404(
            Shipment.objects.select_related("order", "courier"),
            pk=pk,
            courier=request.user,
        )
        return Response(ShipmentSerializer(shipment).data, status=status.HTTP_200_OK)


class CourierShipmentStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        _ensure_courier_user(request.user)
        shipment = get_object_or_404(
            Shipment.objects.select_related("order", "order__shop__owner", "order__user"),
            pk=pk,
            courier=request.user,
        )

        serializer = ShipmentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data.get("payload", {})
        payload.update(
            {
                "updated_by": str(request.user.id),
                "updated_by_email": request.user.email,
            }
        )
        try:
            shipment = update_shipment_status(
                shipment=shipment,
                new_status=serializer.validated_data["status"],
                payload=payload,
            )
        except LogisticsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "shipment_id": str(shipment.id),
                "status": shipment.status,
                "order_status": shipment.order.status,
            },
            status=status.HTTP_200_OK,
        )
