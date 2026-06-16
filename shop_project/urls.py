from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/related/', views.load_more_related, name='load_more_related'),
    path('subscribe/', views.subscribe, name='subscribe'),
]
