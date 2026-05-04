#!/usr/bin/env python3
"""Upload App Store screenshots for all 5 apps to en-US 6.7" iPhone display.

Flow per file:
  1. POST /v1/appScreenshots (reserve upload, returns uploadOperations)
  2. PUT each chunk to its presigned URL with provided headers
  3. PATCH /v1/appScreenshots/{id} with sourceFileChecksum + uploaded=true
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER_ID = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"
DISPLAY_TYPE = "APP_IPHONE_67"   # 1290x2796

APPS = {
    "Drafted":  "6766302520",
    "Scripted": "6766312207",
    "Pulled":   "6766311239",
    "Auracard": "6766311537",
    "Shelf":    "6766311807",
}

def token():
    with open(KEY_PATH) as f: key = f.read()
    now = int(time.time())
    return jwt.encode({"iss": ISSUER_ID, "iat": now, "exp": now+15*60, "aud": "appstoreconnect-v1"},
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

def md5_of_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def get_editable_version_loc(app_id):
    s, d = api("GET", f"/v1/apps/{app_id}/appStoreVersions")
    if s != 200:
        print(f"  ✗ list versions: {s} {d}")
        return None
    versions = d.get("data", [])
    editable = next((v for v in versions
                     if v["attributes"]["appStoreState"] in
                     ("PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED",
                      "METADATA_REJECTED", "WAITING_FOR_REVIEW")), None)
    if not editable:
        print(f"  ✗ no editable version")
        return None
    s, d = api("GET", f"/v1/appStoreVersions/{editable['id']}/appStoreVersionLocalizations")
    if s != 200:
        print(f"  ✗ list version locs: {s} {d}")
        return None
    en = next((l for l in d.get("data", []) if l["attributes"]["locale"] == "en-US"), None)
    return en["id"] if en else None

def get_or_create_screenshot_set(version_loc_id):
    # list existing
    s, d = api("GET", f"/v1/appStoreVersionLocalizations/{version_loc_id}/appScreenshotSets")
    if s == 200:
        for sset in d.get("data", []):
            if sset["attributes"]["screenshotDisplayType"] == DISPLAY_TYPE:
                return sset["id"]
    # create
    s, d = api("POST", "/v1/appScreenshotSets",
               {"data": {"type": "appScreenshotSets",
                         "attributes": {"screenshotDisplayType": DISPLAY_TYPE},
                         "relationships": {"appStoreVersionLocalization":
                            {"data": {"type": "appStoreVersionLocalizations", "id": version_loc_id}}}}})
    if s in (200, 201):
        return d["data"]["id"]
    print(f"  ✗ create screenshot set: {s} {d}")
    return None

def existing_screenshots_in_set(set_id):
    s, d = api("GET", f"/v1/appScreenshotSets/{set_id}/appScreenshots")
    if s != 200: return []
    return d.get("data", [])

def delete_screenshot(ssid):
    s, d = api("DELETE", f"/v1/appScreenshots/{ssid}")
    return s in (200, 204)

def upload_one(set_id, file_path):
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    s, d = api("POST", "/v1/appScreenshots",
               {"data": {"type": "appScreenshots",
                         "attributes": {"fileName": file_name, "fileSize": file_size},
                         "relationships": {"appScreenshotSet":
                            {"data": {"type": "appScreenshotSets", "id": set_id}}}}})
    if s not in (200, 201):
        print(f"    ✗ reserve {file_name}: {s} {d}")
        return False
    ss = d["data"]
    ss_id = ss["id"]
    operations = ss["attributes"]["uploadOperations"]

    with open(file_path, "rb") as f:
        for op in operations:
            f.seek(op["offset"])
            chunk = f.read(op["length"])
            req = urllib.request.Request(op["url"], data=chunk, method=op["method"])
            for h in op["requestHeaders"]:
                req.add_header(h["name"], h["value"])
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    if r.status not in (200, 201, 204):
                        print(f"    ✗ chunk PUT status {r.status}")
                        return False
            except urllib.error.HTTPError as e:
                print(f"    ✗ chunk PUT HTTP {e.code}: {e.read()[:200]}")
                return False

    checksum = md5_of_file(file_path)
    s, d = api("PATCH", f"/v1/appScreenshots/{ss_id}",
               {"data": {"type": "appScreenshots", "id": ss_id,
                         "attributes": {"uploaded": True, "sourceFileChecksum": checksum}}})
    if s not in (200, 204):
        print(f"    ✗ commit {file_name}: {s} {d}")
        return False
    print(f"    ✓ {file_name}")
    return True

def main():
    for name, app_id in APPS.items():
        print(f"\n== {name} ({app_id}) ==")
        vloc = get_editable_version_loc(app_id)
        if not vloc:
            continue
        sset = get_or_create_screenshot_set(vloc)
        if not sset:
            continue
        # Clear existing screenshots in this set so re-runs are idempotent
        existing = existing_screenshots_in_set(sset)
        if existing:
            print(f"  removing {len(existing)} existing screenshots")
            for ss in existing:
                delete_screenshot(ss["id"])
        # Upload our 3 in order
        sdir = f"/tmp/screenshots/{name}"
        files = sorted(os.path.join(sdir, f) for f in os.listdir(sdir) if f.endswith(".png"))
        for fp in files:
            upload_one(sset, fp)

if __name__ == "__main__":
    main()
