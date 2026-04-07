import requests
import uuid
import json
import os
from datetime import datetime

WATCHLIST = [
    {"name": "Nike Dunk Low Panda", "brand": "나이키", "product_id": 0, "kream_id": 116006, "naver_query": "나이키 덩크 로우 판다 DD1391-100", "sizes": ["260","265","270","275","280"]},
    {"name": "Asics Gel-Kayano 14 Cream Black", "brand": "아식스", "product_id": 0, "kream_id": 166924, "naver_query": "아식스 겔 카야노 14 크림 블랙 1201A019-107", "sizes": ["255","260","265","270","275"]},
    {"name": "Jordan 1 Retro High OG Chicago Lost and Found", "brand": "조던", "product_id": 0, "kream_id": 107643, "naver_query": "조던 1 레트로 하이 OG 시카고 DZ5485-612", "sizes": ["265","270","275","280","285"]},
    {"name": "Nike Air Force 1 Low White", "brand": "나이키", "product_id": 0, "kream_id": 3566, "naver_query": "나이키 에어포스 1 로우 화이트 CW2288-111", "sizes": ["260","265","270","275","280"]},
    {"name": "Asics Gel-Nimbus 9 Cream", "brand": "아식스", "product_id": 0, "kream_id": 247631, "naver_query": "아식스 겔 님버스 9 크림 H4E2N-0101", "sizes": ["255","260","265","270","275"]},
]

KREAM_FEE = 0.05
KREAM_INSPECT = 3000
SHIP_COST = 3500

NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")

KREAM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://kream.co.kr/",
    "Origin": "https://kream.co.kr",
}

def get_kream_prices(kream_id):
    url = "https://api.kream.co.kr/api/p/options/display"
    params = {"product_id": kream_id, "picker_type": "sell", "request_key": str(uuid.uuid4())}
    try:
        r = requests.get(url, headers=KREAM_HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        prices = {}
        for item in data.get("content", {}).get("items", []):
            try:
                size = item["title_item"]["text_element"]["default_variation"]["text"]
                price_str = item["description_item"]["text_element"]["default_variation"]["text"]
                price = int(price_str.replace(",", ""))
                if price > 0:
                    prices[size] = price
            except (KeyError, ValueError):
                continue
        return prices
    except Exception as e:
        print(f"  KREAM 오류: {e}")
        return {}

def get_naver_lowest(query):
    if not NAVER_CLIENT_ID:
        return None
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": query, "display": 5, "sort": "asc"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            return None
        item = items[0]
        return {
            "price": int(item.get("lprice", 0)),
            "mall": item.get("mallName", ""),
            "link": item.get("link", ""),
            "title": item.get("title", "").replace("<b>", "").replace("</b>", ""),
            "image": item.get("image", ""),
        }
    except Exception as e:
        print(f"  네이버 오류: {e}")
        return None

def calc(source_price, kream_price):
    fee = kream_price * KREAM_FEE
    net = kream_price - fee - KREAM_INSPECT - SHIP_COST - source_price
    roi = (net / source_price * 100) if source_price > 0 else 0
    return {"net": round(net), "roi": round(roi, 1)}

def main():
    results = []
    for item in WATCHLIST:
        print(f"수집 중: {item['name']}")
        kream_prices = get_kream_prices(item["kream_id"])
        naver = get_naver_lowest(item["naver_query"])

        source_price = naver["price"] if naver else 0
        size_data = []
        best_roi = -999
        best_size = ""

        for size, kream_price in sorted(kream_prices.items()):
            if source_price > 0:
                c = calc(source_price, kream_price)
                size_data.append({"size": size, "kream_price": kream_price, "net": c["net"], "roi": c["roi"]})
                if c["roi"] > best_roi:
                    best_roi = c["roi"]
                    best_size = size
            else:
                size_data.append({"size": size, "kream_price": kream_price, "net": 0, "roi": 0})

        results.append({
            "name": item["name"],
            "brand": item["brand"],
            "kream_id": item["kream_id"],
            "kream_url": f"https://kream.co.kr/products/{item['kream_id']}",
            "naver": naver,
            "source_price": source_price,
            "sizes": size_data,
            "best_roi": best_roi,
            "best_size": best_size,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })

    results.sort(key=lambda x: x["best_roi"], reverse=True)

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "items": results}, f, ensure_ascii=False, indent=2)

    print(f"\n완료! {len(results)}개 상품 수집")
    for r in results:
        if r["best_roi"] > 0:
            print(f"  {r['name']} | {r['best_size']} | ROI {r['best_roi']}%")

if __name__ == "__main__":
    main()
