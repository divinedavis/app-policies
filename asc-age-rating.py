#!/usr/bin/env python3
"""Submit age rating declarations for all 5 apps via ASC API.

Each app's appInfo has an ageRatingDeclaration. We PATCH it with answers
to Apple's age rating questionnaire.

Drafted has occasional crude language (boundary / breakup contexts) → 12+
The rest are clean → 4+
"""
import json, os, time, urllib.request, urllib.parse, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER_ID = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

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

# Default clean answers — used for Scripted, Pulled, Auracard, Shelf
CLEAN = {
    # Booleans (presence/absence of a feature)
    "advertising": False,
    "gambling": False,
    "lootBox": False,
    "messagingAndChat": False,
    "userGeneratedContent": False,
    "healthOrWellnessTopics": False,
    "unrestrictedWebAccess": False,
    "parentalControls": False,
    "ageAssurance": False,
    # Severity (NONE / INFREQUENT_OR_MILD / FREQUENT_OR_INTENSE)
    "alcoholTobaccoOrDrugUseOrReferences": "NONE",
    "contests": "NONE",
    "gamblingSimulated": "NONE",
    "gunsOrOtherWeapons": "NONE",
    "medicalOrTreatmentInformation": "NONE",
    "profanityOrCrudeHumor": "NONE",
    "sexualContentGraphicAndNudity": "NONE",
    "sexualContentOrNudity": "NONE",
    "horrorOrFearThemes": "NONE",
    "matureOrSuggestiveThemes": "NONE",
    "violenceCartoonOrFantasy": "NONE",
    "violenceRealistic": "NONE",
    "violenceRealisticProlongedGraphicOrSadistic": "NONE",
    "ageRatingOverride": "NONE",
}

# Drafted has occasional crude/boundary language in user inputs
DRAFTED = dict(CLEAN, profanityOrCrudeHumor="INFREQUENT_OR_MILD")

APPS = {
    "Drafted":  {"id": "6766302520", "answers": DRAFTED},
    "Scripted": {"id": "6766312207", "answers": CLEAN},
    "Pulled":   {"id": "6766311239", "answers": CLEAN},
    "Auracard": {"id": "6766311537", "answers": CLEAN},
    "Shelf":    {"id": "6766311807", "answers": CLEAN},
}

def get_editable_appinfo(app_id):
    s, d = api("GET", f"/v1/apps/{app_id}/appInfos")
    if s != 200: return None
    EDITABLE = {"PREPARE_FOR_SUBMISSION", "WAITING_FOR_REVIEW", "DEVELOPER_REJECTED",
                "REJECTED", "METADATA_REJECTED", "INVALID_BINARY"}
    for ai in d.get("data", []):
        if ai["attributes"]["state"] in EDITABLE:
            return ai["id"]
    return d["data"][0]["id"] if d.get("data") else None

for name, cfg in APPS.items():
    print(f"\n=== {name} ({cfg['id']}) ===")
    ai_id = get_editable_appinfo(cfg["id"])
    if not ai_id:
        print("  ✗ no appInfo"); continue

    # Get the existing ageRatingDeclaration
    s, d = api("GET", f"/v1/appInfos/{ai_id}/ageRatingDeclaration")
    if s != 200:
        print(f"  ✗ get ageRatingDeclaration: {s} {d}"); continue
    decl = d.get("data")
    if not decl:
        # Create one
        s, d = api("POST", "/v1/ageRatingDeclarations",
                   {"data": {"type": "ageRatingDeclarations",
                             "attributes": cfg["answers"],
                             "relationships": {"appInfo":
                                {"data": {"type": "appInfos", "id": ai_id}}}}})
        if s in (200, 201):
            print(f"  ✓ created ageRatingDeclaration")
        else:
            print(f"  ✗ create: {s} {d}")
        continue

    # Patch existing
    decl_id = decl["id"]
    s, d = api("PATCH", f"/v1/ageRatingDeclarations/{decl_id}",
               {"data": {"type": "ageRatingDeclarations",
                         "id": decl_id,
                         "attributes": cfg["answers"]}})
    if s in (200, 204):
        print(f"  ✓ updated age rating")
    else:
        print(f"  ✗ update: {s} {d}")
