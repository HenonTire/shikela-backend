from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Inventory, Location, StockMovement
from .serializers import (
    InventoryActionSerializer,
    InventorySerializer,
    LocationSerializer,
    StockMovementSerializer,
)
from .services import InventoryService


class LocationListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Location.objects.all().order_by("-id")
    serializer_class = LocationSerializer


class LocationDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class InventoryListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Inventory.objects.select_related("variant__product", "location").all().order_by("-id")
    serializer_class = InventorySerializer


class InventoryDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Inventory.objects.select_related("variant__product", "location").all()
    serializer_class = InventorySerializer


class StockMovementListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = StockMovement.objects.select_related("inventory__variant__product", "inventory__location").all().order_by("-created_at", "-id")
    serializer_class = StockMovementSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        inventory_id = self.request.query_params.get("inventory")
        if inventory_id:
            qs = qs.filter(inventory_id=inventory_id)
        return qs


class InventoryActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        inventory = Inventory.objects.select_related("variant__product", "location").filter(pk=pk).first()
        if not inventory:
            return Response({"detail": "Inventory item not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InventoryActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        qty = serializer.validated_data["quantity"]
        reason = serializer.validated_data.get("reason", "") or ""

        if action == "reserve":
            ok = InventoryService.reserve_stock(inventory, qty, reason=reason or "Order Reserved")
            if not ok:
                return Response({"detail": "Not enough stock to reserve."}, status=status.HTTP_400_BAD_REQUEST)
        elif action == "release":
            if inventory.quantity_reserved < qty:
                return Response({"detail": "Not enough reserved stock to release."}, status=status.HTTP_400_BAD_REQUEST)
            InventoryService.release_stock(inventory, qty, reason=reason or "Order Released")
        elif action == "confirm":
            if inventory.quantity_reserved < qty:
                return Response({"detail": "Not enough reserved stock to confirm."}, status=status.HTTP_400_BAD_REQUEST)
            InventoryService.confirm_stock(inventory, qty, reason=reason or "Order Confirmed")
        else:
            InventoryService.adjust_stock(inventory, qty, reason=reason or "Manual Adjustment")

        inventory.refresh_from_db()
        latest_movement = (
            StockMovement.objects.filter(inventory=inventory).order_by("-created_at", "-id").first()
        )
        payload = {
            "inventory": InventorySerializer(inventory).data,
            "latest_movement": StockMovementSerializer(latest_movement).data if latest_movement else None,
        }
        return Response(payload, status=status.HTTP_200_OK)
