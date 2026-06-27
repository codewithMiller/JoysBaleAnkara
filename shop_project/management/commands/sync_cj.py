from django.core.management.base import BaseCommand
from shop_project.cj_api import get_token, fetch_clothing
from shop_project.models import Product, ProductVariant, VariantImage, Category
import time

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

ALLOWED_KEYWORDS = [
    "fabric", "textile", "cloth", "material", "yardage", "yard", "meter",
    "metres", "wax print", "ankara", "kitenge", "cotton", "polyester",
    "chiffon", "satin", "lace", "velvet", "georgette", "brocade",
    "crepe", "organza", "tulle", "denim", "silk", "linen",
]

BLOCKED_KEYWORDS = [
    "dress", "gown", "skirt", "blouse", "shirt", "trouser", "pant",
    "jacket", "coat", "suit", "jumpsuit", "romper", "top", "tee",
    "hoodie", "sweater", "cardigan", "vest", "shorts",
    "earring", "necklace", "bracelet", "ring", "watch", "wallet",
    "shoe", "sneaker", "boot", "heel", "sandal", "sock", "bag", "purse",
    "hat", "cap", "beanie", "helmet", "scarf", "glove",
    "bed", "sofa", "mattress", "pillow", "chair", "table",
    "curtain", "rug", "blanket", "towel", "bedsheet", "furniture",
    "pet", "cat", "dog", "toy", "lingerie", "underwear",
    "bra", "panties", "bikini", "swim",
]


def parse_price(price_val):
    if not price_val:
        return 0
    price_str = str(price_val).split("--")[0].strip()
    try:
        return float(price_str)
    except (ValueError, TypeError):
        return 0


def is_relevant_fabric(item):
    name = (item.get("productNameEn") or "").strip().lower()
    desc = (item.get("description") or "").strip().lower()
    combined = f"{name} {desc}"

    if not combined.strip():
        return False
    if any(bad in combined for bad in BLOCKED_KEYWORDS):
        return False
    return any(good in combined for good in ALLOWED_KEYWORDS)


class Command(BaseCommand):
    help = "Sync fabric/textile products from CJDropshipping into your store"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keyword",
            type=str,
            default=None,
            help="Single CJ search keyword e.g. 'cotton fabric'"
        )
        parser.add_argument(
            "--all-fabrics",
            action="store_true",
            help="Sync all fabric keywords in one run"
        )
        parser.add_argument(
            "--category",
            type=str,
            default="Fabric",
            help="Local category name to assign products to"
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Max products to save per keyword"
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=5,
            help="Max CJ result pages to fetch per keyword"
        )

    def handle(self, *args, **options):
        category_name = options["category"].strip()
        limit = options["limit"]
        max_pages = options["max_pages"]

        if options["all_fabrics"]:
            keywords = FABRIC_KEYWORDS
        elif options["keyword"]:
            keywords = [options["keyword"].strip()]
        else:
            keywords = FABRIC_KEYWORDS  # default to all

        if limit <= 0 or max_pages <= 0:
            self.stdout.write(self.style.ERROR("limit and max-pages must be greater than 0."))
            return

        token = get_token()
        if not token:
            self.stdout.write(self.style.ERROR("Auth failed. Check your CJ_API_KEY."))
            return

        category, _ = Category.objects.get_or_create(name=category_name)

        grand_created = 0
        grand_updated = 0
        grand_skipped = 0

        for keyword in keywords:
            self.stdout.write(self.style.WARNING(
                f"\n--- Syncing keyword: '{keyword}' ---"
            ))

            total_saved = 0
            total_created = 0
            total_updated = 0
            total_skipped = 0

            for page in range(1, max_pages + 1):
                if total_saved >= limit:
                    break

                products = fetch_clothing(token, keyword=keyword, page=page)

                if not products:
                    self.stdout.write(f"No products on page {page}. Moving on.")
                    break

                self.stdout.write(f"Page {page}: {len(products)} raw results from CJ.")

                for item in products:
                    if total_saved >= limit:
                        break

                    if not is_relevant_fabric(item):
                        total_skipped += 1
                        continue

                    pid = item.get("pid")
                    name = item.get("productNameEn", "Unnamed Product").strip()
                    price = parse_price(item.get("sellPrice", 0))
                    image = item.get("productImage", "")

                    if not pid:
                        total_skipped += 1
                        self.stdout.write(self.style.WARNING("Skipped: no pid."))
                        continue

                    if not image:
                        total_skipped += 1
                        self.stdout.write(self.style.WARNING(f"Skipped (no image): {name}"))
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
                        VariantImage.objects.create(variant=variant, image_url=image)
                        total_created += 1
                        total_saved += 1
                        self.stdout.write(self.style.SUCCESS(f"Added: {name}"))

                    else:
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
                        if not variant:
                            variant = ProductVariant.objects.create(
                                product=product, price=price, stock=99, available=True
                            )
                            changed = True
                        else:
                            if variant.price != price:
                                variant.price = price
                                changed = True
                            if not variant.stock or variant.stock <= 0:
                                variant.stock = 99
                                changed = True
                            if not variant.available:
                                variant.available = True
                                changed = True
                            if changed:
                                variant.save()

                        existing_image = variant.images.first()
                        if not existing_image:
                            VariantImage.objects.create(variant=variant, image_url=image)
                            changed = True
                        elif hasattr(existing_image, "image_url") and existing_image.image_url != image:
                            existing_image.image_url = image
                            existing_image.save()
                            changed = True

                        total_updated += 1
                        total_saved += 1
                        self.stdout.write(self.style.WARNING(f"Updated: {name}"))

                time.sleep(1)  # be polite to CJ rate limits between pages

            self.stdout.write(
                f"'{keyword}' done: created={total_created} updated={total_updated} skipped={total_skipped}"
            )
            grand_created += total_created
            grand_updated += total_updated
            grand_skipped += total_skipped

            time.sleep(2)  # pause between keywords

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== CJ Sync Complete ==="))
        self.stdout.write(f"Category: {category_name}")
        self.stdout.write(f"Total Created: {grand_created}")
        self.stdout.write(f"Total Updated: {grand_updated}")
        self.stdout.write(f"Total Skipped: {grand_skipped}")
