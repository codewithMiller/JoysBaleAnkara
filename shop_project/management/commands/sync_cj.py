import time
import re
from django.core.management.base import BaseCommand
from shop_project.cj_api import get_token, fetch_clothing
from shop_project.models import Product, ProductVariant, VariantImage, Category

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
    "dress", "gown", "skirt", "blouse", "shirt", "trouser", "pant", "pants",
    "jacket", "coat", "suit", "jumpsuit", "romper", "top", "tee", "t-shirt",
    "hoodie", "sweater", "cardigan", "vest", "shorts", "wear", "clothing",
    "earring", "necklace", "bracelet", "ring", "watch", "wallet",
    "shoe", "sneaker", "boot", "heel", "sandal", "sock", "socks", "bag", "purse",
    "hat", "cap", "beanie", "helmet", "scarf", "glove", "gloves",
    "bed", "sofa", "mattress", "pillow", "chair", "table",
    "curtain", "rug", "blanket", "towel", "bedsheet", "furniture",
    "pet", "cat", "dog", "toy", "lingerie", "underwear", "undergarments",
    "bra", "panties", "bikini", "swim", "swimsuit", "swimwear", "bathing", "monokini"
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

    # 1. Extract clean, individual words
    words = set(re.findall(r'\b[a-z]+\b', combined))

    # 2. Block finished clothing words instantly
    if any(bad in words for bad in BLOCKED_KEYWORDS):
        return False
        
    # 3. Block multi-word apparel phrases
    if any(phrase in combined for phrase in ["swim", "bikini", "lingerie", "piece suit", "clothing", "wear"]):
        return False

    # 4. Must contain a raw fabric keyword
    return any(good in words for good in ALLOWED_KEYWORDS)


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
            keywords = FABRIC_KEYWORDS

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

                products = fetch_clothing(token, keyword=keyword, page=page, category_id="A04")

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
                        grand_created += 1
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
                        
                        if changed:
                            total_updated += 1
                            grand_updated += 1
                        else:
                            total_skipped += 1
                            grand_skipped += 1

            self.stdout.write(f"Keyword '{keyword}' summary: Created {total_created}, Updated {total_updated}, Skipped {total_skipped}")

        self.stdout.write(self.style.SUCCESS(
            f"\nSync complete. Total Created: {grand_created}, Total Updated: {grand_updated}, Total Skipped: {grand_skipped}"
        ))
            
