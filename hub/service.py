from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db.models import Case, Count, F, IntegerField, Max, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from catalog.models import Product
from order.models import Order, OrderItem

from .models import Comment, Post, Profile, TypeChoices


class HubFeedService:
    """
    Builds post feed with this mix:
      - 60% posts from followed sellers
      - 30% trending seller posts
      - 10% new/random seller posts

    If a bucket has fewer posts than expected, remaining slots roll into the next
    bucket and then finally backfill from the latest seller posts.
    """

    DEFAULT_LIMIT = 30
    TRENDING_WINDOW_DAYS = 30

    @classmethod
    def build_feed_queryset(cls, user, limit: int = DEFAULT_LIMIT):
        """
        Returns a queryset of Post ordered by mixed feed ranking.
        """
        safe_limit = cls._normalize_limit(limit)
        if safe_limit <= 0:
            return Post.objects.none()

        followed_target, trending_target, new_random_target = cls._get_bucket_sizes(safe_limit)

        selected_ids = []
        selected_id_set = set()

        # 1) Followed sellers bucket (60%)
        followed_ids = cls._get_followed_seller_post_ids(
            user=user,
            limit=followed_target,
            exclude_ids=selected_id_set,
        )
        cls._extend_unique(selected_ids, selected_id_set, followed_ids)
        followed_shortage = max(0, followed_target - len(followed_ids))

        # 2) Trending bucket (30% + spillover from followed)
        trending_target += followed_shortage
        trending_ids = cls._get_trending_post_ids(
            limit=trending_target,
            exclude_ids=selected_id_set,
        )
        cls._extend_unique(selected_ids, selected_id_set, trending_ids)
        trending_shortage = max(0, trending_target - len(trending_ids))

        # 3) New/random bucket (10% + spillover from trending)
        new_random_target += trending_shortage
        new_random_ids = cls._get_new_random_post_ids(
            limit=new_random_target,
            exclude_ids=selected_id_set,
        )
        cls._extend_unique(selected_ids, selected_id_set, new_random_ids)

        # 4) Backfill if still short
        remaining = safe_limit - len(selected_ids)
        if remaining > 0:
            backfill_ids = list(
                Post.objects.filter(author__user_type=TypeChoices.SELLER)
                .exclude(id__in=selected_id_set)
                .order_by("-created_at")
                .values_list("id", flat=True)[:remaining]
            )
            cls._extend_unique(selected_ids, selected_id_set, backfill_ids)

        return cls._ordered_queryset_from_ids(selected_ids)

    @classmethod
    def build_feed(cls, user, limit: int = DEFAULT_LIMIT):
        """
        Returns the feed as an ordered list of Post instances.
        """
        return list(cls.build_feed_queryset(user=user, limit=limit))

    @classmethod
    def _normalize_limit(cls, limit: int) -> int:
        try:
            parsed = int(limit)
        except (TypeError, ValueError):
            parsed = cls.DEFAULT_LIMIT
        return max(0, parsed)

    @staticmethod
    def _get_bucket_sizes(limit: int) -> tuple[int, int, int]:
        followed = int(limit * 0.6)
        trending = int(limit * 0.3)
        new_random = max(0, limit - followed - trending)
        return followed, trending, new_random

    @classmethod
    def _get_followed_seller_post_ids(cls, user, *, limit: int, exclude_ids: set) -> list:
        if limit <= 0:
            return []

        seller_profile_ids = cls._get_followed_seller_profile_ids(user)
        if not seller_profile_ids:
            return []

        queryset = (
            Post.objects.filter(author_id__in=seller_profile_ids, author__user_type=TypeChoices.SELLER)
            .exclude(id__in=exclude_ids)
            .order_by("-created_at")
        )
        return list(queryset.values_list("id", flat=True)[:limit])

    @classmethod
    def _get_followed_seller_profile_ids(cls, user) -> set:
        """
        Resolves followed seller profiles from explicit relation fields if present.

        Fallback: infer affinity sellers from profiles the user has interacted with by
        commenting on seller posts.
        """
        seller_profile_ids = set()
        viewer_profile = cls._resolve_profile(user)

        relation_fields = (
            "followed_sellers",
            "following_sellers",
            "followed_profiles",
            "following_profiles",
            "followed_users",
            "following_users",
            "followed_shops",
            "following_shops",
            "following",
        )

        # Check both auth user and hub profile objects for follow relationships.
        relation_sources = [src for src in (user, viewer_profile) if src is not None]
        for source in relation_sources:
            for relation_name in relation_fields:
                relation = getattr(source, relation_name, None)
                if relation is None:
                    continue
                seller_profile_ids.update(cls._extract_seller_profile_ids_from_relation(relation))

        if seller_profile_ids:
            return seller_profile_ids

        if not viewer_profile:
            return set()

        # Fallback affinity: sellers whose posts this profile has commented on.
        interacted_seller_ids = (
            Comment.objects.filter(author=viewer_profile, post__author__user_type=TypeChoices.SELLER)
            .values_list("post__author_id", flat=True)
            .distinct()
        )
        return {profile_id for profile_id in interacted_seller_ids if profile_id}

    @classmethod
    def _resolve_profile(cls, user):
        if isinstance(user, Profile):
            return user

        profile = getattr(user, "profile", None)
        if isinstance(profile, Profile):
            return profile

        email = getattr(user, "email", None)
        if email:
            return Profile.objects.filter(email=email).first()
        return None

    @classmethod
    def _extract_seller_profile_ids_from_relation(cls, relation) -> set:
        try:
            model = relation.model
            model_name = model.__name__.lower()
            model_fields = {field.name for field in model._meta.fields}

            # Relation already points to Profile-like model.
            if "user_type" in model_fields:
                return set(
                    relation.filter(user_type=TypeChoices.SELLER).values_list("id", flat=True)
                )

            # Relation points to Shop-like model with owner email.
            if "owner" in model_fields:
                owner_emails = relation.values_list("owner__email", flat=True)
                return set(
                    Profile.objects.filter(email__in=owner_emails, user_type=TypeChoices.SELLER)
                    .values_list("id", flat=True)
                )

            # Relation points to User-like model.
            if "email" in model_fields:
                relation_qs = relation
                if "role" in model_fields:
                    relation_qs = relation_qs.filter(role__in=["SHOP_OWNER", "SUPPLIER"])
                return set(
                    Profile.objects.filter(
                        email__in=relation_qs.values_list("email", flat=True),
                        user_type=TypeChoices.SELLER,
                    ).values_list("id", flat=True)
                )

            # Relation points to Follow-like records.
            if "follower" in model_fields and "following" in model_fields:
                return set(
                    relation.filter(following__user_type=TypeChoices.SELLER).values_list("following_id", flat=True)
                )

            # Best effort fallback when relation model name hints profile data.
            if "profile" in model_name:
                return set(relation.values_list("id", flat=True))

            return set()
        except Exception:
            return set()

    @classmethod
    def _get_trending_post_ids(cls, *, limit: int, exclude_ids: set) -> list:
        if limit <= 0:
            return []

        since = timezone.now() - timedelta(days=cls.TRENDING_WINDOW_DAYS)
        base_qs = Post.objects.filter(author__user_type=TypeChoices.SELLER).exclude(id__in=exclude_ids)

        trending_window_qs = (
            base_qs.filter(created_at__gte=since)
            .annotate(comment_count=Count("comments", distinct=True))
            .annotate(
                trend_score=Coalesce(F("like_count") * Value(3), Value(0))
                + Coalesce(F("comment_count") * Value(2), Value(0))
            )
            .order_by("-trend_score", "-like_count", "-comment_count", "-created_at")
        )

        ordered_ids = list(trending_window_qs.values_list("id", flat=True)[:limit])
        if len(ordered_ids) >= limit:
            return ordered_ids

        # If recent window is too sparse, backfill with all-time trending.
        fallback_ids = list(
            base_qs.exclude(id__in=ordered_ids)
            .annotate(comment_count=Count("comments", distinct=True))
            .annotate(
                trend_score=Coalesce(F("like_count") * Value(3), Value(0))
                + Coalesce(F("comment_count") * Value(2), Value(0))
            )
            .order_by("-trend_score", "-like_count", "-comment_count", "-created_at")
            .values_list("id", flat=True)[: (limit - len(ordered_ids))]
        )
        return ordered_ids + fallback_ids

    @classmethod
    def _get_new_random_post_ids(cls, *, limit: int, exclude_ids: set) -> list:
        if limit <= 0:
            return []

        newest_target = (limit + 1) // 2
        random_target = max(0, limit - newest_target)

        base_qs = Post.objects.filter(author__user_type=TypeChoices.SELLER).exclude(id__in=exclude_ids)

        newest_ids = list(base_qs.order_by("-created_at").values_list("id", flat=True)[:newest_target])

        random_ids = []
        if random_target > 0:
            random_ids = list(
                base_qs.exclude(id__in=newest_ids)
                .order_by("?")
                .values_list("id", flat=True)[:random_target]
            )

        return newest_ids + random_ids

    @staticmethod
    def _extend_unique(target_ids: list, target_id_set: set, candidate_ids: Iterable):
        for post_id in candidate_ids:
            if post_id in target_id_set:
                continue
            target_ids.append(post_id)
            target_id_set.add(post_id)

    @staticmethod
    def _ordered_queryset_from_ids(post_ids: list):
        if not post_ids:
            return Post.objects.none()

        order_case = Case(
            *[When(id=post_id, then=position) for position, post_id in enumerate(post_ids)],
            output_field=IntegerField(),
        )
        return Post.objects.filter(id__in=post_ids).select_related("author").prefetch_related("comments").order_by(
            order_case
        )


class SellerFeedService:
    """
    Builds seller product feed with this mix:
      - 40% trending products (what is selling)
      - 30% new products (market movement)
      - 20% followed sellers activity
      - 10% random/discovery
    """

    DEFAULT_LIMIT = 30
    TRENDING_WINDOW_DAYS = 30
    SELLER_ROLES = {"SHOP_OWNER", "SUPPLIER"}

    SALE_STATUSES = (
        Order.Status.PAID,
        Order.Status.CONFIRMED,
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
    )

    BUCKET_KEYS = (
        "trending_products",
        "new_products",
        "followed_sellers_activity",
        "random_discovery",
    )

    @classmethod
    def get_bucket_targets(cls, limit: int) -> dict[str, int]:
        safe_limit = cls._normalize_limit(limit)
        trending = int(safe_limit * 0.4)
        new_products = int(safe_limit * 0.3)
        followed = int(safe_limit * 0.2)
        random_discovery = max(0, safe_limit - trending - new_products - followed)
        return {
            "trending_products": trending,
            "new_products": new_products,
            "followed_sellers_activity": followed,
            "random_discovery": random_discovery,
        }

    @classmethod
    def build_feed_breakdown(cls, user, limit: int = DEFAULT_LIMIT) -> dict[str, list]:
        safe_limit = cls._normalize_limit(limit)
        if safe_limit <= 0:
            return {
                "trending_products": [],
                "new_products": [],
                "followed_sellers_activity": [],
                "random_discovery": [],
                "ordered_product_ids": [],
            }

        own_product_ids = cls._get_own_product_ids(user)
        targets = cls.get_bucket_targets(safe_limit)

        selected_ids = []
        selected_id_set = set()

        trending_ids = cls._get_trending_product_ids(
            limit=targets["trending_products"],
            exclude_ids=selected_id_set,
        )
        cls._extend_unique(selected_ids, selected_id_set, trending_ids)
        trending_shortage = max(0, targets["trending_products"] - len(trending_ids))

        new_target = targets["new_products"] + trending_shortage
        new_ids = cls._get_new_market_products_ids(
            own_product_ids=own_product_ids,
            limit=new_target,
            exclude_ids=selected_id_set,
        )
        cls._extend_unique(selected_ids, selected_id_set, new_ids)
        new_shortage = max(0, new_target - len(new_ids))

        followed_target = targets["followed_sellers_activity"] + new_shortage
        followed_ids = cls._get_followed_seller_activity_ids(
            user=user,
            own_product_ids=own_product_ids,
            limit=followed_target,
            exclude_ids=selected_id_set,
        )
        cls._extend_unique(selected_ids, selected_id_set, followed_ids)
        followed_shortage = max(0, followed_target - len(followed_ids))

        random_target = targets["random_discovery"] + followed_shortage
        random_ids = cls._get_random_discovery_ids(
            own_product_ids=own_product_ids,
            limit=random_target,
            exclude_ids=selected_id_set,
        )
        cls._extend_unique(selected_ids, selected_id_set, random_ids)

        remaining = safe_limit - len(selected_ids)
        if remaining > 0:
            backfill_ids = list(
                Product.objects.filter(is_active=True)
                .exclude(id__in=selected_id_set)
                .order_by("-created_at")
                .values_list("id", flat=True)[:remaining]
            )
            cls._extend_unique(selected_ids, selected_id_set, backfill_ids)
            random_ids += backfill_ids

        return {
            "trending_products": trending_ids,
            "new_products": new_ids,
            "followed_sellers_activity": followed_ids,
            "random_discovery": random_ids,
            "ordered_product_ids": selected_ids,
        }

    @classmethod
    def build_feed_queryset(cls, user, limit: int = DEFAULT_LIMIT):
        breakdown = cls.build_feed_breakdown(user=user, limit=limit)
        return cls.ordered_queryset_from_ids(breakdown["ordered_product_ids"])

    @classmethod
    def build_feed(cls, user, limit: int = DEFAULT_LIMIT):
        return list(cls.build_feed_queryset(user=user, limit=limit))

    @classmethod
    def _normalize_limit(cls, limit: int) -> int:
        try:
            parsed = int(limit)
        except (TypeError, ValueError):
            parsed = cls.DEFAULT_LIMIT
        return max(0, parsed)

    @classmethod
    def _get_own_product_ids(cls, user) -> set:
        if not user or not getattr(user, "is_authenticated", False):
            return set()
        return set(
            Product.objects.filter(Q(shop__owner=user) | Q(supplier=user)).values_list("id", flat=True)
        )

    @classmethod
    def _get_trending_product_ids(cls, *, limit: int, exclude_ids: set) -> list:
        if limit <= 0:
            return []

        since = timezone.now() - timedelta(days=cls.TRENDING_WINDOW_DAYS)
        trending_rows = (
            OrderItem.objects.filter(
                order__status__in=cls.SALE_STATUSES,
                order__created_at__gte=since,
            )
            .annotate(feed_product_id=Coalesce("product_id", "variant__product_id"))
            .exclude(feed_product_id__isnull=True)
            .exclude(feed_product_id__in=exclude_ids)
            .values("feed_product_id")
            .annotate(
                units_sold=Coalesce(Sum("quantity"), Value(0)),
                last_ordered_at=Max("order__created_at"),
            )
            .order_by("-units_sold", "-last_ordered_at")
        )

        ordered_ids = list(trending_rows.values_list("feed_product_id", flat=True)[:limit])
        if not ordered_ids:
            return []

        active_ids = set(
            Product.objects.filter(id__in=ordered_ids, is_active=True).values_list("id", flat=True)
        )
        return [product_id for product_id in ordered_ids if product_id in active_ids]

    @classmethod
    def _get_new_market_products_ids(cls, *, own_product_ids: set, limit: int, exclude_ids: set) -> list:
        if limit <= 0:
            return []

        preferred_ids = list(
            Product.objects.filter(is_active=True)
            .exclude(id__in=exclude_ids)
            .exclude(id__in=own_product_ids)
            .order_by("-created_at")
            .values_list("id", flat=True)[:limit]
        )
        if len(preferred_ids) >= limit:
            return preferred_ids

        fallback_ids = list(
            Product.objects.filter(is_active=True)
            .exclude(id__in=exclude_ids)
            .exclude(id__in=preferred_ids)
            .order_by("-created_at")
            .values_list("id", flat=True)[: (limit - len(preferred_ids))]
        )
        return preferred_ids + fallback_ids

    @classmethod
    def _get_followed_seller_activity_ids(cls, user, *, own_product_ids: set, limit: int, exclude_ids: set) -> list:
        if limit <= 0:
            return []

        seller_ids = cls._get_followed_seller_ids(user)
        if not seller_ids:
            return []

        queryset = (
            Product.objects.filter(is_active=True)
            .exclude(id__in=exclude_ids)
            .exclude(id__in=own_product_ids)
            .filter(Q(shop__owner_id__in=seller_ids) | Q(supplier_id__in=seller_ids))
            .order_by("-updated_at", "-created_at")
        )
        return list(queryset.values_list("id", flat=True)[:limit])

    @classmethod
    def _get_followed_seller_ids(cls, user) -> set:
        if not user or not getattr(user, "is_authenticated", False):
            return set()

        seller_ids = set()
        relation_fields = (
            "followed_sellers",
            "following_sellers",
            "followed_users",
            "following_users",
            "followed_shops",
            "following_shops",
            "following",
        )
        for relation_name in relation_fields:
            relation = getattr(user, relation_name, None)
            if relation is None:
                continue
            seller_ids.update(cls._extract_seller_ids_from_relation(relation))

        if seller_ids:
            return {seller_id for seller_id in seller_ids if seller_id != user.id}

        inferred_ids = set()

        # Seller also follows suppliers implicitly by importing/carrying their products.
        owned_shop = getattr(user, "owned_shop", None)
        if owned_shop:
            inferred_ids.update(
                Product.objects.filter(shop=owned_shop, supplier_id__isnull=False).values_list("supplier_id", flat=True)
            )

        # If supplier products are carried by shops, treat those shop owners as followed activity.
        if getattr(user, "role", None) == "SUPPLIER":
            inferred_ids.update(
                Product.objects.filter(supplier=user, shop__owner_id__isnull=False).values_list("shop__owner_id", flat=True)
            )

        # Fallback for generic users: historic purchase relationships.
        inferred_ids.update(
            Order.objects.filter(user=user).exclude(shop__owner_id__isnull=True).values_list("shop__owner_id", flat=True)
        )

        return {seller_id for seller_id in inferred_ids if seller_id and seller_id != user.id}

    @classmethod
    def _extract_seller_ids_from_relation(cls, relation) -> set:
        try:
            model = relation.model
            model_fields = {field.name for field in model._meta.fields}
            user_model = get_user_model()
            user_model_fields = {field.name for field in user_model._meta.fields}

            if "owner" in model_fields:
                return set(relation.values_list("owner_id", flat=True))

            if "role" in model_fields:
                return set(relation.filter(role__in=cls.SELLER_ROLES).values_list("id", flat=True))

            if "email" in model_fields and "role" not in model_fields and "email" in user_model_fields:
                matched_users = user_model.objects.filter(
                    email__in=relation.values_list("email", flat=True),
                    role__in=cls.SELLER_ROLES,
                )
                return set(matched_users.values_list("id", flat=True))

            return set()
        except Exception:
            return set()

    @classmethod
    def _get_random_discovery_ids(cls, *, own_product_ids: set, limit: int, exclude_ids: set) -> list:
        if limit <= 0:
            return []

        preferred_ids = list(
            Product.objects.filter(is_active=True)
            .exclude(id__in=exclude_ids)
            .exclude(id__in=own_product_ids)
            .order_by("?")
            .values_list("id", flat=True)[:limit]
        )
        if len(preferred_ids) >= limit:
            return preferred_ids

        fallback_ids = list(
            Product.objects.filter(is_active=True)
            .exclude(id__in=exclude_ids)
            .exclude(id__in=preferred_ids)
            .order_by("?")
            .values_list("id", flat=True)[: (limit - len(preferred_ids))]
        )
        return preferred_ids + fallback_ids

    @staticmethod
    def _extend_unique(target_ids: list, target_id_set: set, candidate_ids: Iterable):
        for item_id in candidate_ids:
            if item_id in target_id_set:
                continue
            target_ids.append(item_id)
            target_id_set.add(item_id)

    @staticmethod
    def ordered_queryset_from_ids(product_ids: list):
        if not product_ids:
            return Product.objects.none()

        order_case = Case(
            *[When(id=product_id, then=position) for position, product_id in enumerate(product_ids)],
            output_field=IntegerField(),
        )
        return (
            Product.objects.filter(id__in=product_ids)
            .select_related("shop", "supplier", "category")
            .prefetch_related("variants", "media")
            .order_by(order_case)
        )
