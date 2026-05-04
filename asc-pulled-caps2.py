#!/usr/bin/env python3
"""Register PulledWidget bundle + enable App Groups & SIWA capabilities on
both Pulled bundles. Xcode auto-creates the App Group on next archive when
-allowProvisioningUpdates + ASC API key is supplied."""
import json, os, time, urllib.request, urllib.parse, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER_ID = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

with open(KEY_PATH) as f: key = f.read()
now = int(time.time())
TKN = jwt.encode({"iss": ISSUER_ID, "iat": now, "exp": now+20*60, "aud": "appstoreconnect-v1"},
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

def find_bundle(identifier):
    q = urllib.parse.urlencode({"filter[identifier]": identifier})
    s, d = api("GET", f"/v1/bundleIds?{q}")
    if s != 200: return None
    for b in d.get("data", []):
        if b["attributes"]["identifier"].lower() == identifier.lower():
            return b["id"]
    return None

def create_bundle(identifier, name):
    s, d = api("POST", "/v1/bundleIds",
               {"data": {"type": "bundleIds",
                         "attributes": {"identifier": identifier, "name": name, "platform": "IOS"}}})
    if s in (200, 201): return d["data"]["id"]
    print(f"  ✗ create {identifier}: {s} {d}")
    return None

def list_capabilities(bundle_id):
    s, d = api("GET", f"/v1/bundleIds/{bundle_id}/bundleIdCapabilities")
    if s != 200: return []
    return [c["attributes"]["capabilityType"] for c in d.get("data", [])]

def enable_capability(bundle_id, cap_type):
    body = {"data": {"type": "bundleIdCapabilities",
                     "attributes": {"capabilityType": cap_type},
                     "relationships": {"bundleId": {"data": {"type": "bundleIds", "id": bundle_id}}}}}
    s, d = api("POST", "/v1/bundleIdCapabilities", body)
    if s in (200, 201): return True
    err = json.dumps(d).lower()
    if s == 409 or "already" in err or "conflict" in err:
        return True
    print(f"    ✗ {cap_type}: {s} {d}")
    return False

# 1. Pulled main bundle (already exists; just enable caps)
print("== Pulled bundle ==")
pulled_bid = find_bundle("com.divinedavis.Pulled")
print(f"  resource id: {pulled_bid}")
existing = list_capabilities(pulled_bid)
print(f"  existing caps: {existing}")
for cap in ["APPLE_ID_AUTH", "APP_GROUPS"]:
    if cap in existing:
        print(f"  ✓ {cap} already enabled")
    elif enable_capability(pulled_bid, cap):
        print(f"  ✓ {cap}")

# 2. PulledWidget bundle (probably doesn't exist; create + enable caps)
print("\n== PulledWidget bundle ==")
widget_id = "com.divinedavis.Pulled.PulledWidget"
widget_bid = find_bundle(widget_id)
if widget_bid:
    print(f"  ✓ already registered ({widget_bid})")
else:
    widget_bid = create_bundle(widget_id, "PulledWidget")
    if not widget_bid: exit(1)
    print(f"  ✓ created ({widget_bid})")
existing = list_capabilities(widget_bid)
print(f"  existing caps: {existing}")
if "APP_GROUPS" in existing:
    print(f"  ✓ APP_GROUPS already enabled")
elif enable_capability(widget_bid, "APP_GROUPS"):
    print(f"  ✓ APP_GROUPS")

print("\nDone — App Group will be auto-created by xcodebuild on next archive with -allowProvisioningUpdates")
