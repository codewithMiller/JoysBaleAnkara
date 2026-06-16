from django.contrib import admin
from .models import Category, Product, ProductVariant, VariantImage, SiteSettings, Subscriber


class VariantImageInline(admin.TabularInline):
    model = VariantImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ('parent',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'gender', 'created_at')
    list_filter = ('category', 'gender')
    search_fields = ('name', 'description')
    inlines = [ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'color', 'price', 'stock', 'available', 'in_stock')
    list_filter = ('available', 'color')
    search_fields = ('product__name', 'color')
    inlines = [VariantImageInline]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('whatsapp_number', 'business_name')

    def has_add_permission(self, request):
        # Only allow adding if no instance exists yet (singleton)
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
    readonly_fields = ('subscribed_at',)
