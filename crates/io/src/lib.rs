//! Versioned JSON persistence and portable drawing exports.
mod dxf_export;
pub use dxf_export::{dxf_bytes, export_dxf};
use house_core::*;
use house_geometry::{dimension_value, length, room_bounds, validate, wall_polygon};
use std::{fmt::Write as _, path::Path};
pub fn to_json(d: &Document) -> Result<String, String> {
    validate(d)?;
    serde_json::to_string_pretty(d).map_err(|e| e.to_string())
}
pub fn from_json(s: &str) -> Result<Document, String> {
    let d: Document = serde_json::from_str(s).map_err(|e| e.to_string())?;
    validate(&d)?;
    Ok(d)
}
pub fn load(path: &Path) -> Result<Document, String> {
    from_json(&std::fs::read_to_string(path).map_err(|e| e.to_string())?)
}
/// Write adjacent temporary file then rename, leaving the previous project intact on failure.
pub fn save(d: &Document, path: &Path) -> Result<(), String> {
    atomic_write(path, to_json(d)?.as_bytes())
}
fn atomic_write(path: &Path, data: &[u8]) -> Result<(), String> {
    let tmp = path.with_extension(format!("{}.tmp", Id::new_v4()));
    let result = (|| {
        use std::io::Write;
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&tmp)?;
        file.write_all(data)?;
        file.sync_all()?;
        std::fs::rename(&tmp, path)
    })();
    if result.is_err() {
        let _ = std::fs::remove_file(tmp);
    }
    result.map_err(|e: std::io::Error| e.to_string())
}
fn escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&apos;")
}
pub fn svg(d: &Document) -> Result<String, String> {
    validate(d)?;
    let mut min = Point::new(0.0, 0.0);
    let mut max = Point::new(100.0, 100.0);
    for w in d.walls.values() {
        for p in wall_polygon(w) {
            min.x = min.x.min(p.x);
            min.y = min.y.min(p.y);
            max.x = max.x.max(p.x);
            max.y = max.y.max(p.y);
        }
    }
    let mut s = format!(
        "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"{} {} {} {}\" width=\"{}mm\" height=\"{}mm\">\n<rect x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" fill=\"white\"/>\n",
        min.x - 200.0,
        min.y - 200.0,
        max.x - min.x + 400.0,
        max.y - min.y + 400.0,
        max.x - min.x + 400.0,
        max.y - min.y + 400.0,
        min.x - 200.0,
        min.y - 200.0,
        max.x - min.x + 400.0,
        max.y - min.y + 400.0
    );
    for w in d.walls.values().filter(|w| d.layers[&w.layer].visible) {
        let points = wall_polygon(w)
            .iter()
            .map(|p| format!("{},{}", p.x, p.y))
            .collect::<Vec<_>>()
            .join(" ");
        writeln!(s, "<polygon points=\"{points}\" fill=\"#444\"/>").unwrap();
    }
    for door in d.doors.values() {
        let w = &d.walls[&door.wall];
        if !d.layers[&w.layer].visible {
            continue;
        }
        let l = length(w);
        let ux = (w.end.x - w.start.x) / l;
        let uy = (w.end.y - w.start.y) / l;
        let p = Point::new(
            w.start.x + ux * (door.position - door.width / 2.0),
            w.start.y + uy * (door.position - door.width / 2.0),
        );
        let angle = uy.atan2(ux).to_degrees();
        let sign = if door.swing == Swing::Left { 1.0 } else { -1.0 };
        writeln!(s,"<g transform=\"translate({} {}) rotate({})\"><path d=\"M 0 0 H {}\" stroke=\"white\" stroke-width=\"{}\"/><path d=\"M 0 0 V {} M {} 0 A {} {} 0 0 {} 0 {}\" fill=\"none\" stroke=\"#168\" stroke-width=\"8\"/></g>",p.x,p.y,angle,door.width,w.thickness+2.0,door.width*sign,door.width,door.width,door.width,if sign>0.0{1}else{0},door.width*sign).unwrap();
    }
    for r in d.rooms.values() {
        let b = room_bounds(d, r)?;
        writeln!(s,"<text x=\"{}\" y=\"{}\" font-family=\"sans-serif\" font-size=\"65\" text-anchor=\"middle\">{} · {:.2} m²</text>",b.x+b.width/2.0,b.y+b.height/2.0,escape(&r.name),b.area()/1e6).unwrap();
    }
    for dim in d.dimensions.values() {
        let r = &d.rooms[&dim.room];
        let b = room_bounds(d, r)?;
        let value = dimension_value(d, dim)?;
        let (a, z) = match dim.kind {
            DimensionKind::Width => (
                Point::new(b.x, b.y + 120.0),
                Point::new(b.x + b.width, b.y + 120.0),
            ),
            DimensionKind::Height => (
                Point::new(b.x + 120.0, b.y),
                Point::new(b.x + 120.0, b.y + b.height),
            ),
        };
        writeln!(s,"<path d=\"M {} {} L {} {}\" stroke=\"#678\" stroke-width=\"5\"/><text x=\"{}\" y=\"{}\" font-family=\"sans-serif\" font-size=\"45\">{:.1} mm</text>",a.x,a.y,z.x,z.y,(a.x+z.x)/2.0+15.0,(a.y+z.y)/2.0-15.0,value).unwrap();
    }
    s.push_str("</svg>\n");
    Ok(s)
}
pub fn export_svg(d: &Document, path: &Path) -> Result<(), String> {
    atomic_write(path, svg(d)?.as_bytes())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn round_trip_and_schema() {
        let d = bathroom();
        assert_eq!(from_json(&to_json(&d).unwrap()).unwrap(), d);
        let mut bad = d.clone();
        bad.schema_version = 2;
        assert!(from_json(&serde_json::to_string(&bad).unwrap()).is_err());
        let s = svg(&d).unwrap();
        assert!(s.contains("<polygon"));
        assert!(s.contains("2438.4 mm"));
    }
    #[test]
    fn disk_round_trip() {
        let p = std::env::temp_dir().join(format!("house-{}.json", Id::new_v4()));
        let d = bathroom();
        save(&d, &p).unwrap();
        assert_eq!(load(&p).unwrap(), d);
        std::fs::remove_file(p).unwrap();
    }
}

#[cfg(test)]
mod precision_tests {
    use super::*;
    #[test]
    fn retains_float_bits_after_translation() {
        let mut d = bathroom();
        let wall = d
            .walls
            .values_mut()
            .find(|w| w.name == "Partition")
            .unwrap();
        wall.start.x += 152.4;
        wall.end.x += 152.4;
        let restored = from_json(&to_json(&d).unwrap()).unwrap();
        assert_eq!(restored, d);
    }
}

#[cfg(test)]
mod sample_fixture_tests {
    use super::*;
    #[test]
    fn sample_fixture_has_exact_interior_footprint() {
        let d = from_json(include_str!("../../../examples/bathroom.house.json")).unwrap();
        let wall = |name| d.walls.values().find(|w| w.name == name).unwrap();
        let width = wall("East").start.x
            - wall("East").thickness / 2.0
            - (wall("West").start.x + wall("West").thickness / 2.0);
        let height = wall("South").start.y
            - wall("South").thickness / 2.0
            - (wall("North").start.y + wall("North").thickness / 2.0);
        assert_eq!(width, inches(134.0));
        assert_eq!(height, inches(96.0));
        assert_eq!(d.walls.len(), 5);
        assert_eq!(d.doors.len(), 2);
        assert_eq!(d.rooms.len(), 2);
        assert_eq!(d.dimensions.len(), 4);
    }
}
