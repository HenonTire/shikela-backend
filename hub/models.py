from django.db import models
import uuid
class TypeChoices(models.TextChoices):
    BUYER = "customer", "Customer"
    SELLER = "seller", "Seller"
# Create your models here.
class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    profile = models.ImageField(upload_to='hub/profiles/', blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=TypeChoices.choices)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name
class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    picture = models.ImageField(upload_to='hub/posts/', blank=True, null=True)
    caption = models.TextField()
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='posts')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    like_count = models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.title
class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Comment by {self.author.name} on {self.post.title}"
class Follow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='followers')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('follower', 'following')


class PostLike(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'profile')
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['profile', 'created_at']),
        ]
