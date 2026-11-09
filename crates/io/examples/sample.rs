fn main() -> Result<(), String> {
    let d = house_io::from_json(include_str!("../../../examples/bathroom.house.json"))?;
    std::fs::create_dir_all("examples").map_err(|e| e.to_string())?;
    house_io::save(&d, std::path::Path::new("examples/bathroom.house.json"))?;
    house_io::export_svg(&d, std::path::Path::new("examples/bathroom.svg"))?;
    house_io::export_dxf(&d, std::path::Path::new("examples/bathroom.dxf"))?;
    Ok(())
}
