import AppKit
import Foundation

// 1290 × 2796 — App Store 6.7" iPhone screenshot size
let W = 1290
let H = 2796

struct AppShots {
    let dir: String
    let bg1: NSColor
    let bg2: NSColor
    let textColor: NSColor
    let accent: NSColor
    let iconPath: String
    let shots: [(headline: String, sub: String)]
}

let APPS: [String: AppShots] = [
    "Drafted": AppShots(
        dir: "/tmp/screenshots/Drafted",
        bg1: NSColor(calibratedRed: 85/255,  green: 105/255, blue: 145/255, alpha: 1),
        bg2: NSColor(calibratedRed: 35/255,  green: 45/255,  blue: 80/255,  alpha: 1),
        textColor: NSColor(calibratedRed: 245/255, green: 232/255, blue: 215/255, alpha: 1),
        accent: NSColor(calibratedRed: 245/255, green: 232/255, blue: 215/255, alpha: 1),
        iconPath: "/Users/divinedavis/Desktop/Drafted/Drafted/Assets.xcassets/AppIcon.appiconset/Icon-1024.png",
        shots: [
            ("Draft the hard text.", "AI helps you find the words"),
            ("5 tones. 3 drafts.", "Direct. Soft. Funny.\nBoundary. Apology."),
            ("Send what feels right.", "Re-roll, save, and share.")
        ]
    ),
    "Scripted": AppShots(
        dir: "/tmp/screenshots/Scripted",
        bg1: NSColor(calibratedRed: 248/255, green: 232/255, blue: 230/255, alpha: 1),
        bg2: NSColor(calibratedRed: 200/255, green: 155/255, blue: 170/255, alpha: 1),
        textColor: NSColor(calibratedRed: 92/255,  green: 50/255,  blue: 65/255,  alpha: 1),
        accent: NSColor(calibratedRed: 92/255,  green: 50/255,  blue: 65/255,  alpha: 1),
        iconPath: "/Users/divinedavis/Desktop/Scripted/Scripted/Assets.xcassets/AppIcon.appiconset/Icon-1024.png",
        shots: [
            ("Manifest, beautifully.", "Script your future.\nDaily."),
            ("Three categories.", "Future you. Letter to self.\nDaily intentions."),
            ("Aesthetic themes.", "Cream. Lavender.\nForest. Midnight.")
        ]
    ),
    "Pulled": AppShots(
        dir: "/tmp/screenshots/Pulled",
        bg1: NSColor(calibratedRed: 95/255,  green: 50/255,  blue: 155/255, alpha: 1),
        bg2: NSColor(calibratedRed: 30/255,  green: 10/255,  blue: 60/255,  alpha: 1),
        textColor: NSColor(calibratedRed: 245/255, green: 232/255, blue: 215/255, alpha: 1),
        accent: NSColor(calibratedRed: 220/255, green: 180/255, blue: 110/255, alpha: 1),
        iconPath: "/Users/divinedavis/Desktop/Pulled/Pulled/Assets.xcassets/AppIcon.appiconset/Icon-1024.png",
        shots: [
            ("Pull one card.", "Just one a day."),
            ("AI interprets.", "A short reading\nfor reflection."),
            ("Daily ritual.", "Locked until midnight.\nUnlocks with the sun.")
        ]
    ),
    "Auracard": AppShots(
        dir: "/tmp/screenshots/Auracard",
        bg1: NSColor(calibratedRed: 145/255, green: 75/255,  blue: 195/255, alpha: 1),
        bg2: NSColor(calibratedRed: 85/255,  green: 195/255, blue: 215/255, alpha: 1),
        textColor: NSColor.white,
        accent: NSColor.white,
        iconPath: "/Users/divinedavis/Desktop/Auracard/Auracard/Assets.xcassets/AppIcon.appiconset/Icon-1024.png",
        shots: [
            ("What's your aura?", "Read it from a selfie."),
            ("AI vibe check.", "Score. Color. Three lines."),
            ("Share the glow.", "Story-ready cards.")
        ]
    ),
    "Shelf": AppShots(
        dir: "/tmp/screenshots/Shelf",
        bg1: NSColor(calibratedRed: 235/255, green: 218/255, blue: 188/255, alpha: 1),
        bg2: NSColor(calibratedRed: 195/255, green: 165/255, blue: 130/255, alpha: 1),
        textColor: NSColor(calibratedRed: 92/255,  green: 58/255,  blue: 33/255,  alpha: 1),
        accent: NSColor(calibratedRed: 92/255,  green: 58/255,  blue: 33/255,  alpha: 1),
        iconPath: "/Users/divinedavis/Desktop/Shelf/Shelf/Assets.xcassets/AppIcon.appiconset/Icon-1024.png",
        shots: [
            ("Your books,\nbeautifully shelved.", "Aesthetic reading tracker."),
            ("Scan. Search. Save.", "Open Library.\nNo tracking."),
            ("Build your streak.", "One reading session\nat a time.")
        ]
    ),
]

func renderShot(app: AppShots, headline: String, sub: String, index: Int) {
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: W, pixelsHigh: H,
        bitsPerSample: 8, samplesPerPixel: 4,
        hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0, bitsPerPixel: 32
    )!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)

    // Background gradient
    NSGradient(colors: [app.bg1, app.bg2])!.draw(
        in: NSRect(x: 0, y: 0, width: W, height: H), angle: 270)

    // App icon at top, rounded, with subtle shadow
    if let iconImg = NSImage(contentsOfFile: app.iconPath) {
        let iconSize: CGFloat = 280
        let iconX = (CGFloat(W) - iconSize) / 2
        let iconY: CGFloat = CGFloat(H) - iconSize - 280
        let iconRect = NSRect(x: iconX, y: iconY, width: iconSize, height: iconSize)

        // Rounded clip + draw icon
        NSGraphicsContext.current?.cgContext.saveGState()
        NSBezierPath(roundedRect: iconRect, xRadius: iconSize * 0.22, yRadius: iconSize * 0.22).addClip()
        iconImg.draw(in: iconRect)
        NSGraphicsContext.current?.cgContext.restoreGState()
    }

    // Headline (large bold serif)
    let headlineFont = NSFont(name: "Georgia-Bold", size: 110) ?? NSFont.boldSystemFont(ofSize: 110)
    let para = NSMutableParagraphStyle()
    para.alignment = .center
    para.lineSpacing = 14
    let headlineAttrs: [NSAttributedString.Key: Any] = [
        .font: headlineFont,
        .foregroundColor: app.textColor,
        .paragraphStyle: para,
    ]
    let headlineRect = NSRect(x: 100, y: 1100, width: W - 200, height: 600)
    NSAttributedString(string: headline, attributes: headlineAttrs).draw(in: headlineRect)

    // Subhead (medium sans-serif)
    let subFont = NSFont(name: "HelveticaNeue-Medium", size: 56) ?? NSFont.systemFont(ofSize: 56)
    let subAttrs: [NSAttributedString.Key: Any] = [
        .font: subFont,
        .foregroundColor: app.textColor.withAlphaComponent(0.85),
        .paragraphStyle: para,
    ]
    let subRect = NSRect(x: 100, y: 800, width: W - 200, height: 300)
    NSAttributedString(string: sub, attributes: subAttrs).draw(in: subRect)

    // Decorative dot at bottom (page indicator style)
    let dotY: CGFloat = 380
    let dotSize: CGFloat = 18
    let dotSpacing: CGFloat = 36
    let totalWidth = CGFloat(app.shots.count) * dotSize + CGFloat(app.shots.count - 1) * (dotSpacing - dotSize)
    let dotsStartX = (CGFloat(W) - totalWidth) / 2
    for i in 0..<app.shots.count {
        let x = dotsStartX + CGFloat(i) * dotSpacing
        let color = i == index ? app.accent : app.accent.withAlphaComponent(0.35)
        color.set()
        NSBezierPath(ovalIn: NSRect(x: x, y: dotY, width: dotSize, height: dotSize)).fill()
    }

    NSGraphicsContext.restoreGraphicsState()

    let png = rep.representation(using: .png, properties: [:])!
    try? FileManager.default.createDirectory(atPath: app.dir, withIntermediateDirectories: true)
    let outPath = "\(app.dir)/screenshot-\(String(format: "%02d", index + 1)).png"
    try? png.write(to: URL(fileURLWithPath: outPath))
    print("  wrote \(outPath)")
}

for (name, app) in APPS {
    print("== \(name) ==")
    for (i, shot) in app.shots.enumerated() {
        renderShot(app: app, headline: shot.headline, sub: shot.sub, index: i)
    }
}
