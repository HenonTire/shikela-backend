from rest_framework import serializers
from .models import Product, ProductVariant, ProductMedia, Category
class CatagorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'variant_name', 'price', 'attributes', 'stock']
        read_only_fields = ['id']

class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ['id', 'media_type', 'file', 'caption', 'is_primary', 'order']
        read_only_fields = ['id']

class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, required=False)
    media = ProductMediaSerializer(many=True, required=False)
    category = CatagorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'sku', 'price', 'category_id', 'category', 'is_active', 
                  'weight', 'dimensions', 'tags', 'variants', 'media']
        read_only_fields = ['id']

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        media_data = validated_data.pop('media', [])
        
        # Assign shop from request user
        shop = self.context['request'].user.owned_shop
        validated_data['shop'] = shop
        
        # Create the main product
        product = Product.objects.create(**validated_data)
        
        # Create variants if provided
        for variant in variants_data:
            ProductVariant.objects.create(product=product, **variant)
        
        # Create media if provided
        for media in media_data:
            ProductMedia.objects.create(product=product, **media)
        
        return product

