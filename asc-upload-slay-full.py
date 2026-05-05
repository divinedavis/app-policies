#!/usr/bin/env python3
"""Replace ALL screenshots in each app's APP_IPHONE_67 set with the 5 new Slay-style ones."""
import hashlib, json, os, time, urllib.request, urllib.error
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

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(8192), b""): h.update(c)
    return h.hexdigest()

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

def upload(set_id, path):
    size = os.path.getsize(path); name = os.path.basename(path)
    s, d = api("POST", "/v1/appScreenshots",
               {"data": {"type": "appScreenshots",
                         "attributes": {"fileName": name, "fileSize": size},
                         "relationships": {"appScreenshotSet":
                            {"data": {"type": "appScreenshotSets", "id": set_id}}}}})
    if s not in (200, 201): return f"reserve {s}: {d}"
    ssid = d["data"]["id"]
    for op in d["data"]["attributes"]["uploadOperations"]:
        with open(path, "rb") as f:
            f.seek(op["offset"]); chunk = f.read(op["length"])
        req = urllib.request.Request(op["url"], data=chunk, method=op["method"])
        for h in op["requestHeaders"]: req.add_header(h["name"], h["value"])
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                if r.status not in (200, 201, 204): return f"chunk {r.status}"
        except urllib.error.HTTPError as e: return f"HTTP {e.code}"
    s, d = api("PATCH", f"/v1/appScreenshots/{ssid}",
               {"data": {"type": "appScreenshots", "id": ssid,
                         "attributes": {"uploaded": True, "sourceFileChecksum": md5(path)}}})
    return ("ok", ssid) if s in (200, 204) else f"commit {s}: {d}"

for name, app_id in APPS.items():
    print(f"\n=== {name} ===")
    sset = get_67_set(app_id)
    if not sset: print("  ✗ no set"); continue

    # Delete every existing screenshot in this set
    s, d = api("GET", f"/v1/appScreenshotSets/{sset}/appScreenshots?limit=20")
    existing = d.get("data", []) if s == 200 else []
    for e in existing:
        api("DELETE", f"/v1/appScreenshots/{e['id']}")
    print(f"  cleared {len(existing)} existing")

    # Upload 5 Slay-style ones in order
    new_ids = []
    for i in (1, 2, 3, 4, 5):
        path = f"/tmp/screenshots-slay/{name}/slay-{i:02d}.png"
        if not os.path.exists(path): print(f"    ✗ missing slay-{i:02d}.png"); continue
        result = upload(sset, path)
        if isinstance(result, tuple) and result[0] == "ok":
            new_ids.append(result[1])
            print(f"    ✓ slay-{i:02d}.png")
        else:
            print(f"    ✗ slay-{i:02d}.png — {result}")

    # Lock the order via the relationship endpoint
    body = {"data": [{"type": "appScreenshots", "id": sid} for sid in new_ids]}
    s, d = api("PATCH", f"/v1/appScreenshotSets/{sset}/relationships/appScreenshots", body)
    print(f"  order: {'✓ 1→5' if s in (200, 204) else '✗ '+str(s)}")
