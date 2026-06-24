from django.db import models
from django.urls import reverse
from cloudinary.models import CloudinaryField


class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Product(models.Model):
    GENDER_CHOICES = [
        ('M', 'Men'),
        ('W', 'Women'),
        ('U', 'Unisex'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    min_yards = models.PositiveIntegerField(default=1)
    max_yards = models.PositiveIntegerField(default=10)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cj_pid = models.CharField(max_length=100, blank=True, unique=True, null=True)
    is_cj_product = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.id])

    @property
    def first_variant(self):
        """Convenience accessor - used for default display image/price on listing cards."""
        return self.variants.first()


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='variants',
        on_delete=models.CASCADE
    )
    color = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        if self.color:
            return f"{self.product.name} - {self.color}"
        return self.product.name

    @property
    def in_stock(self):
        """True only if marked available AND stock > 0."""
        return self.available and self.stock > 0


class VariantImage(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        related_name='images',
        on_delete=models.CASCADE
    )
    image = CloudinaryField('image')
    #image = models.ImageField(upload_to='variant_images/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Image for {self.variant}"


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

    class Meta:
        ordering = ['-subscribed_at']
class SiteSettings(models.Model):
    """
    Singleton model for site-wide config the client can edit via admin.
    Only one row should ever exist - use SiteSettings.load() to access it.
    """
    whatsapp_number = models.CharField(
        max_length=20,
        help_text="Include country code, no spaces or symbols. e.g. 2348012345678"
    )
    whatsapp_channel = models.URLField(
        blank=True,
        help_text="Full WhatsApp Channel link e.g. https://whatsapp.com/channel/xxx"
    )
    business_name = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # prevent deletion

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'whatsapp_number': ''})
        return obj
