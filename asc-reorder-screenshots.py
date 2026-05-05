#!/usr/bin/env python3
"""Reorder each app's APP_IPHONE_67 screenshot set so Slay-style shots come first,
followed by the launch screen and populated UI screenshot."""
import json, os, time, urllib.request, urllib.error
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
TKN = jwt.encode({"iss": ISSUER, "iat": now, "exp": now+15*60, "aud": "appstoreconnect-v1"},
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
        return e.code, {"error": e.read().decode()[:600]}

EDIT = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED",
        "METADATA_REJECTED", "WAITING_FOR_REVIEW"}

def get_67_set(app_id):
    s, d = api("GET", f"/v1/apps/{app_id}/appStoreVersions")
    if s != 200: return None
    for v in d.get("data", []):
        if v["attributes"]["appStoreState"] in EDIT:
            s2, d2 = api("GET", f"/v1/appStoreVersions/{v['id']}/appStoreVersionLocalizations")
            for l in d2.get("data", []):
                if l["attributes"]["locale"] == "en-US":
                    s3, d3 = api("GET", f"/v1/appStoreVersionLocalizations/{l['id']}/appScreenshotSets")
                    for s_ in d3.get("data", []):
                        if s_["attributes"]["screenshotDisplayType"] == "APP_IPHONE_67":
                            return s_["id"]
    return None

def list_screenshots(set_id):
    s, d = api("GET", f"/v1/appScreenshotSets/{set_id}/appScreenshots?limit=20")
    return d.get("data", []) if s == 200 else []

# Desired order: slay-01, slay-02, slay-03, then the existing UI shots
PRIORITY = {
    "slay-01.png": 0,
    "slay-02.png": 1,
    "slay-03.png": 2,
    "final-67.png": 3,
    "populated-67.png": 4,
}

for name, app_id in APPS.items():
    print(f"\n=== {name} ===")
    sset = get_67_set(app_id)
    if not sset: print("  ✗ no set"); continue

    items = list_screenshots(sset)
    items.sort(key=lambda x: PRIORITY.get(x["attributes"].get("fileName", ""), 99))
    ordered_ids = [it["id"] for it in items]
    print(f"  → {[it['attributes'].get('fileName') for it in items]}")

    # PATCH the relationship endpoint with ordered IDs.
    body = {"data": [{"type": "appScreenshots", "id": sid} for sid in ordered_ids]}
    s, d = api("PATCH", f"/v1/appScreenshotSets/{sset}/relationships/appScreenshots", body)
    print(f"  reorder: {'✓' if s in (200, 204) else '✗ '+str(s)+' '+str(d)[:200]}")
