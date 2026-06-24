import os
import requests

CJ_API_KEY = os.environ.get("CJ_API_KEY")
BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"


# Search terms that are actually relevant to Ankara / African fashion / fabric
ANKARA_SEARCH_TERMS = [
    "ankara fabric",
    "african wax print fabric",
    "african print fabric",
    "kitenge fabric",
    "dashiki fabric",
    "african dress",
    "ankara dress",
]

# Words that strongly suggest the product is relevant
ALLOWED_KEYWORDS = [
    "ankara",
    "african print",
    "wax print",
    "kitenge",
    "dashiki",
    "african dress",
    "fabric",
    "cloth",
    "textile",
    "material",
    "gown",
    "2 piece",
    "skirt",
    "blouse",
]

# Words that strongly suggest rubbish / irrelevant items
BLOCKED_KEYWORDS = [
    "bed",
    "sofa",
    "mattress",
    "pillow",
    "chair",
    "table",
    "beanie",
    "cap",
    "hat",
    "helmet",
    "lingerie",
    "underwear",
    "bra",
    "panties",
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
    "wallet",
    "watch",
    "shoe",
    "sneaker",
    "sock",
]


def normalize_text(value):
    return (value or "").strip().lower()


def get_token():
    res = requests.post(
        f"{BASE_URL}/authentication/getAccessToken",
        json={"apiKey": CJ_API_KEY},
        timeout=30
    )
    res.raise_for_status()
    data = res.json()

    if data.get("result") and data.get("data"):
        return data["data"].get("accessToken")
    return None


def is_relevant_ankara_item(item):
    """
    Decide whether a CJ product looks relevant to an Ankara/African fashion store.
    """
    name = normalize_text(item.get("productNameEn"))
    desc = normalize_text(item.get("description"))
    combined = f"{name} {desc}".strip()

    if not combined:
        return False

    # Reject obvious junk first
    for bad_word in BLOCKED_KEYWORDS:
        if bad_word in combined:
            return False

    # Accept only if it contains at least one useful term
    for good_word in ALLOWED_KEYWORDS:
        if good_word in combined:
            return True

    return False


def fetch_products_for_keyword(token, keyword, page=1, page_size=20):
    """
    Raw CJ fetch for one keyword.
    """
    headers = {"CJ-Access-Token": token}

    res = requests.get(
        f"{BASE_URL}/product/list",
        headers=headers,
        params={
            "productNameEn": keyword,
            "pageNum": page,
            "pageSize": page_size,
        },
        timeout=30
    )
    res.raise_for_status()
    data = res.json()

    if data.get("result") and data.get("data"):
        return data["data"].get("list", [])
    return []


def fetch_clothing(token, page=1):
    """
    Fetch Ankara/African-fashion-related CJ products using multiple search terms,
    then deduplicate and filter them before returning.
    """
    seen_pids = set()
    filtered_products = []

    for keyword in ANKARA_SEARCH_TERMS:
        products = fetch_products_for_keyword(token, keyword, page=page, page_size=20)

        for item in products:
            pid = item.get("pid")
            if not pid or pid in seen_pids:
                continue

            if not is_relevant_ankara_item(item):
                continue

            seen_pids.add(pid)
            filtered_products.append(item)

    return filtered_products
