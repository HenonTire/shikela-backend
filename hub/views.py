from django.db import transaction
from django.db.models import Case, F, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.serializers import ProductSerializer

from .models import Comment, Follow, Post, PostLike, Profile, TypeChoices
from .serializers import HubCommentSerializer, HubFollowSerializer, HubPostSerializer, HubPostWriteSerializer, HubProfileSerializer
from .service import HubFeedService, SellerFeedService


class IsSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {"SHOP_OWNER", "SUPPLIER"}
        )


class IsBuyer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "CUSTOMER"
        )


def _safe_limit(query_value, default=30, min_value=1, max_value=100):
    try:
        parsed = int(query_value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(max_value, parsed))


def _profile_name_for_user(user):
    full_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
    if full_name:
        return full_name
    email = (user.email or "").strip()
    if email and "@" in email:
        return email.split("@", 1)[0]
    return "User"


def _profile_type_for_user(user):
    if getattr(user, "role", "") in {"SHOP_OWNER", "SUPPLIER", "MARKETER"}:
        return TypeChoices.SELLER
    return TypeChoices.BUYER


def _resolve_or_create_profile(user):
    defaults = {
        "name": _profile_name_for_user(user),
        "phone_number": getattr(user, "phone_number", None),
        "user_type": _profile_type_for_user(user),
    }
    profile, _ = Profile.objects.get_or_create(
        email=user.email,
        defaults=defaults,
    )

    update_fields = []
    expected_name = defaults["name"]
    expected_phone = defaults["phone_number"]
    expected_type = defaults["user_type"]

    if expected_name and profile.name != expected_name:
        profile.name = expected_name
        update_fields.append("name")
    if profile.phone_number != expected_phone:
        profile.phone_number = expected_phone
        update_fields.append("phone_number")
    if profile.user_type != expected_type:
        profile.user_type = expected_type
        update_fields.append("user_type")

    if update_fields:
        profile.save(update_fields=update_fields)

    return profile


class HubMyProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = _resolve_or_create_profile(request.user)
        return Response(HubProfileSerializer(profile, context={"request": request}).data)


class BuyerFeedView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsBuyer]

    def get(self, request):
        limit = _safe_limit(request.query_params.get("limit"), default=HubFeedService.DEFAULT_LIMIT)
        followed_sellers, trending_posts, new_random_posts = HubFeedService._get_bucket_sizes(limit)
        queryset = HubFeedService.build_feed_queryset(user=request.user, limit=limit)
        payload = {
            "limit": limit,
            "mix": {
                "followed_sellers_posts": followed_sellers,
                "trending_posts": trending_posts,
                "new_random_posts": new_random_posts,
            },
            "total": len(queryset),
            "results": HubPostSerializer(queryset, many=True, context={"request": request}).data,
        }
        return Response(payload)


class SellerFeedView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get(self, request):
        limit = _safe_limit(request.query_params.get("limit"), default=SellerFeedService.DEFAULT_LIMIT)
        targets = SellerFeedService.get_bucket_targets(limit)
        breakdown = SellerFeedService.build_feed_breakdown(user=request.user, limit=limit)
        queryset = SellerFeedService.ordered_queryset_from_ids(breakdown["ordered_product_ids"])

        payload = {
            "limit": limit,
            "mix": targets,
            "counts": {
                "trending_products": len(breakdown["trending_products"]),
                "new_products": len(breakdown["new_products"]),
                "followed_sellers_activity": len(breakdown["followed_sellers_activity"]),
                "random_discovery": len(breakdown["random_discovery"]),
                "total": len(breakdown["ordered_product_ids"]),
            },
            "results": ProductSerializer(queryset, many=True, context={"request": request}).data,
        }
        return Response(payload)


class SellerFeedBucketsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get(self, request):
        limit = _safe_limit(request.query_params.get("limit"), default=SellerFeedService.DEFAULT_LIMIT)
        targets = SellerFeedService.get_bucket_targets(limit)
        breakdown = SellerFeedService.build_feed_breakdown(user=request.user, limit=limit)

        payload = {
            "limit": limit,
            "mix": targets,
            "counts": {
                "trending_products": len(breakdown["trending_products"]),
                "new_products": len(breakdown["new_products"]),
                "followed_sellers_activity": len(breakdown["followed_sellers_activity"]),
                "random_discovery": len(breakdown["random_discovery"]),
                "total": len(breakdown["ordered_product_ids"]),
            },
            "buckets": {
                "trending_products": ProductSerializer(
                    SellerFeedService.ordered_queryset_from_ids(breakdown["trending_products"]),
                    many=True,
                    context={"request": request},
                ).data,
                "new_products": ProductSerializer(
                    SellerFeedService.ordered_queryset_from_ids(breakdown["new_products"]),
                    many=True,
                    context={"request": request},
                ).data,
                "followed_sellers_activity": ProductSerializer(
                    SellerFeedService.ordered_queryset_from_ids(breakdown["followed_sellers_activity"]),
                    many=True,
                    context={"request": request},
                ).data,
                "random_discovery": ProductSerializer(
                    SellerFeedService.ordered_queryset_from_ids(breakdown["random_discovery"]),
                    many=True,
                    context={"request": request},
                ).data,
            },
        }
        return Response(payload)


class HubPostListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Post.objects.select_related("author").prefetch_related("comments", "likes").order_by("-created_at")
        mine = request.query_params.get("mine")
        if mine and mine.lower() in {"1", "true", "yes"}:
            profile = _resolve_or_create_profile(request.user)
            queryset = queryset.filter(author=profile)

        serializer = HubPostSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        profile = _resolve_or_create_profile(request.user)
        if profile.user_type != TypeChoices.SELLER:
            return Response(
                {"detail": "Only seller profiles can create posts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = HubPostWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=profile)
        return Response(
            HubPostSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class HubPostDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(Post.objects.select_related("author").prefetch_related("comments", "likes"), pk=pk)
        return Response(HubPostSerializer(post, context={"request": request}).data)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def _update(self, request, pk, partial):
        post = get_object_or_404(Post, pk=pk)
        profile = _resolve_or_create_profile(request.user)
        if post.author_id != profile.id:
            return Response(
                {"detail": "You can only update your own posts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = HubPostWriteSerializer(post, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(HubPostSerializer(post, context={"request": request}).data)

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        profile = _resolve_or_create_profile(request.user)
        if post.author_id != profile.id:
            return Response(
                {"detail": "You can only delete your own posts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HubPostCommentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        comments = post.comments.select_related("author").order_by("-created_at")
        serializer = HubCommentSerializer(comments, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        profile = _resolve_or_create_profile(request.user)
        serializer = HubCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(post=post, author=profile)
        return Response(
            HubCommentSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class HubPostLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        profile = _resolve_or_create_profile(request.user)

        like, created = PostLike.objects.get_or_create(post=post, profile=profile)
        if created:
            Post.objects.filter(pk=post.pk).update(like_count=F("like_count") + 1)

        post.refresh_from_db(fields=["like_count"])
        payload = {
            "liked": True,
            "created": created,
            "like_count": post.like_count,
            "like": {
                "id": str(like.id),
                "post": str(post.id),
                "profile": str(profile.id),
            },
        }
        return Response(payload, status=status.HTTP_200_OK)

    @transaction.atomic
    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        profile = _resolve_or_create_profile(request.user)

        deleted, _ = PostLike.objects.filter(post=post, profile=profile).delete()
        if deleted:
            Post.objects.filter(pk=post.pk).update(
                like_count=Case(
                    When(like_count__gt=0, then=F("like_count") - 1),
                    default=Value(0),
                )
            )

        post.refresh_from_db(fields=["like_count"])
        payload = {
            "liked": False,
            "removed": bool(deleted),
            "like_count": post.like_count,
        }
        return Response(payload, status=status.HTTP_200_OK)


class HubFollowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, profile_id):
        follower = _resolve_or_create_profile(request.user)
        following = get_object_or_404(Profile, pk=profile_id)

        if follower.id == following.id:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if following.user_type != TypeChoices.SELLER:
            return Response(
                {"detail": "You can only follow seller profiles."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow, created = Follow.objects.get_or_create(follower=follower, following=following)
        payload = {
            "following": True,
            "created": created,
            "relationship": HubFollowSerializer(follow, context={"request": request}).data,
        }
        return Response(payload, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    def delete(self, request, profile_id):
        follower = _resolve_or_create_profile(request.user)
        following = get_object_or_404(Profile, pk=profile_id)
        deleted, _ = Follow.objects.filter(follower=follower, following=following).delete()

        payload = {
            "following": False,
            "removed": bool(deleted),
            "follower_id": str(follower.id),
            "following_id": str(following.id),
        }
        return Response(payload)
