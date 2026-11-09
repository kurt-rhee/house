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
    let mut d: Document = serde_json::from_str(s).map_err(|e| e.to_string())?;
    if d.schema_version == 1 {
        d.schema_version = SCHEMA_VERSION;
    }
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
    for f in d.fixtures.values() {
        for p in house_geometry::fixture_corners(f) {
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
    for door in d.doors.values().filter(|v| v.kind == DoorKind::Hinged) {
        let w = &d.walls[&door.wall];
        if !d.layers[&w.layer].visible {
            continue;
        }
        let l = length(w);
        let ux = (w.end.x - w.start.x) / l;
        let uy = (w.end.y - w.start.y) / l;
        let direction = if door.hinge_at_end { -1.0 } else { 1.0 };
        let p = Point::new(
            w.start.x + ux * (door.position - direction * door.width / 2.0),
            w.start.y + uy * (door.position - direction * door.width / 2.0),
        );
        let angle = uy.atan2(ux).to_degrees();
        let sign = if door.swing == Swing::Left { 1.0 } else { -1.0 };
        writeln!(s,"<g transform=\"translate({} {}) rotate({})\"><path d=\"M 0 0 H {}\" stroke=\"white\" stroke-width=\"{}\"/><path d=\"M 0 0 V {} M {} 0 A {} {} 0 0 {} 0 {}\" fill=\"none\" stroke=\"#168\" stroke-width=\"8\"/></g>",p.x,p.y,angle,door.width*direction,w.thickness+2.0,door.width*sign,door.width*direction,door.width,door.width,if sign*direction>0.0{1}else{0},door.width*sign).unwrap();
    }
    for (wall, position, width) in d
        .windows
        .values()
        .map(|v| (v.wall, v.position, v.width))
        .chain(
            d.doors
                .values()
                .filter(|v| v.kind != DoorKind::Hinged)
                .map(|v| (v.wall, v.position, v.width)),
        )
    {
        let w = &d.walls[&wall];
        if !d.layers[&w.layer].visible {
            continue;
        }
        let l = length(w);
        let p = |station: f64| {
            Point::new(
                w.start.x + (w.end.x - w.start.x) * station / l,
                w.start.y + (w.end.y - w.start.y) * station / l,
            )
        };
        let a = p(position - width / 2.0);
        let b = p(position + width / 2.0);
        writeln!(
            s,
            "<path d=\"M {} {} L {} {}\" stroke=\"white\" stroke-width=\"{}\"/>",
            a.x,
            a.y,
            b.x,
            b.y,
            w.thickness + 2.0
        )
        .unwrap();
    }
    for door in d.doors.values().filter(|v| v.kind == DoorKind::Pocket) {
        let wall = &d.walls[&door.wall];
        if !d.layers[&wall.layer].visible {
            continue;
        }
        let sign = if door.swing == Swing::Left { 1.0 } else { -1.0 };
        let start = door.position + sign * door.width / 2.0;
        let end = start + sign * door.width;
        let point = |station| {
            Point::new(
                wall.start.x + (wall.end.x - wall.start.x) * station / length(wall),
                wall.start.y + (wall.end.y - wall.start.y) * station / length(wall),
            )
        };
        let a = point(start);
        let b = point(end);
        writeln!(
            s,
            "<path d=\"M {} {} L {} {}\" stroke=\"white\" stroke-width=\"{}\"/>",
            a.x,
            a.y,
            b.x,
            b.y,
            wall.thickness * 0.6
        )
        .unwrap();
    }
    for symbol in house_geometry::plan_symbols(d) {
        if !d.layers[&symbol.layer].visible {
            continue;
        }
        writeln!(
            s,
            "<g id=\"object-{}\" fill=\"none\" stroke=\"#168\" stroke-width=\"8\">",
            symbol.id
        )
        .unwrap();
        for (a, b) in symbol.lines {
            writeln!(s, "<path d=\"M {} {} L {} {}\"/>", a.x, a.y, b.x, b.y).unwrap();
        }
        s.push_str("</g>\n");
    }
    for label in d.room_labels.values() {
        writeln!(s, "<text x=\"{}\" y=\"{}\" font-family=\"sans-serif\" font-size=\"160\" text-anchor=\"middle\">{}</text>", label.position.x, label.position.y, escape(&label.name)).unwrap();
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
        bad.schema_version = SCHEMA_VERSION + 1;
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

#[cfg(test)]
mod fixture_tests {
    use super::*;
    #[test]
    fn version_one_migrates_and_new_symbols_round_trip_exactly() {
        let legacy = include_str!("../../../examples/bathroom.house.json");
        let mut json: serde_json::Value = serde_json::from_str(legacy).unwrap();
        json["schema_version"] = serde_json::json!(1);
        json.as_object_mut().unwrap().remove("fixtures");
        for door in json["doors"].as_object_mut().unwrap().values_mut() {
            door.as_object_mut().unwrap().remove("kind");
        }
        let migrated = from_json(&json.to_string()).unwrap();
        assert_eq!(migrated.schema_version, SCHEMA_VERSION);
        assert!(migrated.fixtures.is_empty());
        assert!(migrated.doors.values().all(|v| v.kind == DoorKind::Hinged));
        let mut d = Document::default();
        let layer = *d.layers.keys().next().unwrap();
        let f = Fixture {
            id: Id::new_v4(),
            kind: FixtureKind::Bath,
            origin: Point::new(-5000.0, 200.0),
            width: 1524.0,
            depth: 762.0,
            rotation: 90.0,
            layer,
        };
        d.fixtures.insert(f.id, f.clone());
        assert_eq!(from_json(&to_json(&d).unwrap()).unwrap(), d);
        let output = svg(&d).unwrap();
        assert!(output.contains(&format!("object-{}", f.id)));
        // The viewBox includes the full rotated fixture, even without walls.
        let bounds: Vec<f64> = output
            .split("viewBox=\"")
            .nth(1)
            .unwrap()
            .split('"')
            .next()
            .unwrap()
            .split_whitespace()
            .map(|n| n.parse().unwrap())
            .collect();
        for (actual, expected) in bounds.iter().zip([-5962.0, -200.0, 6262.0, 2124.0]) {
            assert!((actual - expected).abs() < 1e-9);
        }
    }
}

#[cfg(test)]
mod room_label_tests {
    use super::*;
    #[test]
    fn garage_door_round_trips_and_exports_as_solid_panels() {
        let mut d = house_core::bathroom();
        let id = *d.doors.keys().next().unwrap();
        for door in d.doors.values_mut() {
            door.kind = DoorKind::Garage;
        }
        assert_eq!(from_json(&to_json(&d).unwrap()).unwrap(), d);
        let symbol = house_geometry::plan_symbols(&d)
            .into_iter()
            .find(|s| s.id == id)
            .unwrap();
        assert_eq!(symbol.lines.len(), 13);
        let door = &d.doors[&id];
        let wall = &d.walls[&door.wall];
        assert!(
            symbol
                .lines
                .iter()
                .flat_map(|(a, b)| [a, b])
                .all(|p| house_geometry::distance(wall, *p) <= wall.thickness / 2.0 + 0.001)
        );
        let bytes = dxf_bytes(&d).unwrap();
        let drawing = dxf::Drawing::load(&mut bytes.as_slice()).unwrap();
        assert!(
            !drawing
                .entities()
                .any(|e| matches!(e.specific, dxf::entities::EntityType::Arc(_)))
        );
    }
    #[test]
    fn labels_round_trip_and_export_with_escaped_names() {
        let mut d = Document::default();
        let id = Id::new_v4();
        d.room_labels.insert(
            id,
            RoomLabel {
                id,
                name: "Kitchen & dining".into(),
                position: Point::new(150.0, 200.0),
            },
        );
        assert_eq!(from_json(&to_json(&d).unwrap()).unwrap(), d);
        let path = std::env::temp_dir().join(format!("room-label-{id}.svg"));
        export_svg(&d, &path).unwrap();
        assert!(
            std::fs::read_to_string(&path)
                .unwrap()
                .contains("Kitchen &amp; dining")
        );
        std::fs::remove_file(path).unwrap();
        let drawing = dxf_bytes(&d).unwrap();
        assert!(String::from_utf8_lossy(&drawing).contains("Kitchen & dining"));
    }
}
