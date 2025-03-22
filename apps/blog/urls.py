from django.urls import path
from . import views

urlpatterns = [
    path('', views.BlogView.as_view(), name='blog'),
    path('blog-detail/', views.BlogDetailView.as_view(), name='blog_detail'),
]