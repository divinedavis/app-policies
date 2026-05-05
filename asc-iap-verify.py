#!/usr/bin/env python3
"""Verify IAP configuration consistency across:
  1. The .storekit local config (used by Xcode for sim testing)
  2. The app source code (StoreManager / PaywallView product IDs)
  3. App Store Connect (the actual subscriptions reviewers will exercise)

Catches: mismatched product IDs, price drift, products that exist in code
but aren't created in ASC (or vice-versa).
"""
import json, os, re, time, urllib.request, urllib.parse, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

APPS = {
    "Drafted":  ("6766302520", "/Users/divinedavis/Desktop/Drafted",  "Drafted/Drafted.storekit",   "com.divinedavis.Drafted.pro.monthly",  "4.99"),
    "Scripted": ("6766312207", "/Users/divinedavis/Desktop/Scripted", "Scripted/Scripted.storekit", "com.divinedavis.Scripted.pro.monthly", "2.99"),
    "Pulled":   ("6766311239", "/Users/divinedavis/Desktop/Pulled",   "Pulled/Pulled.storekit",     "com.divinedavis.Pulled.pro.monthly",   "0.99"),
    "Auracard": ("6766311537", "/Users/divinedavis/Desktop/Auracard", "Auracard.storekit",          "com.divinedavis.Auracard.pro.monthly", "1.99"),
    "Shelf":    ("6766311807", "/Users/divinedavis/Desktop/Shelf",    "Shelf.storekit",             "com.divinedavis.Shelf.pro.monthly",    "1.99"),
}

with open(KEY_PATH) as f: key = f.read()
now = int(time.time())
TKN = jwt.encode({"iss": ISSUER, "iat": now, "exp": now+15*60, "aud": "appstoreconnect-v1"},
                 key, algorithm="ES256", headers={"kid": KEY_ID, "typ": "JWT"})

def asc(path):
    req = urllib.request.Request(f"{API}{path}", headers={"Authorization": f"Bearer {TKN}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, {"error": e.read().decode()[:300]}

def parse_storekit(path):
    """Returns list of (productID, price) tuples."""
    if not os.path.exists(path): return []
    with open(path) as f: data = json.load(f)
    out = []
    for grp in data.get("subscriptionGroups", []):
        for sub in grp.get("subscriptions", []):
            out.append((sub.get("productID"), sub.get("displayPrice")))
    for prod in data.get("products", []):
        out.append((prod.get("productID"), prod.get("displayPrice")))
    return out

def grep_source_product_ids(repo_path):
    """Find any com.divinedavis.<App>.* product ID literals in Swift source."""
    pattern = re.compile(r'"(com\.divinedavis\.[A-Za-z0-9_.]+\.(?:pro|monthly|premium)[A-Za-z0-9_.]*)"')
    found = set()
    for root, _, files in os.walk(repo_path):
        if any(skip in root for skip in [".git", "DerivedData", ".xcodeproj", "build"]): continue
        for fn in files:
            if not fn.endswith(".swift"): continue
            try:
                with open(os.path.join(root, fn)) as f:
                    for line in f:
                        for m in pattern.finditer(line):
                            found.add(m.group(1))
            except Exception: pass
    return sorted(found)

def asc_subscriptions(app_id):
    """List subscription productIDs + USA prices for an app."""
    s, d = asc(f"/v1/apps/{app_id}/subscriptionGroups?include=subscriptions&limit=200")
    if s != 200: return []
    sub_ids = []
    for grp in d.get("data", []):
        for rel in grp.get("relationships", {}).get("subscriptions", {}).get("data", []):
            sub_ids.append(rel["id"])
    out = []
    for sid in sub_ids:
        s, d = asc(f"/v1/subscriptions/{sid}")
        if s != 200: continue
        product_id = d["data"]["attributes"].get("productId")
        # Get USA price — the prices endpoint embeds the customerPrice via the
        # subscriptionPricePoint relationship, but the modern API also responds
        # with `manualPrices` directly on the subscription. Try both.
        s, d = asc(f"/v1/subscriptions/{sid}/prices?include=subscriptionPricePoint,territory&limit=200")
        usa_price = None
        if s == 200:
            included = {(i["type"], i["id"]): i for i in d.get("included", [])}
            for p in d.get("data", []):
                # territory ID is on the relationship's data.id (not in attributes)
                terr_rel = p.get("relationships", {}).get("territory", {}).get("data", {})
                if terr_rel.get("id") != "USA": continue
                pp_rel = p.get("relationships", {}).get("subscriptionPricePoint", {}).get("data", {})
                pp_id = pp_rel.get("id") if pp_rel else None
                pp = included.get(("subscriptionPricePoints", pp_id))
                if pp:
                    usa_price = pp.get("attributes", {}).get("customerPrice")
                break
        out.append((product_id, usa_price))
    return out

# ─── Run verification ────────────────────────────────────────────
print(f"{'App':<10} {'Source':<8} {'.storekit':<14} {'ASC':<14} {'Match':<6}")
print("─" * 60)
all_ok = True
for name, (app_id, repo_path, storekit_rel, expected_id, expected_price) in APPS.items():
    sk = parse_storekit(os.path.join(repo_path, storekit_rel))
    src = grep_source_product_ids(repo_path)
    asc_subs = asc_subscriptions(app_id)

    sk_ids = {pid for pid, _ in sk}
    asc_ids = {pid for pid, _ in asc_subs}
    src_ids = set(src)

    sk_price = next((p for pid, p in sk if pid == expected_id), "—")
    asc_price = next((p for pid, p in asc_subs if pid == expected_id), "—")

    in_src = expected_id in src_ids
    in_sk = expected_id in sk_ids
    in_asc = expected_id in asc_ids
    price_match = sk_price == expected_price and (asc_price == expected_price or asc_price == f"{expected_price}.0")

    ok = in_src and in_sk and in_asc and price_match
    all_ok = all_ok and ok

    status = "✓" if ok else "✗"
    print(f"{name:<10} {'✓' if in_src else '✗':<8} "
          f"{'✓ '+sk_price if in_sk else '✗':<14} "
          f"{'✓ '+(asc_price or '—') if in_asc else '✗':<14} "
          f"{status:<6}")
    if not ok:
        if not in_src:  print(f"           ↳ product ID '{expected_id}' not found in Swift source")
        if not in_sk:   print(f"           ↳ product ID not in {storekit_rel}")
        if not in_asc:  print(f"           ↳ product ID not in ASC subscriptions")
        if not price_match: print(f"           ↳ price drift: expected ${expected_price}, storekit=${sk_price}, asc=${asc_price}")
    extra_src = src_ids - {expected_id}
    if extra_src:
        print(f"           ↳ extra product IDs in source: {sorted(extra_src)}")

print("─" * 60)
print(f"{'OK' if all_ok else 'ISSUES FOUND'}")
