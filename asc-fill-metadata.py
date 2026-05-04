#!/usr/bin/env python3
"""Fill App Store Connect metadata for all 5 indie apps via the ASC API.

Sets per app:
- subtitle, name, privacyPolicyUrl  (appInfoLocalization, en-US)
- primaryCategory, secondaryCategory (appInfo relationships)
- description, keywords, marketingUrl, promotionalText, supportUrl
  (appStoreVersionLocalization, en-US)

Idempotent — safe to re-run.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import jwt
except ImportError:
    sys.exit("error: pyjwt[crypto] not installed. run: pip3 install --user 'pyjwt[crypto]'")

KEY_ID = "DCW4DGNGQ4"
ISSUER_ID = "69a6de85-d1b5-47e3-e053-5b8c7c11a4d1"
KEY_PATH = os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_DCW4DGNGQ4.p8")
API = "https://api.appstoreconnect.apple.com"

POLICIES_BASE = "https://github.com/divinedavis/app-policies/blob/main"

APPS = {
    "Drafted": {
        "appId": "6766302520",
        "subtitle": "Draft hard texts with AI",
        "keywords": "ai,text,helper,draft,boundary,breakup,communication,assistant,messaging",
        "promotionalText": "Stuck on what to say? Drafted finds the words for you.",
        "marketingUrl": "https://github.com/divinedavis/Drafted",
        "supportUrl": f"{POLICIES_BASE}/drafted/support.md",
        "privacyPolicyUrl": f"{POLICIES_BASE}/drafted/privacy.md",
        "primaryCategory": "PRODUCTIVITY",
        "secondaryCategory": "SOCIAL_NETWORKING",
        "description": (
            "Stuck on what to say? Drafted helps you write the texts that matter most.\n\n"
            "Whether you need to send a tough message — a breakup, a boundary, an apology, "
            "an awkward ask — or just find the right tone, Drafted uses Anthropic's Claude AI "
            "to generate three thoughtful drafts based on your situation.\n\n"
            "Pick a tone (Direct, Soft, Funny, Boundary-setting, Apology), describe the "
            "situation, and let Drafted give you options. Tap to copy any draft, re-roll for "
            "new variations, or save the ones you actually send.\n\n"
            "Features\n"
            "• AI-generated drafts in your chosen tone\n"
            "• History of saved drafts\n"
            "• Polaroid-style share cards\n"
            "• Sign in with Apple (optional)\n"
            "• Free: 3 drafts per day\n"
            "• Pro ($4.99/mo): unlimited drafts\n\n"
            "No account required. Your drafts live only on your device. We do not run "
            "servers or collect analytics."
        ),
    },
    "Scripted": {
        "appId": "6766312207",
        "subtitle": "Manifest your future, daily",
        "keywords": "manifestation,journal,scripting,future,intentions,gratitude,wellness,mindfulness,affirmation",
        "promotionalText": "Script the life you want — one entry at a time.",
        "marketingUrl": "https://github.com/divinedavis/Scripted",
        "supportUrl": f"{POLICIES_BASE}/scripted/support.md",
        "privacyPolicyUrl": f"{POLICIES_BASE}/scripted/privacy.md",
        "primaryCategory": "LIFESTYLE",
        "secondaryCategory": "HEALTH_AND_FITNESS",
        "description": (
            "Manifest the life you want, beautifully.\n\n"
            "Scripted is a journaling app for \"scripting\" — writing about your life in the "
            "present tense as if your dreams have already come true. Pick a category, write "
            "freely on a serif-paper canvas, and watch your scripted future build over time.\n\n"
            "Three categories:\n"
            "• Script your future\n"
            "• Letter to future self\n"
            "• Daily intentions\n\n"
            "Features\n"
            "• Aesthetic writing canvas with serif typography\n"
            "• AI-suggested writing prompts (Anthropic Claude)\n"
            "• Theme library — Cream (free), Lavender, Forest, Midnight (Pro)\n"
            "• Monthly recap share cards\n"
            "• Free: 5 entries per month\n"
            "• Pro ($2.99/mo): unlimited entries + premium themes\n\n"
            "No account required. Your entries live only on your device."
        ),
    },
    "Pulled": {
        "appId": "6766311239",
        "subtitle": "Pull one tarot card a day",
        "keywords": "tarot,oracle,daily,card,mystical,witch,intuition,divination,spiritual,horoscope",
        "promotionalText": "One card a day. That's your reading.",
        "marketingUrl": "https://github.com/divinedavis/Pulled",
        "supportUrl": f"{POLICIES_BASE}/pulled/support.md",
        "privacyPolicyUrl": f"{POLICIES_BASE}/pulled/privacy.md",
        "primaryCategory": "LIFESTYLE",
        "secondaryCategory": "ENTERTAINMENT",
        "description": (
            "Pull one card. Just one a day.\n\n"
            "Pulled is a daily ritual — a single tarot card pulled at the start of each day, "
            "with a short AI-generated reading to reflect on. The button locks at midnight and "
            "unlocks again the next morning.\n\n"
            "Includes the 22 Major Arcana cards. Each pull is interpreted by Anthropic's "
            "Claude AI in a playful, conversational tone — for reflection, not divination "
            "advice.\n\n"
            "Features\n"
            "• One-card-per-day ritual\n"
            "• Lock screen widget shows today's card\n"
            "• History of past pulls\n"
            "• Animated card flip reveal\n"
            "• Shareable card art\n"
            "• Pro ($0.99/mo): premium widget designs + remove ad placeholder\n\n"
            "No account required. Your daily pulls live only on your device."
        ),
    },
    "Auracard": {
        "appId": "6766311537",
        "subtitle": "Read your aura from a selfie",
        "keywords": "aura,vibe,reading,selfie,energy,spiritual,fun,personality,share,ai",
        "promotionalText": "Snap a selfie. Get your aura. Share the vibe.",
        "marketingUrl": "https://github.com/divinedavis/Auracard",
        "supportUrl": f"{POLICIES_BASE}/auracard/support.md",
        "privacyPolicyUrl": f"{POLICIES_BASE}/auracard/privacy.md",
        "primaryCategory": "ENTERTAINMENT",
        "secondaryCategory": "LIFESTYLE",
        "description": (
            "What's your aura today?\n\n"
            "Auracard reads your aura from a selfie. Snap a photo and Anthropic's Claude AI "
            "returns a playful aura score, color, and three vibe lines. A glowing card "
            "animates with your aura's color — built for fun and shareability.\n\n"
            "Share cards are rendered in 9:16 for Instagram Stories.\n\n"
            "Features\n"
            "• AI aura readings from photos\n"
            "• Animated breathing-glow card\n"
            "• History grid of past readings\n"
            "• Story-friendly share cards\n"
            "• Deep Aura mode (Pro): longer, richer reading\n"
            "• Pro ($1.99/mo): unlimited readings + Deep Aura + remove ad placeholder\n\n"
            "Auracard is a fun, playful experience — not a spiritual or medical service. "
            "Photos go to Anthropic for the reading, then live only on your device."
        ),
    },
    "Shelf": {
        "appId": "6766311807",
        "subtitle": "BookTok reading tracker",
        "keywords": "books,reading,booktok,tracker,library,bookshelf,bookworm,reads,goodreads",
        "promotionalText": "Track every book you read on a beautiful aesthetic shelf.",
        "marketingUrl": "https://github.com/divinedavis/Shelf",
        "supportUrl": f"{POLICIES_BASE}/shelf/support.md",
        "privacyPolicyUrl": f"{POLICIES_BASE}/shelf/privacy.md",
        "primaryCategory": "BOOKS",
        "secondaryCategory": "LIFESTYLE",
        "description": (
            "Your books, beautifully shelved.\n\n"
            "Shelf is a BookTok-aesthetic reading tracker. Add books by scanning the barcode "
            "or searching by title. Watch your shelves fill up over time. Mark books as "
            "Reading, Want to Read, or Read. Log daily reading sessions to build a streak.\n\n"
            "Powered by Open Library (a free, non-tracking API run by the Internet Archive). "
            "No API key required.\n\n"
            "Features\n"
            "• Aesthetic shelf view with cover art on wood-grain shelves\n"
            "• Barcode scanner (EAN-13)\n"
            "• Reading streak tracker\n"
            "• Monthly recap share cards\n"
            "• Bookshop.org affiliate buy links\n"
            "• Pro ($1.99/mo): premium themes (Forest, Library, Linen) + aesthetic widgets\n\n"
            "No account required. Your shelf lives only on your device."
        ),
    },
}

_token = None
_token_at = 0


def token():
    global _token, _token_at
    now = int(time.time())
    if _token is None or now - _token_at > 15 * 60:
        with open(KEY_PATH) as f:
            key = f.read()
        _token = jwt.encode(
            {"iss": ISSUER_ID, "iat": now, "exp": now + 20 * 60, "aud": "appstoreconnect-v1"},
            key,
            algorithm="ES256",
            headers={"kid": KEY_ID, "typ": "JWT"},
        )
        _token_at = now
    return _token


def api(method, path, body=None):
    url = path if path.startswith("http") else f"{API}{path}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:1500]}


EDITABLE_APPINFO = {"PREPARE_FOR_SUBMISSION", "WAITING_FOR_REVIEW", "DEVELOPER_REJECTED",
                    "REJECTED", "METADATA_REJECTED", "INVALID_BINARY"}
EDITABLE_VERSION = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED",
                    "METADATA_REJECTED", "INVALID_BINARY", "WAITING_FOR_REVIEW",
                    "DEVELOPER_REMOVED_FROM_SALE"}


def fill_app(name, cfg):
    print(f"\n=== {name} ({cfg['appId']}) ===")

    # appInfo (editable one)
    s, d = api("GET", f"/v1/apps/{cfg['appId']}/appInfos")
    if s != 200:
        print(f"  ✗ list appInfos: {s} {d}")
        return
    app_infos = d.get("data", [])
    editable = next((ai for ai in app_infos
                     if ai["attributes"]["state"] in EDITABLE_APPINFO),
                    app_infos[0] if app_infos else None)
    if editable is None:
        print("  ✗ no appInfo found")
        return
    app_info_id = editable["id"]
    print(f"  appInfo: {app_info_id} state={editable['attributes']['state']}")

    # primary category
    s, d = api("PATCH", f"/v1/appInfos/{app_info_id}/relationships/primaryCategory",
               {"data": {"type": "appCategories", "id": cfg["primaryCategory"]}})
    print(f"  {'✓' if s in (200, 204) else '✗'} primary category → {cfg['primaryCategory']} ({s})")
    if s not in (200, 204):
        print(f"    {d}")

    # secondary category
    s, d = api("PATCH", f"/v1/appInfos/{app_info_id}/relationships/secondaryCategory",
               {"data": {"type": "appCategories", "id": cfg["secondaryCategory"]}})
    print(f"  {'✓' if s in (200, 204) else '✗'} secondary category → {cfg['secondaryCategory']} ({s})")
    if s not in (200, 204):
        print(f"    {d}")

    # appInfoLocalizations (en-US): subtitle, privacyPolicyUrl
    s, d = api("GET", f"/v1/appInfos/{app_info_id}/appInfoLocalizations")
    if s != 200:
        print(f"  ✗ list appInfoLocs: {s} {d}")
    else:
        en = next((l for l in d.get("data", []) if l["attributes"]["locale"] == "en-US"), None)
        if en is None:
            s2, d2 = api("POST", "/v1/appInfoLocalizations",
                         {"data": {"type": "appInfoLocalizations",
                                   "attributes": {"locale": "en-US",
                                                  "subtitle": cfg["subtitle"],
                                                  "privacyPolicyUrl": cfg["privacyPolicyUrl"]},
                                   "relationships": {"appInfo": {"data": {"type": "appInfos", "id": app_info_id}}}}})
            print(f"  {'✓' if s2 in (200, 201) else '✗'} created appInfoLoc en-US ({s2})")
            if s2 not in (200, 201):
                print(f"    {d2}")
        else:
            loc_id = en["id"]
            s2, d2 = api("PATCH", f"/v1/appInfoLocalizations/{loc_id}",
                         {"data": {"type": "appInfoLocalizations", "id": loc_id,
                                   "attributes": {"subtitle": cfg["subtitle"],
                                                  "privacyPolicyUrl": cfg["privacyPolicyUrl"]}}})
            print(f"  {'✓' if s2 in (200, 204) else '✗'} updated appInfoLoc en-US (subtitle, privacy URL) ({s2})")
            if s2 not in (200, 204):
                print(f"    {d2}")

    # appStoreVersion (editable)
    s, d = api("GET", f"/v1/apps/{cfg['appId']}/appStoreVersions")
    if s != 200:
        print(f"  ✗ list versions: {s} {d}")
        return
    versions = d.get("data", [])
    editable_v = next((v for v in versions
                       if v["attributes"]["appStoreState"] in EDITABLE_VERSION), None)
    if editable_v is None:
        s2, d2 = api("POST", "/v1/appStoreVersions",
                     {"data": {"type": "appStoreVersions",
                               "attributes": {"platform": "IOS", "versionString": "1.0"},
                               "relationships": {"app": {"data": {"type": "apps", "id": cfg["appId"]}}}}})
        if s2 in (200, 201):
            editable_v = d2["data"]
            print(f"  ✓ created version 1.0")
        else:
            print(f"  ✗ create version: {s2} {d2}")
            return
    version_id = editable_v["id"]
    print(f"  version: {version_id} state={editable_v['attributes']['appStoreState']}")

    # appStoreVersionLocalization (en-US)
    s, d = api("GET", f"/v1/appStoreVersions/{version_id}/appStoreVersionLocalizations")
    if s != 200:
        print(f"  ✗ list version locs: {s} {d}")
        return
    en_v = next((l for l in d.get("data", []) if l["attributes"]["locale"] == "en-US"), None)
    attrs = {
        "description": cfg["description"],
        "keywords": cfg["keywords"],
        "marketingUrl": cfg["marketingUrl"],
        "promotionalText": cfg["promotionalText"],
        "supportUrl": cfg["supportUrl"],
    }
    if en_v is None:
        s2, d2 = api("POST", "/v1/appStoreVersionLocalizations",
                     {"data": {"type": "appStoreVersionLocalizations",
                               "attributes": {"locale": "en-US", **attrs},
                               "relationships": {"appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}}}})
        print(f"  {'✓' if s2 in (200, 201) else '✗'} created version loc en-US ({s2})")
        if s2 not in (200, 201):
            print(f"    {d2}")
    else:
        vloc_id = en_v["id"]
        s2, d2 = api("PATCH", f"/v1/appStoreVersionLocalizations/{vloc_id}",
                     {"data": {"type": "appStoreVersionLocalizations", "id": vloc_id,
                               "attributes": attrs}})
        print(f"  {'✓' if s2 in (200, 204) else '✗'} updated version loc en-US (description, keywords, urls) ({s2})")
        if s2 not in (200, 204):
            print(f"    {d2}")


def main():
    if not os.path.exists(KEY_PATH):
        sys.exit(f"missing key: {KEY_PATH}")
    for name, cfg in APPS.items():
        fill_app(name, cfg)


if __name__ == "__main__":
    main()
