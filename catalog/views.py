from decimal import Decimal, InvalidOperation
from django.db.models import Q
from rest_framework import permissions
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from .models import *
from .serializers import *
from .services import get_ranked_products_queryset
from django.db import transaction
from django.db.models import F
# Create your views here.

class CreateProductView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        return get_ranked_products_queryset(
            query=self.request.query_params.get("q"),
            category_id=self.request.query_params.get("category_id"),
            shop_id=self.request.query_params.get("shop_id"),
        )


class RankedProductListView(ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return get_ranked_products_queryset(
            query=self.request.query_params.get("q"),
            category_id=self.request.query_params.get("category_id"),
            shop_id=self.request.query_params.get("shop_id"),
        )

class ProductMediaUploadView(CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductMediaSerializer

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.kwargs['product_id'])
        # Only the shop owner (or staff) may upload media for this product
        user = self.request.user
        if not (user.is_staff or (product.shop and getattr(product.shop, 'owner', None) == user)):
            raise PermissionDenied("You do not have permission to add media to this product.")
        serializer.save(product=product)

class ProductDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Product.objects.all()
        return Product.objects.filter(
            Q(shop__owner=user) | Q(supplier=user)
        )

class CreateCategoryView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Category.objects.all()
    serializer_class = CatagorySerializer

    def perform_create(self, serializer):
        # Only staff may create new categories
        if not self.request.user.is_staff:
            raise PermissionDenied("Only staff users can create categories.")
        serializer.save()


class ImportSupplierProductView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _unique_name(base_name: str) -> str:
        candidate = base_name
        suffix = 1
        while Product.objects.filter(name=candidate).exists():
            candidate = f"{base_name} ({suffix})"
            suffix += 1
        return candidate

    def post(self, request, pk):
        user = request.user
        if user.role != "SHOP_OWNER":
            return Response({"detail": "Only shop owners can import supplier products."}, status=status.HTTP_403_FORBIDDEN)

        shop = getattr(user, "owned_shop", None)
        if not shop:
            return Response({"detail": "Create a shop before importing products."}, status=status.HTTP_400_BAD_REQUEST)

        source = Product.objects.filter(pk=pk).prefetch_related("variants", "media").first()
        if not source:
            return Response({"detail": "Supplier product not found."}, status=status.HTTP_404_NOT_FOUND)
        if not source.supplier:
            return Response({"detail": "Only supplier products can be imported."}, status=status.HTTP_400_BAD_REQUEST)

        # Price is now required — the shop owner must set their own
        # selling price, and it must be strictly greater than the
        # supplier's price so there's always a profit margin.
        requested_price = request.data.get("price")
        if requested_price is None:
            return Response(
                {"detail": f"price is required and must be greater than the supplier's price (ETB {source.price})."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            selling_price = Decimal(str(requested_price))
        except (InvalidOperation, ValueError):
            return Response({"detail": "price must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)

        if selling_price <= source.price:
            return Response(
                {"detail": f"price must be greater than the supplier's price (ETB {source.price}) to ensure profit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        imported = Product.objects.create(
            name=self._unique_name(source.name),
            description=source.description,
            shop=shop,
            supplier=source.supplier,
            price=selling_price,
            supplier_price=source.price,
            minimum_wholesale_quantity=source.minimum_wholesale_quantity,
            shop_owner_price=selling_price,
            category=source.category,
            is_active=source.is_active,
            weight=source.weight,
            dimensions=source.dimensions,
            tags=source.tags,
        )

        for variant in source.variants.all():
            # Link imported variant back to the supplier's source variant so
            # dropship flows can resolve and mutate the supplier's live stock.
            ProductVariant.objects.create(
                product=imported,
                variant_name=variant.variant_name,
                price=selling_price,
                attributes=variant.attributes,
                stock=0,  # unused for dropship variants — see source_variant/effective_stock
                source_variant=variant,  # mirrors this supplier variant's live stock
            )

        for media in source.media.all():
            ProductMedia.objects.create(
                product=imported,
                media_type=media.media_type,
                file=media.file,
                caption=media.caption,
                is_primary=media.is_primary,
                order=media.order,
            )
        

        return Response(
            {
                "message": "Product imported successfully.",
                "source_product_id": str(source.id),
                "imported_product_id": str(imported.id),
                "shop_id": str(shop.id),
                "price": str(selling_price),
            },
            status=status.HTTP_201_CREATED,
        )
class ProductReviewListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductReviewSerializer

    def get_queryset(self):
        product_id = self.kwargs["pk"]
        return ProductReview.objects.filter(product_id=product_id).select_related("user", "product").order_by("-created_at")

    def perform_create(self, serializer):
        product = Product.objects.filter(id=self.kwargs["pk"]).first()
        if not product:
            raise PermissionDenied("Product not found.")
        if ProductReview.objects.filter(product=product, user=self.request.user).exists():
            raise PermissionDenied("You have already reviewed this product.")
        serializer.save(product=product, user=self.request.user)


class ProductReviewDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductReviewSerializer
    queryset = ProductReview.objects.select_related("user", "product").all()

    def perform_update(self, serializer):
        if serializer.instance.user_id != self.request.user.id:
            raise PermissionDenied("You can only update your own review.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id:
            raise PermissionDenied("You can only delete your own review.")
        instance.delete()


class SupplierProductsForShopView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        supplier_id = self.kwargs["supplier_id"]
        return (
            Product.objects.filter(supplier_id=supplier_id, is_active=True, shop__isnull=True,)
            .select_related("category")
            .prefetch_related("variants", "media")
        )
class MyShopProductsView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role != "SHOP_OWNER":
            return Product.objects.none()
        shop = getattr(user, "owned_shop", None)
        if not shop:
            return Product.objects.none()
        return (
            Product.objects.filter(shop=shop)
            .select_related("category")
            .prefetch_related("variants", "media")
            .order_by("-created_at")
        )