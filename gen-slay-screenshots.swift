import AppKit
import Foundation

// 1290 × 2796 — App Store 6.7" iPhone screenshot size
let W = 1290
let H = 2796

extension NSFont {
    static func systemRounded(size: CGFloat, weight: NSFont.Weight) -> NSFont {
        let base = NSFont.systemFont(ofSize: size, weight: weight)
        if let desc = base.fontDescriptor.withDesign(.rounded) {
            return NSFont(descriptor: desc, size: size) ?? base
        }
        return base
    }
}

struct EmojiSticker {
    let emoji: String
    let center: NSPoint
    let size: CGFloat
    let rotation: CGFloat   // radians
}

struct Shot {
    let app: String
    let index: Int
    let bg: NSColor
    let textColor: NSColor
    let pillBg: NSColor
    let pillFg: NSColor
    let pillText: String
    let headline: String       // newline-separated lines
    let phoneScreenshot: String?  // path to image to embed in phone frame
    let stickers: [EmojiSticker]
}

func render(_ shot: Shot, to outputPath: String) {
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

    // Background
    shot.bg.set()
    NSRect(x: 0, y: 0, width: W, height: H).fill()

    // ─── PILL (small dark capsule at top) ───
    let pillFontSize: CGFloat = 44
    let pillFont = NSFont.systemRounded(size: pillFontSize, weight: .semibold)
    let pillTextSize = (shot.pillText as NSString).size(withAttributes: [.font: pillFont])
    let pillW = pillTextSize.width + 80
    let pillH: CGFloat = 90
    let pillX = (CGFloat(W) - pillW) / 2
    // Place pill near the top of the visible content area
    let pillY: CGFloat = CGFloat(H) - 380
    shot.pillBg.set()
    NSBezierPath(roundedRect: NSRect(x: pillX, y: pillY, width: pillW, height: pillH),
                 xRadius: pillH/2, yRadius: pillH/2).fill()
    let pillPara = NSMutableParagraphStyle()
    pillPara.alignment = .center
    let pillAttrs: [NSAttributedString.Key: Any] = [
        .font: pillFont,
        .foregroundColor: shot.pillFg,
        .paragraphStyle: pillPara,
    ]
    NSAttributedString(string: shot.pillText, attributes: pillAttrs).draw(
        in: NSRect(x: pillX, y: pillY + (pillH - pillTextSize.height)/2 - 4,
                   width: pillW, height: pillTextSize.height + 8)
    )

    // ─── HEADLINE (chunky rounded display text) ───
    let headlineFontSize: CGFloat = 150
    let headlineFont = NSFont.systemRounded(size: headlineFontSize, weight: .black)
    let headlinePara = NSMutableParagraphStyle()
    headlinePara.alignment = .center
    headlinePara.lineSpacing = 0
    let headlineAttrs: [NSAttributedString.Key: Any] = [
        .font: headlineFont,
        .foregroundColor: shot.textColor,
        .paragraphStyle: headlinePara,
    ]
    let headlineString = NSAttributedString(string: shot.headline, attributes: headlineAttrs)
    // Measure the actual rendered size (handles line leading correctly).
    let measured = headlineString.boundingRect(
        with: CGSize(width: CGFloat(W) - 120, height: 10000),
        options: [.usesLineFragmentOrigin, .usesFontLeading]
    )
    let totalHeadlineH = ceil(measured.height)
    let headlineTop = pillY - 60
    let headlineRect = NSRect(x: 60,
                              y: headlineTop - totalHeadlineH,
                              width: CGFloat(W) - 120,
                              height: totalHeadlineH + 8)
    headlineString.draw(with: headlineRect, options: [.usesLineFragmentOrigin, .usesFontLeading], context: nil)

    // ─── PHONE FRAME with embedded screenshot ───
    let phoneArea = NSRect(x: 0, y: 80, width: CGFloat(W), height: headlineRect.minY - 100)
    if let path = shot.phoneScreenshot, let phoneImg = NSImage(contentsOfFile: path) {
        let phoneW: CGFloat = 720
        let phoneH = phoneW * (2796.0 / 1290.0)
        let phoneX = (CGFloat(W) - phoneW) / 2
        let phoneY = phoneArea.minY + (phoneArea.height - phoneH) / 2
        let phoneRect = NSRect(x: phoneX, y: phoneY, width: phoneW, height: phoneH)

        // Soft shadow underneath
        NSGraphicsContext.current?.cgContext.saveGState()
        NSColor.black.withAlphaComponent(0.28).set()
        let shadowPath = NSBezierPath(roundedRect: phoneRect.offsetBy(dx: 8, dy: -16),
                                       xRadius: 86, yRadius: 86)
        shadowPath.fill()
        NSGraphicsContext.current?.cgContext.restoreGState()

        // Phone bezel (black rounded rect)
        NSColor.black.set()
        NSBezierPath(roundedRect: phoneRect, xRadius: 86, yRadius: 86).fill()

        // Inner screen
        let screenInset: CGFloat = 16
        let screenRect = phoneRect.insetBy(dx: screenInset, dy: screenInset)
        NSGraphicsContext.current?.cgContext.saveGState()
        NSBezierPath(roundedRect: screenRect, xRadius: 70, yRadius: 70).addClip()
        // Aspect-fill the screenshot into the screen rect
        let imgSize = phoneImg.size
        let scale = max(screenRect.width / imgSize.width, screenRect.height / imgSize.height)
        let drawSize = NSSize(width: imgSize.width * scale, height: imgSize.height * scale)
        let drawOrigin = NSPoint(
            x: screenRect.midX - drawSize.width / 2,
            y: screenRect.midY - drawSize.height / 2
        )
        phoneImg.draw(in: NSRect(origin: drawOrigin, size: drawSize))
        NSGraphicsContext.current?.cgContext.restoreGState()
    }

    // ─── EMOJI STICKERS (floating, slightly rotated) ───
    for sticker in shot.stickers {
        NSGraphicsContext.current?.cgContext.saveGState()
        let cg = NSGraphicsContext.current!.cgContext
        cg.translateBy(x: sticker.center.x, y: sticker.center.y)
        cg.rotate(by: sticker.rotation)
        let font = NSFont.systemFont(ofSize: sticker.size)
        let attrs: [NSAttributedString.Key: Any] = [.font: font]
        let attr = NSAttributedString(string: sticker.emoji, attributes: attrs)
        let sz = attr.size()
        attr.draw(at: NSPoint(x: -sz.width/2, y: -sz.height/2))
        cg.restoreGState()
    }

    NSGraphicsContext.restoreGraphicsState()

    let png = rep.representation(using: .png, properties: [:])!
    try? FileManager.default.createDirectory(atPath: (outputPath as NSString).deletingLastPathComponent,
                                             withIntermediateDirectories: true)
    try? png.write(to: URL(fileURLWithPath: outputPath))
    print("  wrote \(outputPath)")
}

// ─── Per-app config ────────────────────────────────────────────────

func hex(_ s: String) -> NSColor {
    var v = s.uppercased(); if v.hasPrefix("#") { v.removeFirst() }
    var i: UInt64 = 0; Scanner(string: v).scanHexInt64(&i)
    return NSColor(calibratedRed: CGFloat((i >> 16) & 0xFF)/255,
                   green: CGFloat((i >> 8) & 0xFF)/255,
                   blue:  CGFloat(i & 0xFF)/255, alpha: 1)
}

let WHITE = NSColor.white
let BLACK = NSColor.black
let CREAM = hex("F4ECDA")

// Brand bg colors — saturated to support white text contrast (Slay-style)
let DRAFTED_BG  = hex("5870AD")
let SCRIPTED_BG = hex("E5749E")
let PULLED_BG   = hex("7B4AC4")
let AURACARD_BG = hex("CE52DC")
let SHELF_BG    = hex("6B4226")

// Use the previously captured populated screenshots as phone content
let pop = "/tmp/screenshots-real"

let SHOTS: [Shot] = [
    // ─── DRAFTED ───
    Shot(app: "Drafted", index: 1, bg: DRAFTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Stuck on a text?",
         headline: "Just send\nit. Drafted\ngets it.",
         phoneScreenshot: "\(pop)/Drafted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "💬", center: NSPoint(x: 180, y: 1300), size: 130, rotation: -0.18),
            EmojiSticker(emoji: "✨", center: NSPoint(x: 1110, y: 1100), size: 110, rotation:  0.20),
         ]),
    Shot(app: "Drafted", index: 2, bg: DRAFTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "5 tones, 3 drafts",
         headline: "Pick a tone.\nWe write\nthe rest.",
         phoneScreenshot: "\(pop)/Drafted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "✏️", center: NSPoint(x: 200, y: 900), size: 120, rotation: 0.22),
            EmojiSticker(emoji: "🎯", center: NSPoint(x: 1080, y: 1300), size: 110, rotation: -0.18),
         ]),
    Shot(app: "Drafted", index: 3, bg: DRAFTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Send it once",
         headline: "Mean it.\nSend it.\nMove on.",
         phoneScreenshot: "\(pop)/Drafted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🔥", center: NSPoint(x: 200, y: 1200), size: 130, rotation: -0.15),
            EmojiSticker(emoji: "💌", center: NSPoint(x: 1100, y: 700), size: 120, rotation:  0.22),
         ]),
    Shot(app: "Drafted", index: 4, bg: DRAFTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Stop overthinking",
         headline: "Decide\nbefore you\nover-think it.",
         phoneScreenshot: "\(pop)/Drafted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🧠", center: NSPoint(x: 200, y: 900), size: 130, rotation: 0.18),
            EmojiSticker(emoji: "✅", center: NSPoint(x: 1080, y: 1200), size: 120, rotation: -0.18),
         ]),
    Shot(app: "Drafted", index: 5, bg: DRAFTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "30 seconds flat",
         headline: "Three drafts.\nOne tone.\nDone.",
         phoneScreenshot: "\(pop)/Drafted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "⚡", center: NSPoint(x: 200, y: 1100), size: 130, rotation: -0.2),
            EmojiSticker(emoji: "📝", center: NSPoint(x: 1090, y: 800), size: 120, rotation:  0.18),
         ]),

    // ─── SCRIPTED ───
    Shot(app: "Scripted", index: 1, bg: SCRIPTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Manifestation, but pretty",
         headline: "Script the\nyear you said\nyou would.",
         phoneScreenshot: "\(pop)/Scripted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "✨", center: NSPoint(x: 200, y: 1300), size: 140, rotation: -0.2),
            EmojiSticker(emoji: "🌸", center: NSPoint(x: 1100, y: 900), size: 130, rotation:  0.18),
         ]),
    Shot(app: "Scripted", index: 2, bg: SCRIPTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "3 categories",
         headline: "Future you.\nLetter to self.\nIntentions.",
         phoneScreenshot: "\(pop)/Scripted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "📓", center: NSPoint(x: 180, y: 1100), size: 130, rotation: 0.2),
            EmojiSticker(emoji: "💌", center: NSPoint(x: 1100, y: 1300), size: 120, rotation: -0.2),
         ]),
    Shot(app: "Scripted", index: 3, bg: SCRIPTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "It era unlocked",
         headline: "Aesthetic\njournaling for\nyour it era.",
         phoneScreenshot: "\(pop)/Scripted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🌸", center: NSPoint(x: 200, y: 700), size: 130, rotation: -0.15),
            EmojiSticker(emoji: "✨", center: NSPoint(x: 1080, y: 1200), size: 140, rotation:  0.22),
         ]),
    Shot(app: "Scripted", index: 4, bg: SCRIPTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "5 minutes a day",
         headline: "Show up.\nWrite it down.\nWatch it work.",
         phoneScreenshot: "\(pop)/Scripted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🌷", center: NSPoint(x: 200, y: 900), size: 130, rotation: 0.18),
            EmojiSticker(emoji: "🪞", center: NSPoint(x: 1080, y: 1200), size: 120, rotation: -0.18),
         ]),
    Shot(app: "Scripted", index: 5, bg: SCRIPTED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "4 themes",
         headline: "Cream.\nLavender.\nForest. Midnight.",
         phoneScreenshot: "\(pop)/Scripted/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🌙", center: NSPoint(x: 200, y: 1100), size: 130, rotation: -0.2),
            EmojiSticker(emoji: "🪻", center: NSPoint(x: 1090, y: 800), size: 130, rotation:  0.18),
         ]),

    // ─── PULLED ───
    Shot(app: "Pulled", index: 1, bg: PULLED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Daily ritual",
         headline: "Pull one card.\nJust one.\nJust today.",
         phoneScreenshot: "\(pop)/Pulled/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🌙", center: NSPoint(x: 200, y: 1300), size: 130, rotation: -0.2),
            EmojiSticker(emoji: "⭐", center: NSPoint(x: 1100, y: 900), size: 110, rotation:  0.22),
         ]),
    Shot(app: "Pulled", index: 2, bg: PULLED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "AI reads it",
         headline: "A reading\nfor your\nright now.",
         phoneScreenshot: "\(pop)/Pulled/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🔮", center: NSPoint(x: 200, y: 1100), size: 130, rotation: 0.2),
            EmojiSticker(emoji: "✨", center: NSPoint(x: 1100, y: 1300), size: 120, rotation: -0.2),
         ]),
    Shot(app: "Pulled", index: 3, bg: PULLED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Lock screen drop",
         headline: "Today's card.\nRight there.\nEvery morning.",
         phoneScreenshot: "\(pop)/Pulled/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🌙", center: NSPoint(x: 200, y: 700), size: 130, rotation: -0.18),
            EmojiSticker(emoji: "🌟", center: NSPoint(x: 1080, y: 1200), size: 130, rotation:  0.22),
         ]),
    Shot(app: "Pulled", index: 4, bg: PULLED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Major Arcana, all 22",
         headline: "All the cards.\nOne a day.\nForever.",
         phoneScreenshot: "\(pop)/Pulled/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🃏", center: NSPoint(x: 200, y: 900), size: 130, rotation: 0.2),
            EmojiSticker(emoji: "♾️", center: NSPoint(x: 1080, y: 1200), size: 120, rotation: -0.18),
         ]),
    Shot(app: "Pulled", index: 5, bg: PULLED_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Reflection, not advice",
         headline: "Not divination.\nJust a\nmirror.",
         phoneScreenshot: "\(pop)/Pulled/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🪞", center: NSPoint(x: 200, y: 1100), size: 130, rotation: -0.2),
            EmojiSticker(emoji: "🌌", center: NSPoint(x: 1080, y: 800), size: 130, rotation:  0.18),
         ]),

    // ─── AURACARD ───
    Shot(app: "Auracard", index: 1, bg: AURACARD_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Vibe check",
         headline: "What's\nyour aura\ntoday?",
         phoneScreenshot: "\(pop)/Auracard/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "💜", center: NSPoint(x: 200, y: 1300), size: 130, rotation: -0.2),
            EmojiSticker(emoji: "✨", center: NSPoint(x: 1100, y: 1100), size: 130, rotation:  0.2),
         ]),
    Shot(app: "Auracard", index: 2, bg: AURACARD_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Snap. Read.",
         headline: "AI sees\nwhat you\ncan't.",
         phoneScreenshot: "\(pop)/Auracard/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "📸", center: NSPoint(x: 200, y: 1100), size: 130, rotation: 0.18),
            EmojiSticker(emoji: "🌈", center: NSPoint(x: 1080, y: 1300), size: 120, rotation: -0.2),
         ]),
    Shot(app: "Auracard", index: 3, bg: AURACARD_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Story ready",
         headline: "Aura cards\nmade for\nyour story.",
         phoneScreenshot: "\(pop)/Auracard/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "⚡", center: NSPoint(x: 200, y: 700), size: 130, rotation: -0.15),
            EmojiSticker(emoji: "💫", center: NSPoint(x: 1080, y: 1200), size: 130, rotation:  0.22),
         ]),
    Shot(app: "Auracard", index: 4, bg: AURACARD_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Score the day",
         headline: "0 to 100.\nWhat's\nyour number?",
         phoneScreenshot: "\(pop)/Auracard/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🔢", center: NSPoint(x: 200, y: 900), size: 130, rotation: 0.2),
            EmojiSticker(emoji: "💎", center: NSPoint(x: 1080, y: 1200), size: 120, rotation: -0.18),
         ]),
    Shot(app: "Auracard", index: 5, bg: AURACARD_BG, textColor: WHITE,
         pillBg: BLACK, pillFg: WHITE,
         pillText: "Glow up",
         headline: "9:16.\nMade for\nthe story drop.",
         phoneScreenshot: "\(pop)/Auracard/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "📱", center: NSPoint(x: 200, y: 1100), size: 130, rotation: -0.2),
            EmojiSticker(emoji: "💖", center: NSPoint(x: 1080, y: 800), size: 130, rotation:  0.18),
         ]),

    // ─── SHELF ───
    Shot(app: "Shelf", index: 1, bg: SHELF_BG, textColor: CREAM,
         pillBg: CREAM, pillFg: SHELF_BG,
         pillText: "BookTok core",
         headline: "Books.\nBeautifully\nshelved.",
         phoneScreenshot: "\(pop)/Shelf/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "📚", center: NSPoint(x: 200, y: 1300), size: 140, rotation: -0.2),
            EmojiSticker(emoji: "☕", center: NSPoint(x: 1100, y: 1100), size: 120, rotation:  0.2),
         ]),
    Shot(app: "Shelf", index: 2, bg: SHELF_BG, textColor: CREAM,
         pillBg: CREAM, pillFg: SHELF_BG,
         pillText: "Scan in seconds",
         headline: "Add any book\nin three\nseconds flat.",
         phoneScreenshot: "\(pop)/Shelf/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "📖", center: NSPoint(x: 200, y: 1100), size: 130, rotation: 0.2),
            EmojiSticker(emoji: "🔖", center: NSPoint(x: 1080, y: 1300), size: 130, rotation: -0.2),
         ]),
    Shot(app: "Shelf", index: 3, bg: SHELF_BG, textColor: CREAM,
         pillBg: CREAM, pillFg: SHELF_BG,
         pillText: "Streak it",
         headline: "Read a little\nevery day.\nWatch it add up.",
         phoneScreenshot: "\(pop)/Shelf/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🤎", center: NSPoint(x: 200, y: 700), size: 130, rotation: -0.18),
            EmojiSticker(emoji: "📚", center: NSPoint(x: 1080, y: 1200), size: 140, rotation:  0.22),
         ]),
    Shot(app: "Shelf", index: 4, bg: SHELF_BG, textColor: CREAM,
         pillBg: CREAM, pillFg: SHELF_BG,
         pillText: "Yours alone",
         headline: "No accounts.\nNo ads.\nNo tracking.",
         phoneScreenshot: "\(pop)/Shelf/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🔒", center: NSPoint(x: 200, y: 900), size: 130, rotation: 0.2),
            EmojiSticker(emoji: "📕", center: NSPoint(x: 1080, y: 1200), size: 130, rotation: -0.18),
         ]),
    Shot(app: "Shelf", index: 5, bg: SHELF_BG, textColor: CREAM,
         pillBg: CREAM, pillFg: SHELF_BG,
         pillText: "Aesthetic AF",
         headline: "Real shelves.\nWood-grain\npixels.",
         phoneScreenshot: "\(pop)/Shelf/populated-01.png",
         stickers: [
            EmojiSticker(emoji: "🪵", center: NSPoint(x: 200, y: 1100), size: 130, rotation: -0.2),
            EmojiSticker(emoji: "📖", center: NSPoint(x: 1080, y: 800), size: 130, rotation:  0.18),
         ]),
]

print("Generating \(SHOTS.count) Slay-style screenshots…")
for shot in SHOTS {
    let dir = "/tmp/screenshots-slay/\(shot.app)"
    let path = "\(dir)/slay-\(String(format: "%02d", shot.index)).png"
    render(shot, to: path)
}
print("Done.")
