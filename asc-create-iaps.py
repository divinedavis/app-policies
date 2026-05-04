#!/usr/bin/env python3
"""Create one auto-renewing subscription per app via ASC API.

For each app:
  1. POST /v1/subscriptionGroups — create "<App> Pro" group
  2. POST /v1/subscriptions — create the subscription product with productId
  3. POST /v1/subscriptionLocalizations — en-US display name + description
  4. POST /v1/subscriptionGroupLocalizations — en-US group name (required)
  5. POST /v1/subscriptionPrices — set USA price (best-effort)
"""
import json, os, time, urllib.request, urllib.parse, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER_ID = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

APPS = {
    "Drafted":  {"id": "6766302520", "price": "4.99", "subDesc": "Unlimited drafts. No daily limit."},
    "Scripted": {"id": "6766312207", "price": "2.99", "subDesc": "Unlimited entries plus aesthetic themes."},
    "Pulled":   {"id": "6766311239", "price": "0.99", "subDesc": "Premium widget designs and ad-free."},
    "Auracard": {"id": "6766311537", "price": "1.99", "subDesc": "Unlimited readings, Deep Aura, and ad-free."},
    "Shelf":    {"id": "6766311807", "price": "1.99", "subDesc": "Premium themes and aesthetic widgets."},
}

with open(KEY_PATH) as f: key = f.read()
now = int(time.time())
TKN = jwt.encode({"iss": ISSUER_ID, "iat": now, "exp": now+15*60, "aud": "appstoreconnect-v1"},
                 key, algorithm="ES256", headers={"kid": KEY_ID, "typ": "JWT"})

def api(method, path, body=None):
    url = f"{API}{path}" if path.startswith("/") else path
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": f"Bearer {TKN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:1500]}

def find_group(app_id, ref_name):
    s, d = api("GET", f"/v1/apps/{app_id}/subscriptionGroups?limit=200")
    if s != 200: return None
    for g in d.get("data", []):
        if g["attributes"].get("referenceName") == ref_name:
            return g["id"]
    return None

def find_subscription(group_id, product_id):
    s, d = api("GET", f"/v1/subscriptionGroups/{group_id}/subscriptions?limit=200")
    if s != 200: return None
    for sub in d.get("data", []):
        if sub["attributes"].get("productId") == product_id:
            return sub["id"]
    return None

def find_loc(parent_path, locale):
    s, d = api("GET", parent_path)
    if s != 200: return None
    for l in d.get("data", []):
        if l["attributes"].get("locale") == locale:
            return l["id"]
    return None

def find_price_point(sub_id, customer_price, territory="USA"):
    """USA price points for a subscription. Returns the pricePoint id matching the price."""
    q = urllib.parse.urlencode({"filter[territory]": territory, "limit": "200"})
    s, d = api("GET", f"/v1/subscriptions/{sub_id}/pricePoints?{q}")
    if s != 200:
        print(f"      ✗ price points lookup: {s} {d}")
        return None
    for pp in d.get("data", []):
        if pp["attributes"].get("customerPrice") == customer_price:
            return pp["id"]
    # Sample first few for debugging
    sample = [pp["attributes"].get("customerPrice") for pp in d.get("data", [])[:5]]
    print(f"      ✗ no price point matching {customer_price} (sample: {sample})")
    return None

def fill_app(name, cfg):
    print(f"\n=== {name} ({cfg['id']}) ===")
    product_id = f"com.divinedavis.{name}.pro.monthly"
    group_ref = f"{name}Pro"
    group_localized = f"{name} Pro"

    # 1. group
    gid = find_group(cfg["id"], group_ref)
    if gid:
        print(f"  ✓ group exists ({gid})")
    else:
        s, d = api("POST", "/v1/subscriptionGroups",
                   {"data": {"type": "subscriptionGroups",
                             "attributes": {"referenceName": group_ref},
                             "relationships": {"app": {"data": {"type": "apps", "id": cfg["id"]}}}}})
        if s in (200, 201):
            gid = d["data"]["id"]
            print(f"  ✓ created group ({gid})")
        else:
            print(f"  ✗ create group: {s} {d}")
            return

    # 2. subscription
    sid = find_subscription(gid, product_id)
    if sid:
        print(f"  ✓ subscription exists ({sid})")
    else:
        s, d = api("POST", "/v1/subscriptions",
                   {"data": {"type": "subscriptions",
                             "attributes": {
                                 "name": f"{name} Pro Monthly",
                                 "productId": product_id,
                                 "subscriptionPeriod": "ONE_MONTH",
                                 "familySharable": False,
                                 "groupLevel": 1,
                             },
                             "relationships": {"group":
                                {"data": {"type": "subscriptionGroups", "id": gid}}}}})
        if s in (200, 201):
            sid = d["data"]["id"]
            print(f"  ✓ created subscription ({sid})")
        else:
            print(f"  ✗ create subscription: {s} {d}")
            return

    # 3. group localization (en-US name) — required for App Store display
    gloc_id = find_loc(f"/v1/subscriptionGroups/{gid}/subscriptionGroupLocalizations", "en-US")
    if gloc_id:
        print(f"  ✓ group loc exists")
    else:
        s, d = api("POST", "/v1/subscriptionGroupLocalizations",
                   {"data": {"type": "subscriptionGroupLocalizations",
                             "attributes": {"locale": "en-US", "name": group_localized,
                                            "customAppName": None},
                             "relationships": {"subscriptionGroup":
                                {"data": {"type": "subscriptionGroups", "id": gid}}}}})
        if s in (200, 201):
            print(f"  ✓ created group loc en-US")
        else:
            print(f"  ✗ create group loc: {s} {d}")

    # 4. subscription localization (en-US display name + description)
    sloc_id = find_loc(f"/v1/subscriptions/{sid}/subscriptionLocalizations", "en-US")
    if sloc_id:
        print(f"  ✓ sub loc exists")
    else:
        s, d = api("POST", "/v1/subscriptionLocalizations",
                   {"data": {"type": "subscriptionLocalizations",
                             "attributes": {"locale": "en-US",
                                            "name": f"{name} Pro",
                                            "description": cfg["subDesc"]},
                             "relationships": {"subscription":
                                {"data": {"type": "subscriptions", "id": sid}}}}})
        if s in (200, 201):
            print(f"  ✓ created sub loc en-US")
        else:
            print(f"  ✗ create sub loc: {s} {d}")

    # 5. set USA price
    pp_id = find_price_point(sid, cfg["price"])
    if not pp_id:
        return
    s, d = api("POST", "/v1/subscriptionPrices",
               {"data": {"type": "subscriptionPrices",
                         "attributes": {"preserveCurrentPrice": False, "startDate": None},
                         "relationships": {
                             "subscription":           {"data": {"type": "subscriptions", "id": sid}},
                             "territory":              {"data": {"type": "territories", "id": "USA"}},
                             "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": pp_id}}
                         }}})
    if s in (200, 201):
        print(f"  ✓ set USA price ${cfg['price']}/mo")
    else:
        # 409 conflict = already priced, fine
        if s == 409:
            print(f"  ✓ price already set")
        else:
            print(f"  ✗ set price: {s} {d}")

for name, cfg in APPS.items():
    fill_app(name, cfg)
