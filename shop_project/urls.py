from django.urls import path
from . import views
from django.contrib.sitemaps.views import sitemap
from .sitemaps import StaticViewSitemap, ProductSitemap   # Adjust import if needed

sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
}

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/related/', views.load_more_related, name='load_more_related'),
    path('subscribe/', views.subscribe, name='subscribe'),

    # Add this line for the sitemap
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # ... your media url if you have it
]
