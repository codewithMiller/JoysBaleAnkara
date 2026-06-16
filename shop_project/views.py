from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from urllib.parse import quote
from .models import Category, Product, ProductVariant, SiteSettings, Subscriber


def home(request):
    site_settings = SiteSettings.load()
    # 6 randomized products for homepage cards
    featured_products = (
        Product.objects
        .prefetch_related('variants__images')
        .order_by('?')[:6]
    )
    context = {
        'site_settings': site_settings,
        'featured_products': featured_products,
    }
    return render(request, 'shop/home.html', context)


def subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            _, created = Subscriber.objects.get_or_create(email=email)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Thanks for subscribing!' if created else 'You\'re already subscribed!'
                })
            messages.success(request, 'Thanks for subscribing!')
        return redirect('home')
    return redirect('home')


def get_category_and_descendants(category):
    """
    Returns a list of category IDs: the given category plus all of its
    descendants (recursively), so filtering by a parent category also
    includes its subcategories.
    """
    ids = [category.id]
    for child in category.children.all():
        ids.extend(get_category_and_descendants(child))
    return ids


def shop(request):
    products = Product.objects.select_related('category').prefetch_related('variants__images')

    # --- Search ---
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    # --- Category filter (includes subcategories) ---
    category_id = request.GET.get('category')
    site_settings = SiteSettings.load()
    selected_category = None
    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        category_ids = get_category_and_descendants(selected_category)
        products = products.filter(category_id__in=category_ids)

    # --- Gender filter ---
    gender = request.GET.get('gender')
    if gender in ('M', 'W', 'U'):
        products = products.filter(gender=gender)

    # --- Color filter (matches any variant's color) ---
    color = request.GET.get('color', '').strip()
    if color:
        products = products.filter(variants__color__iexact=color).distinct()

    # Top-level categories for the filter sidebar/dropdown
    categories = Category.objects.filter(parent__isnull=True).prefetch_related('children')

    # Distinct colors across all variants, for the color filter dropdown
    available_colors = (
        ProductVariant.objects
        .exclude(color='')
        .values_list('color', flat=True)
        .distinct()
        .order_by('color')
    )

    context = {
        'products': products,
        'categories': categories,
        'available_colors': available_colors,
        'selected_category': selected_category,
        'query': query,
        'selected_gender': gender,
        'selected_color': color,
        'site_settings': site_settings,
    }
    return render(request, 'shop/shop.html', context)


def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('variants__images'),
        id=product_id
    )
    variants = product.variants.all()

    site_settings = SiteSettings.load()
    product_url = request.build_absolute_uri(product.get_absolute_url())

    # Pre-build a WhatsApp link for each variant, so JS just swaps
    # the Buy button's href on swatch selection - no extra requests.
    for variant in variants:
        message = (
            f"Hi! I'd like to order:\n"
            f"{product.name} - {variant.color or 'Default'}\n"
            f"Price: \u20a6{variant.price}\n"
            f"Product ID: {variant.id}\n"
            f"Link: {product_url}"
        )
        if site_settings.whatsapp_number:
            variant.whatsapp_link = f"https://wa.me/{site_settings.whatsapp_number}?text={quote(message)}"
        else:
            variant.whatsapp_link = ""

    # Related products: same category, excluding this product
    related_qs = (
        Product.objects
        .filter(category=product.category)
        .exclude(id=product.id)
        .select_related('category')
        .prefetch_related('variants__images')
    )

    paginator = Paginator(related_qs, 4)
    related_products = paginator.get_page(1)

    context = {
        'product': product,
        'variants': variants,
        'related_products': related_products,
        'related_has_more': related_products.has_next(),
    }
    return render(request, 'shop/product_detail.html', context)


def load_more_related(request, product_id):
    """
    AJAX endpoint for the 'load more' button on the product detail page.
    Returns rendered HTML for the requested page of related products.
    """
    product = get_object_or_404(Product, id=product_id)
    page_number = int(request.GET.get('page', 2))

    related_qs = (
        Product.objects
        .filter(category=product.category)
        .exclude(id=product.id)
        .select_related('category')
        .prefetch_related('variants__images')
    )

    paginator = Paginator(related_qs, 4)
    page = paginator.get_page(page_number)

    html = render_to_string(
        'shop/_related_product_cards.html',
        {'related_products': page}
    )

    return JsonResponse({
        'html': html,
        'has_next': page.has_next(),
    })
