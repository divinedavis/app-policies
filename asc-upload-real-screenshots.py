#!/usr/bin/env python3
"""Upload real captured screenshots:
- final-01.png (1320x2868) → APP_IPHONE_69 set (new set)
- final-67.png (1290x2796) → APP_IPHONE_67 set (appended after the 3 marketing graphics)
"""
import hashlib, json, os, time, urllib.parse, urllib.request, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER_ID = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
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

def md5_of_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()

def get_editable_version_loc(app_id):
    s, d = api("GET", f"/v1/apps/{app_id}/appStoreVersions")
    if s != 200: return None
    for v in d.get("data", []):
        if v["attributes"]["appStoreState"] in ("PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED",
                                                 "REJECTED", "METADATA_REJECTED", "WAITING_FOR_REVIEW"):
            s2, d2 = api("GET", f"/v1/appStoreVersions/{v['id']}/appStoreVersionLocalizations")
            if s2 != 200: return None
            for l in d2.get("data", []):
                if l["attributes"]["locale"] == "en-US": return l["id"]
    return None

def get_or_create_set(version_loc_id, display_type):
    s, d = api("GET", f"/v1/appStoreVersionLocalizations/{version_loc_id}/appScreenshotSets")
    if s == 200:
        for sset in d.get("data", []):
            if sset["attributes"]["screenshotDisplayType"] == display_type:
                return sset["id"]
    s, d = api("POST", "/v1/appScreenshotSets",
               {"data": {"type": "appScreenshotSets",
                         "attributes": {"screenshotDisplayType": display_type},
                         "relationships": {"appStoreVersionLocalization":
                            {"data": {"type": "appStoreVersionLocalizations", "id": version_loc_id}}}}})
    if s in (200, 201): return d["data"]["id"]
    print(f"  ✗ create set ({display_type}): {s} {d}")
    return None

def upload_one(set_id, file_path, display_label):
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    s, d = api("POST", "/v1/appScreenshots",
               {"data": {"type": "appScreenshots",
                         "attributes": {"fileName": file_name, "fileSize": file_size},
                         "relationships": {"appScreenshotSet":
                            {"data": {"type": "appScreenshotSets", "id": set_id}}}}})
    if s not in (200, 201):
        print(f"    ✗ {display_label} reserve: {s} {d}"); return False
    ss = d["data"]
    ss_id = ss["id"]
    ops = ss["attributes"]["uploadOperations"]
    with open(file_path, "rb") as f:
        for op in ops:
            f.seek(op["offset"])
            chunk = f.read(op["length"])
            req = urllib.request.Request(op["url"], data=chunk, method=op["method"])
            for h in op["requestHeaders"]:
                req.add_header(h["name"], h["value"])
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    if r.status not in (200, 201, 204):
                        print(f"    ✗ {display_label} chunk: {r.status}"); return False
            except urllib.error.HTTPError as e:
                print(f"    ✗ {display_label} chunk HTTP {e.code}: {e.read()[:200]}"); return False
    s, d = api("PATCH", f"/v1/appScreenshots/{ss_id}",
               {"data": {"type": "appScreenshots", "id": ss_id,
                         "attributes": {"uploaded": True, "sourceFileChecksum": md5_of_file(file_path)}}})
    if s not in (200, 204):
        print(f"    ✗ {display_label} commit: {s} {d}"); return False
    print(f"    ✓ {display_label}")
    return True

for name, app_id in APPS.items():
    print(f"\n== {name} ({app_id}) ==")
    vloc = get_editable_version_loc(app_id)
    if not vloc: print("  ✗ no editable version loc"); continue

    # APP_IPHONE_69 — new set, just the real screenshot at native size
    sset69 = get_or_create_set(vloc, "APP_IPHONE_69")
    if sset69:
        upload_one(sset69, f"/tmp/screenshots-real/{name}/final-01.png", "APP_IPHONE_69 real")

    # APP_IPHONE_67 — append real screenshot to existing 3 marketing graphics
    sset67 = get_or_create_set(vloc, "APP_IPHONE_67")
    if sset67:
        upload_one(sset67, f"/tmp/screenshots-real/{name}/final-67.png", "APP_IPHONE_67 real (appended)")
