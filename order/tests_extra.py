from django.test import TestCase
from account.models import User
from catalog.models import Product, ProductVariant, Category
from shop.models import Shop
from order.services import OrderService
from inventory.models import Inventory

class DropshipStockTests(TestCase):
    def setUp(self):
        self.supplier = User.objects.create_user(email='supplier@example.com', password='pass1234', role='SUPPLIER')
        self.shop_owner = User.objects.create_user(email='owner2@example.com', password='pass1234', role='SHOP_OWNER')
        self.shop = Shop.objects.create(name='Dropship Shop', owner=self.shop_owner)
        self.category = Category.objects.create(name='DS Cat')

        # Supplier product and source variant
        self.supplier_product = Product.objects.create(name='SupProduct', supplier=self.supplier, price='10.00', category=self.category)
        self.source_variant = ProductVariant.objects.create(product=self.supplier_product, variant_name='Source', price='10.00', stock=50)

        # Import into shop (simulate importer behavior)
        self.imported_product = Product.objects.create(name='Imported', shop=self.shop, supplier=self.supplier, price='12.00', category=self.category)
        self.imported_variant = ProductVariant.objects.create(product=self.imported_product, variant_name='Imported', price='12.00', stock=5, source_variant=self.source_variant)

    def test_non_dropship_checkout_decrements_local_variant(self):
        # normal product (not dropship)
        local_product = Product.objects.create(name='Local', shop=self.shop, price='20.00', category=self.category)
        local_variant = ProductVariant.objects.create(product=local_product, variant_name='LocalV', price='20.00', stock=10)
        order = OrderService.create_order(user=self.shop_owner, shop=self.shop, items=[{"product": local_product, "variant": local_variant, "quantity": 3}], delivery_address='Addr', payment_method='santimpay')
        local_variant.refresh_from_db()
        self.assertEqual(local_variant.stock, 7)

    def test_dropship_checkout_decrements_source_variant(self):
        # ordering the imported variant should decrement the supplier's source variant
        order = OrderService.create_order(user=self.shop_owner, shop=self.shop, items=[{"product": self.imported_product, "variant": self.imported_variant, "quantity": 4}], delivery_address='Addr', payment_method='santimpay')
        self.source_variant.refresh_from_db()
        self.imported_variant.refresh_from_db()
        # source should go down by 4, imported variant should remain unchanged
        self.assertEqual(self.source_variant.stock, 46)
        self.assertEqual(self.imported_variant.stock, 5)

    def test_restock_imported_variant_rejected(self):
        # Create inventory for imported variant
        inventory = Inventory.objects.create(variant=self.imported_variant, location=None, quantity_available=5, quantity_reserved=0)
        # Attempt to restock (adjust +10)
        client = self.client
        client.force_login(self.shop_owner)
        resp = client.post(f"/inventory/items/{inventory.id}/actions/", {"action": "adjust", "quantity": 10}, content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        inventory.refresh_from_db()
        self.assertEqual(inventory.quantity_available, 5)
