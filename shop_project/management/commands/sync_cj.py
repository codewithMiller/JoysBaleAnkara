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
    help = "Sync Ankara clothing/fabric from CJDropshipping"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=300, help='Maximum products to sync')
        parser.add_argument('--max-pages', type=int, default=5, help='Max pages per keyword')
        parser.add_argument('--clear-old', action='store_true', help='Delete all existing CJ products before sync')

    def handle(self, *args, **options):
        limit = options['limit']
        max_pages = options['max_pages']
        clear_old = options['clear_old']

        token = get_token()
        if not token:
            self.stdout.write(self.style.ERROR("Auth failed. Check your CJ_API_KEY."))
            return

        if clear_old:
            deleted, _ = Product.objects.filter(is_cj_product=True).delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} old CJ products."))

        category, _ = Category.objects.get_or_create(name="Ankara")

        # Use improved multi-page fetch from cj_api
        products = fetch_clothing(token, max_pages=max_pages, max_products=limit)

        if not products:
            self.stdout.write(self.style.WARNING("No products returned from CJ."))
            return

        added_count = 0
        skipped_existing = 0
        skipped_irrelevant = 0
        updated_count = 0

        for item in products:
            pid = item.get("pid")
            name = item.get("productNameEn", "Unnamed")
            price = parse_price(item.get("sellPrice", 0))
            image = item.get("productImage", "")

            if not pid or not image:
                skipped_irrelevant += 1
                continue

            # Create or update product
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

                added_count += 1
                self.stdout.write(self.style.SUCCESS(f"Added: {name}"))
            else:
                # Update existing
                changed = False
                if product.name != name:
                    product.name = name
                    changed = True
                if product.category != category:
                    product.category = category
                    changed = True
                if not product.is_cj_product:
                    product.is_cj_product = True
                    changed = True

                if changed:
                    product.save()

                variant = product.variants.first()
                if variant:
                    if variant.price != price:
                        variant.price = price
                        variant.save()
                        updated_count += 1
                else:
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
                    updated_count += 1

                skipped_existing += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete. Added={added_count}, Existing={skipped_existing}, "
            f"Updated={updated_count}, Skipped={skipped_irrelevant}"
        ))
