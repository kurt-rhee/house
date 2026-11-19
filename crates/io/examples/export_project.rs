//! Regenerate SVG and DXF beside an existing editable project.
fn main() -> Result<(), String> {
    let path = std::env::args()
        .nth(1)
        .ok_or("Usage: export_project PROJECT.house.json")?;
    let path = std::path::Path::new(&path);
    let document = house_io::load(path)?;
    let stem = path.file_name().unwrap().to_string_lossy();
    let stem = stem
        .strip_suffix(".house.json")
        .ok_or("Expected .house.json suffix")?;
    let parent = path.parent().unwrap();
    house_io::export_svg(&document, &parent.join(format!("{stem}.svg")))?;
    house_io::export_dxf(&document, &parent.join(format!("{stem}.dxf")))?;
    println!("Exported revision {}", document.revision);
    Ok(())
}
