use super::*;
use house_core::{Door, bathroom};
use std::io::Cursor;
fn parsed(d: &Document) -> Drawing {
    Drawing::load(&mut Cursor::new(dxf_bytes(d).unwrap())).unwrap()
}
fn has_id(entity: &Entity, id: Id) -> bool {
    entity.common.x_data.iter().any(|data| {
        data.application_name == "HOUSE"
            && data.items.first() == Some(&XDataItem::Str(id.to_string()))
    })
}
fn near(a: f64, b: f64) {
    assert!((a - b).abs() < 1e-9, "{a} != {b}");
}

#[test]
fn sample_units_outlines_annotations_and_identity() {
    let original = bathroom();
    let snapshot = original.clone();
    let drawing = parsed(&original);
    assert_eq!(drawing.header.version, AcadVersion::R2007);
    assert_eq!(drawing.header.default_drawing_units, Units::Millimeters);
    assert_eq!(drawing.header.drawing_units, DrawingUnits::Metric);
    assert!(drawing.app_ids().any(|app| app.name == "HOUSE"));
    assert_eq!(
        drawing
            .entities()
            .filter(|e| matches!(e.specific, EntityType::LwPolyline(_)))
            .count(),
        7
    );
    for wall in original.walls.values() {
        let shapes: Vec<_> = drawing.entities().filter(|e| has_id(e, wall.id)).collect();
        assert!(!shapes.is_empty());
        assert!(shapes.iter().all(|e| e.common.layer.starts_with("WALLS_")));
        for entity in shapes {
            let EntityType::LwPolyline(poly) = &entity.specific else {
                panic!("wall must be a polyline")
            };
            assert!(poly.is_closed());
            assert_eq!(poly.vertices.len(), 4);
            // Every wall fragment retains the actual wall thickness.
            let a = poly.vertices[0];
            let b = poly.vertices[3];
            near((a.x - b.x).hypot(a.y - b.y), wall.thickness);
        }
    }
    let partition = original
        .walls
        .values()
        .find(|w| w.name == "Partition")
        .unwrap();
    let entity = drawing
        .entities()
        .find(|e| has_id(e, partition.id))
        .unwrap();
    let EntityType::LwPolyline(poly) = &entity.specific else {
        unreachable!()
    };
    for (actual, expected) in poly.vertices.iter().zip(wall_polygon(partition)) {
        near(actual.x, expected.x);
        near(actual.y, -expected.y);
    }
    for room in original.rooms.values() {
        let labels: Vec<_> = drawing
            .entities()
            .filter(|e| has_id(e, room.id))
            .filter_map(|e| match &e.specific {
                EntityType::Text(t) => Some(t),
                _ => None,
            })
            .collect();
        assert_eq!(labels.len(), 2);
        assert!(labels.iter().any(|label| label.value == room.name));
        let bounds = room_bounds(&original, room).unwrap();
        assert!(
            labels
                .iter()
                .any(|label| label.value == format!("{:.2} m²", bounds.area() / 1e6))
        );
    }
    for dimension in original.dimensions.values() {
        let value = dimension_value(&original, dimension).unwrap();
        let mut measured = false;
        for e in drawing.entities().filter(|e| has_id(e, dimension.id)) {
            if let EntityType::Line(line) = &e.specific {
                let distance = (line.p2.x - line.p1.x).hypot(line.p2.y - line.p1.y);
                if (distance - value).abs() < 1e-9 {
                    measured = true;
                }
            }
        }
        assert!(
            measured,
            "Dimension line must contain the true geometric length"
        );
    }
    assert_eq!(
        original, snapshot,
        "Export must not mutate the semantic project"
    );
}

#[test]
fn door_openings_are_gaps_in_the_wall_geometry() {
    let d = bathroom();
    let drawing = parsed(&d);
    for door in d.doors.values() {
        let w = &d.walls[&door.wall];
        let l = length(w);
        let spans: Vec<_> = drawing
            .entities()
            .filter(|e| has_id(e, w.id))
            .map(|e| {
                let EntityType::LwPolyline(poly) = &e.specific else {
                    unreachable!()
                };
                let stations: Vec<_> = poly
                    .vertices
                    .iter()
                    .map(|v| {
                        ((v.x - w.start.x) * (w.end.x - w.start.x)
                            + (-v.y - w.start.y) * (w.end.y - w.start.y))
                            / l
                    })
                    .collect();
                (
                    stations.iter().copied().fold(f64::INFINITY, f64::min),
                    stations.iter().copied().fold(f64::NEG_INFINITY, f64::max),
                )
            })
            .collect();
        assert_eq!(spans.len(), 2);
        let open_start = door.position - door.width / 2.0;
        let open_end = door.position + door.width / 2.0;
        let mut total = 0.0;
        for (start, end) in spans {
            assert!(
                end <= open_start + 1e-9 || start >= open_end - 1e-9,
                "Wall outline crosses door opening"
            );
            total += end - start;
        }
        near(total, l - door.width);
    }
}

#[test]
fn reflected_door_arcs_and_leaves_match_both_swing_directions() {
    // Hand-calculated closed and open endpoints for cardinal and 3-4-5 diagonal walls.
    let cases = [
        (
            Point::new(2000.0, 0.0),
            Point::new(500.0, 0.0),
            Point::new(1100.0, 0.0),
            Point::new(500.0, -600.0),
            Point::new(500.0, 600.0),
        ),
        (
            Point::new(0.0, 2000.0),
            Point::new(0.0, -500.0),
            Point::new(0.0, -1100.0),
            Point::new(-600.0, -500.0),
            Point::new(600.0, -500.0),
        ),
        (
            Point::new(1200.0, 1600.0),
            Point::new(300.0, -400.0),
            Point::new(660.0, -880.0),
            Point::new(-180.0, -760.0),
            Point::new(780.0, -40.0),
        ),
    ];
    for (end, hinge, closed, left, right) in cases {
        for swing in [Swing::Left, Swing::Right] {
            let mut d = Document::default();
            let layer = *d.layers.keys().next().unwrap();
            let wall = Wall {
                id: Id::new_v4(),
                name: "Test".into(),
                start: Point::new(0.0, 0.0),
                end,
                thickness: 100.0,
                layer,
            };
            let door = Door {
                id: Id::new_v4(),
                wall: wall.id,
                position: 800.0,
                width: 600.0,
                kind: house_core::DoorKind::Hinged,
                swing,
            };
            d.walls.insert(wall.id, wall);
            d.doors.insert(door.id, door.clone());
            let drawing = parsed(&d);
            let arc = drawing
                .entities()
                .find_map(|e| match &e.specific {
                    EntityType::Arc(a) if has_id(e, door.id) => Some(a),
                    _ => None,
                })
                .unwrap();
            near(arc.center.x, hinge.x);
            near(arc.center.y, hinge.y);
            near(arc.radius, 600.0);
            near((arc.end_angle - arc.start_angle).rem_euclid(360.0), 90.0);
            let endpoint = |degrees: f64| {
                Point::new(
                    arc.center.x + arc.radius * degrees.to_radians().cos(),
                    arc.center.y + arc.radius * degrees.to_radians().sin(),
                )
            };
            let open = if swing == Swing::Left { left } else { right };
            let (expected_start, expected_end) = if swing == Swing::Left {
                (open, closed)
            } else {
                (closed, open)
            };
            let (a, b) = (endpoint(arc.start_angle), endpoint(arc.end_angle));
            near(a.x, expected_start.x);
            near(a.y, expected_start.y);
            near(b.x, expected_end.x);
            near(b.y, expected_end.y);
            let leaf = drawing
                .entities()
                .find_map(|e| match &e.specific {
                    EntityType::Line(l) if has_id(e, door.id) => Some(l),
                    _ => None,
                })
                .unwrap();
            near(leaf.p1.x, hinge.x);
            near(leaf.p1.y, hinge.y);
            near(leaf.p2.x, open.x);
            near(leaf.p2.y, open.y);
        }
    }
}

#[test]
fn unicode_labels_and_hidden_layers_are_safe() {
    let mut d = bathroom();
    let room = d.rooms.values_mut().next().unwrap();
    room.name = "浴室\nRemodel 🚿".into();
    let expected = room.name.replace('\n', " ");
    let drawing = parsed(&d);
    assert!(
        drawing
            .entities()
            .any(|e| matches!(&e.specific,EntityType::Text(t) if t.value==expected))
    );
    for layer in d.layers.values_mut() {
        layer.visible = false;
    }
    let drawing = parsed(&d);
    assert!(
        drawing
            .entities()
            .all(|e| !matches!(e.specific, EntityType::LwPolyline(_) | EntityType::Arc(_)))
    );
}

#[test]
fn invalid_export_preserves_the_destination_file() {
    let path = std::env::temp_dir().join(format!("house-dxf-{}.dxf", Id::new_v4()));
    std::fs::write(&path, b"previous drawing").unwrap();
    let mut d = bathroom();
    d.walls.values_mut().next().unwrap().thickness = -1.0;
    assert!(export_dxf(&d, &path).is_err());
    assert_eq!(std::fs::read(&path).unwrap(), b"previous drawing");
    std::fs::remove_file(path).unwrap();
}

#[test]
fn table_headers_have_unique_handles_and_entities_are_opaque() {
    let bytes = dxf_bytes(&bathroom()).unwrap();
    let text = String::from_utf8(bytes.clone()).unwrap();
    let lines: Vec<_> = text.lines().collect();
    let pairs: Vec<_> = lines
        .as_chunks::<2>()
        .0
        .iter()
        .map(|p| (p[0].trim().parse::<i32>().unwrap(), p[1]))
        .collect();
    let mut handles = std::collections::BTreeSet::new();
    let mut seed = None;
    for (i, (code, value)) in pairs.iter().enumerate() {
        if *code == 5 || *code == 105 {
            let handle = u64::from_str_radix(value, 16).unwrap();
            if i > 0 && pairs[i - 1] == (9, "$HANDSEED") {
                seed = Some(handle);
                continue;
            }
            assert_ne!(handle, 0);
            assert!(handles.insert(handle), "Duplicate handle {value}");
        }
        if (*code, *value) == (0, "TABLE") {
            assert!(
                pairs[i + 2..]
                    .iter()
                    .take_while(|p| p.0 != 0)
                    .any(|p| p.0 == 5),
                "Missing symbol-table handle"
            );
        }
    }
    assert!(seed.unwrap() > *handles.last().unwrap());
    let drawing = Drawing::load(&mut Cursor::new(bytes)).unwrap();
    assert!(
        drawing
            .entities()
            .all(|e| e.common.transparency == 0x0200_00ff)
    );
}

#[test]
fn new_symbols_export_exact_rotated_coordinates_without_sliding_arcs() {
    let mut d = Document::default();
    let layer = *d.layers.keys().next().unwrap();
    let w = house_core::Wall {
        id: Id::new_v4(),
        name: "Host".into(),
        start: Point::new(0.0, 0.0),
        end: Point::new(4000.0, 3000.0),
        thickness: 100.0,
        layer,
    };
    d.walls.insert(w.id, w.clone());
    let door = house_core::Door {
        id: Id::new_v4(),
        wall: w.id,
        position: 3000.0,
        width: 1200.0,
        swing: Swing::Right,
        kind: house_core::DoorKind::SlidingGlass,
    };
    d.doors.insert(door.id, door.clone());
    let window = house_core::Window {
        id: Id::new_v4(),
        wall: w.id,
        position: 1000.0,
        width: 600.0,
    };
    d.windows.insert(window.id, window.clone());
    for kind in [
        house_core::FixtureKind::Bath,
        house_core::FixtureKind::Shower,
    ] {
        let f = house_core::Fixture {
            id: Id::new_v4(),
            kind,
            origin: Point::new(-1000.0, 500.0),
            width: 1524.0,
            depth: 762.0,
            rotation: 37.0,
            layer,
        };
        d.fixtures.insert(f.id, f);
    }
    let bytes = dxf_bytes(&d).unwrap();
    let drawing = dxf::Drawing::load(&mut bytes.as_slice()).unwrap();
    assert!(
        !drawing
            .entities()
            .any(|e| matches!(e.specific, dxf::entities::EntityType::Arc(_)))
    );
    for symbol in house_geometry::plan_symbols(&d) {
        let lines: Vec<_> = drawing
            .entities()
            .filter(|e| {
                e.common.x_data.iter().any(|data| {
                    data.items
                        .contains(&dxf::XDataItem::Str(symbol.id.to_string()))
                })
            })
            .map(|e| match &e.specific {
                dxf::entities::EntityType::Line(l) => l,
                _ => panic!("Expected symbol line"),
            })
            .collect();
        assert_eq!(lines.len(), symbol.lines.len());
        for (actual, (a, b)) in lines.iter().zip(symbol.lines) {
            for (actual, expected) in [
                (actual.p1.x, a.x),
                (actual.p1.y, -a.y),
                (actual.p2.x, b.x),
                (actual.p2.y, -b.y),
            ] {
                assert!((actual - expected).abs() < 1e-9);
            }
        }
    }
    d.layers.get_mut(&layer).unwrap().visible = false;
    let bytes = dxf_bytes(&d).unwrap();
    let hidden = dxf::Drawing::load(&mut bytes.as_slice()).unwrap();
    assert_eq!(hidden.entities().count(), 0);
}
