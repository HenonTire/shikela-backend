from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from catalog.models import Product
from catalog.serializers import ProductSerializer
from .serializers import ProductRestockSerializer
from .services import InventoryService
from .models import Inventory, Location, StockMovement
from .serializers import (
    InventoryActionSerializer,
    InventorySerializer,
    LocationSerializer,
    StockMovementSerializer,
)
from .services import InventoryService
from rest_framework import serializers



class LocationListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LocationSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Location.objects.all().order_by("-id")
        return (
            Location.objects.filter(
                Q(inventory__variant__product__shop__owner=user) | Q(inventory__variant__product__supplier=user)
            )
            .distinct()
            .order_by("-id")
        )


class LocationDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LocationSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Location.objects.all()
        return Location.objects.filter(
            Q(inventory__variant__product__shop__owner=user) | Q(inventory__variant__product__supplier=user)
        ).distinct()


class InventoryListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InventorySerializer

    def get_queryset(self):
        user = self.request.user
        base_qs = Inventory.objects.select_related("variant__product", "location").all().order_by("-id")
        if user.is_staff:
            return base_qs
        return base_qs.filter(
            Q(variant__product__shop__owner=user) | Q(variant__product__supplier=user)
        )


class InventoryDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InventorySerializer

    def get_queryset(self):
        user = self.request.user
        base_qs = Inventory.objects.select_related("variant__product", "location").all()
        if user.is_staff:
            return base_qs
        return base_qs.filter(
            Q(variant__product__shop__owner=user) | Q(variant__product__supplier=user)
        )


class StockMovementListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StockMovementSerializer

    def get_queryset(self):
        base_qs = StockMovement.objects.select_related("inventory__variant__product", "inventory__location").all().order_by("-created_at", "-id")
        user = self.request.user
        if not user.is_staff:
            base_qs = base_qs.filter(
                Q(inventory__variant__product__shop__owner=user) | Q(inventory__variant__product__supplier=user)
            )
        inventory_id = self.request.query_params.get("inventory")
        if inventory_id:
            base_qs = base_qs.filter(inventory_id=inventory_id)
        return base_qs


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
            # Disallow restocking of dropship/imported variants. The source
            # supplier's stock is authoritative and imported variants should not
            # be manually restocked in this shop's inventory.
            if getattr(inventory.variant, "source_variant", None) is not None and qty > 0:
                return Response({"detail": "Cannot restock an imported/dropship variant directly; stock is managed by the source supplier."}, status=status.HTTP_400_BAD_REQUEST)
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



class ProductRestockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        product = get_object_or_404(
            Product.objects.select_related("shop", "shop__owner", "supplier"), pk=pk
        )
        user = request.user
        owns_product = (
            (user.role == "SHOP_OWNER" and product.shop_id and product.shop.owner_id == user.id)
            or (user.role == "SUPPLIER" and product.supplier_id == user.id)
        )
        if not owns_product:
            raise PermissionDenied("You can only restock your own products.")

        serializer = ProductRestockSerializer(data=request.data, context={"product": product})
        serializer.is_valid(raise_exception=True)
        variant = serializer.validated_data["variant"]
        quantity = serializer.validated_data["quantity"]
        reason = serializer.validated_data.get("reason") or "Restock"

        InventoryService.restock_variant(variant, quantity, reason, user=user)
        if variant.source_variant_id:
            raise serializers.ValidationError(
                "This product's stock is managed by the supplier and can't be manually restocked."
            )

        product.refresh_from_db()
        return Response(
            ProductSerializer(product, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )