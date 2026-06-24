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


# Words we WANT in Ankara/fabric products
ALLOWED_KEYWORDS = [
    "ankara",
    "african print",
    "wax print",
    "kitenge",
    "dashiki",
    "aso oke",
    "fabric",
    "cloth",
    "textile",
    "material",
    "print fabric",
    "african fabric",
]

# Words we definitely do NOT want
BLOCKED_KEYWORDS = [
    "bed",
    "sofa",
    "mattress",
    "pillow",
    "chair",
    "table",
    "cap",
    "hat",
    "beanie",
    "helmet",
    "lingerie",
    "bra",
    "panties",
    "underwear",
    "bikini",
    "swim",
    "earring",
    "necklace",
    "bracelet",
    "ring",
    "pet",
    "cat",
    "dog",
    "toy",
    "baseball",
    "bedroom",
    "furniture",
    "curtain",
    "rug",
]


def normalize_text(value):
    return (value or "").strip().lower()


def is_relevant_ankara_product(item):
    """
    Decide whether a CJ item is relevant enough to import into the Ankara store.
    """
    name = normalize_text(item.get("productNameEn"))
    description = normalize_text(item.get("description"))
    combined = f"{name} {description}"

    if not combined.strip():
        return False

    # Reject obvious junk first
    for bad_word in BLOCKED_KEYWORDS:
        if bad_word in combined:
            return False

    # Must contain at least one allowed keyword
    for good_word in ALLOWED_KEYWORDS:
        if good_word in combined:
            return True

    return False


class Command(BaseCommand):
    help = "Sync Ankara clothing/fabric from CJDropshipping"

    def handle(self, *args, **kwargs):
        token = get_token()
        if not token:
            self.stdout.write(self.style.ERROR("Auth failed. Check your CJ_API_KEY."))
            return

        category, _ = Category.objects.get_or_create(name="Ankara")

        # You can test different search phrases later
        products = fetch_clothing(token)

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
                self.stdout.write(f"Skipped missing pid/image: {name}")
                continue

            # FILTER OUT RUBBISH HERE
            if not is_relevant_ankara_product(item):
                skipped_irrelevant += 1
                self.stdout.write(f"Skipped irrelevant: {name}")
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

                added_count += 1
                self.stdout.write(self.style.SUCCESS(f"Added: {name}"))

            else:
                # OPTIONAL: update existing CJ product if needed
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
                self.stdout.write(f"Exists/checked: {name}")

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete. Added={added_count}, Existing={skipped_existing}, "
            f"Updated={updated_count}, Irrelevant Skipped={skipped_irrelevant}"
        ))
