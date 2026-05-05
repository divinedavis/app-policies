#!/usr/bin/env python3
"""Set all 5 apps to Free + worldwide via ASC API.

Pricing: POST /v1/appPriceSchedules with transient-ID manualPrices linking
to the per-app Free ($0.00) price point.

Availability: POST /v1/appAvailabilitiesV2 with all territories. If one already
exists (status 200 on GET), PATCH instead.
"""
import json, os, time, urllib.request, urllib.parse, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

APPS = {
    "Drafted":  "6766302520",
    "Scripted": "6766312207",
    "Pulled":   "6766311239",
    "Auracard": "6766311537",
    "Shelf":    "6766311807",
}

with open(KEY_PATH) as f: key = f.read()
now = int(time.time())
TKN = jwt.encode({"iss": ISSUER, "iat": now, "exp": now+20*60, "aud": "appstoreconnect-v1"},
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
        return e.code, {"error": e.read().decode()[:800]}

def find_free_price_point(app_id):
    s, d = api("GET", f"/v1/apps/{app_id}/appPricePoints?filter[territory]=USA&limit=200")
    if s != 200: return None
    for pp in d.get("data", []):
        if pp["attributes"].get("customerPrice") in ("0.0", "0.00"):
            return pp["id"]
    return None

def list_all_territory_ids():
    """All ~175 ASC territory IDs."""
    ids = []
    cursor = "/v1/territories?limit=200"
    while cursor:
        s, d = api("GET", cursor)
        if s != 200: break
        ids.extend([t["id"] for t in d.get("data", [])])
        next_link = d.get("links", {}).get("next")
        cursor = next_link.replace(API, "") if next_link else None
    return ids

def set_pricing(name, app_id):
    pp_id = find_free_price_point(app_id)
    if not pp_id:
        return f"  ✗ no Free price point"
    body = {
        "data": {
            "type": "appPriceSchedules",
            "relationships": {
                "app": {"data": {"type": "apps", "id": app_id}},
                "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
                "manualPrices": {"data": [{"type": "appPrices", "id": "${free-price}"}]}
            }
        },
        "included": [
            {
                "type": "appPrices",
                "id": "${free-price}",
                "attributes": {"startDate": None},
                "relationships": {
                    "appPricePoint": {"data": {"type": "appPricePoints", "id": pp_id}}
                }
            }
        ]
    }
    s, d = api("POST", "/v1/appPriceSchedules", body)
    if s in (200, 201): return f"  ✓ Free pricing set"
    return f"  ✗ pricing: {s} {d}"

def set_availability(name, app_id, territories):
    # POST /v2/appAvailabilities to create a worldwide availability set
    body = {
        "data": {
            "type": "appAvailabilities",
            "attributes": {"availableInNewTerritories": True},
            "relationships": {
                "app": {"data": {"type": "apps", "id": app_id}},
                "territoryAvailabilities": {
                    "data": [{"type": "territoryAvailabilities", "id": f"${{ta-{i}}}"}
                              for i, _ in enumerate(territories)]
                }
            }
        },
        "included": [
            {
                "type": "territoryAvailabilities",
                "id": f"${{ta-{i}}}",
                "attributes": {"available": True},
                "relationships": {
                    "territory": {"data": {"type": "territories", "id": t}}
                }
            }
            for i, t in enumerate(territories)
        ]
    }
    s, d = api("POST", "/v2/appAvailabilities", body)
    if s in (200, 201): return f"  ✓ Available in {len(territories)} territories"
    return f"  ✗ availability: {s} {d}"

print("Fetching territory list…")
territories = list_all_territory_ids()
print(f"  → {len(territories)} territories")

for name, app_id in APPS.items():
    print(f"\n=== {name} ({app_id}) ===")
    print(set_pricing(name, app_id))
    print(set_availability(name, app_id, territories))
