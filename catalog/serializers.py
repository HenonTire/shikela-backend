from django.db.models import Avg, Count
from rest_framework import serializers
from .models import Product, ProductVariant, ProductMedia, Category, ProductReview
from account.models import User
class CatagorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"

class ProductVariantSerializer(serializers.ModelSerializer):
    available_stock = serializers.SerializerMethodField(read_only=True)
    id = serializers.UUIDField(required=False)  # writable for update-matching, but optional so create() still works

    class Meta:
        model = ProductVariant
        fields = ['id', 'variant_name', 'price', 'attributes', 'stock', 'available_stock']
        read_only_fields = ['id']

    def get_available_stock(self, obj):
        return obj.effective_stock

class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ['id', 'media_type', 'file', 'caption', 'is_primary', 'order']
        read_only_fields = ['id']

class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, required=False)
    media = ProductMediaSerializer(many=True, required=False)
    category = CatagorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True, required=False, allow_null=True)
    stock = serializers.IntegerField(write_only=True, required=False, min_value=0)
    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="SUPPLIER"),
        source="supplier",
        write_only=True,
        required=False,
        allow_null=True,
    )
    supplier = serializers.SerializerMethodField(read_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)
    reviews_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'sku', 'price', 'supplier_price', 'minimum_wholesale_quantity', 'shop_owner_price', 'supplier_id', 'supplier', 'category_id', 'category', 'is_active', 
                  'weight', 'dimensions', 'tags', 'variants', 'media', 'stock', 'average_rating', 'reviews_count']
        read_only_fields = ['id']

    def get_supplier(self, obj):
        if not obj.supplier:
            return None
        return {
            "id": str(obj.supplier.id),
            "email": obj.supplier.email,
            "first_name": obj.supplier.first_name,
            "last_name": obj.supplier.last_name,
        }

    def get_average_rating(self, obj):
        agg = obj.reviews.aggregate(avg=Avg("rating"))
        value = agg.get("avg")
        if value is None:
            return None
        return round(float(value), 2)

    def get_reviews_count(self, obj):
        agg = obj.reviews.aggregate(count=Count("id"))
        return int(agg.get("count") or 0)

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        media_data = validated_data.pop('media', [])
        default_stock = validated_data.pop('stock', None)

        request = self.context["request"]
        user = request.user

        # Role-aware ownership wiring:
        # - SHOP_OWNER products belong to their shop
        # - SUPPLIER products belong to the supplier catalog (shop can be null)
        if user.role == "SHOP_OWNER":
            shop = getattr(user, "owned_shop", None)
            if not shop:
                raise serializers.ValidationError("Shop owner must create a shop before adding products.")
            validated_data["shop"] = shop
        elif user.role == "SUPPLIER":
            validated_data["shop"] = None
            validated_data["supplier"] = user
        else:
            raise serializers.ValidationError("Only shop owners or suppliers can create products.")

        # Create the main product
        product = Product.objects.create(**validated_data)
        
        # Create variants if provided
        for variant in variants_data:
            if default_stock is not None and variant.get("stock") is None:
                variant["stock"] = default_stock
            ProductVariant.objects.create(product=product, **variant)

        # Ensure every product has a stock-carrying variant.
        if not variants_data:
            ProductVariant.objects.create(
                product=product,
                variant_name="Default",
                price=product.price,
                stock=default_stock if default_stock is not None else 1,
            )
        
        # Create media if provided
        for media in media_data:
            ProductMedia.objects.create(product=product, **media)
        
        return product
    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', None)
        media_data = validated_data.pop('media', None)
        validated_data.pop('stock', None)  # not used on update; variants carry their own stock

        # Update simple fields on the product itself
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Only touch variants if the request actually sent variant data.
        # An empty/omitted list here means "don't change variants" rather
        # than "delete all variants" — safer default for a PATCH.
        if variants_data:
            existing_variants = {str(v.id): v for v in instance.variants.all()}
            sent_ids = set()
            for variant_data in variants_data:
                variant_id = variant_data.pop('id', None)
                if variant_id and str(variant_id) in existing_variants:
                    variant = existing_variants[str(variant_id)]
                    for attr, value in variant_data.items():
                        setattr(variant, attr, value)
                    variant.save()
                    sent_ids.add(str(variant_id))
                else:
                    new_variant = ProductVariant.objects.create(product=instance, **variant_data)
                    sent_ids.add(str(new_variant.id))
            # Remove variants that were dropped from the form
            for vid, variant in existing_variants.items():
                if vid not in sent_ids:
                    variant.delete()

        # New media gets appended; existing media isn't touched here since
        # your Flutter update flow uploads new media separately via the
        # /media/ endpoint rather than sending it inline.
        if media_data:
            for media_item in media_data:
                ProductMedia.objects.create(product=instance, **media_item)

        return instance


class ProductReviewSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductReview
        fields = ["id", "product", "user", "rating", "title", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "product", "user", "created_at", "updated_at"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("rating must be between 1 and 5.")
        return value

    def get_user(self, obj):
        return {
            "id": str(obj.user.id),
            "email": obj.user.email,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
        }
