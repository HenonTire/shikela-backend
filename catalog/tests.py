from django.test import TestCase
from rest_framework.test import APIRequestFactory

from account.models import User
from catalog.models import Category, Product, ProductVariant
from catalog.serializers import ProductSerializer
from shop.models import Shop


class CatalogModelTests(TestCase):
    def test_category_str_returns_name(self):
        category = Category.objects.create(name="Gadgets", slug="gadgets")
        self.assertEqual(str(category), "Gadgets")

    def test_category_slug_is_auto_generated(self):
        category = Category.objects.create(name="Home Audio")
        self.assertEqual(category.slug, "home-audio")

    def test_product_sku_is_auto_generated(self):
        owner = User.objects.create_user(
            email="owner-sku@example.com",
            password="Pass123!",
            role="SHOP_OWNER",
            marketer_type="CREATOR",
        )
        shop = Shop.objects.create(name="SKU Shop", owner=owner)
        category = Category.objects.create(name="Accessories")
        product = Product.objects.create(
            name="Wireless Earbuds",
            description="Demo",
            shop=shop,
            price="79.99",
            category=category,
        )
        self.assertIsNotNone(product.sku)
        self.assertRegex(product.sku, r"^WIRELESSEARB-")


class ProductSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = User.objects.create_user(
            email="shopowner@example.com",
            password="Pass123!",
            role="SHOP_OWNER",
            marketer_type="CREATOR",
        )
        self.shop = Shop.objects.create(name="My Shop", owner=self.owner)
        self.category = Category.objects.create(name="Phones", slug="phones")

    def test_create_product_with_variants_assigns_owner_shop(self):
        request = self.factory.post("/catalog/products/")
        request.user = self.owner
        serializer = ProductSerializer(
            data={
                "name": "Smartphone X",
                "description": "Flagship phone",
                "sku": "PHONE-X",
                "price": "999.99",
                "category_id": str(self.category.id),
                "variants": [
                    {
                        "variant_name": "Black / 128GB",
                        "price": "999.99",
                        "attributes": {"color": "black", "storage": "128GB"},
                    },
                    {
                        "variant_name": "Silver / 256GB",
                        "price": "1099.99",
                        "attributes": {"color": "silver", "storage": "256GB"},
                    },
                ],
            },
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()

        self.assertEqual(product.shop_id, self.shop.id)
        self.assertEqual(product.category_id, self.category.id)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ProductVariant.objects.filter(product=product).count(), 2)
