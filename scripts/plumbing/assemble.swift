// Usage: swift assemble.swift CURRENT.pdf STAGE REVISED.pdf
import AppKit
import PDFKit

struct Manifest: Decodable {
    struct Sheet: Decodable {
        let id: String
        let title: String
    }
    let sheets: [Sheet]
    let fixtureTags: [String]
    let utilityTags: [String]
}

let args = CommandLine.arguments
precondition(args.count == 4)
let sourceURL = URL(fileURLWithPath: args[1]).standardizedFileURL
let stage = URL(fileURLWithPath: args[2], isDirectory: true)
let result = URL(fileURLWithPath: args[3]).standardizedFileURL
precondition(sourceURL != result)
let source = PDFDocument(url: sourceURL)!
let manifest = try JSONDecoder().decode(Manifest.self,
    from: Data(contentsOf: stage.appendingPathComponent("plumbing-manifest.json")))
let replacementIDs = manifest.sheets.map(\.id) + ["E-00"]
let sheets = Dictionary(uniqueKeysWithValues: replacementIDs.map { id in
    let file = PDFDocument(url: stage.appendingPathComponent(id + ".pdf"))!
    precondition(file.pageCount == 1)
    return (id, file)
})
let root = source.outlineRoot!
let sectionNames = (0..<root.numberOfChildren).map { root.child(at: $0)!.label! }
precondition(sectionNames.contains("Interior elevations"))
let location = CGPoint(x: 0, y: 792)
let output = PDFDocument()
let outline = PDFOutline()
var expected: [PDFPage] = []
var newSheetIndices: [String: Int] = [:]
var originalCount = 0

func addSection(_ name: String, _ items: [(String, PDFPage)]) {
    precondition(!items.isEmpty)
    let section = PDFOutline()
    section.label = name
    section.destination = PDFDestination(page: items[0].1, at: location)
    outline.insertChild(section, at: outline.numberOfChildren)
    for (title, page) in items {
        output.insert(page, at: output.pageCount)
        expected.append(page)
        let entry = PDFOutline()
        entry.label = title
        entry.destination = PDFDestination(page: page, at: location)
        section.insertChild(entry, at: section.numberOfChildren)
    }
}

for (index,name) in sectionNames.enumerated() {
    let original = root.child(at: index)!
    originalCount += original.numberOfChildren
    if name == "Plumbing plans" { continue }
    if name == "Interior elevations" {
        let start = output.pageCount
        addSection("Plumbing plans", manifest.sheets.map {
            ("\($0.id)  \($0.title)", sheets[$0.id]!.page(at: 0)!)
        })
        for (offset, sheet) in manifest.sheets.enumerated() {
            newSheetIndices[sheet.id] = start + offset
        }
    }
    addSection(name, (0..<original.numberOfChildren).map {
        let entry = original.child(at: $0)!
        let title = entry.label!
        let page = title.hasPrefix("E-00") ? sheets["E-00"]!.page(at: 0)! : entry.destination!.page!
        return (title, page)
    })
}
precondition(originalCount == source.pageCount, "Every source sheet must be bookmarked")
precondition(output.pageCount == source.pageCount + (sectionNames.contains("Plumbing plans") ? 0 : manifest.sheets.count))
output.outlineRoot = outline
output.documentAttributes = source.documentAttributes
precondition(output.write(to: result))

let reopened = PDFDocument(url: result)!
let size = NSSize(width: 1224, height: 792)
precondition(reopened.pageCount == expected.count)
precondition(reopened.outlineRoot?.numberOfChildren == 5)
func tokens(_ page: PDFPage) -> [Substring] {
    page.string!.split(whereSeparator: \.isWhitespace)
}
for (index, page) in expected.enumerated() {
    let actual = reopened.page(at: index)!
    precondition(actual.bounds(for: .mediaBox).size == size)
    precondition(tokens(page).sorted() == tokens(actual).sorted(), "Text changed on page \(index+1)")
    let before = page.thumbnail(of: size, for: .mediaBox).tiffRepresentation!
    let after = actual.thumbnail(of: size, for: .mediaBox).tiffRepresentation!
    if before == after { continue }
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
                 Double(largeDeltas) / Double(count) < 0.012, "Drawing changed on page \(index+1)")
}
for (id, tags) in [("P-01", manifest.fixtureTags), ("P-02", manifest.utilityTags), ("P-03", manifest.fixtureTags)] {
    let page = reopened.page(at: newSheetIndices[id]!)!
    let words = tokens(page)
    precondition(words.contains(Substring(id)))
    precondition(tags.allSatisfy { words.contains(Substring($0)) }, "Missing coordinated tag on \(id)")
}
let water = reopened.page(at: newSheetIndices["P-02"]!)!.string!
precondition(water.contains("Proposed design is all-electric."))
print("Verified \(reopened.pageCount) landscape sheets, three plumbing sheets and \(manifest.fixtureTags.count) coordinated fixture tags.")
