// Insert the electrical and interior sheets before the A-07–A-13 render gallery.
// Usage: swift assemble.swift existing-planset.pdf staging-directory revised-planset.pdf
import AppKit
import PDFKit

struct Sheet: Decodable {
    let id: String
    let title: String
    let tags: [String]
}

struct Manifest: Decodable {
    let sheets: [Sheet]
    let mainTags: [String]
    let detachedTags: [String]
}

let arguments = CommandLine.arguments
guard arguments.count == 4 else {
    fatalError("Provide existing plan set, staging directory, and destination PDF")
}
let source = PDFDocument(url: URL(fileURLWithPath: arguments[1]))!
let staging = URL(fileURLWithPath: arguments[2])
let destination = URL(fileURLWithPath: arguments[3])
precondition(URL(fileURLWithPath: arguments[1]).standardizedFileURL != destination.standardizedFileURL)
let manifest = try JSONDecoder().decode(Manifest.self, from: Data(contentsOf: staging.appendingPathComponent("manifest.json")))
let entries = [
    Sheet(id: "E-00", title: "Electrical criteria and branch circuit intent", tags: []),
    Sheet(id: "E-01", title: "Main house receptacle plan", tags: manifest.mainTags),
    Sheet(id: "E-02", title: "Detached wing receptacle plan", tags: manifest.detachedTags),
] + manifest.sheets
let generated = entries.map { PDFDocument(url: staging.appendingPathComponent($0.id + ".pdf"))! }
precondition(generated.allSatisfy { $0.pageCount == 1 })
let originalPages = (0..<source.pageCount).map { source.page(at: $0)! }
let renderIndex = originalPages.firstIndex { $0.string?.contains("Range and round window") == true }!
precondition(renderIndex >= 7 && originalPages.count == renderIndex + 7)
let renderPages = Array(originalPages[renderIndex...])
let originalOutline = source.outlineRoot!
let originalSections = (0..<originalOutline.numberOfChildren).map { originalOutline.child(at: $0)! }
let plumbing = originalSections.first { $0.label == "Plumbing plans" }
let gallery = originalSections.last!
precondition(gallery.numberOfChildren == renderPages.count)
let renderTitles = (0..<gallery.numberOfChildren).map { gallery.child(at: $0)!.label! }
let plumbingEntries = (0..<(plumbing?.numberOfChildren ?? 0)).map { plumbing!.child(at: $0)! }
let plumbingPages = plumbingEntries.map { $0.destination!.page! }
let generatedPages = generated.map { $0.page(at: 0)! }
let interiorStart = 10 + plumbingPages.count
let galleryStart = 7 + generated.count + plumbingPages.count
let pages = Array(originalPages.prefix(7)) + Array(generatedPages.prefix(3)) + plumbingPages
    + Array(generatedPages.dropFirst(3)) + renderPages
let output = PDFDocument()
for (index, page) in pages.enumerated() {
    output.insert(page, at: index)
}

let root = PDFOutline()
var sectionNames = ["Site and exterior drawings", "Electrical plans"]
if !plumbingPages.isEmpty { sectionNames.append("Plumbing plans") }
sectionNames += ["Interior elevations", gallery.label!]
let architecturalTitles = ["Site plan", "Before floor plan", "After floor plan", "Main house north and east",
                           "Main house south and west", "Detached wing north and east", "Detached wing south and west"]
var groups = [0..<7, 7..<10]
if !plumbingPages.isEmpty { groups.append(10..<interiorStart) }
groups += [interiorStart..<galleryStart, galleryStart..<pages.count]
let generatedTitles = entries.map { $0.id + "  " + $0.title.replacingOccurrences(of: " | ", with: " — ") }
let titles = architecturalTitles + Array(generatedTitles.prefix(3)) + plumbingEntries.map { $0.label! }
    + Array(generatedTitles.dropFirst(3)) + renderTitles
for (groupIndex, indices) in groups.map(Array.init).enumerated() {
    let section = PDFOutline()
    section.label = sectionNames[groupIndex]
    section.destination = PDFDestination(page: pages[indices[0]], at: CGPoint(x: 0, y: 792))
    root.insertChild(section, at: groupIndex)
    for (childIndex, pageIndex) in indices.enumerated() {
        let entry = PDFOutline()
        entry.label = titles[pageIndex]
        entry.destination = PDFDestination(page: pages[pageIndex], at: CGPoint(x: 0, y: 792))
        section.insertChild(entry, at: childIndex)
    }
}
output.outlineRoot = root
output.documentAttributes = [
    PDFDocumentAttribute.titleAttribute: "214 N Katherine Drive | Before and After Plan Set"
]
precondition(output.write(to: destination))
let reread = PDFDocument(url: destination)!
precondition(reread.pageCount == pages.count)
precondition(reread.outlineRoot?.numberOfChildren == groups.count)
let size = NSSize(width: 1224, height: 792)
func textTokens(_ string: String) -> [Substring] {
    string.split(whereSeparator: \.isWhitespace)
}
for index in 0..<reread.pageCount {
    let page = reread.page(at: index)!
    let text = page.string!
    precondition(page.bounds(for: .mediaBox).size == size)
    if (7..<10).contains(index) || (interiorStart..<galleryStart).contains(index) {
        let sheet = entries[index - 7 - (index >= interiorStart ? plumbingPages.count : 0)]
        precondition(text.contains(sheet.id), sheet.id)
        let tokens = textTokens(text)
        for tag in sheet.tags {
            precondition(tokens.filter { $0 == tag }.count >= 2, "Missing symbol or schedule for \(tag) on \(sheet.id)")
        }
        if sheet.id.hasPrefix("I-") {
            let electricalTags = manifest.mainTags + manifest.detachedTags
            precondition(electricalTags.allSatisfy { !tokens.contains(Substring($0)) }, sheet.id)
        }
    } else {
        let expected = pages[index]
        let before = expected.thumbnail(of: size, for: .mediaBox).tiffRepresentation!
        let after = page.thumbnail(of: size, for: .mediaBox).tiffRepresentation!
        precondition(textTokens(text).sorted() == textTokens(expected.string!).sorted(), "Sheet \(index + 1) text changed")
        if before != after {
            let a = NSBitmapImageRep(data: before)!
            let b = NSBitmapImageRep(data: after)!
            precondition(a.bytesPerRow == b.bytesPerRow && a.pixelsHigh == b.pixelsHigh)
            let count = a.bytesPerRow * a.pixelsHigh
            let aData = a.bitmapData!
            let bData = b.bitmapData!
            var totalDelta = 0
            var largeDeltas = 0
            for pixel in 0..<count {
                let delta = abs(Int(aData[pixel]) - Int(bData[pixel]))
                totalDelta += delta
                if delta > 24 { largeDeltas += 1 }
            }
            precondition(Double(totalDelta) / Double(count) < 1 &&
                         Double(largeDeltas) / Double(count) < 0.012, "Sheet \(index + 1) changed")
        }
    }
}
print("Verified \(reread.pageCount) landscape 11 × 17 pages, \(entries.count) new sheets and \(manifest.mainTags.count + manifest.detachedTags.count) electrical tags.")
