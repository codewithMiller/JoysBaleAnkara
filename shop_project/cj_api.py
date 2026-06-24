import requests
import os

CJ_API_KEY = os.environ.get("CJ_API_KEY")
BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"

def get_token():
    res = requests.post(
        f"{BASE_URL}/authentication/getAccessToken",
        json={"apiKey": CJ_API_KEY}
    )
    data = res.json()
    if data.get("result"):
        return data["data"]["accessToken"]
    return None

def fetch_clothing(token, keyword="Ankara fabric", page=1):
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
