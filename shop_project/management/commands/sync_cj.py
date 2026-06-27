from django.core.management.base import BaseCommand
from shop_project.cj_api import get_token, fetch_clothing
from shop_project.models import Product, ProductVariant, VariantImage, Category


def parse_price(price_val):
    """
    CJ sometimes returns price values like:
    '12.5'
    '12.5--18.9'
    None
    """
    if not price_val:
        return 0

    price_str = str(price_val).split("--")[0].strip()

    try:
        return float(price_str)
    except (ValueError, TypeError):
        return 0


class Command(BaseCommand):
    help = "Sync clothing products from CJDropshipping into your store"

    def add_arguments(self, parser):
    parser.add_argument("--keyword", type=str, default=None)
    parser.add_argument("--category", type=str, default="Fabric")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument(
        "--all-fabrics",
        action="store_true",
        help="Sync all fabric keywords in one run"
    )
    def handle(self, *args, **options):
        keyword = options["keyword"].strip()
        category_name = options["category"].strip()
        limit = options["limit"]
        max_pages = options["max_pages"]

        FABRIC_KEYWORDS = [
    "textile fabric",
    "wax print fabric",
    "cotton fabric",
    "polyester fabric",
    "lace fabric",
    "chiffon fabric",
    "ankara fabric",
    "satin fabric",
    "velvet fabric",
    "georgette fabric",
    "brocade fabric",
]

if options["all_fabrics"]:
    keywords = FABRIC_KEYWORDS
elif options["keyword"]:
    keywords = [options["keyword"].strip()]
else:
    keywords = FABRIC_KEYWORDS  # default to all if nothing passed

for keyword in keywords:
    # your existing page loop goes here, indented under this for loop
    ...

        if limit <= 0:
            self.stdout.write(self.style.ERROR("Limit must be greater than 0."))
            return

        if max_pages <= 0:
            self.stdout.write(self.style.ERROR("max-pages must be greater than 0."))
            return

        token = get_token()
        if not token:
            self.stdout.write(self.style.ERROR("Auth failed. Check your CJ_API_KEY."))
            return

        category, _ = Category.objects.get_or_create(name=category_name)

        total_saved = 0
        total_created = 0
        total_updated = 0
        total_skipped = 0

        self.stdout.write(
            self.style.WARNING(
                f"Starting CJ sync | keyword='{keyword}' | category='{category_name}' | "
                f"limit={limit} | max_pages={max_pages}"
            )
        )

        for page in range(1, max_pages + 1):
            if total_saved >= limit:
                break

            products = fetch_clothing(token, keyword=keyword, page=page)

            if not products:
                self.stdout.write(f"No products returned from CJ on page {page}.")
                break

            self.stdout.write(f"Fetched {len(products)} products from CJ page {page}.")

            for item in products:
                if total_saved >= limit:
                    break

                pid = item.get("pid")
                name = item.get("productNameEn", "Unnamed Product").strip()
                price = parse_price(item.get("sellPrice", 0))
                image = item.get("productImage", "")

                if not pid:
                    total_skipped += 1
                    self.stdout.write(self.style.WARNING("Skipped product with no pid."))
                    continue

                if not image:
                    total_skipped += 1
                    self.stdout.write(self.style.WARNING(f"Skipped {name} (no image)."))
                    continue

                # Create or update the Product
                product, created = Product.objects.get_or_create(
                    cj_pid=pid,
                    defaults={
                        "name": name,
                        "category": category,
                        "is_cj_product": True,
                    }
                )

                if created:
                    # Brand new CJ product
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

                    total_created += 1
                    total_saved += 1
                    self.stdout.write(self.style.SUCCESS(f"Added: {name}"))

                else:
                    # Existing product: keep it updated
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

                    # Ensure it has at least one variant
                    variant = product.variants.first()
                    if not variant:
                        variant = ProductVariant.objects.create(
                            product=product,
                            price=price,
                            stock=99,
                            available=True
                        )
                        changed = True
                    else:
                        # update variant price / availability if needed
                        if variant.price != price:
                            variant.price = price
                            changed = True

                        if variant.stock is None or variant.stock <= 0:
                            variant.stock = 99
                            changed = True

                        if not variant.available:
                            variant.available = True
                            changed = True

                        if changed:
                            variant.save()

                    # Ensure it has at least one image
                    existing_image = variant.images.first()
                    if not existing_image:
                        VariantImage.objects.create(
                            variant=variant,
                            image_url=image
                        )
                        changed = True
                    else:
                        # If image_url exists and is different, update it
                        if hasattr(existing_image, "image_url") and existing_image.image_url != image:
                            existing_image.image_url = image
                            existing_image.save()
                            changed = True

                    total_updated += 1
                    total_saved += 1
                    self.stdout.write(self.style.WARNING(f"Updated existing: {name}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== CJ Sync Complete ==="))
        self.stdout.write(f"Keyword: {keyword}")
        self.stdout.write(f"Category: {category_name}")
        self.stdout.write(f"Created: {total_created}")
        self.stdout.write(f"Updated: {total_updated}")
        self.stdout.write(f"Skipped: {total_skipped}")
        self.stdout.write(f"Processed into store: {total_saved}")
