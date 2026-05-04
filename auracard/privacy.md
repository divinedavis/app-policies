# Privacy Policy — Auracard

**Effective:** May 4, 2026

## What we collect

- The photo you choose to read (taken via the camera or selected from your photo library).
- The aura reading generated for that photo (score, color, vibe lines).
- Your app subscription status, managed by Apple.

We do not collect names, email addresses, contact lists, location, or device identifiers other than what Apple's StoreKit uses for subscription management.

## How we use the photo

- When you tap "Capture aura," your photo is compressed to JPEG and sent to Anthropic's Claude API as base64-encoded data. Claude returns a JSON aura reading.
- The photo and reading are then stored locally on your device in a SwiftData record so you can view past readings.
- Photos are **never** uploaded to our servers (we do not run any servers).

## Anthropic's handling

Anthropic processes the image to produce the reading and does not retain it for model training or other purposes per their API terms. See https://www.anthropic.com/privacy and https://www.anthropic.com/legal/api-terms.

## Third-party services

- **Anthropic (Claude API)** — image data + prompt go to the API, response comes back.
- **Apple StoreKit** — subscription status.

No analytics, ads, or third-party tracking.

## Storage

Your captured photos and readings live in a local SwiftData store on your device. You can delete any reading from the History grid.

## Children

Auracard is not directed at children under 13.

## Changes

If our practices change, we will update this page.

## Contact

**divinejdavis@gmail.com**
