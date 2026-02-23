from django.urls import path
from .views import *

urlpatterns = [
    path('products/', CreateProductView.as_view(), name='create-product'),
    path('products/<uuid:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/', CreateCategoryView.as_view(), name='create-category'),
  
]
