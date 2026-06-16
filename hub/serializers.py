from rest_framework import serializers

from .models import Comment, Follow, Post, PostLike, Profile


class HubProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["id", "name", "email", "phone_number", "user_type", "profile"]


class HubPostSerializer(serializers.ModelSerializer):
    author = HubProfileSerializer(read_only=True)
    comments_count = serializers.IntegerField(source="comments.count", read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "picture",
            "caption",
            "author",
            "like_count",
            "likes_count",
            "comments_count",
            "created_at",
            "updated_at",
        ]


class HubPostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["title", "picture", "caption"]


class HubCommentSerializer(serializers.ModelSerializer):
    author = HubProfileSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "post", "author", "content", "created_at", "updated_at"]
        read_only_fields = ["id", "post", "author", "created_at", "updated_at"]


class HubFollowSerializer(serializers.ModelSerializer):
    follower = HubProfileSerializer(read_only=True)
    following = HubProfileSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "follower", "following", "created_at", "updated_at"]
        read_only_fields = fields


class HubPostLikeSerializer(serializers.ModelSerializer):
    post = serializers.UUIDField(source="post_id", read_only=True)
    profile = serializers.UUIDField(source="profile_id", read_only=True)

    class Meta:
        model = PostLike
        fields = ["id", "post", "profile", "created_at"]
        read_only_fields = fields
