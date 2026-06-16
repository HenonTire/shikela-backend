from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.db.models import (
    Avg,
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Random
from django.utils import timezone

from order.models import OrderItem

from .models import Product, ProductReview


def get_ranked_products_queryset(
    *,
    base_queryset: Optional[QuerySet] = None,
    query: Optional[str] = None,
    category_id: Optional[str] = None,
    shop_id: Optional[str] = None,
    include_inactive: bool = False,
) -> QuerySet:
    """
    Reusable product ranking queryset for homepage, search, and category pages.

    Ranking score:
        score =
            (sales * 3) +
            (rating * 2) +
            (freshness * 2) +
            (price_penalty * 2) +
            (relevance * 1.5) +
            random_boost
    """
    queryset = base_queryset if base_queryset is not None else Product.objects.all()

    # Keep listing fast by filtering early before annotations.
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if shop_id:
        queryset = queryset.filter(shop_id=shop_id)

    # If a search query exists, trim search space first, then compute relevance.
    normalized_query = (query or "").strip()
    if normalized_query:
        queryset = queryset.filter(
            Q(name__icontains=normalized_query)
            | Q(description__icontains=normalized_query)
            | Q(sku__icontains=normalized_query)
        )

    # Aggregate once for dynamic price bands used by price_penalty.
    average_price = queryset.aggregate(avg_price=Avg("price"))["avg_price"] or Decimal("0.00")

    # Subqueries avoid join multiplication between reviews and order items.
    sales_subquery = (
        OrderItem.objects.filter(product_id=OuterRef("pk"))
        .values("product_id")
        .annotate(total_sales=Sum("quantity"))
        .values("total_sales")[:1]
    )
    rating_subquery = (
        ProductReview.objects.filter(product_id=OuterRef("pk"))
        .values("product_id")
        .annotate(avg_rating=Avg("rating"))
        .values("avg_rating")[:1]
    )
    review_count_subquery = (
        ProductReview.objects.filter(product_id=OuterRef("pk"))
        .values("product_id")
        .annotate(total_reviews=Count("id"))
        .values("total_reviews")[:1]
    )

    now = timezone.now()
    freshness_expr = Case(
        # New products get higher freshness.
        When(created_at__gte=now - timedelta(days=7), then=Value(5.0)),
        When(created_at__gte=now - timedelta(days=30), then=Value(4.0)),
        When(created_at__gte=now - timedelta(days=90), then=Value(3.0)),
        When(created_at__gte=now - timedelta(days=180), then=Value(2.0)),
        default=Value(1.0),
        output_field=FloatField(),
    )

    # Higher price should contribute less to score.
    if average_price > 0:
        price_penalty_expr = Case(
            When(price__lte=average_price * Decimal("0.50"), then=Value(5.0)),
            When(price__lte=average_price, then=Value(4.0)),
            When(price__lte=average_price * Decimal("1.50"), then=Value(3.0)),
            When(price__lte=average_price * Decimal("2.00"), then=Value(2.0)),
            default=Value(1.0),
            output_field=FloatField(),
        )
    else:
        price_penalty_expr = Value(3.0, output_field=FloatField())

    if normalized_query:
        relevance_expr = Case(
            When(name__icontains=normalized_query, then=Value(3.0)),
            When(description__icontains=normalized_query, then=Value(2.0)),
            When(sku__icontains=normalized_query, then=Value(1.5)),
            default=Value(1.0),
            output_field=FloatField(),
        )
    else:
        # Default relevance when no query is provided.
        relevance_expr = Value(1.0, output_field=FloatField())

    queryset = queryset.annotate(
        total_sales=Coalesce(Subquery(sales_subquery, output_field=IntegerField()), Value(0)),
        average_rating=Coalesce(Subquery(rating_subquery, output_field=FloatField()), Value(0.0)),
        reviews_count=Coalesce(Subquery(review_count_subquery, output_field=IntegerField()), Value(0)),
        freshness=freshness_expr,
        price_penalty=price_penalty_expr,
        relevance=relevance_expr,
        # Small jitter to prevent static ordering among near-ties.
        random_boost=ExpressionWrapper(Random() * Value(0.15), output_field=FloatField()),
    ).annotate(
        score=ExpressionWrapper(
            (F("total_sales") * Value(3.0))
            + (F("average_rating") * Value(2.0))
            + (F("freshness") * Value(2.0))
            + (F("price_penalty") * Value(2.0))
            + (F("relevance") * Value(1.5))
            + F("random_boost"),
            output_field=FloatField(),
        )
    )

    return queryset.select_related("category", "shop").order_by("-score", "-total_sales", "-created_at")
