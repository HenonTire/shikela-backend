from django.contrib import admin
from .models import Product, ProductVariant, ProductMedia, Category, ProductReview
# Register your models here.

admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(ProductMedia)
admin.site.register(Category)
admin.site.register(ProductReview)
