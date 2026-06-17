from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product

# Static Pages
class StaticViewSitemap(Sitemap):
    priority = 0.9
    changefreq = 'monthly'

    def items(self):
        return ['home', 'shop', 'subscribe']

    def location(self, item):
        return reverse(item)

# Products Sitemap
class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.all()   # No filter needed for now

    def location(self, obj):
        return reverse('product_detail', args=[obj.id])

    def lastmod(self, obj):
        return obj.updated_at
