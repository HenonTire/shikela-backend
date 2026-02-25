from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from order.models import Order
from .services import MarketerCommissionService


@receiver(pre_save, sender=Order)
def _cache_previous_order_status(sender, instance: Order, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    previous = Order.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    instance._previous_status = previous


@receiver(post_save, sender=Order)
def _approve_commissions_on_delivery(sender, instance: Order, **kwargs):
    previous = getattr(instance, "_previous_status", None)
    if previous == instance.status:
        return
    if instance.status == Order.Status.DELIVERED:
        MarketerCommissionService.approve_for_order(instance)
