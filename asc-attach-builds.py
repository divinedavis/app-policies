#!/usr/bin/env python3
"""Attach the latest VALID TestFlight build to each app's editable App Store
version so the icon appears in ASC's app list (and the version is one click
from Submit for Review)."""
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
        "METADATA_REJECTED", "WAITING_FOR_REVIEW", "INVALID_BINARY"}

for name, app_id in APPS.items():
    print(f"\n=== {name} ===")

    # 1. Find the latest VALID build
    s, d = api("GET", f"/v1/apps/{app_id}/builds?limit=200")
    if s != 200: print(f"  ✗ list builds: {s} {d}"); continue
    # Sort newest first by uploadedDate locally since the relationship endpoint
    # disallows the sort param.
    builds = sorted(d.get("data", []),
                    key=lambda b: b["attributes"].get("uploadedDate", ""),
                    reverse=True)
    valid_builds = [b for b in builds
                    if b["attributes"].get("processingState") == "VALID"]
    if not valid_builds:
        print(f"  ✗ no VALID build (states: {[b['attributes'].get('processingState') for b in d.get('data',[])]})")
        continue
    build = valid_builds[0]
    build_id = build["id"]
    build_v = build["attributes"]["version"]
    print(f"  latest VALID build: 1.0 ({build_v}) — {build_id}")

    # 2. Find the editable App Store version
    s, d = api("GET", f"/v1/apps/{app_id}/appStoreVersions")
    if s != 200: print(f"  ✗ list versions: {s} {d}"); continue
    editable = next((v for v in d.get("data", [])
                     if v["attributes"]["appStoreState"] in EDIT), None)
    if not editable:
        print(f"  ✗ no editable version"); continue
    version_id = editable["id"]
    print(f"  version: {version_id}")

    # 3. Attach the build
    s, d = api("PATCH", f"/v1/appStoreVersions/{version_id}/relationships/build",
               {"data": {"type": "builds", "id": build_id}})
    print(f"  attach: {'✓' if s in (200, 204) else '✗ '+str(s)+' '+str(d)[:200]}")
