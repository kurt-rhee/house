// Replace gallery sheets in the published set.
// Usage: swift assemble.swift CURRENT.pdf STAGE REVISED.pdf
import AppKit
import PDFKit

struct Gallery: Decodable {
    let id: String
    let title: String
    struct View: Decodable {
        let title: String
        let caption: String
    }

    let views: [View]
}

let args = CommandLine.arguments
precondition(args.count == 4)
let stage = URL(fileURLWithPath: args[2], isDirectory: true)
let sourceURL = URL(fileURLWithPath: args[1])
let resultURL = URL(fileURLWithPath: args[3])
precondition(sourceURL.standardizedFileURL != resultURL.standardizedFileURL)
let source = PDFDocument(url: sourceURL)!
let manifestURL = stage.appendingPathComponent("gallery-manifest.json")
let gallery = try JSONDecoder().decode([Gallery].self, from: Data(contentsOf: manifestURL))
let oldRoot = source.outlineRoot!
let oldSections = (0..<oldRoot.numberOfChildren).map { oldRoot.child(at: $0)! }
let galleryName = "Proposed 3D renderings"
let oldGallery = oldSections.last!
precondition([galleryName, "Before and After Renderings"].contains(oldGallery.label ?? ""))
precondition(oldGallery.numberOfChildren == gallery.count)
let startGallery = source.pageCount - gallery.count
let replacementDocs = gallery.map { PDFDocument(url: stage.appendingPathComponent("\($0.id).pdf"))! }
precondition(replacementDocs.allSatisfy { $0.pageCount == 1 })
for (index, sheet) in gallery.enumerated() {
    let pageIndex = startGallery + index
    precondition(source.index(for: oldGallery.child(at: index)!.destination!.page!) == pageIndex)
    precondition(source.page(at: pageIndex)!.string!.contains(sheet.id))
}

let pages = (0..<startGallery).map { source.page(at: $0)! }
    + replacementDocs.map { $0.page(at: 0)! }

let output = PDFDocument()
for (index,page) in pages.enumerated() {
    output.insert(page, at: index)
}

let outline = PDFOutline()
func copyOutline(_ previous: PDFOutline) -> PDFOutline {
    let entry = PDFOutline()
    entry.label = previous.label
    if let target = previous.destination, let page = target.page {
        let index = source.index(for: page)
        precondition((0..<startGallery).contains(index))
        let destination = PDFDestination(page: pages[index], at: target.point)
        destination.zoom = target.zoom
        entry.destination = destination
    }
    for index in 0..<previous.numberOfChildren {
        entry.insertChild(copyOutline(previous.child(at: index)!), at: index)
    }
    return entry
}
for (index, previous) in oldSections.dropLast().enumerated() {
    outline.insertChild(copyOutline(previous), at: index)
}
let section = PDFOutline()
section.label = galleryName
section.destination = PDFDestination(page: pages[startGallery], at: CGPoint(x: 0, y: 792))
outline.insertChild(section, at: oldSections.count - 1)
for (index, sheet) in gallery.enumerated() {
    let entry = PDFOutline()
    entry.label = sheet.id + "  " + sheet.title.replacingOccurrences(of: " | ", with: " — ")
    entry.destination = PDFDestination(page: pages[startGallery + index], at: CGPoint(x: 0, y: 792))
    section.insertChild(entry, at: index)
}
output.outlineRoot = outline
output.documentAttributes = source.documentAttributes
precondition(output.write(to: resultURL))

let reopened = PDFDocument(url: resultURL)!
let size = NSSize(width: 1224, height: 792)
precondition(reopened.pageCount == pages.count)
let reopenedGallery = reopened.outlineRoot!.child(at: oldSections.count - 1)!
precondition(reopenedGallery.label == galleryName && reopenedGallery.numberOfChildren == gallery.count)
func words(_ text: String) -> [Substring] {
    text.split(whereSeparator: \.isWhitespace).sorted()
}
for (index,expected) in pages.enumerated() {
    let actual = reopened.page(at: index)!
    let text = actual.string!
    precondition(actual.bounds(for: .mediaBox).size == size)
    precondition(words(text) == words(expected.string!), "Text changed at sheet \(index+1)")
    let before = expected.thumbnail(of: size, for: .mediaBox).tiffRepresentation!
    let after = actual.thumbnail(of: size, for: .mediaBox).tiffRepresentation!
    if index >= startGallery {
        let sheet = gallery[index-startGallery]
        precondition(text.contains(sheet.id))
        precondition(text.contains("PROPOSED 3D RENDERINGS"))
        let normalized = text.split(whereSeparator: \.isWhitespace).joined(separator: " ")
        precondition(!normalized.contains("BEFORE / ORIGINAL FROM A-01"))
        let page = reopenedGallery.child(at: index - startGallery)!.destination!.page!
        precondition(reopened.index(for: page) == index)
        for view in sheet.views {
            precondition(normalized.contains(view.title), "Missing \(view.title) on \(sheet.id)")
            precondition(normalized.contains(view.caption), "Missing caption for \(view.title) on \(sheet.id)")
        }
    }
    if before == after {
        continue
    }
    let expectedImage = NSBitmapImageRep(data: before)!
    let actualImage = NSBitmapImageRep(data: after)!
    precondition(expectedImage.bytesPerRow == actualImage.bytesPerRow && expectedImage.pixelsHigh == actualImage.pixelsHigh)
    let count = actualImage.bytesPerRow * actualImage.pixelsHigh
    let a = expectedImage.bitmapData!
    let b = actualImage.bitmapData!
    var total = 0
    var largeDeltas = 0
    for k in 0..<count {
        let delta = abs(Int(a[k]) - Int(b[k]))
        total += delta
        if delta > 24 { largeDeltas += 1 }
    }
    let delta = Double(total) / Double(count)
    let fraction = Double(largeDeltas) / Double(count)
    precondition(delta < 1 && fraction < 0.012,
                 "Sheet \(index+1) changed at assembly (mean pixel delta \(delta), high-delta fraction \(fraction))")
}
print("Verified \(reopened.pageCount) sheets and \(gallery.flatMap { $0.views }.count) proposed views with captions.")
