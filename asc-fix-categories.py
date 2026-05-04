#!/usr/bin/env python3
"""Categories must be PATCHed on the appInfo resource itself with embedded
relationships, not via /relationships/primaryCategory (that endpoint is read-only)."""
import json, os, time, urllib.request, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER_ID = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

APPS = {
    "Drafted":  {"id": "6766302520", "primary": "PRODUCTIVITY",  "secondary": "SOCIAL_NETWORKING"},
    "Scripted": {"id": "6766312207", "primary": "LIFESTYLE",     "secondary": "HEALTH_AND_FITNESS"},
    "Pulled":   {"id": "6766311239", "primary": "LIFESTYLE",     "secondary": "ENTERTAINMENT"},
    "Auracard": {"id": "6766311537", "primary": "ENTERTAINMENT", "secondary": "LIFESTYLE"},
    "Shelf":    {"id": "6766311807", "primary": "BOOKS",         "secondary": "LIFESTYLE"},
}

def token():
    with open(KEY_PATH) as f: key = f.read()
    now = int(time.time())
    return jwt.encode({"iss": ISSUER_ID, "iat": now, "exp": now+20*60, "aud": "appstoreconnect-v1"},
                      key, algorithm="ES256", headers={"kid": KEY_ID, "typ": "JWT"})

TKN = token()

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

EDITABLE = {"PREPARE_FOR_SUBMISSION", "WAITING_FOR_REVIEW", "DEVELOPER_REJECTED",
            "REJECTED", "METADATA_REJECTED", "INVALID_BINARY"}

for name, cfg in APPS.items():
    print(f"\n=== {name} ({cfg['id']}) ===")
    s, d = api("GET", f"/v1/apps/{cfg['id']}/appInfos")
    if s != 200:
        print(f"  ✗ list: {s} {d}"); continue
    app_infos = d.get("data", [])
    editable = next((ai for ai in app_infos if ai["attributes"]["state"] in EDITABLE),
                    app_infos[0] if app_infos else None)
    if not editable:
        print("  ✗ no appInfo"); continue
    aid = editable["id"]
    print(f"  appInfo: {aid}")

    # PATCH the appInfo with category relationships embedded
    s, d = api("PATCH", f"/v1/appInfos/{aid}",
               {"data": {"type": "appInfos", "id": aid,
                         "relationships": {
                             "primaryCategory":   {"data": {"type": "appCategories", "id": cfg["primary"]}},
                             "secondaryCategory": {"data": {"type": "appCategories", "id": cfg["secondary"]}}
                         }}})
    if s in (200, 204):
        print(f"  ✓ {cfg['primary']} / {cfg['secondary']}")
    else:
        print(f"  ✗ {s}: {d}")
