import os
import time
import requests
import re # Added for strict word filtering

CJ_API_KEY = os.environ.get("CJ_API_KEY")
BASE_URL = "https://cjdropshipping.com"

ANKARA_SEARCH_TERMS = [
    "textile fabric", "wax print fabric", "cotton fabric", "polyester fabric",
    "lace fabric", "chiffon fabric", "ankara fabric", "african print fabric",
    "satin fabric", "velvet fabric", "georgette fabric", "brocade fabric", "sequin fabric",
]

ALLOWED_KEYWORDS = [
    "fabric", "textile", "cloth", "material", "yardage", "yard", "meter",
    "metres", "wax print", "ankara", "kitenge", "cotton", "polyester",
    "chiffon", "satin", "lace", "velvet", "georgette", "brocade",
    "sequin", "crepe", "organza", "tulle", "denim", "silk", "linen",
]

BLOCKED_KEYWORDS = [
    # garments & swimwear
    "dress", "gown", "skirt", "blouse", "shirt", "trouser", "pant", "pants",
    "jacket", "coat", "suit", "jumpsuit", "romper", "top", "tee", "t-shirt",
    "hoodie", "sweater", "cardigan", "vest", "shorts", "wear", "clothing",
    "bikini", "swim", "swimsuit", "swimwear", "bathing", "monokini", "lingerie", "underwear", "bra", "panties",
    # accessories & home finished goods
    "earring", "necklace", "bracelet", "ring", "watch", "wallet",
    "shoe", "sneaker", "boot", "heel", "sandal", "sock", "socks", "bag", "purse",
    "hat", "cap", "beanie", "helmet", "scarf", "glove", "gloves",
    "bed", "sofa", "mattress", "pillow", "chair", "table", "bedroom", "furniture",
    "curtain", "rug", "blanket", "towel", "bedsheet", "pet", "cat", "dog", "toy",
]

def normalize_text(value):
    return (value or "").strip().lower()

def get_token():
    try:
        res = requests.post(
            f"{BASE_URL}/authentication/getAccessToken",
            json={"apiKey": CJ_API_KEY},
            timeout=30
        )
        res.raise_for_status()
        data = res.json()
        if data.get("result") and data.get("data"):
            return data["data"].get("accessToken")
    except requests.RequestException as e:
        print(f"CJ auth error: {e}")
    return None

def is_relevant_ankara_item(item):
    name = normalize_text(item.get("productNameEn"))
    desc = normalize_text(item.get("description"))
    combined = f"{name} {desc}".strip()

    if not combined:
        return False

    # Extract distinct whole words
    words = set(re.findall(r'\b[a-z]+\b', combined))

    # Strict Check 1: If any standalone word matches our blocked list, reject it
    if any(bad in words for bad in BLOCKED_KEYWORDS):
        return False

    # Strict Check 2: Protect against phrase variations like "two piece" or "swim suit"
    if any(phrase in combined for phrase in ["swim", "bikini", "piece suit", "lingerie"]):
        return False

    # Strict Check 3: Must include at least one valid fabric identifier word
    return any(good in words for good in ALLOWED_KEYWORDS)

def fetch_products_for_keyword(token, keyword, page=1, page_size=20, retries=3, category_id="A04"):
    # "A04" is the common top-level CJ category prefix for Home Textiles / Fabrics
    headers = {"CJ-Access-Token": token}
    params = {
        "productNameEn": keyword,
        "pageNum": page,
        "pageSize": page_size,
    }
    if category_id:
        params["categoryId"] = category_id

    for attempt in range(retries):
        try:
            res = requests.get(
                f"{BASE_URL}/product/list",
                headers=headers,
                params=params,
                timeout=30
            )

            if res.status_code == 429:
                wait_time = 5 * (attempt + 1)
                print(f"[CJ] Rate limited on '{keyword}' page {page}. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue

            res.raise_for_status()
            data = res.json()

            if data.get("result") and data.get("data"):
                return data["data"].get("list", [])
            return []

        except requests.RequestException as e:
            print(f"[CJ] Error fetching '{keyword}' page {page}: {e}")
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
            else:
                return []
    return []

def fetch_clothing(token, keyword, page=1, category_id="A04"):
    """Updated to include optional categoryId filtering directly inside parameters"""
    headers = {"CJ-Access-Token": token}
    params = {
        "productNameEn": keyword,
        "pageNum": page,
        "pageSize": 20
    }
    if category_id:
        params["categoryId"] = category_id

    try:
        res = requests.get(f"{BASE_URL}/product/list", headers=headers, params=params, timeout=30)
        data = res.json()
        if data.get("result") and data.get("data"):
            return data["data"].get("list", [])
    except Exception as e:
        print(f"Error in fetch_clothing: {e}")
    return []
