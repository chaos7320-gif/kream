"""
KREAM 시세 수집기 v2
- 실제 API: https://api.kream.co.kr/api/p/options/display
- picker_type=sell → 즉시판매가 (내가 판매할 때 받는 금액)
- picker_type=buy  → 즉시구매가 (구매자가 지불하는 금액)
- 실행: python kream_price_tracker.py
"""

import requests
import uuid
from datetime import datetime

WATCHLIST = [
    {
        "name": "(W) 나이키 문 슈 서밋 화이트 팀 크림슨",
        "product_id": 852618,
        "source_price": 139000,
        "source_size": "W240",   # KREAM은 "W220", "W225" 형식
    },
    # 추가 예시:
    # {"name": "Nike Dunk Low Panda", "product_id": 123456, "source_price": 130000, "source_size": "270"},
]

KREAM_FEE_RATE  = 0.05
KREAM_INSPECT   = 3000
SHIP_TO_KREAM   = 3500

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://kream.co.kr/",
    "Origin": "https://kream.co.kr",
}

def get_kream_prices(product_id: int, picker_type: str = "sell") -> dict:
    """사이즈별 시세 반환. 예: {"W240": 140000, "W245": 183000, ...}"""
    url = "https://api.kream.co.kr/api/p/options/display"
    params = {
        "product_id": product_id,
        "picker_type": picker_type,
        "request_key": str(uuid.uuid4()),
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [오류] {e}")
        return {}

    prices = {}
    for item in data.get("content", {}).get("items", []):
        try:
            size = item["title_item"]["text_element"]["default_variation"]["text"]
            price_str = item["description_item"]["text_element"]["default_variation"]["text"]
            price = int(price_str.replace(",", ""))
            prices[size] = price
        except (KeyError, ValueError):
            continue
    return prices

def calc_profit(source_price: int, sell_price: int) -> dict:
    fee = sell_price * KREAM_FEE_RATE
    net = sell_price - fee - KREAM_INSPECT - SHIP_TO_KREAM - source_price
    roi = (net / source_price * 100) if source_price > 0 else 0
    return {"net": round(net), "roi": round(roi, 1), "fee": round(fee)}

def run():
    print(f"\n{'='*62}")
    print(f"  KREAM 시세 트래커  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*62}\n")

    opportunities = []

    for item in WATCHLIST:
        name      = item["name"]
        pid       = item["product_id"]
        src_price = item["source_price"]
        src_size  = item["source_size"]

        print(f"▶ {name}")
        print(f"  ID: {pid}  소싱가: {src_price:,}원  사이즈: {src_size}")

        sell_prices = get_kream_prices(pid, picker_type="sell")

        if not sell_prices:
            print("  → 데이터 없음\n")
            continue

        print(f"\n  {'사이즈':<8} {'즉시판매가':>12} {'수수료':>9} {'순수익':>10} {'ROI':>7}")
        print(f"  {'-'*51}")

        target_result = None

        for size, sell_price in sorted(sell_prices.items()):
            if sell_price == 0:
                print(f"  {size:<8} {'시세없음':>12}")
                continue
            r = calc_profit(src_price, sell_price)
            flag  = " 🔥" if r["roi"] >= 15 else (" ✅" if r["roi"] >= 10 else "")
            mark  = " ◀ 내 사이즈" if size == src_size else ""
            print(f"  {size:<8} {sell_price:>11,}원 {r['fee']:>8,}원 {r['net']:>9,}원 {r['roi']:>6}%{flag}{mark}")
            if size == src_size:
                target_result = {**r, "sell_price": sell_price}

        if target_result:
            print(f"\n  → [{src_size}] 순수익: {target_result['net']:,}원  ROI: {target_result['roi']}%")
            if target_result["roi"] >= 10:
                opportunities.append({**item, **target_result})
        else:
            print(f"\n  → 사이즈 {src_size} 시세 없음")
        print()

    print(f"{'='*62}")
    if opportunities:
        print(f"  🔥 ROI 10% 이상 매수 추천 ({len(opportunities)}건)\n")
        for o in opportunities:
            print(f"  {o['name']}  {o['source_size']}  즉시판매가 {o['sell_price']:,}원  순수익 {o['net']:,}원  ROI {o['roi']}%")
    else:
        print("  현재 ROI 10% 이상 기회 없음")
    print(f"{'='*62}\n")

if __name__ == "__main__":
    run()
