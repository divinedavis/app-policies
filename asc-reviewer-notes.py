#!/usr/bin/env python3
"""Set App Review notes + contact info for all 5 apps via ASC API."""
import json, os, time, urllib.request, urllib.error
import jwt

KEY_ID = "DCW4DGNGQ4"
ISSUER = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

CONTACT = {
    "firstName": "Divine",
    "lastName": "Davis",
    "phoneNumber": "+1 717 659 9140",
    "emailAddress": "divinejdavis@gmail.com",
}

NOTES = {
    "Drafted": (
        "Drafted is an AI-assisted message-drafting tool. The user describes a "
        "situation, picks a tone, and the app calls Anthropic Claude (via our "
        "Supabase Edge Function proxy) to generate three draft messages.\n\n"
        "How to test:\n"
        "1. Open the app and tap into 'What's the situation?'.\n"
        "2. Type any short scenario (e.g. 'asking my landlord to fix the heater').\n"
        "3. Pick a tone (Direct/Soft/Funny/Boundary/Apology) and tap Draft.\n"
        "4. Three numbered drafts appear; tap to copy or save.\n\n"
        "Sandbox IAP: subscribing to Pro at $4.99/mo unlocks unlimited drafts (free is 3/day).\n\n"
        "Content moderation: prompts are constrained server-side; harmful requests "
        "return a 'try rephrasing' error. AI key is server-side; no third-party API "
        "key ships in the binary."
    ),
    "Scripted": (
        "Scripted is a journaling app for manifestation/scripting writing. Users "
        "write in three categories on a serif paper canvas; an AI 'Suggest prompt' "
        "button (Anthropic Claude via Supabase Edge Function) provides starter "
        "prompts.\n\n"
        "How to test:\n"
        "1. Tap any of the three category cards on Home (Script your future / "
        "Letter to future self / Daily intentions).\n"
        "2. Tap '✨ Suggest prompt' to get an AI-generated starter, or write freely.\n"
        "3. Save → entry appears in Library tab.\n\n"
        "Sandbox IAP: Pro at $2.99/mo unlocks unlimited entries + premium themes "
        "(free tier is 5 entries/month + Cream theme)."
    ),
    "Pulled": (
        "Pulled is a once-a-day tarot card app. Tapping 'Pull' draws one of the 22 "
        "Major Arcana cards and shows a short AI-generated reading. The button "
        "locks until midnight local time.\n\n"
        "How to test:\n"
        "1. On Home (Today tab), tap the 'Pull' button.\n"
        "2. A card flips and shows a 1–2 sentence reading.\n"
        "3. Past pulls live in the History tab.\n"
        "4. Settings tab → 'Restore Purchases' for IAP recovery.\n\n"
        "Sandbox IAP: Pro at $0.99/mo removes the bottom ad placeholder and "
        "unlocks premium widget designs.\n\n"
        "AI content note: prompts are constrained to the wise/warm tarot reader "
        "tone; readings are explicitly framed as reflective, not divinatory advice."
    ),
    "Auracard": (
        "Auracard reads a fun playful 'aura' from a selfie or photo using "
        "Anthropic Claude vision (via our Supabase Edge Function proxy).\n\n"
        "How to test:\n"
        "1. Tap 'Capture aura' on Home.\n"
        "2. Take a photo or pick from library.\n"
        "3. The app sends a 512×512 compressed JPEG to the proxy and shows a "
        "score, color, and three vibe lines.\n"
        "4. Past readings live in History; Restore in Settings tab.\n\n"
        "Sandbox IAP: Pro at $1.99/mo enables unlimited readings + Deep Aura mode.\n\n"
        "Content moderation: server-side prompt explicitly forbids commenting on "
        "race/gender/age/weight/attractiveness. Photos are sent to Anthropic for "
        "the reading, then stored only on-device. Not a real spiritual or medical "
        "service — purely entertainment."
    ),
    "Shelf": (
        "Shelf is a BookTok-aesthetic reading tracker. No AI / no third-party API "
        "key — uses Open Library (Internet Archive) for book search and metadata.\n\n"
        "How to test:\n"
        "1. Tap the brown '+' button (top-right) on Shelf tab.\n"
        "2. Search by title, or tap 'Scan Barcode' to scan an EAN-13 ISBN.\n"
        "3. Pick a book → choose status (Reading / Want to Read / Read) → Add.\n"
        "4. Books appear on the appropriate shelf.\n"
        "5. Stats tab shows reading streak; Settings has Restore Purchases.\n\n"
        "Sandbox IAP: Pro at $1.99/mo unlocks premium themes (Forest/Library/Linen) "
        "and aesthetic widget designs."
    ),
}

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

EDITABLE = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED",
            "METADATA_REJECTED", "WAITING_FOR_REVIEW", "INVALID_BINARY"}

for name, app_id in APPS.items():
    print(f"\n=== {name} ({app_id}) ===")
    s, d = api("GET", f"/v1/apps/{app_id}/appStoreVersions")
    if s != 200:
        print(f"  ✗ versions: {s} {d}"); continue
    editable = next((v for v in d.get("data", [])
                     if v["attributes"]["appStoreState"] in EDITABLE), None)
    if not editable:
        print("  ✗ no editable version"); continue
    version_id = editable["id"]

    # Get the appStoreReviewDetail relationship
    s, d = api("GET", f"/v1/appStoreVersions/{version_id}/appStoreReviewDetail")
    detail_id = None
    if s == 200 and d.get("data"):
        detail_id = d["data"]["id"]
    elif s == 200:
        # Empty data — need to create
        pass

    payload = {
        "data": {
            "type": "appStoreReviewDetails",
            "attributes": {
                "contactFirstName": CONTACT["firstName"],
                "contactLastName": CONTACT["lastName"],
                "contactPhone": CONTACT["phoneNumber"],
                "contactEmail": CONTACT["emailAddress"],
                "demoAccountRequired": False,
                "demoAccountName": None,
                "demoAccountPassword": None,
                "notes": NOTES[name],
            },
        }
    }
    if detail_id:
        payload["data"]["id"] = detail_id
        s, d = api("PATCH", f"/v1/appStoreReviewDetails/{detail_id}", payload)
    else:
        payload["data"]["relationships"] = {
            "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}
        }
        s, d = api("POST", "/v1/appStoreReviewDetails", payload)

    if s in (200, 201, 204):
        print(f"  ✓ reviewer notes set ({len(NOTES[name])} chars)")
    else:
        print(f"  ✗ {s}: {d}")
