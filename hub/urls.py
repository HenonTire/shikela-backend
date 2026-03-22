from django.urls import path

from .views import (
    BuyerFeedView,
    HubFollowView,
    HubMyProfileView,
    HubPostCommentListCreateView,
    HubPostDetailView,
    HubPostLikeView,
    HubPostListCreateView,
    SellerFeedBucketsView,
    SellerFeedView,
)


urlpatterns = [
    path("profiles/me/", HubMyProfileView.as_view(), name="hub-my-profile"),
    path("profiles/<uuid:profile_id>/follow/", HubFollowView.as_view(), name="hub-follow"),

    path("posts/", HubPostListCreateView.as_view(), name="hub-posts"),
    path("posts/<uuid:pk>/", HubPostDetailView.as_view(), name="hub-post-detail"),
    path("posts/<uuid:pk>/comments/", HubPostCommentListCreateView.as_view(), name="hub-post-comments"),
    path("posts/<uuid:pk>/like/", HubPostLikeView.as_view(), name="hub-post-like"),

    path("buyer/feed/", BuyerFeedView.as_view(), name="buyer-feed"),
    path("seller/feed/", SellerFeedView.as_view(), name="seller-feed"),
    path("seller/feed/buckets/", SellerFeedBucketsView.as_view(), name="seller-feed-buckets"),
]
