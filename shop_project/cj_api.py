import os
import time
import requests

CJ_API_KEY = os.environ.get("CJ_API_KEY")
BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"

ANKARA_SEARCH_TERMS = [
    "ankara fabric",
    "african wax print fabric",
    "african print fabric",
    "ankara dress",
]

ALLOWED_KEYWORDS = [
    "ankara",
    "african print",
    "wax print",
    "kitenge",
    "dashiki",
    "african dress",
    "ankara dress",
    "fabric",
    "cloth",
    "textile",
    "material",
    "gown",
    "skirt",
    "blouse",
]

BLOCKED_KEYWORDS = [
    "bed", "sofa", "mattress", "pillow", "chair", "table",
    "beanie", "cap", "hat", "helmet",
    "lingerie", "underwear", "bra", "panties", "bikini", "swim",
    "earring", "necklace", "bracelet", "ring",
    "pet", "cat", "dog", "toy", "baseball",
    "bedroom", "furniture", "curtain", "rug",
    "wallet", "watch", "shoe", "sneaker", "sock",
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

    if any(bad in combined for bad in BLOCKED_KEYWORDS):
        return False

    return any(good in combined for good in ALLOWED_KEYWORDS)

def fetch_products_for_keyword(token, keyword, page=1, page_size=20, retries=3):
    headers = {"CJ-Access-Token": token}

    for attempt in range(retries):
        try:
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


def fetch_clothing(token, keyword, page=1):
    headers = {"CJ-Access-Token": token}
    res = requests.get(
        f"{BASE_URL}/product/list",
        headers=headers,
        params={
            "productNameEn": keyword,
            "pageNum": page,
            "pageSize": 20
        }
    )
    data = res.json()
    if data.get("result"):
        return data["data"]["list"]
    return []
