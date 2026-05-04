#!/usr/bin/env python3
"""Set prices using PATCH on the subscription with included transient subscriptionPrices."""
import json, os, time, urllib.request, urllib.parse, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER_ID = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

SUBS = {
    "Drafted":  ("6766321262", "4.99"),
    "Scripted": ("6766321323", "2.99"),
    "Pulled":   ("6766321326", "0.99"),
    "Auracard": ("6766321264", "1.99"),
    "Shelf":    ("6766321439", "1.99"),
}

with open(KEY_PATH) as f: key = f.read()
now = int(time.time())
TKN = jwt.encode({"iss": ISSUER_ID, "iat": now, "exp": now+15*60, "aud": "appstoreconnect-v1"},
                 key, algorithm="ES256", headers={"kid": KEY_ID, "typ": "JWT"})

def api(method, path, body=None):
    url = f"{API}{path}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": f"Bearer {TKN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:1500]}

def find_price_point(sub_id, customer_price):
    q = urllib.parse.urlencode({"filter[territory]": "USA", "limit": "200"})
    s, d = api("GET", f"/v1/subscriptions/{sub_id}/pricePoints?{q}")
    if s != 200: return None
    for pp in d.get("data", []):
        if pp["attributes"].get("customerPrice") == customer_price:
            return pp["id"]
    return None

for name, (sid, price) in SUBS.items():
    print(f"\n=== {name} → ${price}/mo ===")
    pp_id = find_price_point(sid, price)
    if not pp_id:
        print(f"  ✗ price point not found"); continue

    # PATCH the subscription with the price as a transient included resource
    body = {
        "data": {
            "type": "subscriptions",
            "id": sid,
            "relationships": {
                "prices": {
                    "data": [{"type": "subscriptionPrices", "id": "${new-price}"}]
                }
            }
        },
        "included": [
            {
                "type": "subscriptionPrices",
                "id": "${new-price}",
                "attributes": {"preserveCurrentPrice": False, "startDate": None},
                "relationships": {
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": pp_id}},
                    "territory": {"data": {"type": "territories", "id": "USA"}}
                }
            }
        ]
    }
    s, d = api("PATCH", f"/v1/subscriptions/{sid}", body)
    print(f"  PATCH → {s}")
    if s not in (200, 204):
        print(f"  {d}")
    else:
        print(f"  ✓ ${price} set")
