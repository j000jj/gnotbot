import requests
import time
from playwright.sync_api import sync_playwright

WEBHOOK_URL = "https://discord.com/api/webhooks/1476604892817788941/I_20LL6FnqIprH0GmY_EF4_8C__OepKAX2GJPx5S768v3JCgA9cl8RgCcF0YPHXLnrwY"

SEEN = set()
ALGOLIA_KEY = None
KEY_REFRESH_CYCLES = 0

SEARCHES = [
    {"query": "rick owens geobasket", "max_price": 500},
    {"query": "chrome hearts t shirt", "max_price": 200},
    {"query": "chrome hearts hoodie", "max_price": 500},
    {"query": "chrome hearts paper jam", "max_price": 1500},
    {"query": "chrome hearts belt", "max_price": 2500},
    {"query": "chrome hearts bracelet", "max_price": 1000},
    {"query": "chrome hearts pendant", "max_price": 1000},
    {"query": "chrome hearts necklace", "max_price": 1500},
    {"query": "rick owens jeans", "max_price": 300},
]

def get_algolia_key():
    print("Fetching fresh Algolia key...")
    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page()
        api_key = None

        def handle_request(request):
            nonlocal api_key
            if "algolia.net" in request.url:
                key = request.headers.get("x-algolia-api-key")
                if key:
                    api_key = key

        page.on("request", handle_request)
        page.goto("https://www.grailed.com/feed")
        page.wait_for_timeout(5000)
        browser.close()

    if api_key:
        print(f"Got key: {api_key[:10]}...")
    else:
        print("Failed to get key!")
    return api_key

def search_grailed(query, max_price, api_key):
    url = "https://mnrwefss2q-dsn.algolia.net/1/indexes/*/queries"
    params = {
        "x-algolia-agent": "Algolia for JavaScript (4.14.3); Browser",
        "x-algolia-application-id": "MNRWEFSS2Q",
        "x-algolia-api-key": api_key,
    }
    payload = {
        "requests": [{
            "indexName": "Listing_by_date_added_production",
            "query": query,
            "filters": f"price < {max_price}",
            "hitsPerPage": 20,
        }]
    }
    r = requests.post(url, params=params, json=payload)
    print(r.status_code, r.text[:300])
    return r.json()["results"][0].get("hits", [])

def send_to_discord(item):
    photo_url = item.get("cover_photo", {}).get("url", "")
    listing_url = f"https://www.grailed.com/listings/{item['objectID']}"
    payload = {
        "embeds": [{
            "title": item.get("title", "New Listing"),
            "url": listing_url,
            "color": 0x00b4d8,
            "fields": [
                {"name": "Price", "value": f"${item['price']}", "inline": True},
                {"name": "Size", "value": item.get("size", "?"), "inline": True},
                {"name": "Condition", "value": item.get("condition", "?"), "inline": True},
            ],
            "thumbnail": {"url": photo_url} if photo_url else {},
            "footer": {"text": "Grailed Deal Alert"}
        }]
    }
    r = requests.post(WEBHOOK_URL, json=payload)
    print(f"Discord response: {r.status_code}")

def run():
    global KEY_REFRESH_CYCLES
    print("Bot running...")
    api_key = get_algolia_key()

    while True:
        # Refresh key every 30 minutes (180 cycles x 10 seconds)
        if KEY_REFRESH_CYCLES > 0 and KEY_REFRESH_CYCLES % 180 == 0:
            print("Refreshing Algolia key...")
            api_key = get_algolia_key()

        for search in SEARCHES:
            try:
                listings = search_grailed(search["query"], search["max_price"], api_key)
                print(f"Found {len(listings)} listings for '{search['query']}'")
                for item in listings:
                    if item["objectID"] not in SEEN:
                        SEEN.add(item["objectID"])
                        send_to_discord(item)
                        print(f"Sent: {item.get('title')}")
            except Exception as e:
                print(f"Error: {e}")
                # Refresh key immediately if 403
                if "results" in str(e) or "403" in str(e):
                    print("Key likely expired, refreshing...")
                    api_key = get_algolia_key()

        KEY_REFRESH_CYCLES += 1
        time.sleep(10)

run()
