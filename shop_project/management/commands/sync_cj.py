from django.core.management.base import BaseCommand
from shop_project.cj_api import get_token, fetch_clothing
from shop_project.models import Product, ProductVariant, VariantImage, Category


def parse_price(price_val):
    if not price_val:
        return 0
    price_str = str(price_val).split('--')[0].strip()
    try:
        return float(price_str)
    except ValueError:
        return 0


class Command(BaseCommand):
    help = "Sync Ankara clothing from CJDropshipping"

    def handle(self, *args, **kwargs):
        token = get_token()
        if not token:
            self.stdout.write("Auth failed. Check your CJ_API_KEY.")
            return

        category, _ = Category.objects.get_or_create(name="Ankara")
        products = fetch_clothing(token, keyword="Ankara fabric")

        if not products:
            self.stdout.write("No products returned from CJ.")
            return

        for item in products:
            pid = item.get("pid")
            name = item.get("productNameEn", "Unnamed")
            price = parse_price(item.get("sellPrice", 0))
            image = item.get("productImage", "")

            if not pid or not image:
                continue

            product, created = Product.objects.get_or_create(
                cj_pid=pid,
                defaults={
                    "name": name,
                    "category": category,
                    "is_cj_product": True,
                }
            )

            if created:
                variant = ProductVariant.objects.create(
                    product=product,
                    price=price,
                    stock=99,
                    available=True
                )
                VariantImage.objects.create(
                    variant=variant,
                    image_url=image
                )
                self.stdout.write(f"Added: {name}")
            else:
                self.stdout.write(f"Skipped (exists): {name}")

        self.stdout.write("Sync complete.")
