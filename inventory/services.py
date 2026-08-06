
from .models import *
from django.db import transaction
from django.db.models import F
from catalog.models import ProductVariant

class InventoryService:
    
    @staticmethod
    def reserve_stock(inventory: Inventory, qty: int, reason="Order Reserved") -> bool:
        if inventory.quantity_available >= qty:
            inventory.quantity_available -= qty
            inventory.quantity_reserved += qty
            inventory.save()
            StockMovement.objects.create(
                inventory=inventory,
                quantity=-qty,
                reason=reason
            )
            return True
        return False

    @staticmethod
    def release_stock(inventory: Inventory, qty: int, reason="Order Released"):
        inventory.quantity_reserved -= qty
        inventory.quantity_available += qty
        inventory.save()
        StockMovement.objects.create(
            inventory=inventory,
            quantity=qty,
            reason=reason
        )

    @staticmethod
    def confirm_stock(inventory: Inventory, qty: int, reason="Order Confirmed"):
        # Move reserved stock to sold / shipped
        inventory.quantity_reserved -= qty
        inventory.save()
        StockMovement.objects.create(
            inventory=inventory,
            quantity=-qty,
            reason=reason
        )

    @staticmethod
    def adjust_stock(inventory: Inventory, qty: int, reason="Manual Adjustment"):
        # Positive qty = stock_in, Negative qty = stock_out
        inventory.quantity_available += qty
        inventory.save()
        StockMovement.objects.create(
            inventory=inventory,
            quantity=qty,
            reason=reason

        )
    @staticmethod
    def restock_variant(variant: ProductVariant, qty: int, reason: str, user=None) -> Inventory:
        """Restock = stock-in. Keeps Inventory.quantity_available and
        ProductVariant.stock in sync, race-safe via select_for_update."""
        with transaction.atomic():
            inventory, _ = Inventory.objects.select_for_update().get_or_create(
                variant=variant, location=None, defaults={"quantity_available": 0}
            )
            inventory.quantity_available = F("quantity_available") + qty
            inventory.save(update_fields=["quantity_available", "last_updated"])
            inventory.refresh_from_db()

            variant_locked = ProductVariant.objects.select_for_update().get(pk=variant.pk)
            variant_locked.stock = F("stock") + qty
            variant_locked.save(update_fields=["stock", "updated_at"])
            variant_locked.refresh_from_db()

            StockMovement.objects.create(
                inventory=inventory,
                quantity=qty,
                reason=reason,
            )
        return inventory


class StockManager:

    @staticmethod
    def allocate_order(variant: ProductVariant, qty: int):
        # Example: find inventory across locations
        inventories = Inventory.objects.filter(variant=variant).order_by("quantity_available")
        allocated = 0
        for inv in inventories:
            if inv.quantity_available <= 0:
                continue
            take_qty = min(qty - allocated, inv.quantity_available)
            InventoryService.reserve_stock(inv, take_qty, reason="Order Allocation")
            allocated += take_qty
            if allocated >= qty:
                break
        if allocated < qty:
            raise Exception("Not enough stock to fulfill order")

    @staticmethod
    def release_order(variant: ProductVariant, qty: int):
        # Find reserved stock and release
        inventories = Inventory.objects.filter(variant=variant).filter(quantity_reserved__gt=0)
        released = 0
        for inv in inventories:
            take_qty = min(qty - released, inv.quantity_reserved)
            InventoryService.release_stock(inv, take_qty, reason="Order Release")
            released += take_qty
            if released >= qty:
                break
        if released < qty:
            raise Exception("Not enough reserved stock to release order")

    @staticmethod
    def confirm_order(variant: ProductVariant, qty: int):
        # Consume reserved stock after payment confirmation
        inventories = Inventory.objects.filter(variant=variant).filter(quantity_reserved__gt=0)
        confirmed = 0
        for inv in inventories:
            if inv.quantity_reserved <= 0:
                continue
            take_qty = min(qty - confirmed, inv.quantity_reserved)
            InventoryService.confirm_stock(inv, take_qty, reason="Order Confirmed")
            confirmed += take_qty
            if confirmed >= qty:
                break
        if confirmed < qty:
            raise Exception("Not enough reserved stock to confirm order")
